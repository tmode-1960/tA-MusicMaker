"""tA-MusicMaker - a local Windows desktop front end for the Plenio YuE2 song workflow.

Runs a small local web server (stdlib only), opens it in an app-style window and talks to a
ComfyUI instance in the background. The UI form is turned into the ComfyUI workflow
(YuE2-Song.json) on every run.

Usage:  python server.py [--no-window] [--port 8765]
"""

from __future__ import annotations

import argparse
import importlib
import json
import mimetypes
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from typing import Any
import urllib.parse
import urllib.request
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from comfy_client import ComfyClient, ComfyError
from workflow_converter import ConversionError, WorkflowConverter, load_workflow
import srt_translate
import voice_swap

APP_VERSION = "1.08"
IS_FROZEN = getattr(sys, "frozen", False)
BUNDLE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.dirname(os.path.abspath(sys.executable)) if IS_FROZEN else os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BUNDLE_DIR, "web") if os.path.isdir(os.path.join(BUNDLE_DIR, "web")) else os.path.join(APP_DIR, "web")


def _resolve_data_dir() -> str:
    local_data = os.path.join(APP_DIR, "data")
    try:
        os.makedirs(os.path.join(local_data, "renders"), exist_ok=True)
        probe = os.path.join(local_data, ".write_test")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe)
        return local_data
    except OSError:
        appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        fallback = os.path.join(appdata, "tA-MusicMaker", "data")
        os.makedirs(os.path.join(fallback, "renders"), exist_ok=True)
        return fallback


DATA_DIR = _resolve_data_dir()
RENDERS_DIR = os.path.join(DATA_DIR, "renders")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
HISTORY_PATH = os.path.join(DATA_DIR, "history.json")
LAST_SETTINGS_PATH = os.path.join(DATA_DIR, "last_settings.json")


def _resolve_templates_path() -> str:
    for c in (
        os.path.join(DATA_DIR, "plenio_templates.json"),
        os.path.join(APP_DIR, "data", "plenio_templates.json"),
        os.path.join(BUNDLE_DIR, "data", "plenio_templates.json"),
    ):
        if os.path.isfile(c):
            return c
    return os.path.join(DATA_DIR, "plenio_templates.json")


PLENIO_TEMPLATES_PATH = _resolve_templates_path()

