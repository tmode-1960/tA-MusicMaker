"""Voice swap and RVC pipeline integration for tA-MusicMaker.

Uses local Applio runtime, UVR stem separation, pure RVC inference, and FFmpeg 9+ mastering limiter mix.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


def get_applio_paths() -> dict:
    applio_dir = os.environ.get("APPLIO_PATH") or os.path.expanduser(r"~\AppData\Local\Applio")
    python_exe = os.path.join(applio_dir, "data", "runtime", ".venv", "Scripts", "python.exe")
    core_py = os.path.join(applio_dir, "data", "runtime", "core.py")
    backend_dir = os.path.join(applio_dir, "app", "backend", "applio")
    runtime_dir = os.path.join(applio_dir, "data", "runtime")
    # Prefer modern system ffmpeg (v9.0.1 supports amix normalize=0 + alimiter)
    ffmpeg_exe = shutil.which("ffmpeg") or os.path.join(runtime_dir, "ffmpeg.exe")
    if not os.path.isfile(ffmpeg_exe):
        ffmpeg_exe = "ffmpeg"
    logs_dir = os.path.join(runtime_dir, "logs")

    available = os.path.isfile(python_exe) and os.path.isdir(backend_dir)
    return {
        "applio_dir": applio_dir,
        "python_exe": python_exe,
        "core_py": core_py,
        "backend_dir": backend_dir,
        "runtime_dir": runtime_dir,
        "ffmpeg_exe": ffmpeg_exe,
        "logs_dir": logs_dir,
        "available": available,
    }


def _scan_directory_for_models(base_dir: str) -> list[dict]:
    if not os.path.isdir(base_dir):
        return []
    models = []
    seen_ids = set()

    def _epoch_key(item):
        m = re.search(r"(\d+)e_", item.name)
        return int(m.group(1)) if m else 0

    try:
        entries = list(os.scandir(base_dir))
    except OSError:
        return []

    # 1. Scan subdirectories (standard Applio / RVC model folder layout)
    for entry in entries:
        if not entry.is_dir():
            continue
        folder_name = entry.name
        try:
            sub_entries = list(os.scandir(entry.path))
        except OSError:
            continue
        pth_files = [
            f for f in sub_entries
            if f.name.endswith(".pth") and not f.name.startswith(("G_", "D_"))
        ]
        if not pth_files:
            continue

        best_pth = max(pth_files, key=_epoch_key)
        index_files = [f for f in sub_entries if f.name.endswith(".index")]
        best_index = index_files[0].path if index_files else ""

        epochs = _epoch_key(best_pth)
        display_name = f"{folder_name} ({epochs} Epochen)" if epochs else folder_name

        seen_ids.add(folder_name.lower())
        models.append({
            "id": folder_name,
            "name": folder_name,
            "display_name": display_name,
            "pth_path": best_pth.path,
            "pth_filename": best_pth.name,
            "index_path": best_index,
            "epochs": epochs,
        })

    # 2. Also scan loose .pth files directly in base_dir
    index_files = [f for f in entries if f.is_file() and f.name.endswith(".index")]
    for f in entries:
        if not f.is_file() or not f.name.endswith(".pth") or f.name.startswith(("G_", "D_")):
            continue
        model_name = os.path.splitext(f.name)[0]
        if model_name.lower() in seen_ids:
            continue

        best_index = ""
        for idx in index_files:
            idx_base = os.path.splitext(idx.name)[0]
            if idx_base.lower() == model_name.lower() or model_name.lower() in idx_base.lower():
                best_index = idx.path
                break
        if not best_index and len(index_files) == 1:
            best_index = index_files[0].path

        epochs = _epoch_key(f)
        display_name = f"{model_name} ({epochs} Epochen)" if epochs else model_name

        seen_ids.add(model_name.lower())
        models.append({
            "id": model_name,
            "name": model_name,
            "display_name": display_name,
            "pth_path": f.path,
            "pth_filename": f.name,
            "index_path": best_index,
            "epochs": epochs,
        })

    return models


def list_voice_models(models_dir: str | None = None) -> list[dict]:
    paths = get_applio_paths()
    custom_dir = os.path.abspath(os.path.expanduser(models_dir.strip())) if models_dir and models_dir.strip() else None

    models = []
    seen_ids = set()

    if custom_dir and os.path.isdir(custom_dir):
        for m in _scan_directory_for_models(custom_dir):
            if m["id"].lower() not in seen_ids:
                seen_ids.add(m["id"].lower())
                models.append(m)

    # If no custom directory given, or custom directory has no models, check default Applio logs directory
    default_logs = paths["logs_dir"]
    if not models and os.path.isdir(default_logs):
        for m in _scan_directory_for_models(default_logs):
            if m["id"].lower() not in seen_ids:
                seen_ids.add(m["id"].lower())
                models.append(m)

    models.sort(key=lambda m: m["name"].lower())
    return models


def _find_matching_stems(output_dir: str, song_base: str) -> tuple[str | None, str | None]:
    """Find the vocal and instrumental stems belonging specifically to ``song_base``."""
    if not os.path.isdir(output_dir):
        return None, None
    prefix = song_base.lower()
    vocals_file = None
    instrumental_file = None
    for f in os.scandir(output_dir):
        fname = f.name.lower()
        if not fname.endswith((".wav", ".flac")):
            continue
        if not fname.startswith(prefix):
            continue
        if "(instrumental)" in fname or "_instrumental" in fname or "karaoke" in fname:
            instrumental_file = f.path
        elif "(vocals)" in fname or "_vocals" in fname:
            vocals_file = f.path
    return vocals_file, instrumental_file


def run_uvr_separation(song_path: str, output_dir: str, device: str = "auto") -> tuple[str, str]:
    """Separate song into vocals and instrumental using Applio UVR."""
    paths = get_applio_paths()
    if not paths["available"]:
        raise RuntimeError("Applio installation not found.")

    os.makedirs(output_dir, exist_ok=True)
    song_base = os.path.splitext(os.path.basename(song_path))[0]

    vocals_file, instrumental_file = _find_matching_stems(output_dir, song_base)
    if (
        vocals_file
        and instrumental_file
        and os.path.getsize(vocals_file) > 1024
        and os.path.getsize(instrumental_file) > 1024
    ):
        return vocals_file, instrumental_file

    env = os.environ.copy()
    env["APPLIO_BACKEND_ROOT"] = paths["backend_dir"]
    env["PYTHONPATH"] = paths["backend_dir"]

    cmd = [
        paths["python_exe"],
        paths["core_py"],
        "uvr",
        "--input-path", os.path.abspath(song_path),
        "--model", "vr-vocals-hp4",
        "--output-dir", os.path.abspath(output_dir),
        "--output-format", "wav",
        "--device", device,
    ]

    res = subprocess.run(cmd, env=env, cwd=paths["runtime_dir"], capture_output=True, text=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if res.returncode != 0:
        raise RuntimeError(f"UVR separation failed: {res.stderr or res.stdout}")

    vocals_file, instrumental_file = _find_matching_stems(output_dir, song_base)
    if not vocals_file:
        raise RuntimeError(f"UVR did not generate a vocal stem for '{song_base}'.")
    if not instrumental_file:
        raise RuntimeError(f"UVR did not generate an instrumental stem for '{song_base}'.")

    return vocals_file, instrumental_file


def run_voice_conversion(
    vocal_in: str,
    vocal_out: str,
    model_pth: str,
    index_file: str,
    pitch: int = 0,
    index_rate: float = 0.75,
    f0_method: str = "rmvpe",
) -> str:
    """Run pure RVC Voice Conversion on vocals and normalize output peak to -1.5 dBFS (0.84)."""
    paths = get_applio_paths()
    if not paths["available"]:
        raise RuntimeError("Applio installation not found.")

    os.makedirs(os.path.dirname(os.path.abspath(vocal_out)), exist_ok=True)

    worker_code = f"""
