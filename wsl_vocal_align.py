"""WSL GPU Vocal Isolation (Demucs) + Qwen3-ASR + Qwen3-ForcedAligner worker.

Run inside WSL with ComfyUI's python_embeded environment:
    python3 wsl_vocal_align.py --audio <path> --out <json_path> [--lyrics <txt_path>] [--vocals-cache <wav_path>] [--lang auto]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

PLENIO_ROOT = Path("/home/thomas/CEI1-DEV/ComfyUI/custom_nodes/Plenio-Music-Production-System")
ASR_MODEL_DIR = Path("/home/thomas/CEI1-DEV/ComfyUI/models/plenio/asr/qwen3-asr-1.7b-hf")
ALIGNER_MODEL_DIR = Path("/home/thomas/CEI1-DEV/ComfyUI/models/plenio/asr/qwen3-forcedaligner-0.6b-hf")
RATE = 16000

LANG_MAP = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
}

_ONES = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
)
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")


def _num_to_words(n: int) -> str:
    if n < 0 or n >= 1000:
        return str(n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        t, r = divmod(n, 10)
        return _TENS[t] + (f" {_ONES[r]}" if r else "")
    h, r = divmod(n, 100)
    if r == 0:
        return f"{_ONES[h]} hundred"
    return f"{_ONES[h]} {_num_to_words(r)}"


def _normalize_for_match(text: str) -> str:
    s = text.lower().replace("’", "'").replace("'", "")
    s = re.sub(r"\b(\d{1,3})\b", lambda m: _num_to_words(int(m.group(1))), s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _consonant_skeleton(norm: str) -> str:
    # Collapse vowels and double letters so phonetic near-misses ("oven door closed" vs "open door closed") align closely
    s = re.sub(r"[aeiouy\s]+", "", norm)
    return re.sub(r"(.)\1+", r"\1", s)


def _match_score(a: str, b: str) -> float:
    na = _normalize_for_match(a)
    nb = _normalize_for_match(b)
    if not na or not nb:
        return 0.0
    wa, wb = na.split(), nb.split()
    if not wa or not wb:
        return 0.0
    len_ratio = min(len(wa), len(wb)) / max(len(wa), len(wb))
    if len_ratio < 0.42:
        return 0.0
    char_sim = SequenceMatcher(None, na, nb).ratio()
    cons_sim = SequenceMatcher(None, _consonant_skeleton(na), _consonant_skeleton(nb)).ratio()
    word_sim = SequenceMatcher(None, wa, wb).ratio()
    return (0.45 * char_sim + 0.35 * cons_sim + 0.20 * word_sim) * (0.75 + 0.25 * len_ratio)


def _token_sim(a_norm: str, b_norm: str) -> float:
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    c_sim = SequenceMatcher(None, a_norm, b_norm).ratio()
    ca, cb = _consonant_skeleton(a_norm), _consonant_skeleton(b_norm)
    k_sim = SequenceMatcher(None, ca, cb).ratio() if (ca and cb) else c_sim
    return 0.55 * c_sim + 0.45 * k_sim


def _parse_lyrics_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if re.match(r"^\[.*\]$", s):
            continue
        lines.append(s)
    return lines


def _isolate_vocals(audio_path: Path, vocals_cache: Path | None) -> Path:
    if vocals_cache and vocals_cache.is_file() and vocals_cache.stat().st_size > 10_000:
        return vocals_cache

    tmp_dir = Path(tempfile.mkdtemp(prefix="demucs_vocals_"))
    try:
        cmd = [
            sys.executable,
            "-m",
            "demucs",
            "--two-stems=vocals",
            "-n",
            "htdemucs",
            "-d",
            "cuda",
            "-o",
            str(tmp_dir),
            str(audio_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        found = list(tmp_dir.rglob("vocals.wav"))
        if not found:
            raise RuntimeError("Demucs produced no vocals.wav")
        src = found[0]
        if vocals_cache:
            vocals_cache.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, vocals_cache)
            return vocals_cache
        kept = Path(tempfile.mktemp(suffix="_vocals.wav"))
        shutil.copyfile(src, kept)
        return kept
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _find_vocal_blocks(audio, min_silence_s: float = 0.8, target_max_s: float = 38.0) -> list[tuple[float, float]]:
    import numpy as np

    hop = int(0.05 * RATE)
    n_frames = len(audio) // hop
    if n_frames == 0:
        return [(0.0, len(audio) / RATE)]
    frames = audio[: n_frames * hop].reshape(n_frames, hop)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    peak_rms = float(np.percentile(rms, 95)) if len(rms) else 0.01
    thresh = max(1e-4, peak_rms * 0.04)
    is_silent = rms < thresh

    min_sil_frames = int(min_silence_s / 0.05)
    sil_spans = []
    start = None
    for i, s in enumerate(is_silent):
        if s and start is None:
            start = i
        elif not s and start is not None:
            if i - start >= min_sil_frames:
                sil_spans.append((start * 0.05, i * 0.05))
            start = None
    if start is not None and n_frames - start >= min_sil_frames:
        sil_spans.append((start * 0.05, n_frames * 0.05))

    total_s = len(audio) / RATE
    cuts = [0.0]
    cur = 0.0
    for s0, s1 in sil_spans:
        mid = (s0 + s1) / 2.0
        if mid - cur >= 12.0:
            cuts.append(mid)
            cur = mid
    if total_s - cur > 1.0:
        cuts.append(total_s)

    blocks = []
    for i in range(len(cuts) - 1):
        a, b = cuts[i], cuts[i + 1]
        while b - a > target_max_s:
            f0 = int((a + 18.0) * 20)
            f1 = min(n_frames - 1, int((a + target_max_s) * 20))
            if f1 > f0:
                best_f = f0 + int(np.argmin(rms[f0:f1]))
                split_t = best_f * 0.05
            else:
                split_t = a + target_max_s
            blocks.append((a, split_t))
            a = split_t
        if b - a >= 0.5:
            blocks.append((a, b))
    return blocks


def align_words_to_lyrics(all_words: list[dict], written_lines: list[str]) -> list[dict]:
    """Directly map exact word-level ASR timestamps from the isolated vocal stem onto written lyric lines.

    Every line's start and end timestamp comes directly from the actually sung words on the vocal stem,
    eliminating forced-aligner drift when the singer adds ad-libs, repeats choruses, or alters words.
    """
    line_norms = [_normalize_for_match(ln) for ln in written_lines]
    line_toks = [n.split() for n in line_norms]
    n_w = len(all_words)
    n_l = len(written_lines)

    results: list[dict] = []
    unmatched_buf: list[dict] = []

    def flush_unmatched(next_matched_start: float | None = None, next_first_tok: str = "") -> float | None:
        nonlocal unmatched_buf
        if not unmatched_buf:
            return None
        groups: list[list[dict]] = []
        for w in unmatched_buf:
            if groups and (w["start"] - groups[-1][-1]["end"]) > 0.65:
                groups.append([w])
            elif not groups:
                groups.append([w])
            else:
                groups[-1].append(w)
        unmatched_buf = []

        lead_in_start: float | None = None
        if groups and next_matched_start is not None:
            last_g = groups[-1]
            if 1 <= len(last_g) <= 2 and (next_matched_start - last_g[-1]["end"]) < 0.45:
                joined_norm = " ".join(x["norm"] for x in last_g)
                if next_first_tok and _token_sim(joined_norm, next_first_tok) >= 0.48:
                    lead_in_start = last_g[0]["start"]
                    groups.pop()

        valid_words: list[dict] = []
        for g in groups:
            if len(g) <= 2 and (g[-1]["end"] - g[0]["start"]) < 1.25:
                continue
            valid_words.extend(g)

        if not valid_words:
            return lead_in_start

        cur: list[dict] = []
        for w in valid_words:
            if cur:
                gap = w["start"] - cur[-1]["end"]
                prev_punct = bool(re.search(r"[.!?]$", cur[-1]["text"]))
                comma_punct = bool(re.search(r"[,;:]$", cur[-1]["text"]))
                dur = cur[-1]["end"] - cur[0]["start"]
                if (
                    (gap > 1.8)
                    or (gap > 1.15 and dur >= 1.2)
                    or (gap > 0.55 and len(cur) >= 4 and dur >= 1.2)
                    or (prev_punct and len(cur) >= 4 and dur >= 1.4)
                    or (comma_punct and len(cur) >= 7)
                    or len(cur) >= 12
                ):
                    if len(cur) >= 3 or (cur[-1]["end"] - cur[0]["start"]) >= 1.2:
                        results.append({
                            "start": round(cur[0]["start"], 3),
                            "end": round(cur[-1]["end"], 3),
                            "text": " ".join(x["text"] for x in cur),
                        })
                    cur = []
            cur.append(w)
        if cur and (len(cur) >= 3 or (cur[-1]["end"] - cur[0]["start"]) >= 1.2):
            results.append({
                "start": round(cur[0]["start"], 3),
                "end": round(cur[-1]["end"], 3),
                "text": " ".join(x["text"] for x in cur),
            })
        return lead_in_start

    i = 0
    prev_line_idx = -1
    while i < n_w:
        gap_before = (all_words[i]["start"] - all_words[i - 1]["end"]) if i > 0 else 9.9
        punct_before = bool(re.search(r"[.!?,;:]$", all_words[i - 1]["text"])) if i > 0 else True
        at_phrase_start = (i == 0) or (gap_before >= 0.35) or punct_before

        best = None  # (total_score, raw_sim, w_span, l_idx)
        for l_idx in range(n_l):
            ltoks = line_toks[l_idx]
            L = len(ltoks)
            if L == 0:
                continue
            if L <= 4:
                if not at_phrase_start:
                    continue
                if prev_line_idx > l_idx + 2:
                    continue

            s0 = _token_sim(all_words[i]["norm"], ltoks[0])
            s1 = _token_sim(all_words[i]["norm"], ltoks[1]) if L > 2 else 0.0
            first_sim = max(s0, s1 * 0.88)
            if first_sim < 0.50:
                continue

            min_span = max(2, int(round(L * 0.62))) if L >= 3 else L
            max_span = max(L + 2, int(round(L * 1.32)))

            for span in range(min_span, max_span + 1):
                j = i + span
                if j > n_w:
                    break
                if span > 1:
                    max_internal_gap = max(all_words[k]["start"] - all_words[k - 1]["end"] for k in range(i + 1, j))
                    if max_internal_gap > 2.2:
                        break
                e0 = _token_sim(all_words[j - 1]["norm"], ltoks[-1])
                e1 = _token_sim(all_words[j - 1]["norm"], ltoks[-2]) if L >= 3 else 0.0
                last_sim = max(e0, e1 * 0.88)
                is_expected_next = (l_idx == prev_line_idx + 1)
                if last_sim < (0.28 if (is_expected_next and s0 >= 0.85) else 0.45):
                    continue

                sub_norm = " ".join(all_words[k]["norm"] for k in range(i, j))
                sim = _match_score(sub_norm, line_norms[l_idx])
                min_req_sim = (0.62 if (s0 >= 0.85 and e0 >= 0.85) else 0.72) if L <= 4 else 0.55
                if sim < min_req_sim:
                    continue

                cut_short_pen = 0.0
                if j < n_w and (all_words[j]["start"] - all_words[j - 1]["end"]) < 0.55:
                    if _token_sim(all_words[j]["norm"], ltoks[-1]) > e0 + 0.20:
                        cut_short_pen = 0.16

                overreach_pen = 0.0
                if span > min_span and l_idx + 1 < n_l and line_toks[l_idx + 1]:
                    if _token_sim(all_words[j - 1]["norm"], line_toks[l_idx + 1][0]) > e0 + 0.15:
                        overreach_pen = 0.18

                if is_expected_next:
                    cont_bonus = 0.07
                elif prev_line_idx >= 0 and 0 < (l_idx - prev_line_idx) <= 3:
                    cont_bonus = 0.03
                elif prev_line_idx > l_idx:
                    cont_bonus = -0.03
                else:
                    cont_bonus = 0.0

                len_bonus = 0.05 * (1.0 - min(1.0, abs(span - L) / max(1, L)))
                total = sim + 0.12 * first_sim + 0.14 * last_sim + cont_bonus + len_bonus - cut_short_pen - overreach_pen
                if best is None or total > best[0]:
                    best = (total, sim, span, l_idx)

        if best is not None:
            _, sim, span, l_idx = best
            w_start = all_words[i]["start"]
            w_end = all_words[i + span - 1]["end"]
            lead_in = flush_unmatched(w_start, line_toks[l_idx][0] if line_toks[l_idx] else "")
            if lead_in is not None:
                w_start = lead_in
            results.append({
                "start": round(w_start, 3),
                "end": round(w_end, 3),
                "text": written_lines[l_idx],
            })
            prev_line_idx = l_idx
            i += span
        else:
            unmatched_buf.append(all_words[i])
            i += 1

    flush_unmatched()
    return results


def run_pipeline(audio_path: Path, lyrics_path: Path | None, out_path: Path, vocals_cache: Path | None, lang: str) -> None:
    if str(PLENIO_ROOT) not in sys.path:
        sys.path.insert(0, str(PLENIO_ROOT))

    import torch
    import torchaudio
    from plenio.third_party import qwen3_asr

    vocals_path = _isolate_vocals(audio_path, vocals_cache)
    wav, sr = torchaudio.load(str(vocals_path))
    wav = wav.mean(dim=0)
    if sr != RATE:
        wav = torchaudio.functional.resample(wav, sr, RATE)
    audio = wav.numpy().astype("float32")

    written_lines = _parse_lyrics_lines(lyrics_path.read_text(encoding="utf-8")) if lyrics_path and lyrics_path.is_file() else []
    blocks = _find_vocal_blocks(audio)

    lang_arg = LANG_MAP.get(lang.lower(), lang) if lang and lang.lower() != "auto" else None
    asr_cls, aligner_cls = qwen3_asr.models()

    # Pass 1: Vocal-stem ASR on natural pause blocks
    asr_proc = qwen3_asr.processor(ASR_MODEL_DIR)
    asr_model = asr_cls.from_pretrained(str(ASR_MODEL_DIR), dtype=torch.bfloat16, device_map="cuda")
    block_asr: list[str] = []
    detected_lang = lang_arg or "English"
    for a, b in blocks:
        piece = audio[int(a * RATE) : int(b * RATE)]
        opts = {"language": lang_arg} if lang_arg else {}
        inputs = asr_proc.apply_transcription_request(audio=piece, **opts).to(asr_model.device, asr_model.dtype)
        with torch.inference_mode():
            out = asr_model.generate(**inputs, max_new_tokens=int(64 + 8 * (b - a)), do_sample=False)
        parsed = asr_proc.decode(out[:, inputs["input_ids"].shape[1] :], return_format="parsed")[0]
        txt = (parsed.get("transcription") if isinstance(parsed, dict) else getattr(parsed, "transcription", "")) or ""
        if not lang_arg and isinstance(parsed, dict) and parsed.get("language"):
            detected_lang = str(parsed["language"])
        block_asr.append(txt.strip())

    del asr_model
    torch.cuda.empty_cache()

    # Pass 2: Forced-align the actually sung ASR words per block for exact word-level timestamps
    al_proc = qwen3_asr.processor(ALIGNER_MODEL_DIR)
    aligner = aligner_cls.from_pretrained(str(ALIGNER_MODEL_DIR), dtype=torch.bfloat16, device_map="cuda")

    all_words: list[dict] = []
    for (a, b), txt in zip(blocks, block_asr):
        if not re.search(r"[a-zA-Z0-9]", txt):
            continue
        piece = audio[int(a * RATE) : int(b * RATE)]
        inputs, word_lists = al_proc.prepare_forced_aligner_inputs(
            audio=piece, transcript=txt, language=detected_lang
        )
        inputs = inputs.to(aligner.device, aligner.dtype)
        with torch.inference_mode():
            logits = aligner(**inputs).logits
        items = al_proc.decode_forced_alignment(
            logits=logits,
            input_ids=inputs["input_ids"],
            word_lists=word_lists,
            timestamp_token_id=aligner.config.timestamp_token_id,
        )[0]
        raw_tokens = txt.strip().split()
        for idx, item in enumerate(items):
            w_txt = str(item.get("text") or "").strip()
            norm_t = _normalize_for_match(w_txt)
            if not norm_t:
                continue
            raw_tok = raw_tokens[idx] if idx < len(raw_tokens) else w_txt
            ws = a + float(item["start_time"])
            we = max(a + float(item["end_time"]), ws + 0.05)
            all_words.append({
                "text": raw_tok,
                "clean": w_txt,
                "norm": norm_t,
                "cons": _consonant_skeleton(norm_t),
                "start": ws,
                "end": we,
            })

    final_lines = align_words_to_lyrics(all_words, written_lines)

    # Enforce non-overlapping monotonic timings
    cleaned: list[dict] = []
    for item in final_lines:
        txt = item["text"].strip()
        if len(re.sub(r"[^a-zA-Z0-9]", "", txt)) < 2:
            continue
        if cleaned and item["start"] < cleaned[-1]["end"]:
            cleaned[-1]["end"] = round(max(cleaned[-1]["start"] + 0.15, item["start"] - 0.04), 3)
        cleaned.append(item)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"language": detected_lang, "lines": cleaned}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--vocals-cache", default="")
    ap.add_argument("--lang", default="auto")
    args = ap.parse_args()
    run_pipeline(
        audio_path=Path(args.audio),
        lyrics_path=Path(args.lyrics) if args.lyrics else None,
        out_path=Path(args.out),
        vocals_cache=Path(args.vocals_cache) if args.vocals_cache else None,
        lang=args.lang,
    )


if __name__ == "__main__":
    main()