if sys.stdout is None or sys.stderr is None:
    _log_fh = open(os.path.join(DATA_DIR, "app.log"), "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = _log_fh
    if sys.stderr is None:
        sys.stderr = _log_fh

DEFAULT_CONFIG = {
    "comfy_url": "http://127.0.0.1:8188",
    "workflow": "YuE2-Song.json",
    "comfy_dir": "",
    "comfy_start_command": "",
    "voice_models_dir": "",
    "theme": "dark",
    "language": "en",
}

# Node ids in YuE2-Song.json (top level defaults, updated dynamically if v1.3+ detected)
N_BRIEF, N_DRAFT_SEED, N_SHEET_TEXT, N_SHEET_SCORE, N_TAKE_SEED = 2, 5, 7, 13, 14
N_WRITER, N_PREVIEW, N_EXPORT = 4, 18, 19
N_PLAN = 8
N_WRITER_MODEL = 6
N_BEST_TAKE = 16
N_MASTER, N_MASTER_EQ, N_MASTER_LOUDNESS = 17, "17:405", "17:406"
N_COVER, N_COVER_PREVIEW, N_COVER_SEED = 21, 22, 23
N_HQ_MASTERING = 24
N_REFINE_MODEL, N_REFINE, N_STEMS = 13, 14, 1107
SHEET_KINDS = ("title", "style", "lyrics", "artwork_prompt")
EMPTY_SHEET_STATE = json.dumps({"schema": "plenio.sheet_state/1", "docs": {}}, separators=(",", ":"))
MODE_REVIEW, MODE_AUTO = "one song, stop to review", "new song every run"

PHASES = [
    ("3:", "phase.model"), ("4:", "phase.write"), ("7:", "phase.plan"), ("8:", "phase.plan"),
    ("11:", "phase.arrange"), ("15:", "phase.render"), ("16", "phase.best_take"), ("17:", "phase.master"),
    ("18", "phase.preview"), ("19", "phase.export"), ("21:", "phase.cover"),
    ("1107:", "phase.stems"), ("13", "phase.refine"), ("14", "phase.refine"),
    ("hq_stereo", "phase.master"), ("hq_sr_model", "phase.model"), ("hq_regen", "phase.refine"), ("hq_dereverb", "phase.master"),
]
AUDIO_EXT = {".flac", ".mp3", ".wav", ".ogg", ".opus", ".m4a"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}

_lock = threading.Lock()
JOBS: dict[str, dict] = {}
STATE = {"config": dict(DEFAULT_CONFIG), "last_ping": time.time(), "had_ping": False}


# ----------------------------------------------------------------- config / data

def load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def config() -> dict:
    return STATE["config"]


def _tr(en: str, de: str) -> str:
    return de if config().get("language") == "de" else en


def client() -> ComfyClient:
    return ComfyClient(config()["comfy_url"])


def workflow_path() -> str:
    path = config()["workflow"]
    if os.path.isabs(path):
        return path
    candidate = os.path.join(APP_DIR, path)
    if os.path.isfile(candidate):
        return candidate
    return os.path.join(BUNDLE_DIR, path)


def converter() -> WorkflowConverter:
    return WorkflowConverter(load_workflow(workflow_path()))


def get_workflow_nodes(conv: WorkflowConverter) -> dict[str, Any]:
    nodes = conv.top.nodes
    res = {
        "brief": 2, "draft_seed": 5, "writer": 4, "writer_model": 6,
        "sheet_text": 7, "plan": 8, "plan_seed": 9, "arrange": 11,
        "sheet_score": 13, "take_seed": 14, "render": 15, "best_take": 16,
        "master": 17, "master_eq": "17:405", "master_loudness": "17:406",
        "preview": 18, "export": 19, "cover": 21, "cover_preview": 22,
        "cover_seed": 23, "hq_mastering": 24, "loras": 25, "refine": 14, "refine_model": 13, "stems": 1107,
    }
    # Fallback to older 19-node layout if present
    if 19 not in nodes and 17 in nodes:
        res.update({
            "sheet_text": 6, "plan": 7, "sheet_score": 9, "take_seed": 10,
            "master": 15, "master_eq": "15:401", "master_loudness": "15:402",
            "preview": 16, "export": 17, "cover": 18, "cover_preview": 19,
        })
    for nid, node in nodes.items():
        ntype = str(node.get("type", ""))
        title = str(node.get("title", "")).lower()
        if ntype == "PlenioSongBrief":
            res["brief"] = nid
        elif ntype == "PlenioExportRelease":
            res["export"] = nid
        elif ntype == "PreviewAudio":
            res["preview"] = nid
        elif ntype == "PlenioBestTake":
            res["best_take"] = nid
        elif ntype == "PlenioWriterChoice":
            res["writer_model"] = nid
        elif ntype == "PlenioHQMastering":
            res["hq_mastering"] = nid
        elif ntype == "PlenioLoras":
            res["loras"] = nid
        elif ntype == "PlenioSongSheet":
            if "score" in title:
                res["sheet_score"] = nid
            else:
                res["sheet_text"] = nid
        elif ntype in ("PlenioSeed", "SeedNode"):
            part = str(node.get("properties", {}).get("plenio_part", "")).lower()
            if "take" in part or "take" in title:
                res["take_seed"] = nid
            elif "draft" in part or "draft" in title:
                res["draft_seed"] = nid
            elif "plan" in part or "plan" in title:
                res["plan_seed"] = nid
            elif "cover" in part or "cover" in title:
                res["cover_seed"] = nid
    m_id = res["master"]
    if m_id == 15:
        res["master_eq"] = "15:401"
        res["master_loudness"] = "15:402"
    elif m_id == 17:
        res["master_eq"] = "17:405"
        res["master_loudness"] = "17:406"
    return res


# ------------------------------------------------------------------ defaults

def workflow_defaults() -> dict:
    conv = converter()
    wn = get_workflow_nodes(conv)
    brief = conv.widget_defaults(wn["brief"])
    brief.setdefault("creativity", 100)
    export = conv.widget_defaults(wn["export"])
    sheet = conv.widget_defaults(wn["sheet_text"])
    cover = conv.widget_defaults(wn["cover"])
    raw_writer = None
    if wn.get("writer_model") and wn["writer_model"] in conv.top.nodes:
        raw_writer = conv.widget_defaults(wn["writer_model"]).get("model")
    if not raw_writer and wn.get("writer") and wn["writer"] in conv.top.nodes:
        raw_writer = conv.widget_defaults(wn["writer"]).get("clip_name")
    writer_model = resolve_model_field_value("CLIPLoader", "clip_name", raw_writer)
    return {
        "brief": brief,
        "draft_seed": conv.widget_defaults(wn["draft_seed"]).get("seed"),
        "export": {k: export.get(k) for k in ("folder", "naming", "collision", "flac", "mp3", "wav", "tags",
                                              "sheet_music", "sheet_music_size", "project_in_flac", "lyrics_srt",
                                              "lyrics_timing", "song_page")},
        "cover_size": cover.get("size", 1024),
        "writer_model": writer_model,
        "review": sheet.get("review"),
    }


DEFAULT_BRIEF_OPTIONS: dict[str, list[str]] = {
    "mode": [
        "new song every run",
        "one song, stop to review",
    ],
    "length": [
        "very short (about 1:00)",
        "short (about 1:30)",
        "about 2:00",
        "about 2:30",
        "standard (about 3:00)",
        "about 3:30",
        "about 4:00",
        "long (about 4:30)",
        "about 5:00",
        "very long (about 6:00)",
    ],
    "vocals": [
        "sung",
        "sparse vocals",
        "instrumental",
    ],
    "vocals.lyrics_from": [
        "written from the idea below",
        "my own, sung as written below",
    ],
    "lyrics_fidelity": [
        "standard",
        "high - best of 2 takes",
        "highest - best of 3 takes",
    ],
    "arrangement": [
        "off",
        "standard",
        "sterile",
        "unplugged",
        "varied",
        "call and response",
        "signature motif",
        "hypnotic",
        "breakdown",
        "dramatic",
        "many instruments",
        "jazz colours",
        "fantasy",
        "key change",
    ],
}


def brief_options() -> dict:
    """Option lists for the brief's combo fields, read live from ComfyUI with offline fallbacks."""
    result: dict = {k: list(v) for k, v in DEFAULT_BRIEF_OPTIONS.items()}
    try:
        info = client().object_info("PlenioSongBrief").get("PlenioSongBrief", {})
    except ComfyError:
        info = {}
    inputs = info.get("input", {})
    if inputs:
        result["_live"] = True
    for section in ("required", "optional"):
        for name, spec in (inputs.get(section) or {}).items():
            opts = _extract_options(spec)
            if opts:
                result[name] = opts
    try:
        sr_info = client().object_info("PlenioAudioModelLoader").get("PlenioAudioModelLoader", {})
        kind_spec = (sr_info.get("input", {}).get("required") or {}).get("kind")
        if isinstance(kind_spec, list) and len(kind_spec) > 1 and isinstance(kind_spec[1], dict):
            for opt_entry in kind_spec[1].get("options") or []:
                if isinstance(opt_entry, dict) and opt_entry.get("key") == "super-resolution":
                    m_spec = (opt_entry.get("inputs", {}).get("required") or {}).get("model")
                    sr_opts = _extract_options(m_spec)
                    if sr_opts is not None:
                        result["_audio_sr_models"] = sr_opts
    except Exception:
        pass
    if "template" not in result or not result["template"]:
        if os.path.isfile(PLENIO_TEMPLATES_PATH):
            try:
                tmpls = load_json(PLENIO_TEMPLATES_PATH, {})
                if tmpls:
                    result["template"] = ["none"] + sorted(tmpls.keys())
            except Exception:
                pass
    return result


def _extract_options(spec):
    if not isinstance(spec, list) or not spec:
        return None
    head = spec[0]
    if isinstance(head, list):
        return [o for o in head if isinstance(o, (str, int, float))]
    if isinstance(spec[1:], list) and spec[1:] and isinstance(spec[1], dict):
        options = spec[1].get("options")
        if isinstance(options, list):
            out = []
            for o in options:
                if isinstance(o, dict) and "key" in o:
                    out.append(o["key"])
                elif isinstance(o, (str, int, float)):
                    out.append(o)
            return out
    return None


_OBJECT_INFO_CACHE: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 30.0


def get_object_info(class_type: str) -> dict:
    now = time.time()
    if class_type in _OBJECT_INFO_CACHE:
        cached_time, cached_val = _OBJECT_INFO_CACHE[class_type]
        if now - cached_time < CACHE_TTL:
            return cached_val
    try:
        info = client().object_info(class_type).get(class_type, {})
        _OBJECT_INFO_CACHE[class_type] = (now, info)
        return info
    except Exception:
        if class_type in _OBJECT_INFO_CACHE:
            return _OBJECT_INFO_CACHE[class_type][1]
        return {}


def get_field_choices(class_type: str, field_name: str, node_inputs: dict | None = None) -> list[str] | None:
    info = get_object_info(class_type)
    if not info:
        return None

    req = info.get("input", {}).get("required", {})
    opt = info.get("input", {}).get("optional", {})
    spec = req.get(field_name) or opt.get(field_name)
    opts = _extract_options(spec)
    if opts is None and "." in field_name:
        parent, child = field_name.split(".", 1)
        p_spec = req.get(parent) or opt.get(parent)
        parent_val = node_inputs.get(parent) if isinstance(node_inputs, dict) else None
        if isinstance(p_spec, list) and len(p_spec) > 1 and isinstance(p_spec[1], dict):
            sub_opts: list = []
            matched_parent = False
            for o_entry in p_spec[1].get("options") or []:
                if isinstance(o_entry, dict):
                    if parent_val is not None and o_entry.get("key") != parent_val:
                        continue
                    c_spec = (o_entry.get("inputs", {}).get("required") or {}).get(child)
                    extracted = _extract_options(c_spec)
                    if extracted is not None:
                        matched_parent = True
                        sub_opts.extend(extracted)
            if matched_parent:
                opts = sub_opts
    if opts is None:
        return None
    return [str(x) for x in opts]


def _match_choice(choices: list[str], current_val: str) -> str | None:
    if not choices:
        return None

    # 1. Exact match
    if current_val in choices:
        return current_val

    norm_cur = current_val.replace("\\", "/").strip()
    norm_cur_lower = norm_cur.lower()
    base_cur = norm_cur.split("/")[-1]
    base_cur_lower = base_cur.lower()

    # 2. Path match ignoring slash direction and case
    for ch in choices:
        norm_ch = ch.replace("\\", "/").strip()
        if norm_ch.lower() == norm_cur_lower:
            return ch

    # 3. Match candidate ending with current_val
    for ch in choices:
        norm_ch = ch.replace("\\", "/").strip()
        if norm_ch.lower().endswith("/" + norm_cur_lower):
            return ch

    # 4. Basename exact match (case-sensitive)
    base_matches = []
    for ch in choices:
        norm_ch = ch.replace("\\", "/").strip()
        if norm_ch.split("/")[-1] == base_cur:
            base_matches.append(ch)

    if base_matches:
        cur_parts = norm_cur.split("/")
        if len(cur_parts) > 1:
            parent = cur_parts[-2].lower()
            for bm in base_matches:
                bm_norm = bm.replace("\\", "/").strip().lower()
                if f"/{parent}/" in f"/{bm_norm}":
                    return bm
        return base_matches[0]

    # 5. Basename case-insensitive match
    base_matches_ci = []
    for ch in choices:
        norm_ch = ch.replace("\\", "/").strip()
        if norm_ch.split("/")[-1].lower() == base_cur_lower:
            base_matches_ci.append(ch)

    if base_matches_ci:
        cur_parts = norm_cur.split("/")
        if len(cur_parts) > 1:
            parent = cur_parts[-2].lower()
            for bm in base_matches_ci:
                bm_norm = bm.replace("\\", "/").strip().lower()
                if f"/{parent}/" in f"/{bm_norm}":
                    return bm
        return base_matches_ci[0]

    return None


def resolve_model_field_value(class_type: str, field_name: str, current_val: Any,
                              node_inputs: dict | None = None) -> Any:
    if not isinstance(current_val, str) or not current_val:
        return current_val
    choices = get_field_choices(class_type, field_name, node_inputs)
    if not choices:
        return current_val
    matched = _match_choice(choices, current_val)
    return matched if matched is not None else current_val


def resolve_prompt_models(prompt: dict) -> dict:
    """Inspects all nodes in the API prompt and resolves any model paths to the exact
    path format registered in the active ComfyUI instance (e.g. root vs subfolders)."""
    try:
        for node_id, node_data in prompt.items():
            if not isinstance(node_data, dict):
                continue
            class_type = node_data.get("class_type")
            inputs = node_data.get("inputs")
            if not class_type or not isinstance(inputs, dict):
                continue
            for field_name, val in list(inputs.items()):
                if isinstance(val, str) and val.strip():
                    new_val = resolve_model_field_value(class_type, field_name, val, inputs)
                    if new_val != val:
                        print(f"[Model Resolver] Node {node_id} ({class_type}.{field_name}): '{val}' -> '{new_val}'")
                        inputs[field_name] = new_val
    except Exception as ex:
        print(f"[Model Resolver] Warning during model resolution: {ex}")
    return prompt


KNOWN_MODELS: dict[str, dict[str, str]] = {
    "pytorch_model.bin": {
        "name": "pytorch_model.bin",
        "url": "https://huggingface.co/woongzip1/universr-audio/resolve/main/pytorch_model.bin",
        "directory": "audio_sr",
    },
    "model_bs_roformer_ep_17_sdr_9.6568.ckpt": {
        "name": "model_bs_roformer_ep_17_sdr_9.6568.ckpt",
        "url": "https://github.com/ZFTurbo/Music-Source-Separation-Training/releases/download/v1.0.12/model_bs_roformer_ep_17_sdr_9.6568.ckpt",
        "directory": "audio_separation",
    },
    "yue2_3b_int8_convrot.safetensors": {
        "name": "yue2_3b_int8_convrot.safetensors",
        "url": "https://huggingface.co/Comfy-Org/YuE2/resolve/main/checkpoints/yue2_3b_int8_convrot.safetensors",
        "directory": "checkpoints",
    },
    "ar_lora_inst_v3abc_comfyui.safetensors": {
        "name": "ar_lora_inst_v3abc_comfyui.safetensors",
        "url": "https://huggingface.co/Mothersuperior/YuE2-instrumental-cot-full-loras/resolve/947f2f4b28978b2b6c3e316e6a87925c76bf3c4b/ar_lora_inst_v3abc_comfyui.safetensors",
        "directory": "loras",
    },
    "gemma4_e4b_it_fp8_scaled.safetensors": {
        "name": "gemma4_e4b_it_fp8_scaled.safetensors",
        "url": "https://huggingface.co/Comfy-Org/gemma-4/resolve/main/text_encoders/gemma4_e4b_it_fp8_scaled.safetensors",
        "directory": "text_encoders",
    },
    "flux-2-klein-4b.safetensors": {
        "name": "flux-2-klein-4b.safetensors",
        "url": "https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/diffusion_models/flux-2-klein-4b.safetensors",
        "directory": "diffusion_models",
    },
    "qwen_3_4b.safetensors": {
        "name": "qwen_3_4b.safetensors",
        "url": "https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors",
        "directory": "text_encoders",
    },
    "flux2-vae.safetensors": {
        "name": "flux2-vae.safetensors",
        "url": "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors",
        "directory": "vae",
    },
}


def get_known_models() -> dict[str, dict[str, str]]:
    out = {k.lower(): dict(v) for k, v in KNOWN_MODELS.items()}
    try:
        wf = converter().workflow
        all_nodes = list(wf.get("nodes") or [])
        for sub in (wf.get("definitions", {}).get("subgraphs") or []):
            if isinstance(sub, dict):
                all_nodes.extend(sub.get("nodes") or [])
        for n in all_nodes:
            if not isinstance(n, dict):
                continue
            for m in (n.get("properties", {}).get("models") or []):
                if isinstance(m, dict) and m.get("name") and m.get("url") and m.get("directory"):
                    base = str(m["name"]).replace("\\", "/").strip().split("/")[-1]
                    out[base.lower()] = {
                        "name": base,
                        "url": str(m["url"]).strip(),
                        "directory": str(m["directory"]).strip(),
                    }
    except Exception:
        pass
    return out


_WSL_DISTROS_CACHE: list[str] | None = None


def _get_wsl_distros() -> list[str]:
    global _WSL_DISTROS_CACHE
    if _WSL_DISTROS_CACHE is not None:
        return _WSL_DISTROS_CACHE
    if os.name != "nt":
        _WSL_DISTROS_CACHE = []
        return _WSL_DISTROS_CACHE
    try:
        flags = 0x08000000  # CREATE_NO_WINDOW
        res = subprocess.run(["wsl", "-l", "-q"], capture_output=True, timeout=5, creationflags=flags)
        raw = res.stdout.replace(b"\x00", b"").decode("utf-8", errors="ignore")
        _WSL_DISTROS_CACHE = [line.strip() for line in raw.splitlines() if line.strip()]
    except Exception:
        _WSL_DISTROS_CACHE = []
    return _WSL_DISTROS_CACHE


def _to_local_windows_path(raw_path: str) -> str | None:
    if not raw_path or not isinstance(raw_path, str):
        return None
    p = raw_path.strip()
    if not p:
        return None

    # 1. Native Windows path or UNC path
    if (len(p) >= 2 and p[1] == ":") or p.startswith("\\\\"):
        norm = os.path.normpath(p)
        if os.path.isdir(norm) or os.path.isdir(os.path.dirname(norm)):
            return norm

    # 2. WSL /mnt/<drive>/... path
    if p.startswith("/mnt/") and len(p) >= 7 and p[6] == "/":
        drive = p[5].upper()
        rest = p[7:].replace("/", "\\")
        norm = os.path.normpath(f"{drive}:\\{rest}")
        if os.path.isdir(norm) or os.path.isdir(os.path.dirname(norm)):
            return norm

    # 3. Linux path inside WSL -> \\wsl.localhost\<distro>\...
    if p.startswith("/"):
        for distro in _get_wsl_distros():
            unc = os.path.normpath(f"\\\\wsl.localhost\\{distro}" + p.replace("/", "\\"))
            if os.path.isdir(unc) or os.path.isdir(os.path.dirname(unc)):
                return unc

    return None


def _resolve_writable_model_dir(category: str) -> str | None:
    candidates: list[str] = []
    try:
        fp = client().folder_paths()
        if isinstance(fp, dict):
            cat_paths = fp.get(category)
            if isinstance(cat_paths, list):
                candidates.extend(str(x) for x in cat_paths if x)
            for ckpt_dir in (fp.get("checkpoints") or []):
                if isinstance(ckpt_dir, str) and ckpt_dir.strip():
                    parent = ckpt_dir.rstrip("/\\").rsplit("/", 1)[0].rsplit("\\", 1)[0]
                    if parent:
                        sep = "/" if "/" in ckpt_dir else "\\"
                        candidates.append(f"{parent}{sep}{category}")
    except Exception:
        pass

    comfy_dir = (config().get("comfy_dir") or "").strip()
    if comfy_dir:
        candidates.append(os.path.join(comfy_dir, "models", category))
        candidates.append(os.path.join(comfy_dir, "ComfyUI", "models", category))

    for cand in candidates:
        win_dir = _to_local_windows_path(cand)
        if win_dir:
            try:
                os.makedirs(win_dir, exist_ok=True)
                return win_dir
            except OSError:
                continue
    return None


def _download_missing_model(model_info: dict[str, str], job: dict) -> str:
    filename = model_info["name"]
    url = model_info["url"]
    category = model_info["directory"]

    target_dir = _resolve_writable_model_dir(category)
    if not target_dir:
        raise ComfyError(_tr(
            f"Required model '{filename}' is missing in ComfyUI (models/{category}) and the directory is not locally accessible. Please download it from: {url}",
            f"Das benötigte Modell „{filename}“ fehlt in ComfyUI (models/{category}) und das Verzeichnis ist lokal nicht erreichbar. Bitte manuell herunterladen von: {url}",
        ))

    dest_path = os.path.join(target_dir, filename)
    if os.path.isfile(dest_path) and os.path.getsize(dest_path) > 0:
        return dest_path

    part_path = dest_path + ".part"
    prev_phase = job.get("phase", "phase.preparing")
    job["phase"] = "phase.downloading_model"
    job["detail"] = f"{filename} (0 MB)"
    print(f"[Model Downloader] Downloading '{filename}' from {url} -> {dest_path}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tA-MusicMaker/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total_bytes = int(resp.headers.get("Content-Length") or 0)
            bytes_done = 0
            with open(part_path, "wb") as f:
                while True:
                    if job.get("cancel"):
                        raise ComfyError("Cancelled.")
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_done += len(chunk)
                    mb_done = bytes_done / (1024 * 1024)
                    if total_bytes > 0:
                        mb_total = total_bytes / (1024 * 1024)
                        pct = int((bytes_done / total_bytes) * 100)
                        job["detail"] = f"{filename} ({mb_done:.0f} / {mb_total:.0f} MB · {pct}%)"
                        job["progress"] = round(min(bytes_done / total_bytes, 0.99), 4)
                    else:
                        job["detail"] = f"{filename} ({mb_done:.1f} MB)"
        os.replace(part_path, dest_path)
        print(f"[Model Downloader] Successfully downloaded '{filename}' ({bytes_done} bytes).")
    except ComfyError:
        try:
            if os.path.exists(part_path):
                os.remove(part_path)
        except OSError:
            pass
        raise
    except Exception as err:
        try:
            if os.path.exists(part_path):
                os.remove(part_path)
        except OSError:
            pass
        raise ComfyError(_tr(
            f"Failed to download model '{filename}': {err}",
            f"Fehler beim automatischen Herunterladen von „{filename}“: {err}",
        )) from err
    finally:
        job["detail"] = ""
        job["phase"] = prev_phase

    return dest_path


def ensure_prompt_models(prompt: dict, job: dict) -> None:
    """Checks if any model required by the prompt is missing in ComfyUI and automatically
    downloads it into the appropriate ComfyUI models/<category> directory before execution."""
    known = get_known_models()
    downloaded_any = False

    for node_id, node_data in prompt.items():
        if not isinstance(node_data, dict):
            continue
        class_type = node_data.get("class_type")
        inputs = node_data.get("inputs")
        if not class_type or not isinstance(inputs, dict):
            continue

        for field_name, val in list(inputs.items()):
            if not isinstance(val, str) or not val.strip():
                continue
            base_lower = val.replace("\\", "/").strip().split("/")[-1].lower()
            if base_lower not in known:
                continue

            choices = get_field_choices(class_type, field_name, inputs)
            if choices is not None and _match_choice(choices, val) is None:
                # Re-check with fresh object_info in case the file was just placed there
                _OBJECT_INFO_CACHE.pop(class_type, None)
                choices = get_field_choices(class_type, field_name, inputs)
                if choices is not None and _match_choice(choices, val) is None:
                    model_info = known[base_lower]
                    _download_missing_model(model_info, job)
                    downloaded_any = True
                    _OBJECT_INFO_CACHE.pop(class_type, None)
                    fresh_choices = get_field_choices(class_type, field_name, inputs) or []
                    matched = _match_choice(fresh_choices, val) or _match_choice(fresh_choices, model_info["name"])
                    inputs[field_name] = matched if matched is not None else model_info["name"]

    if downloaded_any:
        _OBJECT_INFO_CACHE.clear()


# --------------------------------------------------------------- prompt building

_CREATIVITY_ANCHORS: dict[str, dict[int, tuple[float, float, int]]] = {
    "writer": {
        0: (0.60, 0.95, 64),
        50: (0.80, 0.95, 64),
        100: (1.00, 0.95, 64),
        200: (1.10, 0.95, 64),
    },
    "arrangement": {
        0: (0.55, 0.95, 64),
        50: (0.70, 0.95, 64),
        100: (0.90, 0.95, 64),
        200: (1.00, 0.95, 64),
    },
    "plan": {
        0: (0.55, 0.85, 20),
        50: (0.70, 0.90, 30),
        100: (0.92, 0.95, 50),
        200: (1.00, 0.96, 64),
    },
    "take": {
        0: (0.90, 0.92, 60),
        50: (1.00, 0.95, 100),
        100: (1.10, 0.97, 150),
        200: (1.15, 0.98, 200),
    },
}


def _extract_creativity(brief: dict | None) -> int:
    if not isinstance(brief, dict):
        return 100
    val = brief.get("creativity")
    if val is None or str(val).strip() == "":
        return 100
    try:
        return max(0, min(200, round(float(val))))
    except (TypeError, ValueError):
        return 100


def _creativity_sampling(creativity: int, stage: str) -> tuple[float, float, int]:
    val = max(0, min(200, int(creativity)))
    anchors = _CREATIVITY_ANCHORS.get(stage) or _CREATIVITY_ANCHORS["take"]
    points = sorted(anchors)
    low = max(p for p in points[:-1] if p <= val)
    high = points[points.index(low) + 1]
    share = (val - low) / (high - low)
    a_t, a_p, a_k = anchors[low]
    b_t, b_p, b_k = anchors[high]
    return (
        round(a_t + (b_t - a_t) * share, 3),
        round(a_p + (b_p - a_p) * share, 3),
        round(a_k + (b_k - a_k) * share),
    )


def _brief_supports_creativity() -> bool:
    info = get_object_info("PlenioSongBrief")
    if not info:
        return False
    inp = info.get("input") or {}
    return "creativity" in (inp.get("required") or {}) or "creativity" in (inp.get("optional") or {})


def _coerce_brief(brief: dict) -> dict:
    out = {}
    supports_creativity = _brief_supports_creativity()
    for key, value in (brief or {}).items():
        if value is None:
            continue
        if key == "creativity":
            if not supports_creativity:
                continue
            try:
                value = max(0, min(200, int(round(float(value)))))
            except (TypeError, ValueError):
                continue
        if key == "genre_closeness":
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
        if key == "lines_under_singing":
            value = bool(value)
        if key in (
            "tempo", "description", "genre", "mood", "key", "meter",
            "vocals.theme", "vocals.language", "vocals.voice",
            "vocals.lyrics_from", "vocals.lyrics", "lyrics_fidelity", "vocals"
        ) and not isinstance(value, str):
            value = str(value)
        out[key] = value
    return out


def _inject_audio_hq_nodes(prompt: dict, hq_cfg: dict, options: dict) -> None:
    """Dynamically wires Plenio Audio HQ stages (HQ 1 Stereo Cleanup, HQ 2 Regenerate Highs,
    HQ 3 De-Reverb) before Mastering when supported by the connected ComfyUI installation."""
    if not hq_cfg:
        return
    stereo_on = bool(hq_cfg.get("stereo_enabled", False))
    regen_on = bool(hq_cfg.get("regen_enabled", False))
    derev_on = bool(hq_cfg.get("dereverb_enabled", False))
    if not (stereo_on or regen_on or derev_on):
        return

    # Check if modern Plenio 1.3 subgraph Master nodes (17:401, 17:403, 17:404) are already present
    if "17:401" in prompt and "17:403" in prompt:
        if stereo_on:
            st_preset = hq_cfg.get("stereo_preset") or "auto - from the song's genre"
            prompt["17:401"]["inputs"]["preset"] = st_preset
            if st_preset.startswith("custom"):
                prompt["17:401"]["inputs"]["preset.side_highcut_hz"] = float(hq_cfg.get("stereo_highcut_hz", 10500.0))
                prompt["17:401"]["inputs"]["preset.side_cleanup"] = float(hq_cfg.get("stereo_cleanup", 0.65))
                prompt["17:401"]["inputs"]["preset.warmth"] = float(hq_cfg.get("stereo_warmth", 0.18))
        if regen_on:
            rg_preset = hq_cfg.get("regen_preset") or "auto - from the song's genre"
            prompt["17:403"]["inputs"]["preset"] = rg_preset
            prompt["17:403"]["inputs"]["seed"] = int(hq_cfg.get("regen_seed", 0))
            prompt["17:403"]["inputs"]["model_steps"] = int(hq_cfg.get("regen_steps", 4))
            if rg_preset.startswith("custom"):
                prompt["17:403"]["inputs"]["preset.from_hz"] = float(hq_cfg.get("regen_from_hz", 8200.0))
                prompt["17:403"]["inputs"]["preset.new_share"] = float(hq_cfg.get("regen_new_share", 0.85))
                prompt["17:403"]["inputs"]["preset.level_match"] = float(hq_cfg.get("regen_level_match", 0.90))
        if derev_on and "17:404" in prompt:
            dr_preset = hq_cfg.get("dereverb_preset") or "auto - from the song's genre"
            prompt["17:404"]["inputs"]["preset"] = dr_preset
            if dr_preset.startswith("custom"):
                prompt["17:404"]["inputs"]["preset.dereverb"] = float(hq_cfg.get("dereverb_amount", 0.35))
                prompt["17:404"]["inputs"]["preset.phase_lock"] = float(hq_cfg.get("dereverb_phase_lock", 0.35))
        return

    # Fallback for older workflows: dynamically inject top-level HQ nodes before Mastering / Export
    target_eq = "15:401" if "15:401" in prompt else "17:405"
    if target_eq in prompt and "audio" in prompt[target_eq].get("inputs", {}):
        cur_audio = prompt[target_eq]["inputs"]["audio"]
        downstream = [(target_eq, "audio")]
    elif "17" in prompt and "audio" in prompt["17"].get("inputs", {}):
        cur_audio = prompt["17"]["inputs"]["audio"]
        downstream = [("17", "audio")]
        if "16" in prompt and "audio" in prompt["16"].get("inputs", {}):
            downstream.append(("16", "audio"))
    elif "19" in prompt and "audio" in prompt["19"].get("inputs", {}):
        cur_audio = prompt["19"]["inputs"]["audio"]
        downstream = [("19", "audio")]
        if "18" in prompt and "audio" in prompt["18"].get("inputs", {}):
            downstream.append(("18", "audio"))
    else:
        return

    brief_nid = "2"
    if stereo_on and get_object_info("PlenioHQStereoCleanup"):
        st_preset = hq_cfg.get("stereo_preset") or "auto - from the song's genre"
        st_inputs: dict[str, Any] = {
            "audio": cur_audio,
            "brief": [brief_nid, 0],
            "preset": st_preset,
        }
        if st_preset.startswith("custom"):
            st_inputs["preset.side_highcut_hz"] = float(hq_cfg.get("stereo_highcut_hz", 10500.0))
            st_inputs["preset.side_cleanup"] = float(hq_cfg.get("stereo_cleanup", 0.65))
            st_inputs["preset.warmth"] = float(hq_cfg.get("stereo_warmth", 0.18))
        prompt["hq_stereo"] = {"class_type": "PlenioHQStereoCleanup", "inputs": st_inputs}
        cur_audio = ["hq_stereo", 0]

    if regen_on and get_object_info("PlenioHQRegenerateHighs"):
        sr_model = (options.get("refine_cfg") or {}).get("model") or "pytorch_model.bin"
        prompt["hq_sr_model"] = {
            "class_type": "PlenioAudioModelLoader",
            "inputs": {"kind": "super-resolution", "kind.model": sr_model},
        }
        rg_preset = hq_cfg.get("regen_preset") or "auto - from the song's genre"
        rg_inputs: dict[str, Any] = {
            "audio": cur_audio,
            "hq_mastering": True,
            "model": ["hq_sr_model", 0],
            "brief": [brief_nid, 0],
            "preset": rg_preset,
            "seed": int(hq_cfg.get("regen_seed", 0)),
            "model_steps": int(hq_cfg.get("regen_steps", 4)),
        }
        if rg_preset.startswith("custom"):
            rg_inputs["preset.from_hz"] = float(hq_cfg.get("regen_from_hz", 8200.0))
            rg_inputs["preset.new_share"] = float(hq_cfg.get("regen_new_share", 0.85))
            rg_inputs["preset.level_match"] = float(hq_cfg.get("regen_level_match", 0.90))
        prompt["hq_regen"] = {"class_type": "PlenioHQRegenerateHighs", "inputs": rg_inputs}
        cur_audio = ["hq_regen", 0]

    if derev_on and get_object_info("PlenioHQDeReverb"):
        dr_preset = hq_cfg.get("dereverb_preset") or "auto - from the song's genre"
        dr_inputs: dict[str, Any] = {
            "audio": cur_audio,
            "brief": [brief_nid, 0],
            "preset": dr_preset,
        }
        if dr_preset.startswith("custom"):
            dr_inputs["preset.dereverb"] = float(hq_cfg.get("dereverb_amount", 0.35))
            dr_inputs["preset.phase_lock"] = float(hq_cfg.get("dereverb_phase_lock", 0.35))
        prompt["hq_dereverb"] = {"class_type": "PlenioHQDeReverb", "inputs": dr_inputs}
        cur_audio = ["hq_dereverb", 0]

    for nid, inp_name in downstream:
        prompt[nid]["inputs"][inp_name] = cur_audio


def build_render_prompt(conv: WorkflowConverter, req: dict, auto: bool) -> dict:
    wn = get_workflow_nodes(conv)
    options = req.get("options") or {}
    raw_brief = req.get("brief") or {}
    creativity = _extract_creativity(raw_brief)
    brief = _coerce_brief(raw_brief)
    brief["mode"] = MODE_AUTO if auto else brief.get("mode") or MODE_REVIEW
    sheet = req.get("sheet") or {}
    rnd = lambda: random.randint(1, 2**53 - 1)  # noqa: E731

    w_temp, w_top_p, w_top_k = _creativity_sampling(creativity, "writer")
    p_temp, p_top_p, p_top_k = _creativity_sampling(creativity, "plan")
    t_temp, t_top_p, t_top_k = _creativity_sampling(creativity, "take")

    overrides: dict = {
        wn["brief"]: brief,
        "4:503": {"sampling_mode.temperature": w_temp, "sampling_mode.top_p": w_top_p, "sampling_mode.top_k": w_top_k},
        "7:701": {"temperature": p_temp, "top_p": p_top_p, "top_k": p_top_k},
        "8:701": {"temperature": p_temp, "top_p": p_top_p, "top_k": p_top_k},
        "11:801": {"temperature": t_temp, "top_p": t_top_p, "top_k": t_top_k},
        "15:801": {"temperature": t_temp, "top_p": t_top_p, "top_k": t_top_k},
    }
    draft_seed = req.get("draft_seed")
    overrides[wn["draft_seed"]] = {"seed": rnd() if (auto or draft_seed in (None, "")) else int(draft_seed)}
    take_seed = req.get("take_seed")
    overrides[wn["take_seed"]] = {"seed": rnd() if take_seed in (None, "") else int(take_seed)}

    unlinks: dict = {}
    score_doc = str(sheet.get("score") or "").strip()
    if score_doc:
        overrides[wn["sheet_score"]] = {
            "review": "continue",
            "sheet_state": json.dumps({"schema": "plenio.sheet_state/1", "docs": {"score": {"state": "manual", "text": score_doc}}}, ensure_ascii=False, separators=(",", ":")),
        }
        unlinks[wn["sheet_score"]] = ["score"]
    else:
        overrides[wn["sheet_score"]] = {"review": "continue", "sheet_state": EMPTY_SHEET_STATE}

    plan_seed = req.get("plan_seed")
    if auto or "plan_seed" in req:
        overrides[wn["plan"]] = {"seed": int(plan_seed) if (plan_seed not in (None, "") and not auto) else rnd()}
        if wn.get("plan_seed") and wn["plan_seed"] in conv.top.nodes:
            overrides[wn["plan_seed"]] = {"seed": int(plan_seed) if (plan_seed not in (None, "") and not auto) else rnd()}

    sheet_states = req.get("sheet_states")
    if isinstance(sheet_states, dict):
        docs: dict = {}
        for kind in SHEET_KINDS:
            st = sheet_states.get(kind, "auto")
            txt = str(sheet.get(kind) or "").strip()
            if st == "manual":
                if not auto and kind in ("title", "style", "lyrics") and not txt:
                    raise ConversionError(_tr(
                        f"Manual field '{kind}' is empty. Enter text or switch it back to auto.",
                        f"Das manuelle Feld „{kind}“ ist leer. Bitte Text eingeben oder zurück auf Auto stellen.",
                    ))
                if txt or not auto:
                    docs[kind] = {"state": "manual", "text": txt}
            elif not auto and txt:
                # Draft already present in the editor: freeze it for this render so the writer need not run twice.
                docs[kind] = {"state": "manual", "text": txt}
        overrides[wn["sheet_text"]] = {
            "review": "continue",
            "sheet_state": json.dumps({"schema": "plenio.sheet_state/1", "docs": docs}, ensure_ascii=False,
                                      separators=(",", ":")),
        }
        if docs:
            unlinks[wn["sheet_text"]] = list(docs.keys())
    elif auto:
        overrides[wn["sheet_text"]] = {"review": "continue", "sheet_state": EMPTY_SHEET_STATE}
    else:
        docs = {kind: {"state": "manual", "text": str(sheet.get(kind) or "")} for kind in SHEET_KINDS
                if kind in sheet}
        if not sheet.get("title") or not sheet.get("lyrics") or not sheet.get("style"):
            raise ConversionError(_tr(
                "Title, style, and lyrics must be filled in before rendering.",
                "Titel, Stil und Songtext müssen ausgefüllt sein, bevor gerendert wird.",
            ))
        overrides[wn["sheet_text"]] = {
            "review": "continue",
            "sheet_state": json.dumps({"schema": "plenio.sheet_state/1", "docs": docs}, ensure_ascii=False,
                                      separators=(",", ":")),
        }
        unlinks[wn["sheet_text"]] = [k for k in docs]

    export = {k: v for k, v in (options.get("export") or {}).items() if v is not None}
    for key in ("flac", "mp3", "wav", "project_in_flac", "lyrics_srt", "song_page"):
        if key in export:
            export[key] = bool(export[key])
    if "lyrics_timing" not in export:
        export["lyrics_timing"] = "the song"
    if "song_page" not in export:
        export["song_page"] = False
    overrides[wn["export"]] = export

    if options.get("writer_model"):
        if wn.get("writer_model") and wn["writer_model"] in conv.top.nodes:
            overrides[wn["writer_model"]] = {"model": options["writer_model"]}
        overrides[wn["writer"]] = {"clip_name": options["writer_model"]}

    outputs = [wn["preview"], wn["export"]]
    modes: dict = {}
    if options.get("cover"):
        modes[wn["cover"]] = 0
        modes[wn["cover_preview"]] = 0
        outputs.append(wn["cover_preview"])
        cover = {"noise_seed": rnd()}
        if options.get("cover_size"):
            cover["size"] = int(options["cover_size"])
        overrides[wn["cover"]] = cover
    else:
        if wn.get("cover"):
            modes[wn["cover"]] = 2
        if wn.get("cover_preview"):
            modes[wn["cover_preview"]] = 2
        if wn.get("export"):
            unlinks.setdefault(wn["export"], []).append("cover")

    loras_nid = wn.get("loras")
    if loras_nid is None:
        for nid, node in conv.top.nodes.items():
            if node.get("type") == "PlenioLoras":
                loras_nid = nid
                break
    if loras_nid is not None and loras_nid in conv.top.nodes:
        # Fallback for ComfyUI installations with older Plenio versions missing PlenioLoras:
        # If PlenioLoras is not registered in ComfyUI, bypass it (mode 4) so MODEL and CLIP
        # pass through cleanly from the YuE2 Model Loader without triggering HTTP 400.
        if not bool(get_object_info("PlenioLoras")):
            modes[loras_nid] = 4
    if options.get("stems") and wn.get("stems") in conv.top.nodes:
        modes[wn["stems"]] = 0

    if wn.get("hq_mastering") and wn["hq_mastering"] in conv.top.nodes:
        overrides[wn["hq_mastering"]] = {
            "hq_mastering": bool(options.get("audio_hq", {}).get("enabled") or options.get("mastering", {}).get("enabled", True))
        }

    mst = options.get("mastering") or {}
    if mst.get("enabled") is False:
        modes[wn["master"]] = 4
    elif mst:
        srate = mst.get("sample_rate") or "keep"
        overrides[wn["master"]] = {"sample_rate": srate}

        eq_mode = mst.get("eq_mode") or "match preset"
        master_eq = wn["master_eq"]
        if eq_mode == "flat":
            overrides[master_eq] = {"mode": "flat"}
            unlinks[master_eq] = ["mode.preset"]
        elif eq_mode == "custom match":
            overrides[master_eq] = {
                "mode": "custom match",
                "mode.target": mst.get("eq_target") or "warm",
                "mode.strength": float(mst.get("eq_strength", 0.35)),
                "mode.max_gain_db": float(mst.get("eq_max_gain_db", 2.0)),
                "mode.max_bands": int(mst.get("eq_max_bands", 4)),
                "mode.min_hz": float(mst.get("eq_min_hz", 40.0)),
                "mode.max_hz": float(mst.get("eq_max_hz", 16000.0)),
            }
            unlinks[master_eq] = ["mode.preset"]
        else:
            overrides[master_eq] = {
                "mode": "match preset",
                "mode.preset": mst.get("eq_preset") or "Warm - gentle (workflow default)",
            }

        loud_target = mst.get("loudness_target") or "streaming (-14 LUFS, -1 dBTP)"
        comp = mst.get("compression") or "Balanced - gentle glue"
        loud_ov: dict = {"target": loud_target, "compression": comp}
        if loud_target == "custom":
            loud_ov["target.lufs"] = float(mst.get("custom_lufs", -14.0))
            loud_ov["target.ceiling_dbtp"] = float(mst.get("custom_ceiling", -1.0))
        if comp == "custom":
            loud_ov["compression.threshold_db"] = float(mst.get("comp_threshold", -18.0))
            loud_ov["compression.ratio"] = float(mst.get("comp_ratio", 1.5))
            loud_ov["compression.knee_db"] = float(mst.get("comp_knee", 6.0))
            loud_ov["compression.attack_ms"] = float(mst.get("comp_attack", 20.0))
            loud_ov["compression.release_ms"] = float(mst.get("comp_release", 150.0))
            loud_ov["compression.sidechain_hz"] = float(mst.get("comp_sidechain", 80.0))
            loud_ov["compression.detector"] = mst.get("comp_detector") or "RMS"
        overrides[wn["master_loudness"]] = loud_ov

    hq_cfg = options.get("audio_hq") or {}
    hq_regen_fallback = bool(hq_cfg.get("regen_enabled")) and not bool(get_object_info("PlenioHQRegenerateHighs"))

    if (options.get("refine") or hq_regen_fallback) and wn.get("refine") in conv.top.nodes:
        ref_cfg = options.get("refine_cfg") or {}
        engine = "model" if hq_regen_fallback else (ref_cfg.get("engine") or "resample only")
        modes[wn["refine"]] = 0
        overrides[wn["refine"]] = {
            "engine": engine,
            "preset": ref_cfg.get("preset") or "custom - the three fields below",
            "sr_gain": float(hq_cfg.get("regen_new_share", 0.85) if hq_regen_fallback else ref_cfg.get("sr_gain", 1.0)),
            "crossover_hz": float(hq_cfg.get("regen_from_hz", 8200.0) if hq_regen_fallback else ref_cfg.get("crossover_hz", 0.0)),
            "pre_hz": float(ref_cfg.get("pre_hz", 0.0)),
            "post_hz": float(ref_cfg.get("post_hz", 0.0)),
            "seed": int(hq_cfg.get("regen_seed", 0) if hq_regen_fallback else ref_cfg.get("seed", 0)),
        }
        if engine == "model" and wn.get("refine_model") in conv.top.nodes:
            modes[wn["refine_model"]] = 0
            sr_model = ref_cfg.get("model") or "pytorch_model.bin"
            overrides[wn["refine_model"]] = {"kind": "super-resolution", "kind.model": sr_model}
        else:
            unlinks[wn["refine"]] = ["model"]
    prompt = conv.convert(outputs, overrides=overrides, modes=modes, unlinks=unlinks)
    _inject_audio_hq_nodes(prompt, hq_cfg, options)
    return resolve_prompt_models(prompt)


def build_draft_prompt(conv: WorkflowConverter, req: dict) -> dict:
    wn = get_workflow_nodes(conv)
    raw_brief = req.get("brief") or {}
    creativity = _extract_creativity(raw_brief)
    w_temp, w_top_p, w_top_k = _creativity_sampling(creativity, "writer")
    brief = _coerce_brief(raw_brief)
    brief["mode"] = brief.get("mode") or MODE_REVIEW
    seed = req.get("draft_seed")
    overrides: dict = {
        wn["brief"]: brief,
        wn["draft_seed"]: {"seed": random.randint(1, 2**53 - 1) if seed in (None, "") else int(seed)},
        "4:503": {"sampling_mode.temperature": w_temp, "sampling_mode.top_p": w_top_p, "sampling_mode.top_k": w_top_k},
    }
    if (req.get("options") or {}).get("writer_model"):
        if wn.get("writer_model") and wn["writer_model"] in conv.top.nodes:
            overrides[wn["writer_model"]] = {"model": req["options"]["writer_model"]}
        overrides[wn["writer"]] = {"clip_name": req["options"]["writer_model"]}
    sources = {"d_title": (wn["writer"], 0), "d_style": (wn["writer"], 1), "d_lyrics": (wn["writer"], 2),
               "d_artwork": (wn["writer"], 3)}
    prompt = conv.convert([], overrides=overrides, extra_sources=sources)
    return resolve_prompt_models(prompt)


# -------------------------------------------------------------------- jobs

def new_job(kind: str, total: int = 1) -> dict:
    job = {"id": uuid.uuid4().hex[:10], "kind": kind, "status": "queued", "phase": "phase.waiting", "progress": 0.0,
           "run": 1, "runs": total, "error": None, "results": [], "cancel": False, "started": time.time(),
           "log": []}
    with _lock:
        JOBS[job["id"]] = job
    return job


def public_job(job: dict) -> dict:
    return {k: v for k, v in job.items() if k != "cancel"}


def _phase_for(node_id: str) -> str:
    for prefix, text in PHASES:
        if node_id == prefix or (prefix.endswith(":") and node_id.startswith(prefix)):
            return text
    return "phase.preparing"


def _progress_handler(job: dict, prompt: dict):
    state = {"done": 0, "node_frac": 0.0}
    total = max(len(prompt), 1)

    def handler(event: dict):
        kind = event.get("type")
        if kind == "execution_cached":
            state["done"] += len(event.get("nodes", []))
        elif kind == "executing":
            node = event.get("node")
            if node is not None:
                if state.get("current") != node:
                    if state.get("current") is not None:
                        state["done"] += 1
                    state["current"] = node
                    state["node_frac"] = 0.0
                job["phase"] = _phase_for(str(node))
        elif kind == "progress":
            if event.get("max"):
                state["node_frac"] = event["value"] / event["max"]
                job["detail"] = f"{event['value']}/{event['max']}"
        elif kind == "queued":
            job["phase"] = "phase.queued"
        done = min(state["done"] + state["node_frac"], total)
        base = (job["run"] - 1) / job["runs"]
        job["progress"] = round(min(base + (done / total) / job["runs"], 0.999), 4)

    return handler


def collect_outputs(entry: dict) -> dict:
    media, texts, raw = [], [], entry.get("outputs", {})
    for node_id, out in raw.items():
        for key, values in out.items():
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, dict) and "filename" in value:
                    ext = os.path.splitext(value["filename"])[1].lower()
                    kind = "audio" if ext in AUDIO_EXT else "image" if ext in IMAGE_EXT else "file"
                    qs = urllib.parse.urlencode({"filename": value["filename"], "subfolder": value.get("subfolder", ""),
                                                 "type": value.get("type", "output")})
                    media.append({"node": node_id, "kind": kind, "name": value["filename"], "url": "/api/view?" + qs,
                                  "temp": value.get("type") == "temp"})
                elif isinstance(value, str):
                    texts.append({"node": node_id, "key": key, "text": value})
    if any(m["kind"] == "audio" and not m["temp"] for m in media):
        media = [m for m in media if not (m["kind"] == "audio" and m["temp"])]
    return {"media": media, "texts": texts}


def run_job(job: dict, prompts: list[dict], req: dict, finish) -> None:
    job["status"] = "running"
    try:
        for index, prompt in enumerate(prompts):
            job["run"] = index + 1
            ensure_prompt_models(prompt, job)
            resolve_prompt_models(prompt)
            entry = client().run_prompt(prompt, _progress_handler(job, prompt), lambda: job["cancel"])
            job["results"].append({"run": index + 1, **collect_outputs(entry), "raw": entry.get("outputs", {})})
        job["progress"] = 1.0
        job["phase"] = "phase.done"
        finish(job)
        job["status"] = "done"
    except (ComfyError, ConversionError) as err:
        job["status"] = "cancelled" if job["cancel"] else "error"
        job["error"] = str(err)
    except Exception as err:  # noqa: BLE001 - surface unexpected failures in the UI
        traceback.print_exc()
        job["status"] = "error"
        job["error"] = _tr(f"Internal error: {err}", f"Interner Fehler: {err}")


def start_draft(req: dict) -> dict:
    job = new_job("draft")
    prompt = build_draft_prompt(converter(), req)

    def finish(j):
        raw = j["results"][-1]["raw"]
        pick = lambda nid: ((raw.get(nid) or {}).get("text") or [""])[0]  # noqa: E731
        lyrics_text = pick("d_lyrics")
        raw_brief = req.get("brief") or {}
        if raw_brief.get("vocals.lyrics_from") == "my own, sung as written below" and raw_brief.get("vocals.lyrics"):
            lyrics_text = raw_brief["vocals.lyrics"].strip()
        j["draft"] = {"title": pick("d_title"), "style": pick("d_style"), "lyrics": lyrics_text,
                      "artwork_prompt": pick("d_artwork")}
        if not j["draft"]["lyrics"]:
            raise ComfyError(_tr(
                "The writer model did not return any lyrics. Please try again.",
                "Das Textmodell hat keinen Songtext geliefert. Bitte erneut versuchen.",
            ))

    threading.Thread(target=run_job, args=(job, [prompt], req, finish), daemon=True).start()
    return job


def fetch_audio_to_file(url: str, dest_path: str):
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    filename = qs.get("filename", [""])[0]
    base_name = os.path.basename(filename)

    # Search candidates across all local directories first
    candidates = [
        os.path.join(RENDERS_DIR, base_name),
        os.path.join(DATA_DIR, base_name),
        os.path.join(APP_DIR, "data", "renders", base_name),
    ]
    sub = qs.get("subfolder", [""])[0]
    comfy_out = _resolve_comfy_output_dir(sub)
    if comfy_out:
        candidates.append(os.path.join(comfy_out, base_name))

    for cand in candidates:
        if os.path.isfile(cand):
            if os.path.abspath(cand) != os.path.abspath(dest_path):
                shutil.copy2(cand, dest_path)
            return

    # Check if a render_* prefixed or suffix-matching file exists in RENDERS_DIR
    if os.path.isdir(RENDERS_DIR):
        for f in os.listdir(RENDERS_DIR):
            if f.endswith(base_name) or (base_name and base_name in f):
                cand = os.path.join(RENDERS_DIR, f)
                if os.path.isfile(cand):
                    if os.path.abspath(cand) != os.path.abspath(dest_path):
                        shutil.copy2(cand, dest_path)
                    return

    if qs.get("source") == ["local"]:
        if os.path.isfile(base_name):
            if os.path.abspath(base_name) != os.path.abspath(dest_path):
                shutil.copy2(base_name, dest_path)
            return
        raise FileNotFoundError(f"Local file not found: {filename}")

    # Fallback to ComfyUI client
    tp = qs.get("type", ["output"])[0]
    data, _ = client().view(filename, sub, tp)
    with open(dest_path, "wb") as fh:
        fh.write(data)


def _resolve_comfy_output_dir(subfolder: str = "") -> str | None:
    """Find the local Windows filesystem path to ComfyUI's output directory if accessible."""
    try:
        stats = client().system_stats()
        argv = stats.get("system", {}).get("argv", [])
        for i, arg in enumerate(argv):
            if arg == "--output-directory" and i + 1 < len(argv):
                win_base = _to_local_windows_path(argv[i + 1])
                if win_base:
                    out = os.path.join(win_base, subfolder) if subfolder else win_base
                    os.makedirs(out, exist_ok=True)
                    return out
    except Exception:
        pass
    cdir = config().get("comfy_dir")
    if cdir:
        cand = os.path.join(cdir, "output", subfolder) if subfolder else os.path.join(cdir, "output")
        win_c = _to_local_windows_path(cand)
        if win_c and os.path.isdir(win_c):
            return win_c
    return None


def build_subtitles_for_audio(audio_url: str, local_audio_path: str | None = None, target_lang: str | None = "en", fallback_lyrics: str | None = None) -> list[dict]:
    """Extract or fetch the song's `.srt` subtitles and create translated `.en.srt` and `.bilingual-en.srt` files.
    Also copies the resulting .srt files directly to ComfyUI's output directory alongside the song FLAC."""
    importlib.reload(srt_translate)
    srt_text = None
    sung_srt_text = None
    base_path = local_audio_path

    # 1. Try reading embedded Plenio timing directly from the local FLAC file
    if local_audio_path and os.path.isfile(local_audio_path):
        srt_text = srt_translate.extract_srt_from_flac(local_audio_path, fallback_lyrics=fallback_lyrics)
        sung_srt_text = srt_translate.extract_sung_srt_from_flac(local_audio_path)

    # 2. Inspect audio_url and resolve ComfyUI output directory
    parsed = urllib.parse.urlparse(audio_url or "")
    qs = urllib.parse.parse_qs(parsed.query)
    sub = qs.get("subfolder", [""])[0] or "plenio"
    extra_out_dir = _resolve_comfy_output_dir(sub)

    fn = qs.get("filename", [""])[0]
    raw_name = fn or (os.path.basename(local_audio_path) if local_audio_path else "song.flac")
    base_path = base_path or os.path.join(RENDERS_DIR, os.path.basename(raw_name))

    if extra_out_dir and fn:
        direct_file = os.path.join(extra_out_dir, os.path.basename(fn))
        if os.path.isfile(direct_file):
            if not srt_text:
                srt_text = srt_translate.extract_srt_from_flac(direct_file, fallback_lyrics=fallback_lyrics)
            if not sung_srt_text:
                sung_srt_text = srt_translate.extract_sung_srt_from_flac(direct_file)

    if qs.get("source") == ["local"]:
        fname = os.path.basename(fn)
        loc = os.path.join(RENDERS_DIR, fname)
        base_path = base_path or loc
        if os.path.isfile(loc):
            if not srt_text:
                srt_text = srt_translate.extract_srt_from_flac(loc, fallback_lyrics=fallback_lyrics)
            if not sung_srt_text:
                sung_srt_text = srt_translate.extract_sung_srt_from_flac(loc)
            stem = os.path.splitext(loc)[0]
            if not srt_text:
                for cand in (f"{stem} (lines).srt", re.sub(r"_[^_]+_final$", "", stem) + " (lines).srt"):
                    if os.path.isfile(cand):
                        with open(cand, "r", encoding="utf-8") as fh:
                            srt_text = fh.read()
                        break
            if not sung_srt_text:
                for cand in (f"{stem} (sung).srt", re.sub(r"_[^_]+_final$", "", stem) + " (sung).srt"):
                    if os.path.isfile(cand):
                        with open(cand, "r", encoding="utf-8") as fh:
                            sung_srt_text = fh.read()
                        break
    else:
        tp = qs.get("type", ["output"])[0]
        stem = os.path.splitext(fn)[0]
        base_path = base_path or os.path.join(RENDERS_DIR, os.path.basename(fn))
        # Try fetching `<stem> (lines).srt` and `<stem> (sung).srt` directly from ComfyUI output
        if not srt_text:
            try:
                raw_srt, _ = client().view(f"{stem} (lines).srt", sub, tp)
                srt_text = raw_srt.decode("utf-8", errors="replace")
            except Exception:
                pass
        if not sung_srt_text:
            try:
                raw_sung, _ = client().view(f"{stem} (sung).srt", sub, tp)
                sung_srt_text = raw_sung.decode("utf-8", errors="replace")
            except Exception:
                pass
        if not srt_text and not sung_srt_text:
            # Fallback: fetch the FLAC and read its embedded Plenio timing block
            try:
                if not os.path.isfile(base_path):
                    fetch_audio_to_file(audio_url, base_path)
                srt_text = srt_translate.extract_srt_from_flac(base_path, fallback_lyrics=fallback_lyrics)
                sung_srt_text = srt_translate.extract_sung_srt_from_flac(base_path)
            except Exception:
                pass

    if not srt_text and sung_srt_text:
        srt_text = sung_srt_text

    # Validate srt_text alignment: if the first cue is suspiciously delayed (> 38s) or misaligned,
    # trigger local Whisper alignment on the actual audio file to ensure lyrics sync properly in the player.
    if srt_text and base_path and os.path.isfile(base_path):
        try:
            cues = srt_translate.parse_srt(srt_text)
            if cues:
                t0_str = cues[0]["time"].split("-->")[0].strip()
                t0 = srt_translate.parse_srt_timestamp(t0_str)
                if t0 > 38.0 and len(cues) > 3:
                    print(f"[Subtitles] Note: ComfyUI SRT cue begins late ({t0:.1f}s), re-aligning with local Whisper...")
                    w_srt = srt_translate.align_lyrics_with_whisper(base_path, fallback_lyrics=fallback_lyrics)
                    if w_srt:
                        srt_text = w_srt
        except Exception as ex:
            print(f"[Subtitles] Note: SRT validation check skipped: {ex}")

    if not srt_text or not base_path:
        return []

    resolve_srt_text = None
    try:
        if base_path and os.path.isfile(base_path):
            resolve_srt_text = srt_translate.extract_srt_from_flac(base_path, fallback_lyrics=fallback_lyrics, resolve_mode=True)
    except Exception as ex:
        print("[Subtitles] Resolve cut-exact extraction note:", ex)

    if target_lang == "auto":
        target_lang = srt_translate.get_auto_translation_target(fallback_lyrics or srt_text or "")

    out = srt_translate.generate_translated_srt_files(
        srt_text, base_path, target_lang=target_lang, extra_output_dir=extra_out_dir,
        resolve_srt_text=resolve_srt_text
    )
    # Determine clean language flags
    orig_lang = srt_translate.detect_lyrics_language(fallback_lyrics or srt_text)
    orig_label = "🇩🇪 Original (.srt)" if orig_lang == "de" else "🇬🇧 Original (.srt)"

    items = []
    # 1. DaVinci Resolve (cut-exact, zero-overlap)
    if out.get("resolve_srt") and os.path.isfile(out["resolve_srt"]):
        bn = os.path.basename(out["resolve_srt"])
        items.append({
            "node": "srt", "kind": "subtitle", "role": "resolve",
            "label": "🎬 DaVinci Resolve (.resolve.srt)", "name": bn,
            "url": f"/api/view?filename={urllib.parse.quote(bn)}&source=local&download=1",
            "temp": False,
        })

    # 2. Original language reading version
    if out.get("orig_srt") and os.path.isfile(out["orig_srt"]):
        bn = os.path.basename(out["orig_srt"])
        items.append({
            "node": "srt", "kind": "subtitle", "role": "orig",
            "label": orig_label, "name": bn,
            "url": f"/api/view?filename={urllib.parse.quote(bn)}&source=local&download=1",
            "temp": False,
        })

    # 3. Optional single translation
    if out.get("trans_srt") and os.path.isfile(out["trans_srt"]):
        t_lang = out.get("target_lang", "en")
        t_label = "🇬🇧 English (.srt)" if t_lang == "en" else ("🇩🇪 Deutsch (.srt)" if t_lang == "de" else f"🌐 {t_lang.upper()} (.srt)")
        bn = os.path.basename(out["trans_srt"])
        items.append({
            "node": "srt", "kind": "subtitle", "role": "trans",
            "label": t_label, "name": bn,
            "url": f"/api/view?filename={urllib.parse.quote(bn)}&source=local&download=1",
            "temp": False,
        })

    return items


def start_voice_swap(req: dict) -> dict:
    job = new_job("voice_swap")
    audio_url = req.get("audio_url", "")
    filename = req.get("filename") or "song.flac"
    model_name = req.get("model")
    pitch = int(req.get("pitch", 0))
    index_rate = float(req.get("index_rate", 0.75))
    title = req.get("title") or os.path.splitext(os.path.basename(filename))[0]

    def worker():
        job["status"] = "running"
        try:
            if not IS_FROZEN:
                importlib.reload(voice_swap)
            clean_name = re.sub(r"^\[[^\]]+\]\s*", "", os.path.basename(filename))
            temp_in = os.path.join(RENDERS_DIR, f"input_{job['id']}_{clean_name}")
            fetch_audio_to_file(audio_url, temp_in)

            def on_status(ph, pr):
                job["phase"] = ph
                job["progress"] = pr

            res = voice_swap.voice_swap_pipeline(
                song_input_path=temp_in,
                output_dir=RENDERS_DIR,
                model_name=model_name,
                pitch=pitch,
                index_rate=index_rate,
                status_cb=on_status,
                models_dir=config().get("voice_models_dir"),
            )

            final_name = os.path.basename(res["final_song"])
            disp_title = f"[{res['model']}] {title}"
            media_item = {
                "node": "voice_swap",
                "kind": "audio",
                "name": final_name,
                "url": f"/api/view?filename={urllib.parse.quote(final_name)}&source=local",
                "temp": False,
            }
            sub_items = []
            try:
                sub_items = build_subtitles_for_audio(media_item["url"], res["final_song"])
            except Exception as ex:
                print("Subtitle generation during voice swap failed:", ex)

            all_media = [media_item, *sub_items]
            job["results"] = [{
                "run": 1,
                "media": all_media,
                "texts": [{"node": "voice_swap", "key": "status", "text": f"Voice swapped to {res['model']}"}],
                "raw": {},
            }]
            job["progress"] = 1.0
            job["phase"] = "phase.done"
            job["status"] = "done"

            history = load_json(HISTORY_PATH, [])
            history.insert(0, {
                "id": uuid.uuid4().hex[:10],
                "ts": int(time.time()),
                "title": disp_title,
                "brief": None,
                "sheet": None,
                "options": {"voice_swap": True, "model": res["model"], "pitch": pitch, "index_rate": index_rate},
                "media": all_media,
                "texts": [],
                "auto": False,
            })
            save_json(HISTORY_PATH, history[:200])

        except Exception as err:
            traceback.print_exc()
            job["status"] = "error"
            job["error"] = str(err)

    threading.Thread(target=worker, daemon=True).start()
    return job


def start_render(req: dict) -> dict:
    auto = req.get("mode") == "auto"
    count = max(1, min(int(req.get("count") or 1), 50)) if auto else 1
    conv = converter()
    prompts = [build_render_prompt(conv, req, auto) for _ in range(count)]
    job = new_job("render", count)

    def finish(j):
        has_any_audio = any(m.get("kind") == "audio" for res in j["results"] for m in res.get("media", []))
        if not has_any_audio:
            raise ComfyError(_tr(
                "ComfyUI did not produce an audio output. Please check the workflow or ComfyUI logs.",
                "ComfyUI hat keine Audiodatei erzeugt. Bitte den Workflow oder die ComfyUI-Logs prüfen.",
            ))
        history = load_json(HISTORY_PATH, [])
        options = req.get("options") or {}
        vswap = options.get("voice_swap")
        export_opts = options.get("export") or {}
        want_srt = export_opts.get("lyrics_srt", True)
        want_srt_en = bool(options.get("srt_en", True))
        for res in j["results"]:
            audio = [m for m in res["media"] if m["kind"] == "audio"]
            tmp_song = None
            if audio:
                first_audio = audio[0]
                song_name = first_audio["name"]
                if vswap or want_srt:
                    try:
                        tmp_song = os.path.join(RENDERS_DIR, f"render_{j['id']}_{os.path.basename(song_name)}")
                        fetch_audio_to_file(first_audio["url"], tmp_song)
                    except Exception as ex:
                        print("Fetching rendered audio failed:", ex)

            if vswap and audio and tmp_song and os.path.isfile(tmp_song):
                try:
                    if not IS_FROZEN:
                        importlib.reload(voice_swap)
                    j["phase"] = "phase.converting_voice"
                    first_audio = audio[0]
                    song_name = first_audio["name"]
                    v_res = voice_swap.voice_swap_pipeline(
                        song_input_path=tmp_song,
                        output_dir=RENDERS_DIR,
                        model_name=options.get("voice_model"),
                        pitch=int(options.get("voice_pitch", 0)),
                        index_rate=float(options.get("voice_index_rate", 0.75)),
                        models_dir=config().get("voice_models_dir"),
                    )
                    final_name = os.path.basename(v_res["final_song"])
                    swapped_media = {
                        "node": "voice_swap",
                        "kind": "audio",
                        "name": f"[{v_res['model']}] {song_name}",
                        "url": f"/api/view?filename={urllib.parse.quote(final_name)}&source=local",
                        "temp": False,
                    }
                    res["media"].insert(0, swapped_media)
                    audio.insert(0, swapped_media)
                except Exception as ex:
                    print("Auto voice swap failed:", ex)
                    traceback.print_exc()

            sub_items = []
            if want_srt and audio:
                try:
                    j["phase"] = "phase.translating_srt"
                    req_lyrics = (req.get("sheet") or {}).get("lyrics")
                    t_lang = srt_translate.get_auto_translation_target(req_lyrics or "") if want_srt_en else None
                    sub_items = build_subtitles_for_audio(audio[0]["url"], tmp_song, target_lang=t_lang, fallback_lyrics=req_lyrics)
                    res["media"].extend(sub_items)
                except Exception as ex:
                    print("Auto SRT generation/translation failed:", ex)
                    traceback.print_exc()

            kept_media = (audio[:2] if vswap else audio[:1]) + sub_items
            rec = None
            if tmp_song and os.path.isfile(tmp_song):
                try:
                    rec = srt_translate.extract_plenio_record_from_flac(tmp_song)
                except Exception:
                    pass
            history.insert(0, {
                "id": uuid.uuid4().hex[:10], "ts": int(time.time()), "title": req.get("sheet", {}).get("title") if
                not auto else "", "brief": req.get("brief"), "sheet": req.get("sheet"),
                "options": req.get("options"), "record": rec, "media": kept_media, "texts": res["texts"], "auto": auto,
            })
        save_json(HISTORY_PATH, history[:200])

    threading.Thread(target=run_job, args=(job, prompts, req, finish), daemon=True).start()
    return job


def start_new_take(req: dict) -> dict:
    """Renders a fresh vocal/instrumental take of an existing song, preserving melody/score, lyrics and brief."""
    hist_id = req.get("id")
    history = load_json(HISTORY_PATH, [])
    found = None
    if hist_id:
        for h in history:
            if h.get("id") == hist_id:
                found = h
                break
    if not found and history:
        found = history[0]

    if not found:
        raise ValueError(_tr("No song found to create a new take from.", "Kein Song gefunden, um einen neuen Take zu erzeugen."))

    rec = found.get("record")
    flac_path = None
    for m in (found.get("media") or []):
        if m.get("kind") == "audio" and str(m.get("name", "")).endswith(".flac"):
            candidates = [
                os.path.join(RENDERS_DIR, m["name"]),
                os.path.join(DATA_DIR, m["name"]),
                os.path.join(APP_DIR, "data", "renders", m["name"]),
            ]
            comfy_out = _resolve_comfy_output_dir("plenio")
            if comfy_out:
                candidates.append(os.path.join(comfy_out, m["name"]))
            for cand in candidates:
                if os.path.isfile(cand):
                    flac_path = cand
                    break
            if flac_path:
                break

    if not rec and flac_path and os.path.isfile(flac_path):
        rec = srt_translate.extract_plenio_record_from_flac(flac_path)

    brief = dict(found.get("brief") or {})
    options = copy.deepcopy(found.get("options") or {})
    sheet = dict(found.get("sheet") or {})

    if rec and isinstance(rec.get("documents"), dict):
        docs = rec["documents"]
        for k in ("title", "style", "lyrics", "score", "artwork_prompt"):
            if docs.get(k):
                sheet[k] = docs[k]

    new_render_req = {
        "mode": "review",
        "brief": brief,
        "sheet": sheet,
        "options": options,
        "take_seed": random.randint(1, 2**53 - 1),
        "sheet_states": {
            "title": "manual",
            "style": "manual",
            "lyrics": "manual",
            "artwork_prompt": "manual" if sheet.get("artwork_prompt") else "auto",
        },
    }
    return start_render(new_render_req)


def find_plenio_player_bat() -> str | None:
    cdir = config().get("comfy_dir")
    if cdir:
        cand = os.path.join(cdir, "custom_nodes", "Plenio-Music-Production-System", "Plenio Player.bat")
        if os.path.isfile(cand):
            return cand
    return None


_WINDOWS_FONTS_CACHE: dict[str, str] | None = None


def get_windows_fonts() -> dict[str, str]:
    global _WINDOWS_FONTS_CACHE
    if _WINDOWS_FONTS_CACHE is not None:
        return _WINDOWS_FONTS_CACHE

    fonts: dict[str, str] = {}
    try:
        import winreg
    except ImportError:
        winreg = None

    if winreg:
        keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
        ]
        windir = os.environ.get("WINDIR", r"C:\Windows")
        sys_fonts_dir = os.path.join(windir, "Fonts")
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        user_fonts_dir = os.path.join(local_appdata, r"Microsoft\Windows\Fonts") if local_appdata else ""

        for root_hkey, subkey in keys:
            try:
                with winreg.OpenKey(root_hkey, subkey) as key:
                    count = winreg.QueryInfoKey(key)[1]
                    for i in range(count):
                        try:
                            name, val, _ = winreg.EnumValue(key, i)
                            clean_name = name.split(" (")[0].strip()
                            if not clean_name:
                                continue
                            if os.path.isabs(val):
                                font_path = val
                            else:
                                cand = os.path.join(sys_fonts_dir, val)
                                if os.path.exists(cand):
                                    font_path = cand
                                elif user_fonts_dir and os.path.exists(os.path.join(user_fonts_dir, val)):
                                    font_path = os.path.join(user_fonts_dir, val)
                                else:
                                    font_path = cand
                            if clean_name not in fonts and os.path.exists(font_path):
                                fonts[clean_name] = font_path
                        except OSError:
                            pass
            except OSError:
                pass

    if not fonts:
        for std in ("Impact", "Arial", "Segoe UI", "Tahoma", "Verdana", "Georgia", "Comic Sans MS", "Trebuchet MS", "Times New Roman"):
            fonts[std] = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", f"{std.lower().replace(' ', '')}.ttf")

    _WINDOWS_FONTS_CACHE = fonts
    return fonts