import os, sys, numpy as np, soundfile as sf
runtime_dir = r"{paths['runtime_dir']}"
app_backend = r"{paths['backend_dir']}"
sys.path.insert(0, app_backend)
os.chdir(runtime_dir)

from rvc.infer.infer import VoiceConverter
vc = VoiceConverter()

out_p = r"{os.path.abspath(vocal_out)}"
vc.convert_audio(
    audio_input_path=r"{os.path.abspath(vocal_in)}",
    audio_output_path=out_p,
    model_path=r"{os.path.abspath(model_pth)}",
    index_path=r"{os.path.abspath(index_file)}" if r"{index_file}" else "",
    pitch={int(pitch)},
    index_rate={float(index_rate)},
    f0_method="{f0_method}",
    export_format="WAV"
)

# Normalize pure RVC vocal peak to -1.5 dBFS (0.84) with a single constant gain factor
# (Because thomas_voice training slices were recorded at -9.7 dB peak, raw RVC output sits at -8.5 dB peak)
y, sr = sf.read(out_p, dtype="float32")
peak = float(np.max(np.abs(y)))
if peak > 1e-4:
    y = y * (0.84 / peak)
    sf.write(out_p, y, sr, subtype="PCM_24")
"""
    cmd = [paths["python_exe"], "-c", worker_code]
    res = subprocess.run(cmd, cwd=paths["runtime_dir"], capture_output=True, text=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if res.returncode != 0:
        raise RuntimeError(f"Voice conversion failed: {res.stderr or res.stdout}")

    if not os.path.isfile(vocal_out):
        raise RuntimeError("Voice conversion completed without creating the output file.")

    return vocal_out


def copy_plenio_flac_metadata(src_flac_path: str, dst_flac_path: str) -> bool:
    """Copy the embedded Plenio project block (`PLNO`) from src_flac to dst_flac if present."""
    try:
        src = Path(src_flac_path)
        dst = Path(dst_flac_path)
        if not src.is_file() or not dst.is_file():
            return False
        s_bytes = src.read_bytes()
        d_bytes = dst.read_bytes()
        if s_bytes[:4] != b"fLaC" or d_bytes[:4] != b"fLaC":
            return False

        def parse_blocks(data: bytes):
            blocks = []
            idx = 4
            while idx + 4 <= len(data):
                hdr = data[idx]
                length = int.from_bytes(data[idx + 1 : idx + 4], "big")
                if idx + 4 + length > len(data):
                    break
                blocks.append((hdr & 0x7F, data[idx + 4 : idx + 4 + length]))
                idx += 4 + length
                if hdr & 0x80:
                    return blocks, idx
            return blocks, idx

        s_blocks, _ = parse_blocks(s_bytes)
        plno_body = next((b for k, b in s_blocks if k == 2 and b[:4] == b"PLNO"), None)
        if not plno_body:
            return False

        d_blocks, d_start = parse_blocks(d_bytes)
        d_kept = [(k, b) for k, b in d_blocks if not (k == 2 and b[:4] == b"PLNO")]
        d_kept.append((2, plno_body))

        out = [b"fLaC"]
        for i, (kind, body) in enumerate(d_kept):
            last = 0x80 if i == len(d_kept) - 1 else 0
            out.append(bytes([last | kind]) + len(body).to_bytes(3, "big") + body)
        out.append(d_bytes[d_start:])
        dst.write_bytes(b"".join(out))
        return True
    except Exception:
        return False


def mix_tracks(
    instrumental_path: str,
    vocal_path: str,
    final_output_path: str,
    orig_vocal_path: str | None = None,
    orig_song_path: str | None = None,
    vocal_gain: float = 1.15,
    inst_gain: float = 1.0,
) -> str:
    """Mix vocal and instrumental tracks together using FFmpeg 9+ without auto-normalization ducking."""
    paths = get_applio_paths()
    ffmpeg = paths["ffmpeg_exe"]
    os.makedirs(os.path.dirname(os.path.abspath(final_output_path)), exist_ok=True)

    if not instrumental_path or not os.path.isfile(instrumental_path):
        cmd = [ffmpeg, "-y", "-i", vocal_path, final_output_path]
    else:
        filt = (
            f"[0:a]volume={inst_gain:.2f}[a0];"
            f"[1:a]volume={vocal_gain:.2f}[a1];"
            f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
            f"alimiter=limit=0.98:attack=5:release=50:level=disabled"
        )
        cmd = [
            ffmpeg, "-y",
            "-i", os.path.abspath(instrumental_path),
            "-i", os.path.abspath(vocal_path),
            "-filter_complex", filt,
            os.path.abspath(final_output_path),
        ]

    res = subprocess.run(cmd, capture_output=True, text=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg mixing failed: {res.stderr or res.stdout}")

    if orig_song_path and final_output_path.lower().endswith(".flac"):
        copy_plenio_flac_metadata(orig_song_path, final_output_path)

    return final_output_path


def voice_swap_pipeline(
    song_input_path: str,
    output_dir: str,
    model_name: str | None = None,
    pitch: int = 0,
    index_rate: float = 0.75,
    existing_vocal_stem: str | None = None,
    existing_instrumental_stem: str | None = None,
    status_cb=None,
    models_dir: str | None = None,
) -> dict:
    """End-to-end voice swap on a song."""
    os.makedirs(output_dir, exist_ok=True)
    models = list_voice_models(models_dir)
    if not models:
        raise RuntimeError("No trained voice models found.")

    selected_model = None
    if model_name:
        selected_model = next((m for m in models if m["id"] == model_name or m["name"] == model_name), None)
    if not selected_model and model_name and os.path.isfile(model_name) and model_name.endswith(".pth"):
        base_no_ext = os.path.splitext(model_name)[0]
        idx = base_no_ext + ".index"
        selected_model = {
            "id": os.path.basename(base_no_ext),
            "name": os.path.basename(base_no_ext),
            "display_name": os.path.basename(base_no_ext),
            "pth_path": model_name,
            "pth_filename": os.path.basename(model_name),
            "index_path": idx if os.path.isfile(idx) else "",
            "epochs": 0,
        }
    if not selected_model and models:
        selected_model = models[0]

    base_name = os.path.splitext(os.path.basename(song_input_path))[0]
    out_prefix = os.path.join(output_dir, f"{base_name}_{selected_model['name']}")

    vocals_file = existing_vocal_stem
    inst_file = existing_instrumental_stem

    if not vocals_file or not os.path.isfile(vocals_file):
        if status_cb:
            status_cb("phase.separating_stems", 0.15)
        sep_dir = os.path.join(output_dir, "uvr_stems")
        vocals_file, inst_file = run_uvr_separation(song_input_path, sep_dir)

    if status_cb:
        status_cb("phase.converting_voice", 0.55)
    rvc_vocal_path = f"{out_prefix}_vocal_rvc.wav"
    run_voice_conversion(
        vocal_in=vocals_file,
        vocal_out=rvc_vocal_path,
        model_pth=selected_model["pth_path"],
        index_file=selected_model["index_path"],
        pitch=pitch,
        index_rate=index_rate,
    )

    if status_cb:
        status_cb("phase.mixing_song", 0.85)
    final_song_path = f"{out_prefix}_final.flac"
    mix_tracks(
        instrumental_path=inst_file,
        vocal_path=rvc_vocal_path,
        final_output_path=final_song_path,
        orig_vocal_path=vocals_file,
        orig_song_path=song_input_path,
    )

    if status_cb:
        status_cb("phase.done", 1.0)

    return {
        "final_song": final_song_path,
        "vocals_rvc": rvc_vocal_path,
        "instrumental": inst_file,
        "vocals_orig": vocals_file,
        "model": selected_model["name"],
    }