def get_fonts_payload() -> dict:
    fmap = get_windows_fonts()
    sorted_names = sorted(fmap.keys(), key=lambda s: s.lower())
    default_font = "Impact" if "Impact" in fmap else ("Arial" if "Arial" in fmap else (sorted_names[0] if sorted_names else "Impact"))
    return {
        "fonts": sorted_names,
        "default": default_font,
    }


def render_video_ffmpeg(audio_url: str, title: str = "Song", aspect: str = "16:9",
                         cover_url: str | None = None, srt_url: str | None = None,
                         style: str = "retro", bg_video_url: str | None = None,
                         duration_mode: str = "audio",
                         subtitle_font: str = "Impact",
                         include_subtitles: bool = True,
                         subtitle_offset: float = 0.0,
                         subtitle_speed: float = 1.0,
                         audio_start: float = 0.0,
                         audio_duration: float | None = None) -> dict:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise ValueError(_tr("FFmpeg is not installed on this system.", "FFmpeg ist auf diesem System nicht installiert."))

    ts = int(time.time())
    safe_title = re.sub(r'[\s<>:"/\\|?*]+', "_", title).strip("_")[:60] or "song"
    audio_tmp = os.path.join(RENDERS_DIR, f"temp_vid_{ts}.flac")
    fetch_audio_to_file(audio_url, audio_tmp)

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    # Trim audio if a specific clip / range is requested
    if (audio_start > 0.001 or (audio_duration is not None and audio_duration > 0.001)) and os.path.isfile(audio_tmp):
        cut_tmp = os.path.join(RENDERS_DIR, f"temp_vid_cut_{ts}.flac")
        cut_cmd = [ffmpeg_bin, "-y"]
        if audio_start > 0.001:
            cut_cmd.extend(["-ss", f"{audio_start:.3f}"])
        cut_cmd.extend(["-i", audio_tmp])
        if audio_duration is not None and audio_duration > 0.001:
            cut_cmd.extend(["-t", f"{audio_duration:.3f}"])
        cut_cmd.extend(["-c:a", "flac", cut_tmp])
        proc_cut = subprocess.run(cut_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)
        if proc_cut.returncode == 0 and os.path.isfile(cut_tmp):
            try:
                os.remove(audio_tmp)
            except OSError:
                pass
            audio_tmp = cut_tmp
        else:
            print(f"[Video Render] Audio cut failed: {proc_cut.stderr.decode('utf-8', 'replace')[-200:]}")

    bg_video_tmp = None
    is_custom_image = style == "custom_image"
    if bg_video_url:
        try:
            url_path = urllib.parse.urlparse(bg_video_url).path
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(bg_video_url).query)
            fn = qs.get("filename", [""])[0] or url_path
            ext = os.path.splitext(fn)[1].lower() or (".png" if is_custom_image else ".mp4")
            if ext in (".png", ".jpg", ".jpeg", ".webp"):
                is_custom_image = True
            bg_video_tmp = os.path.join(RENDERS_DIR, f"temp_vid_bg_{ts}{ext}")
            fetch_audio_to_file(bg_video_url, bg_video_tmp)
        except Exception as ex:
            print(f"[Video Render] Error fetching custom background media: {ex}")
            bg_video_tmp = None

    cover_tmp = None
    if cover_url:
        try:
            cover_tmp = os.path.join(RENDERS_DIR, f"temp_vid_cov_{ts}.png")
            fetch_audio_to_file(cover_url, cover_tmp)
        except Exception:
            cover_tmp = None

    srt_tmp = None
    is_temp_srt = False
    if srt_url:
        try:
            srt_tmp = os.path.join(RENDERS_DIR, f"temp_vid_sub_{ts}.srt")
            fetch_audio_to_file(srt_url, srt_tmp)
            is_temp_srt = True
        except Exception:
            srt_tmp = None

    if include_subtitles and not (srt_tmp and os.path.isfile(srt_tmp)):
        # Auto-extract synchronized subtitles directly from FLAC or match in RENDERS_DIR
        if audio_tmp and os.path.isfile(audio_tmp):
            try:
                auto_srt = srt_translate.extract_srt_from_flac(audio_tmp)
                if auto_srt:
                    srt_tmp = os.path.join(RENDERS_DIR, f"temp_vid_sub_{ts}.srt")
                    with open(srt_tmp, "w", encoding="utf-8") as sfh:
                        sfh.write(auto_srt)
                    is_temp_srt = True
            except Exception as ex:
                print(f"[Video Render] Auto-extract subtitles from audio FLAC skipped: {ex}")

        if not (srt_tmp and os.path.isfile(srt_tmp)):
            safe_query = re.sub(r'[\s_]+', '.*', re.escape(safe_title[:30]))
            for fname in os.listdir(RENDERS_DIR) if os.path.isdir(RENDERS_DIR) else []:
                if fname.lower().endswith(".srt") and re.search(safe_query, fname, re.IGNORECASE):
                    cand = os.path.join(RENDERS_DIR, fname)
                    if os.path.isfile(cand):
                        srt_tmp = cand
                        is_temp_srt = False
                        break

    if include_subtitles and srt_tmp and os.path.isfile(srt_tmp):
        if abs(subtitle_offset) > 0.001 or abs(subtitle_speed - 1.0) > 0.001 or audio_start > 0.001 or (audio_duration is not None and audio_duration > 0.001):
            try:
                with open(srt_tmp, "r", encoding="utf-8") as sfh:
                    raw_sub = sfh.read()
                adj_sub = srt_translate.adjust_srt_timing(
                    raw_sub,
                    offset_sec=subtitle_offset,
                    speed_factor=subtitle_speed,
                    clip_start=audio_start,
                    clip_duration=audio_duration
                )
                adj_tmp = os.path.join(RENDERS_DIR, f"temp_vid_sub_adj_{ts}.srt")
                with open(adj_tmp, "w", encoding="utf-8") as sfh:
                    sfh.write(adj_sub)
                if is_temp_srt and srt_tmp != adj_tmp:
                    try:
                        os.remove(srt_tmp)
                    except OSError:
                        pass
                srt_tmp = adj_tmp
                is_temp_srt = True
            except Exception as ex:
                print(f"[Video Render] Adjust SRT timing failed: {ex}")

    out_name = f"video_{safe_title}_{ts}.mp4"
    out_path = os.path.join(RENDERS_DIR, out_name)

    is_portrait = aspect == "9:16"
    w, h = (1080, 1920) if is_portrait else (1920, 1080)
    wave_w, wave_h = (920, 160) if is_portrait else (1280, 140)
    fg_w, fg_h = (880, 880) if is_portrait else (680, 680)

    cmd = [ffmpeg_bin, "-y"]
    has_bg_media = bool(bg_video_tmp and os.path.isfile(bg_video_tmp))
    has_cover = bool(cover_tmp and os.path.isfile(cover_tmp))

    if has_bg_media:
        if is_custom_image:
            # Custom static image looped for the full duration
            cmd.extend(["-loop", "1", "-i", bg_video_tmp])
            cmd.extend(["-i", audio_tmp])
        elif duration_mode == "video":
            # Video plays once and dictates duration; audio loops if shorter or cuts if longer
            cmd.extend(["-i", bg_video_tmp])
            cmd.extend(["-stream_loop", "-1", "-i", audio_tmp])
        else:
            # Song dictates duration; video loops seamlessly (strip audio from bg video so it doesn't limit length)
            cmd.extend(["-stream_loop", "-1", "-an", "-i", bg_video_tmp])
            cmd.extend(["-i", audio_tmp])
    elif has_cover:
        cmd.extend(["-loop", "1", "-i", cover_tmp])
        cmd.extend(["-i", audio_tmp])
    else:
        bg_col = "0x0b0420" if style == "retro" else "0x050811" if style == "stars" else "0x0f1117"
        cmd.extend(["-f", "lavfi", "-i", f"color=c={bg_col}:s={w}x{h}:r=30"])
        cmd.extend(["-i", audio_tmp])

    # If both custom background media AND cover are present, cover is input 2
    if has_bg_media and has_cover and not is_custom_image:
        cmd.extend(["-loop", "1", "-i", cover_tmp])

    # Audio wave generator filter based on style
    if style == "bars":
        audio_filter = f"[1:a]showfreqs=s={wave_w}x{wave_h}:mode=bar:colors=0x7c5cff|0x33d6a6:scale=log[wave]"
    elif style == "scope":
        audio_filter = f"[1:a]showwaves=s={wave_w}x{wave_h}:mode=line:colors=0x33d6a6[wave]"
    elif style == "radial":
        audio_filter = f"[1:a]avectorscope=s={wave_w}x{wave_h}:m=lissajous:draw=line:rc=124:gc=92:bc=255[wave]"
    elif style == "stars":
        audio_filter = f"[1:a]showwaves=s={wave_w}x{wave_h}:mode=p2p:colors=0xffffff|0x33d6a6[wave]"
    elif style == "retro":
        audio_filter = f"[1:a]showwaves=s={wave_w}x{wave_h}:mode=cline:colors=0xff007f|0x33d6a6[wave]"
    else:  # blur / custom / custom_image
        audio_filter = f"[1:a]showwaves=s={wave_w}x{wave_h}:mode=cline:colors=0x33d6a6|0x7c5cff[wave]"

    filters = []
    if has_bg_media:
        # Keep custom media pure: no waveform overlay, no extra elements unless subtitles are present
        filters.append(f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1[v2]")
    elif has_cover:
        filters.append(f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},gblur=sigma=22[bg]")
        filters.append(f"[0:v]scale={fg_w}:{fg_h}:force_original_aspect_ratio=decrease[fg]")
        if is_portrait:
            filters.append(f"[bg][fg]overlay=(W-w)/2:200[v1]")
            filters.append(audio_filter)
            filters.append(f"[v1][wave]overlay=(W-w)/2:H-480[v2]")
        else:
            filters.append(f"[bg][fg]overlay=(W-w)/2:(H-h)/2-50[v1]")
            filters.append(audio_filter)
            filters.append(f"[v1][wave]overlay=(W-w)/2:H-160[v2]")
    else:
        filters.append("[0:v]null[v1]")
        filters.append(audio_filter)
        filters.append(f"[v1][wave]overlay=(W-w)/2:(H-h)/2[v2]")

    last_v = "v2"
    if include_subtitles and srt_tmp and os.path.isfile(srt_tmp):
        escaped_srt = srt_tmp.replace("\\", "/").replace(":", r"\:")
        fsize = 38 if is_portrait else 34
        font_map = get_windows_fonts()
        chosen_font = (subtitle_font or "Impact").strip()
        font_path = font_map.get(chosen_font)
        windir = os.environ.get("WINDIR", r"C:\Windows")
        default_sys_fonts = os.path.join(windir, "Fonts")
        font_dir = os.path.dirname(font_path) if font_path and os.path.isfile(font_path) else default_sys_fonts
        font_dir_escaped = font_dir.replace("\\", "/").replace(":", r"\:")
        safe_font = chosen_font.replace("'", "").replace(",", "").strip() or "Impact"
        filters.append(f"[{last_v}]subtitles=filename='{escaped_srt}':fontsdir='{font_dir_escaped}':force_style='Fontname={safe_font},FontSize={fsize},PrimaryColour=&H00ffffff,OutlineColour=&HB0000000,BorderStyle=1,Outline=3.0,Shadow=1.5,Alignment=2,MarginV=45'[vout]")
        last_v = "vout"

    cmd.extend(["-filter_complex", ";".join(filters)])
    cmd.extend(["-map", f"[{last_v}]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", out_path])

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)

    # Clean up temp inputs
    for tmp in (audio_tmp, cover_tmp, bg_video_tmp):
        if tmp and os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    if is_temp_srt and srt_tmp and os.path.isfile(srt_tmp):
        try:
            os.remove(srt_tmp)
        except OSError:
            pass

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace")[-500:]
        raise ValueError(f"FFmpeg error: {err}")

    return {
        "ok": True,
        "name": out_name,
        "url": f"/api/view?filename={urllib.parse.quote(out_name)}&source=local",
        "download_url": f"/api/view?filename={urllib.parse.quote(out_name)}&source=local&download=1",
    }


def delete_history_item(del_id: str) -> dict:
    """Permanently delete a history item and all associated media files from disk."""
    if not del_id:
        return {"ok": False, "error": "No ID provided"}

    known_h_candidates = [
        HISTORY_PATH,
        os.path.join(DATA_DIR, "history.json"),
        os.path.join(APP_DIR, "data", "history.json"),
        os.path.join(APP_DIR, "dist", "data", "history.json"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\tA-MusicMaker\data\history.json"),
    ]
    candidate_renders_dirs = [
        RENDERS_DIR,
        os.path.join(DATA_DIR, "renders"),
        os.path.join(APP_DIR, "data", "renders"),
        os.path.join(APP_DIR, "dist", "data", "renders"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\tA-MusicMaker\data\renders"),
    ]

    files_to_delete = set()
    job_prefixes = set()
    base_stems = set()

    # 1. Collect target file names, job prefixes, and base names across history candidates
    for cand_h in known_h_candidates:
        if os.path.isfile(cand_h):
            try:
                h_list = load_json(cand_h, [])
                if isinstance(h_list, list):
                    for h in h_list:
                        if h.get("id") == del_id:
                            for m in (h.get("media") or []):
                                u = m.get("url") or ""
                                if "filename=" in u:
                                    qs = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
                                    fn = qs.get("filename", [""])[0]
                                    if fn:
                                        bfn = os.path.basename(fn)
                                        files_to_delete.add(bfn)
                                        base_stems.add(os.path.splitext(bfn)[0])
                                n = m.get("name") or ""
                                clean_n = re.sub(r"^\[.*?\]\s*", "", n).strip()
                                if clean_n:
                                    bcn = os.path.basename(clean_n)
                                    files_to_delete.add(bcn)
                                    base_stems.add(os.path.splitext(bcn)[0])
            except Exception as ex:
                print(f"[History Delete] Error inspecting {cand_h}: {ex}")

    # Extract job prefixes like render_1234567890_ or input_1234567890_
    for fn in list(files_to_delete):
        m = re.match(r"^(?:render|input)_([a-f0-9]{8,16})_", fn)
        if m:
            job_id = m.group(1)
            job_prefixes.add(f"render_{job_id}_")
            job_prefixes.add(f"input_{job_id}_")

    def _safe_remove(fpath: str) -> bool:
        if not os.path.isfile(fpath):
            return False
        for _ in range(4):
            try:
                os.remove(fpath)
                return True
            except PermissionError:
                time.sleep(0.06)
            except OSError:
                break
        return False

    deleted_files = []

    # 2. Delete matched files from all candidate renders directories
    for r_dir in candidate_renders_dirs:
        if not os.path.isdir(r_dir):
            continue

        # Exact filenames
        for fn in list(files_to_delete):
            full_p = os.path.join(r_dir, fn)
            if _safe_remove(full_p):
                deleted_files.append(fn)

        # Prefix matches and associated SRTs/videos
        try:
            for entry in os.listdir(r_dir):
                entry_p = os.path.join(r_dir, entry)
                if not os.path.isfile(entry_p):
                    continue
                should_del = False
                for pref in job_prefixes:
                    if entry.startswith(pref):
                        should_del = True
                        break
                if not should_del and base_stems:
                    for stem in base_stems:
                        if stem and (entry == f"{stem}.flac" or entry.startswith(f"{stem} (lines)") or entry.startswith(f"{stem}.bilingual") or entry.startswith(f"{stem}.en") or entry.startswith(f"{stem}.srt")):
                            should_del = True
                            break
                if should_del:
                    if _safe_remove(entry_p):
                        deleted_files.append(entry)
        except OSError:
            pass

        # Also check stems in uvr_stems subdirectory
        uvr_dir = os.path.join(r_dir, "uvr_stems")
        if os.path.isdir(uvr_dir):
            try:
                for sf in os.listdir(uvr_dir):
                    sfp = os.path.join(uvr_dir, sf)
                    if not os.path.isfile(sfp):
                        continue
                    should_del = False
                    for pref in job_prefixes:
                        if pref in sf:
                            should_del = True
                            break
                    for stem in base_stems:
                        if stem and stem in sf:
                            should_del = True
                            break
                    if should_del:
                        if _safe_remove(sfp):
                            deleted_files.append(f"uvr_stems/{sf}")
            except OSError:
                pass

    # 3. Remove entry from all history.json candidates (and purge duplicate entries referencing the deleted audio)
    for cand_h in known_h_candidates:
        if os.path.isfile(cand_h):
            try:
                h_list = load_json(cand_h, [])
                if isinstance(h_list, list):
                    new_list = []
                    for h in h_list:
                        if h.get("id") == del_id:
                            continue
                        audio_names = [os.path.basename(m.get("name") or "") for m in (h.get("media") or []) if m.get("kind") == "audio"]
                        audio_urls = [os.path.basename(urllib.parse.parse_qs(urllib.parse.urlparse(m.get("url") or "").query).get("filename", [""])[0]) for m in (h.get("media") or []) if m.get("kind") == "audio"]
                        if any(an in deleted_files for an in audio_names if an) or any(au in deleted_files for au in audio_urls if au):
                            continue
                        new_list.append(h)
                    save_json(cand_h, new_list)
            except Exception as ex:
                print(f"[History Delete] Error saving {cand_h}: {ex}")

    return {"ok": True, "id": del_id, "deleted_files": list(set(deleted_files))}


# --------------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quiet
        pass

    # helpers
    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _fail(self, message: str, status=400):
        self._json({"error": message}, status)

    # routing
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path, query = parsed.path, urllib.parse.parse_qs(parsed.query)
        try:
            if path == "/api/ping":
                STATE["last_ping"], STATE["had_ping"] = time.time(), True
                return self._json({"ok": True})
            if path == "/api/status":
                return self._json(self._status())
            if path == "/api/changelog":
                return self._json(self._get_changelog())
            if path == "/api/defaults":
                return self._json(workflow_defaults())
            if path == "/api/options":
                return self._json(brief_options())
            if path == "/api/templates":
                return self._json(load_json(PLENIO_TEMPLATES_PATH, {}))
            if path == "/api/last_settings":
                return self._json(load_json(LAST_SETTINGS_PATH, {}))
            if path == "/api/config":
                return self._json(config())
            if path == "/api/voice_models":
                models_dir = config().get("voice_models_dir")
                return self._json({
                    "available": voice_swap.get_applio_paths()["available"],
                    "models": voice_swap.list_voice_models(models_dir),
                })
            if path.startswith("/api/job/"):
                job = JOBS.get(path.rsplit("/", 1)[1])
                return self._json(public_job(job)) if job else self._fail("Unknown job", 404)
            if path == "/api/history":
                return self._json(self._get_history())
            if path == "/api/fonts":
                return self._json(get_fonts_payload())
            if path == "/api/font_file":
                return self._font_file(query)
            if path == "/api/view":
                return self._view(query)
            return self._static(path)
        except Exception as err:  # noqa: BLE001
            traceback.print_exc()
            self._fail(str(err), 500)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == "/api/video/upload_bg":
                clen = int(self.headers.get("Content-Length") or 0)
                if clen <= 0 or clen > 500 * 1024 * 1024:
                    return self._fail("Invalid file size (max 500 MB)", 400)
                ext = self.headers.get("X-File-Ext", "mp4").strip(".").lower()
                if ext not in ("mp4", "webm", "mov", "mkv", "avi", "png", "jpg", "jpeg", "webp"):
                    ext = "mp4"
                bg_name = f"bg_{int(time.time())}_{uuid.uuid4().hex[:6]}.{ext}"
                bg_path = os.path.join(RENDERS_DIR, bg_name)
                remaining = clen
                with open(bg_path, "wb") as f_out:
                    while remaining > 0:
                        chunk = self.rfile.read(min(remaining, 65536))
                        if not chunk:
                            break
                        f_out.write(chunk)
                        remaining -= len(chunk)
                return self._json({
                    "ok": True,
                    "name": bg_name,
                    "url": f"/api/view?filename={urllib.parse.quote(bg_name)}&source=local",
                })

            body = self._body()
            if path in ("/api/draft", "/api/render"):
                try:
                    save_json(LAST_SETTINGS_PATH, {
                        "brief": body.get("brief", {}),
                        "opts": body.get("options", {}),
                    })
                except Exception:
                    pass
            if path == "/api/draft":
                return self._json(public_job(start_draft(body)))
            if path == "/api/render":
                return self._json(public_job(start_render(body)))
            if path == "/api/song/new_take":
                return self._json(public_job(start_new_take(body)))
            if path == "/api/voice_swap":
                return self._json(public_job(start_voice_swap(body)))
            if path == "/api/translate_srt":
                return self._json(self._translate_srt(body))
            if path == "/api/cancel":
                job = JOBS.get(body.get("id"))
                if job:
                    job["cancel"] = True
                try:
                    client().interrupt()
                except ComfyError:
                    pass
                return self._json({"ok": True})
            if path == "/api/last_settings":
                save_json(LAST_SETTINGS_PATH, body if isinstance(body, dict) else {})
                return self._json({"ok": True})
            if path == "/api/config":
                config().update({k: v for k, v in body.items() if k in DEFAULT_CONFIG})
                save_json(CONFIG_PATH, config())
                return self._json(config())
            if path == "/api/comfy/start":
                return self._json(self._start_comfy())
            if path == "/api/plenio_player/launch":
                return self._json(self._launch_plenio_player())
            if path == "/api/video/render":
                try:
                    a_start = float(body.get("audio_start") or 0.0)
                except (ValueError, TypeError):
                    a_start = 0.0
                try:
                    a_dur = float(body.get("audio_duration") or 0.0)
                except (ValueError, TypeError):
                    a_dur = 0.0
                return self._json(render_video_ffmpeg(
                    body.get("audio_url") or "",
                    title=body.get("title") or "Song",
                    aspect=body.get("aspect") or "16:9",
                    cover_url=body.get("cover_url"),
                    srt_url=body.get("srt_url"),
                    style=body.get("style") or "retro",
                    bg_video_url=body.get("bg_video_url"),
                    duration_mode=body.get("duration_mode") or "audio",
                    subtitle_font=body.get("subtitle_font") or "Impact",
                    include_subtitles=bool(body.get("include_subtitles", True)),
                    subtitle_offset=float(body.get("subtitle_offset", 0.0) or 0.0),
                    subtitle_speed=float(body.get("subtitle_speed", 1.0) or 1.0),
                    audio_start=a_start,
                    audio_duration=a_dur if a_dur > 0.001 else None,
                ))
            if path == "/api/history/delete":
                del_id = body.get("id")
                return self._json(delete_history_item(del_id))
            self._fail("Unknown endpoint", 404)
        except (ConversionError, ComfyError, KeyError, ValueError, OSError) as err:
            self._fail(str(err), 400)
        except Exception as err:  # noqa: BLE001
            traceback.print_exc()
            self._fail(str(err), 500)

    # handlers
    def _status(self) -> dict:
        alive = client().is_alive()
        wf_ok = os.path.exists(workflow_path())
        plenio_api = False
        plenio_ver = None
        if alive:
            try:
                p_info = client().plenio_info()
                if isinstance(p_info, dict):
                    plenio_api = True
                    plenio_ver = p_info.get("plenio")
            except Exception:
                plenio_api = bool(client().has_plenio_api())
        info = {"version": APP_VERSION, "comfy": alive, "workflow": wf_ok, "workflow_path": workflow_path(), "comfy_url": config()["comfy_url"],
                "can_start": bool(config().get("comfy_start_command")), "plenio_player": bool(find_plenio_player_bat()),
                "plenio_api": plenio_api, "plenio_version": plenio_ver,
                "ffmpeg": bool(shutil.which("ffmpeg"))}
        if alive:
            try:
                dev = client().system_stats().get("devices", [{}])[0]
                info["gpu"] = dev.get("name")
                info["vram_free"] = dev.get("vram_free")
                info["vram_total"] = dev.get("vram_total")
            except (ComfyError, IndexError):
                pass
        return info

    def _get_history(self) -> list:
        items = load_json(HISTORY_PATH, [])
        if not isinstance(items, list):
            items = []
        changed = False

        # 1. Scan active renders directory files
        renders_files = []
        all_local_files_map = {}
        candidate_renders_dirs = [
            RENDERS_DIR,
            os.path.join(APP_DIR, "data", "renders"),
        ]
        for r_dir in candidate_renders_dirs:
            if os.path.isdir(r_dir):
                for rf in os.listdir(r_dir):
                    if rf not in all_local_files_map:
                        full_p = os.path.join(r_dir, rf)
                        if os.path.isfile(full_p):
                            all_local_files_map[rf] = full_p
                            renders_files.append(rf)

        # 2. Filter out orphaned items whose audio file no longer exists on disk
        valid_items = []
        for h in items:
            media = h.get("media") or []
            audio_items = [m for m in media if m.get("kind") == "audio"]
            if not audio_items:
                changed = True
                continue

            has_existing_audio = False
            for m in audio_items:
                m_name = m.get("name") or ""
                clean_m = re.sub(r"^\[.*?\]\s*", "", m_name)
                matched_rf = None
                if m_name in all_local_files_map:
                    matched_rf = m_name
                elif clean_m in all_local_files_map:
                    matched_rf = clean_m
                else:
                    for rf in renders_files:
                        if rf.endswith(clean_m) or clean_m in rf:
                            matched_rf = rf
                            break
                if matched_rf:
                    has_existing_audio = True
                    loc_url = f"/api/view?filename={urllib.parse.quote(matched_rf)}&source=local"
                    if m.get("url") != loc_url and "source=local" not in (m.get("url") or ""):
                        m["url"] = loc_url
                        changed = True

            if has_existing_audio:
                valid_items.append(h)
            else:
                changed = True

        items = valid_items

        # 3. Update existing items' subtitle URLs to point to local files if present
        for h in items:
            media = h.get("media") or []
            has_sub = any(m.get("kind") == "subtitle" for m in media)
            # Deduplicate subtitles if any
            sub_roles = {}
            cleaned_media = []
            for m in media:
                if m.get("kind") == "subtitle":
                    r = m.get("role") or "orig"
                    if r not in sub_roles:
                        sub_roles[r] = m
                        cleaned_media.append(m)
                    else:
                        changed = True
                else:
                    cleaned_media.append(m)
            media = cleaned_media
            h["media"] = media
            if not has_sub:
                audio_items = [m for m in media if m.get("kind") == "audio"]
                if audio_items:
                    a_name = audio_items[0].get("name", "")
                    title = h.get("title", "")
                    clean_t = re.sub(r'[\s_]+', '.*', re.escape(title[:25])) if title else ""
                    matched_srts = {}
                    for rf in renders_files:
                        if not rf.lower().endswith(".srt"):
                            continue
                        if (clean_t and re.search(clean_t, rf, re.IGNORECASE)) or (a_name and (rf in a_name or a_name in rf or os.path.splitext(a_name)[0] in rf)):
                            if rf.endswith(".bilingual-en.srt"):
                                matched_srts["bilingual"] = rf
                            elif rf.endswith(".en.srt"):
                                matched_srts["en"] = rf
                            elif "(sung)" in rf.lower() or rf.endswith(".sung.srt"):
                                matched_srts["sung"] = rf
                            elif rf.endswith(".srt"):
                                matched_srts["orig"] = rf

                    if matched_srts:
                        for role, label, key in (
                            ("sung", "🎤 Wie gesungen (.srt)", "sung"),
                            ("en", "🇬🇧 English (.srt)", "en"),
                            ("bilingual", "🇩🇪+🇬🇧 Bilingual (.srt)", "bilingual"),
                            ("orig", "🇩🇪 Original (.srt)", "orig"),
                        ):
                            rf = matched_srts.get(key)
                            if rf:
                                media.append({
                                    "node": "srt",
                                    "kind": "subtitle",
                                    "role": role,
                                    "label": label,
                                    "name": rf,
                                    "url": f"/api/view?filename={urllib.parse.quote(rf)}&source=local&download=1",
                                    "temp": False,
                                })
                                changed = True
                        h["media"] = media

        # 4. Auto-recover any uncataloged FLAC files from renders directory
        known_audio_names = set()
        for h in items:
            for m in (h.get("media") or []):
                if m.get("kind") == "audio":
                    known_audio_names.add(m.get("name", "").lower())
                    u = m.get("url", "")
                    if "filename=" in u:
                        fn = urllib.parse.parse_qs(urllib.parse.urlparse(u).query).get("filename", [""])[0]
                        known_audio_names.add(fn.lower())

        for rf, flac_full in list(all_local_files_map.items()):
            if rf.lower().endswith(".flac") and not rf.lower().startswith("temp_vid_"):
                rf_lower = rf.lower()
                clean_rf = re.sub(r"^render_[a-f0-9]+_", "", rf_lower)
                clean_rf = re.sub(r"^input_[a-f0-9]+_", "", clean_rf)
                song_base = re.sub(r"\.flac$", "", clean_rf)
                if rf_lower not in known_audio_names and clean_rf not in known_audio_names:
                    try:
                        rec = srt_translate.extract_plenio_record_from_flac(flac_full)
                    except Exception:
                        rec = None
                    docs = (rec.get("documents") or {}) if rec else {}
                    title = (rec.get("title") or (rec.get("audio", {}).get("tags", {}).get("title") if rec else "")) if rec else ""
                    if not title:
                        title = os.path.splitext(clean_rf)[0]
                        title = re.sub(r"^\d{4}-\d{2}-\d{2}\s*", "", title)
                    lyrics = (docs.get("lyrics") or {}).get("text") or ""
                    flac_mtime = int(os.path.getmtime(flac_full))
                    flac_media = [{
                        "node": "audio",
                        "kind": "audio",
                        "name": rf,
                        "url": f"/api/view?filename={urllib.parse.quote(rf)}&source=local",
                        "temp": False,
                    }]
                    for srf in renders_files:
                        if srf.lower().endswith(".srt") and song_base in srf.lower():
                            role = "bilingual" if ".bilingual-en" in srf else ("en" if ".en" in srf else ("sung" if "(sung)" in srf.lower() or srf.endswith(".sung.srt") else "orig"))
                            flac_media.append({
                                "node": "srt",
                                "kind": "subtitle",
                                "role": role,
                                "label": "🇬🇧 English (.srt)" if role == "en" else ("🇩🇪+🇬🇧 Bilingual (.srt)" if role == "bilingual" else ("🎤 Wie gesungen (.srt)" if role == "sung" else "🇩🇪 Original (.srt)")),
                                "name": srf,
                                "url": f"/api/view?filename={urllib.parse.quote(srf)}&source=local&download=1",
                                "temp": False,
                            })
                    items.append({
                        "id": uuid.uuid4().hex[:10],
                        "ts": flac_mtime,
                        "title": title or "Song",
                        "brief": None,
                        "sheet": {"title": title, "lyrics": lyrics},
                        "options": {},
                        "media": flac_media,
                        "texts": [],
                        "auto": False,
                    })
                    known_audio_names.add(rf_lower)
                    changed = True

        items.sort(key=lambda x: x.get("ts", 0), reverse=True)
        if changed:
            try:
                save_json(HISTORY_PATH, items)
            except Exception:
                pass
        return items

    def _start_comfy(self) -> dict:
        cmd = config().get("comfy_start_command")
        if not cmd:
            raise ValueError(_tr(
                "No start command configured for ComfyUI in settings.",
                "In den Einstellungen ist kein Startbefehl für ComfyUI hinterlegt.",
            ))
        cwd = config().get("comfy_dir") or None
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen(cmd, shell=True, cwd=cwd, creationflags=flags)
        return {"started": True}

    def _get_changelog(self) -> dict:
        cand_dirs = [
            APP_DIR,
            os.path.dirname(APP_DIR),
            BASE_DIR if "BASE_DIR" in globals() else "",
        ]
        for cdir in cand_dirs:
            if not cdir:
                continue
            cand = os.path.join(cdir, "CHANGELOG.md")
            if os.path.isfile(cand):
                try:
                    with open(cand, "r", encoding="utf-8") as f:
                        return {"content": f.read()}
                except OSError as ex:
                    return {"content": f"Fehler beim Lesen der CHANGELOG.md: {ex}"}
        return {"content": "# Changelog\n\nKeine CHANGELOG.md gefunden."}

    def _launch_plenio_player(self) -> dict:
        bat = find_plenio_player_bat()
        if not bat:
            raise ValueError(_tr("Plenio Player was not found.", "Plenio Player.bat wurde nicht gefunden."))
        cwd = os.path.dirname(bat)
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen([bat, "--port", "8766"], cwd=cwd, shell=True, creationflags=flags)
        return {"started": True, "port": 8766}

    def _translate_srt(self, body: dict) -> dict:
        audio_url = body.get("audio_url") or ""
        target_lang = body.get("target_lang")
        if not target_lang or target_lang == "auto":
            target_lang = srt_translate.get_auto_translation_target(fallback_lyrics or "")
        fallback_lyrics = None
        history = load_json(HISTORY_PATH, [])
        for h in history:
            media = h.get("media") or []
            if any(m.get("url") == audio_url for m in media):
                fallback_lyrics = (h.get("sheet") or {}).get("lyrics")
                break
        items = build_subtitles_for_audio(audio_url, target_lang=target_lang, fallback_lyrics=fallback_lyrics)
        if not items:
            raise ValueError(_tr(
                "No subtitles (.srt) found for this song.",
                "Für diesen Song wurden keine Untertitel (.srt) gefunden.",
            ))
        # Also attach to matching history entry if present
        history = load_json(HISTORY_PATH, [])
        changed = False
        for h in history:
            media = h.get("media") or []
            if any(m.get("url") == audio_url for m in media):
                kept = [m for m in media if m.get("kind") != "subtitle"]
                h["media"] = kept + items
                changed = True
        if changed:
            save_json(HISTORY_PATH, history[:200])
        return {"subtitles": items}

    def _font_file(self, query):
        name = query.get("name", [""])[0]
        if not name:
            return self._fail("Font name required", 400)
        fonts = get_windows_fonts()
        font_path = fonts.get(name)
        if not font_path or not os.path.isfile(font_path):
            return self._fail(f"Font file for '{name}' not found", 404)
        try:
            with open(font_path, "rb") as fh:
                data = fh.read()
            ext = os.path.splitext(font_path)[1].lower()
            if ext == ".ttf":
                ctype = "font/ttf"
            elif ext == ".otf":
                ctype = "font/otf"
            elif ext == ".woff2":
                ctype = "font/woff2"
            elif ext == ".woff":
                ctype = "font/woff"
            else:
                ctype = "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(data)
        except OSError as ex:
            return self._fail(str(ex), 500)

    def _stream_local_file(self, full: str, fname: str, query: dict):
        file_size = os.path.getsize(full)
        if fname.lower().endswith(".srt"):
            ctype = "text/plain; charset=utf-8"
        else:
            ctype = mimetypes.guess_type(fname)[0] or "audio/flac"

        range_header = self.headers.get("Range")
        start = 0
        end = file_size - 1
        status = 200

        if range_header and range_header.startswith("bytes="):
            ranges = range_header[6:].split("-")
            try:
                if ranges[0]:
                    start = int(ranges[0])
                if len(ranges) > 1 and ranges[1]:
                    end = int(ranges[1])
                end = min(end, file_size - 1)
                if start <= end and start < file_size:
                    status = 206
                else:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    return
            except ValueError:
                pass

        content_length = end - start + 1
        with open(full, "rb") as fh:
            fh.seek(start)
            data = fh.read(content_length)

        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        if query.get("download") == ["1"] or query.get("dl") == ["1"]:
            safe_ascii = re.sub(r'[^a-zA-Z0-9_.-]', '_', fname)
            safe_disp = urllib.parse.quote(fname)
            self.send_header("Content-Disposition", f'attachment; filename="{safe_ascii}"; filename*=UTF-8\'\'{safe_disp}')
        self.end_headers()
        self.wfile.write(data)

    def _view(self, query):
        if query.get("source") == ["local"]:
            fname = os.path.basename(query.get("filename", [""])[0])
            full = os.path.join(RENDERS_DIR, fname)
            if not os.path.isfile(full):
                # Search candidate fallback paths
                for cand in (
                    os.path.join(DATA_DIR, fname),
                    os.path.join(APP_DIR, "data", "renders", fname),
                    os.path.join(APP_DIR, "dist", "data", "renders", fname),
                    os.path.join(os.path.dirname(APP_DIR), "data", "renders", fname),
                    os.path.join(os.path.dirname(APP_DIR), "dist", "data", "renders", fname),
                    os.path.expandvars(rf"%LOCALAPPDATA%\Programs\tA-MusicMaker\data\renders\{fname}"),
                ):
                    if os.path.isfile(cand):
                        full = cand
                        break
            if not os.path.isfile(full):
                return self._fail("Local file not found", 404)
            return self._stream_local_file(full, fname, query)

        try:
            data, headers = client().view(query["filename"][0], query.get("subfolder", [""])[0],
                                          query.get("type", ["output"])[0], self.headers.get("Range"))
            fname = os.path.basename(query.get("filename", [""])[0])
            ctype = headers.get("Content-Type") or (mimetypes.guess_type(fname)[0] if fname else None) or "application/octet-stream"
            status = 206 if headers.get("Content-Range") else 200
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Access-Control-Allow-Origin", "*")
            if headers.get("Content-Range"):
                self.send_header("Content-Range", headers["Content-Range"])
            if query.get("download") == ["1"] or query.get("dl") == ["1"]:
                if fname:
                    safe_ascii = re.sub(r'[^a-zA-Z0-9_.-]', '_', fname)
                    safe_disp = urllib.parse.quote(fname)
                    self.send_header("Content-Disposition", f'attachment; filename="{safe_ascii}"; filename*=UTF-8\'\'{safe_disp}')
            self.end_headers()
            self.wfile.write(data)
            return
        except Exception:
            # Fallback to local renders if ComfyUI is offline or file is local
            target_fn = os.path.basename(query.get("filename", [""])[0])
            for cand_dir in (
                RENDERS_DIR,
                DATA_DIR,
                os.path.join(APP_DIR, "data", "renders"),
                os.path.join(APP_DIR, "dist", "data", "renders"),
                os.path.join(os.path.dirname(APP_DIR), "data", "renders"),
                os.path.join(os.path.dirname(APP_DIR), "dist", "data", "renders"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\tA-MusicMaker\data\renders"),
            ):
                if os.path.isdir(cand_dir):
                    cand_path = os.path.join(cand_dir, target_fn)
                    if os.path.isfile(cand_path):
                        return self._stream_local_file(cand_path, target_fn, query)
                    for rf in os.listdir(cand_dir):
                        if rf.endswith(target_fn) or target_fn in rf:
                            cand_path = os.path.join(cand_dir, rf)
                            if os.path.isfile(cand_path):
                                return self._stream_local_file(cand_path, rf, query)
            return self._fail("File not found locally or in ComfyUI", 404)
        self.end_headers()
        self.wfile.write(data)

    def _static(self, path: str):
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        full = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not full.startswith(WEB_DIR) or not os.path.isfile(full):
            return self._fail("Not found", 404)
        with open(full, "rb") as fh:
            data = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", (mimetypes.guess_type(full)[0] or "application/octet-stream") +
                         ("; charset=utf-8" if full.endswith((".html", ".js", ".css")) else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


# --------------------------------------------------------------------- main

def find_browser() -> str | None:
    for name in ("msedge", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    return next((c for c in candidates if os.path.exists(c)), None)


def open_window(url: str) -> bool:
    browser = find_browser()
    if browser:
        profile = os.path.join(DATA_DIR, "browser-profile")
        subprocess.Popen([browser, f"--app={url}", "--window-size=1320,900", f"--user-data-dir={profile}",
                          "--no-first-run", "--no-default-browser-check", "--disable-sync",
                          "--disable-features=msImplicitSignin,msEdgeSyncConsent,msUndersideSignIn"])
        return True
    webbrowser.open(url)
    return False


def watchdog(server: ThreadingHTTPServer):
    """Close the server when the app window was closed (no heartbeat for a while)."""
    while True:
        time.sleep(3)
        busy = any(j["status"] in ("queued", "running") for j in JOBS.values())
        if STATE["had_ping"] and not busy and time.time() - STATE["last_ping"] > 25:
            server.shutdown()
            return


def patch_pywebview_download_filter() -> None:
    """Ensure pywebview native SaveFileDialog sets specific file filters (e.g. MP4 Video (*.mp4)) instead of All Files."""
    try:
        from webview.platforms import edgechromium
        def custom_on_download_starting(self, sender, args):
            if not edgechromium.webview_settings.get("ALLOW_DOWNLOADS"):
                args.Cancel = True
                return

            dialog = edgechromium.WinForms.SaveFileDialog()
            try:
                import winreg
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
                ) as windows_key:
                    dialog.InitialDirectory = winreg.QueryValueEx(
                        windows_key, "{374DE290-123F-4565-9164-39C4925E467B}"
                    )[0]
            except Exception:
                pass

            fname = os.path.basename(args.ResultFilePath) if args.ResultFilePath else ""
            ext = os.path.splitext(fname)[1].lower()

            if ext == ".mp4":
                dialog.Filter = "MP4 Video (*.mp4)|*.mp4|Alle Dateien (*.*)|*.*"
                dialog.DefaultExt = "mp4"
            elif ext in (".flac", ".wav", ".mp3", ".ogg", ".m4a"):
                desc = ext[1:].upper()
                dialog.Filter = f"{desc} Audio (*{ext})|*{ext}|Alle Dateien (*.*)|*.*"
                dialog.DefaultExt = ext[1:]
            elif ext == ".srt":
                dialog.Filter = "Untertitel (*.srt)|*.srt|Alle Dateien (*.*)|*.*"
                dialog.DefaultExt = "srt"
            elif ext in (".png", ".jpg", ".jpeg", ".webp"):
                dialog.Filter = f"Bild (*{ext})|*{ext}|Alle Dateien (*.*)|*.*"
                dialog.DefaultExt = ext[1:]
            elif ext == ".pdf":
                dialog.Filter = "PDF Dokument (*.pdf)|*.pdf|Alle Dateien (*.*)|*.*"
                dialog.DefaultExt = "pdf"
            else:
                dialog.Filter = "Alle Dateien (*.*)|*.*"

            dialog.FilterIndex = 1
            dialog.RestoreDirectory = True
            dialog.FileName = fname

            result = dialog.ShowDialog(self.form)
            if result == edgechromium.WinForms.DialogResult.OK:
                args.ResultFilePath = dialog.FileName
            else:
                args.Cancel = True

        edgechromium.EdgeChrome.on_download_starting = custom_on_download_starting
    except Exception as ex:
        print("[pywebview] Note: download filter customization skipped:", ex)


def run_native_window(url: str, server: ThreadingHTTPServer) -> bool:
    """Open the UI in a native Windows desktop window using pywebview (Edge WebView2)."""
    try:
        import webview  # type: ignore
    except ImportError:
        return False

    try:
        patch_pywebview_download_filter()
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        bg = "#f3f4f8" if config().get("theme") == "light" else "#0f1117"
        webview.create_window(
            f"thomo.ART MusicMaker v{APP_VERSION} (Lantern House Edition)",
            url,
            width=1360,
            height=920,
            min_size=(960, 640),
            background_color=bg,
        )
        icon_path = os.path.join(BUNDLE_DIR, "app.ico")
        if not os.path.isfile(icon_path):
            icon_path = os.path.join(APP_DIR, "app.ico")
        webview_storage = os.path.join(DATA_DIR, "webview")
        os.makedirs(webview_storage, exist_ok=True)
        webview.start(
            icon=icon_path if os.path.isfile(icon_path) else None,
            private_mode=False,
            storage_path=webview_storage,
        )
        server.shutdown()
        server.server_close()
        return True
    except Exception as exc:
        print("pywebview window failed, falling back to browser mode:", exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-window", action="store_true")
    parser.add_argument("--browser", action="store_true", help="Open in browser app mode instead of native pywebview window")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    STATE["config"] = {**DEFAULT_CONFIG, **load_json(CONFIG_PATH, {})}
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/"
    print(f"tA-MusicMaker running on {url}  (ComfyUI: {config()['comfy_url']})")

    if not args.no_window and not args.browser:
        if run_native_window(url, server):
            print("Stopped.")
            return

    if not args.no_window:
        if open_window(url):
            threading.Thread(target=watchdog, args=(server,), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    print("Stopped.")


if __name__ == "__main__":
    main()
