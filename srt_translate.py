"""Subtitle (.srt) extraction and translation (e.g. German -> English / Bilingual) for tA-MusicMaker.

Works zero-dependency using Python stdlib:
- Extracts timed lyrics directly from Plenio's embedded FLAC project record (`PLNO` block) or reads `.srt` files.
- Translates subtitle lines while keeping exact millisecond timestamps intact.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

PROJECT_ID = b"PLNO"
PROJECT_SCHEMA = b"plenio.project/1\x00"


def srt_timestamp(seconds: float) -> str:
    millis = max(0, round(float(seconds) * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def wrap_subtitle_line(text: str, limit: int = 42) -> str:
    text = " ".join(text.strip().split())
    if len(text) <= limit:
        return text
    spaces = [m.start() for m in re.finditer(r" ", text)]
    if not spaces:
        return text
    mid = len(text) / 2

    def cost(idx: int) -> float:
        rows = max(idx, len(text) - idx - 1)
        return abs(idx - mid) - (10 if text[idx - 1] in ",;:.!?–—" else 0) + (50 if rows > limit else 0)

    split = min(spaces, key=cost)
    return text[:split].rstrip() + "\n" + text[split + 1 :].lstrip()


def extract_plenio_record_from_flac(flac_path: str | Path) -> dict | None:
    """Read the embedded Plenio release record from a FLAC file's APPLICATION block."""
    path = Path(flac_path)
    if not path.is_file():
        return None
    try:
        with path.open("rb") as fh:
            if fh.read(4) != b"fLaC":
                return None
            while True:
                header = fh.read(4)
                if len(header) < 4:
                    return None
                kind = header[0] & 0x7F
                is_last = bool(header[0] & 0x80)
                length = int.from_bytes(header[1:4], "big")
                if kind == 2 and length > len(PROJECT_ID) + len(PROJECT_SCHEMA):
                    body = fh.read(length)
                    prefix = PROJECT_ID + PROJECT_SCHEMA
                    if body.startswith(prefix):
                        decomp = zlib.decompressobj(16 + zlib.MAX_WBITS)
                        raw = decomp.decompress(body[len(prefix) :])
                        return json.loads(raw.decode("utf-8"))
                else:
                    fh.seek(length, 1)
                if is_last:
                    return None
    except Exception:
        return None


def count_text_syllables(text: str) -> int:
    """Approximate syllable count of a line for proportional subtitle duration."""
    words = re.findall(r"[a-zA-ZäöüÄÖÜßáéíóú0-9']+", text)
    count = 0
    for w in words:
        vowels = len(re.findall(r"[aeiouyäöüáéíóú]+", w.lower()))
        count += max(1, vowels)
    return max(2, count)


def normalize_section_name(name: str) -> str:
    n = name.strip().lower()
    n = re.sub(r"[\d\.\-_]+", " ", n).strip()
    if "pre" in n and "chorus" in n:
        return "pre-chorus"
    if "post" in n and "chorus" in n:
        return "post-chorus"
    if "chorus" in n or "refrain" in n or "hook" in n:
        return "chorus"
    if "verse" in n or "strophe" in n:
        return "verse"
    if "bridge" in n:
        return "bridge"
    if "intro" in n:
        return "intro"
    if "outro" in n or "ending" in n:
        return "outro"
    if "interlude" in n or "solo" in n:
        return "interlude"
    return n


def count_bars_in_abc_chunk(lines: list[str]) -> int:
    vocal_bars = 0
    ins_bars = 0
    cur_voice = None
    for line in lines:
        sline = line.strip()
        if sline.startswith("V:"):
            cur_voice = "Vocal" if "Vocal" in sline else "Ins"
            continue
        if "|" in sline:
            parts = [b.strip() for b in sline.split("|") if b.strip()]
            cnt = 0
            for p in parts:
                m_z = re.match(r"^Z(\d+)?$", p)
                cnt += int(m_z.group(1)) if (m_z and m_z.group(1)) else 1
            if cur_voice == "Vocal":
                vocal_bars += cnt
            else:
                ins_bars += cnt
    return vocal_bars if vocal_bars > 0 else ins_bars


def align_score_and_lyric_sections(score_timed_secs: list[dict], lyric_secs: list[tuple[str, list[str]]]):
    """Align musical sections from ABC score with parsed lyric sections.
    Handles unlyricized intros, outros, interludes and pre-choruses that merge into verses.
    Returns list of (score_section_dict, list_of_lyric_subsections)."""
    if not score_timed_secs or not lyric_secs:
        return None

    lyr_names = [name for name, _ in lyric_secs]

    # Filter out score sections that are clearly non-lyric (intro/outro/interlude without corresponding lyrics)
    score_vocal = [
        s for s in score_timed_secs
        if not (s["name"] in ("intro", "outro", "interlude", "solo") and s["name"] not in lyr_names)
    ]
    if not score_vocal:
        score_vocal = score_timed_secs

    # 1. Direct match
    if len(score_vocal) == len(lyric_secs):
        return [(s, [l]) for s, l in zip(score_vocal, lyric_secs)]

    # 2. Merge pre-chorus/post-chorus into preceding section where score doesn't have an explicit pre-chorus
    merged_lyr_groups: list[list[tuple[str, list[str]]]] = []
    for l_name, l_lines in lyric_secs:
        expected_s = score_vocal[len(merged_lyr_groups)]["name"] if len(merged_lyr_groups) < len(score_vocal) else None
        if l_name == "pre-chorus" and expected_s != "pre-chorus" and merged_lyr_groups:
            merged_lyr_groups[-1].append((l_name, l_lines))
        elif l_name == "post-chorus" and expected_s != "post-chorus" and merged_lyr_groups:
            merged_lyr_groups[-1].append((l_name, l_lines))
        else:
            merged_lyr_groups.append([(l_name, l_lines)])

    if len(score_vocal) == len(merged_lyr_groups):
        return list(zip(score_vocal, merged_lyr_groups))

    return None


def extend_cues_until_next_sentence(cues: list[dict], pause_before_next: float = 1.0, max_duration: float = 6.0) -> list[dict]:
    """Extend each cue's display time until `pause_before_next` seconds before the next cue starts,
    providing a calm, professional subtitle pacing."""
    if not cues:
        return cues
    for i in range(len(cues)):
        t0 = cues[i]["start"]
        cur_end = cues[i]["end"]
        min_d = 1.4 if len(cues[i]["text"].split()) <= 2 else 2.2
        cues[i]["end"] = max(t0 + min_d, cur_end)

        if i + 1 < len(cues):
            next_start = cues[i + 1]["start"]
            target_end = next_start - pause_before_next
            # If gap between lines is tight (<= 1.2s), preserve at least a 0.15s visual transition
            if next_start - cues[i]["end"] <= 1.2:
                target_end = max(cues[i]["end"], next_start - 0.15)
            # Extend if target is later than current end
            if target_end > cues[i]["end"]:
                cues[i]["end"] = target_end
            max_allowed = max(t0 + 0.5, next_start - 0.08)
            cues[i]["end"] = min(t0 + max_duration, cues[i]["end"], max_allowed)
        else:
            # Last cue of song
            cues[i]["end"] = min(t0 + max_duration, cues[i]["end"] + 1.5)
    return cues


def synthesize_srt_from_record(rec: dict, fallback_lyrics: str | None = None) -> str | None:
    """Synthesize timed subtitle cues from embedded Plenio score and lyrics (or fallback lyrics)
    when Plenio's ASR worker was skipped or failed."""
    if not rec and not fallback_lyrics:
        return None
    rec = rec or {}
    docs = rec.get("documents") or {}
    lyrics_doc = docs.get("lyrics") or {}
    lyrics_text = (lyrics_doc.get("text") or "").strip() or (fallback_lyrics or "").strip()
    if not lyrics_text:
        return None

    score_doc = docs.get("score") or {}
    score_text = (score_doc.get("text") or "").strip()

    files = rec.get("files") or []
    duration = float(files[0].get("seconds", 0.0)) if files and files[0].get("seconds") else 0.0

    # Parse lyrics into sections and lines
    lyric_sections: list[tuple[str, list[str]]] = []
    cur_sec_name = "verse"
    cur_lines: list[str] = []
    for raw in lyrics_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            if cur_lines:
                lyric_sections.append((normalize_section_name(cur_sec_name), cur_lines))
            cur_sec_name = line[1:-1].strip()
            cur_lines = []
        else:
            cur_lines.append(line)
    if cur_lines:
        lyric_sections.append((normalize_section_name(cur_sec_name), cur_lines))

    all_plain_lines = [l for _, lines in lyric_sections for l in lines]
    if not all_plain_lines:
        return None

    cues: list[dict] = []
    parsed_with_score = False

    # Try parsing ABC score for timing
    if score_text:
        try:
            m_bpm = re.search(r"Q:(?:1/4=)?(\d+)", score_text)
            bpm = int(m_bpm.group(1)) if m_bpm else 120
            m_meter = re.search(r"M:(\d+)/(\d+)", score_text)
            m_num, m_den = (int(m_meter.group(1)), int(m_meter.group(2))) if m_meter else (4, 4)
            quarter_sec = 60.0 / max(20, bpm)
            bar_sec = quarter_sec * (4.0 * m_num / m_den)

            # Split score into sections with lines and compute bars
            raw_score_secs: list[tuple[str, list[str]]] = []
            cur_sname = "intro"
            cur_slines: list[str] = []
            for raw_line in score_text.splitlines():
                sline = raw_line.strip()
                if sline.startswith("%"):
                    raw_score_secs.append((normalize_section_name(cur_sname), cur_slines))
                    cur_sname = sline[1:].strip()
                    cur_slines = []
                else:
                    cur_slines.append(sline)
            raw_score_secs.append((normalize_section_name(cur_sname), cur_slines))

            score_secs_timed: list[dict] = []
            cur_bar_offset = 0
            for name, slines in raw_score_secs:
                bars = count_bars_in_abc_chunk(slines)
                phrases = []
                cur_v = None
                for l in slines:
                    sl = l.strip()
                    if sl.startswith("V:"):
                        cur_v = "Vocal" if "Vocal" in sl else "Ins"
                    elif cur_v == "Vocal" and "|" in sl:
                        parts = [b.strip() for b in sl.split("|") if b.strip()]
                        cnt = sum(int(re.match(r"^Z(\d+)?$", p).group(1)) if (re.match(r"^Z(\d+)?$", p) and re.match(r"^Z(\d+)?$", p).group(1)) else 1 for p in parts)
                        notes = len(re.findall(r"[A-Ga-g]", sl))
                        phrases.append({"bars": cnt, "notes": notes})
                start_t = cur_bar_offset * bar_sec
                dur_t = bars * bar_sec
                cur_bar_offset += bars
                if bars > 0 or name not in ("intro",):
                    score_secs_timed.append({
                        "name": name,
                        "bars": bars,
                        "start": start_t,
                        "dur": dur_t,
                        "phrases": phrases,
                    })

            aligned = align_score_and_lyric_sections(score_secs_timed, lyric_sections)
            if aligned:
                def _split_subsections(s_info: dict, subsecs: list[tuple[str, list[str]]]):
                    if len(subsecs) == 1:
                        return [(s_info["start"], s_info["dur"], subsecs[0][0], subsecs[0][1])]
                    total_bars = s_info.get("bars", 0)
                    phrases = s_info.get("phrases", [])
                    cum_phrase_bars = []
                    cb = 0
                    for p in phrases:
                        cb += p.get("bars", 0)
                        cum_phrase_bars.append(cb)

                    name0, lines0 = subsecs[0]
                    name1, lines1 = subsecs[1]
                    if name0 == "verse" and name1 == "pre-chorus":
                        target_a = 16 if total_bars >= 20 else 8
                    elif name0 == "chorus" and name1 == "post-chorus":
                        target_a = 16 if total_bars >= 20 else 8
                    else:
                        target_a = round(total_bars * len(lines0) / (len(lines0) + len(lines1)))

                    if cum_phrase_bars and len(cum_phrase_bars) > 1:
                        bars_a = min(cum_phrase_bars[:-1], key=lambda b: abs(b - target_a))
                    else:
                        bars_a = min(max(2, total_bars - 2), max(2, target_a))
                    bars_b = max(1, total_bars - bars_a)
                    start_a = s_info["start"]
                    dur_a = bars_a * bar_sec
                    start_b = start_a + dur_a
                    dur_b = bars_b * bar_sec
                    return [
                        (start_a, dur_a, name0, lines0),
                        (start_b, dur_b, name1, lines1),
                    ]

                for s_info, subsecs in aligned:
                    parts = _split_subsections(s_info, subsecs)
                    for part_start, part_dur, _, lines in parts:
                        total_syl = sum(count_text_syllables(l) for l in lines) or len(lines)
                        usable_dur = max(1.5, part_dur - 0.25)
                        cur_t = part_start
                        for line in lines:
                            syl = count_text_syllables(line)
                            l_dur = usable_dur * (syl / total_syl)
                            t0 = cur_t
                            t1 = min(part_start + part_dur - 0.1, t0 + l_dur - 0.15)
                            if duration > 0:
                                t1 = min(duration, t1)
                            cues.append({"start": t0, "end": max(t0 + 0.5, t1), "text": line})
                            cur_t += l_dur
                parsed_with_score = bool(cues)
        except Exception as ex:
            print(f"[SRT Synthesizer] Score alignment failed, using fallback: {ex}")
            parsed_with_score = False

    # Fallback if no score or score parsing failed: distribute proportionally across audio duration
    if not parsed_with_score or not cues:
        cues = []
        total_time = duration if duration > 10.0 else len(all_plain_lines) * 4.0
        intro_t = min(12.0, max(4.0, total_time * 0.08))
        outro_t = min(10.0, max(3.0, total_time * 0.05))
        singing_time = max(10.0, total_time - intro_t - outro_t)
        total_syl = sum(count_text_syllables(l) for l in all_plain_lines) or len(all_plain_lines)
        cur_t = intro_t
        for i, txt in enumerate(all_plain_lines):
            syl = count_text_syllables(txt)
            l_dur = singing_time * (syl / total_syl)
            t0 = cur_t
            t1 = min(total_time - 0.2, t0 + l_dur - 0.2)
            cues.append({"start": t0, "end": max(t0 + 0.5, t1), "text": txt})
            cur_t += l_dur

    cues = extend_cues_until_next_sentence(cues)
    blocks = []
    for idx, c in enumerate(cues, start=1):
        txt = wrap_subtitle_line(c["text"])
        if txt:
            blocks.append(f"{idx}\n{srt_timestamp(c['start'])} --> {srt_timestamp(c['end'])}\n{txt}")
    return "\n\n".join(blocks) + "\n" if blocks else None


def get_whisper_model_dir() -> str:
    """Return local directory for cached Whisper models (downloads on demand if missing)."""
    local_dir = os.path.abspath("models/whisper")
    if os.path.isdir(local_dir):
        return local_dir
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    model_dir = os.path.join(appdata, "tA-MusicMaker", "models", "whisper")
    os.makedirs(model_dir, exist_ok=True)
    return model_dir


def align_lyrics_with_whisper(flac_path: str | Path, rec: dict | None = None, fallback_lyrics: str | None = None) -> str | None:
    """Align lyrics with actual audio speech using faster-whisper.
    Downloads the model automatically to local storage if not present on the PC."""
    try:
        from faster_whisper import WhisperModel
    except Exception as ex:
        print(f"[Whisper Alignment] faster-whisper nicht verfuegbar ({ex}), nutze Score-Fallback.")
        return None

    if not rec:
        rec = extract_plenio_record_from_flac(flac_path)
    if not rec and not fallback_lyrics:
        return None

    docs = (rec or {}).get("documents") or {}
    lyrics_text = (docs.get("lyrics") or {}).get("text") or (fallback_lyrics or "").strip()
    score_text = (docs.get("score") or {}).get("text") or ""
    if not lyrics_text:
        return None

    lyric_sections: list[tuple[str, list[str]]] = []
    cur_sec_name = "verse"
    cur_lines: list[str] = []
    for raw in lyrics_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            inner = line[1:-1].strip()
            norm_sec = normalize_section_name(inner)
            is_structural = any(norm_sec == s or norm_sec.startswith(s) for s in ["intro", "verse", "chorus", "bridge", "outro", "pre-chorus", "post-chorus", "hook", "refrain"])
            if is_structural:
                if cur_lines:
                    lyric_sections.append((normalize_section_name(cur_sec_name), cur_lines))
                cur_sec_name = inner
                cur_lines = []
        else:
            cur_lines.append(line)
    if cur_lines:
        lyric_sections.append((normalize_section_name(cur_sec_name), cur_lines))

    all_lines = [l for _, lines in lyric_sections for l in lines]
    if not all_lines:
        return None

    # 1. Parse musical sections if score exists
    score_secs_timed = []
    bar_sec = 2.0
    if score_text:
        try:
            m_bpm = re.search(r"Q:(?:1/4=)?(\d+)", score_text)
            bpm = int(m_bpm.group(1)) if m_bpm else 120
            m_meter = re.search(r"M:(\d+)/(\d+)", score_text)
            m_num, m_den = (int(m_meter.group(1)), int(m_meter.group(2))) if m_meter else (4, 4)
            quarter_sec = 60.0 / max(20, bpm)
            bar_sec = quarter_sec * (4.0 * m_num / m_den)

            raw_score_secs: list[tuple[str, list[str]]] = []
            cur_sname = "intro"
            cur_slines: list[str] = []
            for raw_line in score_text.splitlines():
                sline = raw_line.strip()
                if sline.startswith("%"):
                    raw_score_secs.append((normalize_section_name(cur_sname), cur_slines))
                    cur_sname = sline[1:].strip()
                    cur_slines = []
                else:
                    cur_slines.append(sline)
            raw_score_secs.append((normalize_section_name(cur_sname), cur_slines))

            cur_bar_offset = 0
            for name, slines in raw_score_secs:
                bars = count_bars_in_abc_chunk(slines)
                start_t = cur_bar_offset * bar_sec
                dur_t = bars * bar_sec
                cur_bar_offset += bars
                if bars > 0 or name not in ("intro",):
                    score_secs_timed.append({
                        "name": name,
                        "bars": bars,
                        "start": start_t,
                        "dur": dur_t,
                        "end": start_t + dur_t,
                    })
        except Exception:
            pass

    files = (rec or {}).get("files") or []
    audio_dur = float(files[0].get("seconds", 0.0)) if files and files[0].get("seconds") else 0.0

    # 2. Transcribe audio with Whisper
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    model_dir = get_whisper_model_dir()
    prompt = " ".join(" ".join(all_lines).split()[:200])

    words = []
    try:
        try:
            model = WhisperModel("base", device="cpu", compute_type="int8", download_root=model_dir)
        except Exception:
            model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root=model_dir)
        segments, info = model.transcribe(str(flac_path), vad_filter=False, word_timestamps=True, initial_prompt=prompt, condition_on_previous_text=False)
        if hasattr(info, "duration") and info.duration:
            audio_dur = max(audio_dur, float(info.duration))
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    # Filter out zero-duration hallucination artifacts
                    if w.end - w.start >= 0.06:
                        cw = re.sub(r"[^\w]", "", w.word.lower())
                        if cw:
                            words.append({"clean": cw, "start": float(w.start), "end": float(w.end), "raw": w.word})
    except Exception as ex:
        print(f"[Whisper] Transkription fehlgeschlagen ({ex}), nutze Score-Fallback.")
        return None

    if not words:
        return None

    # 3. Map lyric sections to score sections or proportional song bounds
    lyric_sec_bounds: list[tuple[float, float]] = []
    if score_secs_timed:
        sec_sc_cursor = 0
        last_bound_end = 0.0
        for sname, slines in lyric_sections:
            matched_sc = None
            for i in range(sec_sc_cursor, len(score_secs_timed)):
                sc = score_secs_timed[i]
                if sc["name"] == sname:
                    matched_sc = sc
                    sec_sc_cursor = i + 1
                    break
            if matched_sc:
                b_start = max(last_bound_end, matched_sc["start"])
                b_end = max(b_start + len(slines) * 2.0, matched_sc["end"])
                lyric_sec_bounds.append((b_start, b_end))
                last_bound_end = b_end
            else:
                next_sc_start = None
                for i in range(sec_sc_cursor, len(score_secs_timed)):
                    sc = score_secs_timed[i]
                    if sc["start"] > last_bound_end:
                        next_sc_start = sc["start"]
                        break
                b_start = last_bound_end
                b_end = next_sc_start if (next_sc_start and next_sc_start > b_start) else (b_start + len(slines) * 4.0)
                lyric_sec_bounds.append((b_start, b_end))
                last_bound_end = b_end
    else:
        total_time = audio_dur if audio_dur > 20.0 else len(all_lines) * 4.0
        intro_pad = min(12.0, max(3.0, total_time * 0.06))
        outro_pad = min(10.0, max(3.0, total_time * 0.05))
        avail_time = max(10.0, total_time - intro_pad - outro_pad)
        total_lines_count = sum(len(slines) for _, slines in lyric_sections) or 1
        cur_b_start = intro_pad
        for sname, slines in lyric_sections:
            sec_dur = avail_time * (len(slines) / total_lines_count)
            lyric_sec_bounds.append((cur_b_start, cur_b_start + sec_dur))
            cur_b_start += sec_dur

    # 4. Section-bounded audio alignment with Whisper word matching
    cues = []
    last_cue_end = 0.0

    for (sname, slines), (sec_start, sec_end) in zip(lyric_sections, lyric_sec_bounds):
        # Words belonging to this section window (+ generous margin for early pickups or trailing sustains)
        sec_words = [w for w in words if (sec_start - 3.5) <= w["start"] <= (sec_end + 3.5)]
        cur_w_idx = 0

        for l_idx, line in enumerate(slines):
            clean_words = re.findall(r"[a-z0-9äöüß]+", line.lower())
            if not clean_words:
                continue
            content_words = [w for w in clean_words if len(w) >= 3] or clean_words

            best_span = None
            best_score = 0.0
            target_len = len(clean_words)

            for i in range(cur_w_idx, len(sec_words)):
                min_k = max(1, target_len - 2)
                max_k = min(target_len + 4, len(sec_words) - i + 1)
                for k in range(min_k, max_k):
                    cand_slice = [sec_words[i + m]["clean"] for m in range(k)]
                    matches = 0.0
                    for cw in cand_slice:
                        for tw in content_words:
                            if cw == tw:
                                matches += 1.0
                                break
                            elif len(cw) >= 4 and len(tw) >= 4 and (cw in tw or tw in cw):
                                matches += 0.8
                                break

                    if cand_slice and any(cand_slice[0] == tw or (len(cand_slice[0]) >= 4 and len(tw) >= 4 and cand_slice[0] in tw) for tw in content_words[:2]):
                        matches += 1.0
                    if cand_slice and any(cand_slice[-1] == tw or (len(cand_slice[-1]) >= 4 and len(tw) >= 4 and cand_slice[-1] in tw) for tw in content_words[-2:]):
                        matches += 1.0

                    score = matches / max(1, len(content_words))
                    if score > best_score:
                        best_score = score
                        best_span = (i, i + k)

            if best_score >= 0.28 and best_span is not None:
                w_start = sec_words[best_span[0]]["start"]
                w_end = sec_words[best_span[1] - 1]["end"]
                cur_w_idx = best_span[1]
                t0 = max(last_cue_end + 0.08, w_start)
                min_d = 1.4 if len(clean_words) <= 2 else 2.5
                t1 = max(t0 + min_d, min(t0 + 5.5, w_end))
                cues.append({"start": t0, "end": t1, "text": line})
                last_cue_end = t1
            else:
                # Interpolate line within the section slot
                rem_lines = len(slines) - l_idx
                rem_time = max(rem_lines * 2.0, sec_end - max(last_cue_end, sec_start))
                slot_dur = rem_time / rem_lines
                t0 = max(last_cue_end + 0.15, sec_start + l_idx * slot_dur)
                est_dur = max(2.0, min(slot_dur - 0.2, len(clean_words) * 0.45))
                t1 = t0 + est_dur
                cues.append({"start": t0, "end": t1, "text": line})
                last_cue_end = t1

    # 5. Enforce strict monotonicity and prevent overlap
    for i in range(len(cues) - 1):
        if cues[i + 1]["start"] <= cues[i]["start"]:
            cues[i + 1]["start"] = cues[i]["start"] + 0.5
        if cues[i]["end"] > cues[i + 1]["start"] - 0.08:
            cues[i]["end"] = max(cues[i]["start"] + 0.5, cues[i + 1]["start"] - 0.08)

    # 6. Apply calm subtitle extension until 1.0s before next sentence
    cues = extend_cues_until_next_sentence(cues)
    blocks = []
    for idx, c in enumerate(cues, start=1):
        txt = wrap_subtitle_line(c["text"])
        if txt:
            blocks.append(f"{idx}\n{srt_timestamp(c['start'])} --> {srt_timestamp(c['end'])}\n{txt}")
    return "\n\n".join(blocks) + "\n" if blocks else None


def _format_timing_lines_to_srt(lines: list[dict]) -> str | None:
    parsed_cues = []
    for line in lines:
        start = float(line.get("start", 0.0))
        end = float(line.get("end", start + 2.0))
        txt = str(line.get("text") or "")
        parsed_cues.append({"start": start, "end": end, "text": txt})
    parsed_cues = extend_cues_until_next_sentence(parsed_cues)
    blocks = []
    for idx, c in enumerate(parsed_cues, start=1):
        txt = wrap_subtitle_line(c["text"])
        if txt:
            blocks.append(f"{idx}\n{srt_timestamp(c['start'])} --> {srt_timestamp(c['end'])}\n{txt}")
    if blocks:
        return "\n\n".join(blocks) + "\n"
    return None


def extract_sung_srt_from_flac(flac_path: str | Path) -> str | None:
    """Extract the actually sung lyrics `(sung).srt` from a Plenio FLAC file's embedded timing record."""
    rec = extract_plenio_record_from_flac(flac_path)
    if not rec:
        return None
    timings = rec.get("timing") or []
    if timings and isinstance(timings, list):
        sung_info = timings[0].get("sung")
        if isinstance(sung_info, dict) and sung_info.get("lines"):
            return _format_timing_lines_to_srt(sung_info.get("lines") or [])
    return None


def extract_srt_from_flac(flac_path: str | Path, fallback_lyrics: str | None = None, prefer_sung: bool = False) -> str | None:
    """Build the original `(lines).srt` or `(sung).srt` content from a Plenio FLAC file's embedded timing record,
    or via local Whisper ASR alignment, or synthesize from score when ASR did not run."""
    rec = extract_plenio_record_from_flac(flac_path)
    if not rec and not fallback_lyrics:
        return None
    rec = rec or {}

    # 1. Check embedded timing record from server ASR
    timings = rec.get("timing") or []
    if timings and isinstance(timings, list):
        first_t = timings[0]
        sung_info = first_t.get("sung")
        lines = None
        if prefer_sung and isinstance(sung_info, dict) and sung_info.get("lines"):
            lines = sung_info.get("lines") or []
        elif first_t.get("lines"):
            lines = first_t.get("lines") or []
        elif isinstance(sung_info, dict) and sung_info.get("lines"):
            lines = sung_info.get("lines") or []

        if lines:
            res = _format_timing_lines_to_srt(lines)
            if res:
                return res

    # 2. Local Whisper ASR Audio-Alignment (downloads model on demand if not present on PC)
    whisper_srt = align_lyrics_with_whisper(flac_path, rec=rec, fallback_lyrics=fallback_lyrics)
    if whisper_srt:
        return whisper_srt

    # 3. Fallback: synthesize from embedded score and lyrics
    return synthesize_srt_from_record(rec, fallback_lyrics=fallback_lyrics)


def parse_srt(srt_text: str) -> list[dict]:
    """Parse an SRT string into a list of {'index': str, 'time': str, 'text': str}."""
    norm = srt_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not norm:
        return []
    raw_blocks = re.split(r"\n\s*\n", norm)
    cues = []
    for block in raw_blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) >= 2 and "-->" in lines[1]:
            cues.append({
                "index": lines[0],
                "time": lines[1],
                "text": "\n".join(lines[2:]),
            })
        elif len(lines) >= 2 and "-->" in lines[0]:
            cues.append({
                "index": str(len(cues) + 1),
                "time": lines[0],
                "text": "\n".join(lines[1:]),
            })
    return cues


def format_srt(cues: list[dict]) -> str:
    blocks = [f"{i}\n{c['time']}\n{c['text']}" for i, c in enumerate(cues, start=1)]
    return "\n\n".join(blocks) + "\n" if blocks else ""


def parse_srt_timestamp(ts_str: str) -> float:
    try:
        parts = ts_str.strip().replace(".", ",").split(":")
        if len(parts) == 3:
            h, m, sm = parts
            s, ms = sm.split(",")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
        elif len(parts) == 2:
            m, sm = parts
            s, ms = sm.split(",")
            return int(m) * 60 + int(s) + int(ms) / 1000.0
    except Exception:
        pass
    return 0.0


def adjust_srt_timing(srt_text: str, offset_sec: float = 0.0, speed_factor: float = 1.0,
                      clip_start: float = 0.0, clip_duration: float | None = None) -> str:
    """Apply manual offset (in seconds), speed multiplier, and optional clip slicing to an SRT string."""
    if not srt_text:
        return ""
    if abs(offset_sec) < 0.001 and abs(speed_factor - 1.0) < 0.001 and abs(clip_start) < 0.001 and (clip_duration is None or clip_duration <= 0):
        return srt_text
    cues = parse_srt(srt_text)
    if not cues:
        return srt_text
    clip_end = (clip_start + clip_duration) if (clip_duration is not None and clip_duration > 0.001) else None
    new_blocks = []
    idx = 1
    for c in cues:
        t_str = c.get("time") or ""
        if "-->" not in t_str:
            continue
        p1, p2 = [p.strip() for p in t_str.split("-->")]
        t0 = parse_srt_timestamp(p1)
        t1 = parse_srt_timestamp(p2)
        # Scale
        t0_scaled = t0 * speed_factor
        t1_scaled = t1 * speed_factor
        # Clip filtering
        if clip_start > 0.001 and t1_scaled <= clip_start:
            continue
        if clip_end is not None and t0_scaled >= clip_end:
            continue
        # Shift relative to clip_start and apply offset_sec
        new_t0 = max(0.0, t0_scaled - clip_start + offset_sec)
        new_t1 = max(new_t0 + 0.3, t1_scaled - clip_start + offset_sec)
        if clip_end is not None:
            max_clip_dur = clip_end - clip_start
            if new_t0 >= max_clip_dur:
                continue
            new_t1 = min(max_clip_dur, new_t1)
            if new_t1 <= new_t0:
                new_t1 = new_t0 + 0.3
        txt = c.get("text", "")
        new_blocks.append(f"{idx}\n{srt_timestamp(new_t0)} --> {srt_timestamp(new_t1)}\n{txt}")
        idx += 1
    return "\n\n".join(new_blocks) + "\n" if new_blocks else srt_text


def translate_lines(lines: list[str], target_lang: str = "en", source_lang: str = "auto") -> list[str]:
    """Translate a list of lyric lines into `target_lang` via Google Translate GTX endpoint,
    with robust error handling and fallback so translations never crash."""
    if not lines:
        return []
    import time
    clean_lines = [" ".join(l.split()) for l in lines]
    out: list[str] = []
    batch_size = 25
    for start in range(0, len(clean_lines), batch_size):
        chunk = clean_lines[start : start + batch_size]
        joined = "\n".join(chunk)
        success = False
        # Try batch request
        try:
            url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode({
                "client": "gtx",
                "sl": source_lang,
                "tl": target_lang,
                "dt": "t",
                "q": joined,
            })
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            translated_text = "".join(part[0] for part in (data[0] or []) if part and part[0])
            split_trans = [t.strip() for t in translated_text.split("\n")]
            if len(split_trans) == len(chunk):
                out.extend(split_trans)
                success = True
        except Exception as ex:
            # e.g. HTTP 429 Too Many Requests or timeout
            pass

        if success:
            continue

        # Fallback: line by line with backoff or keep original text
        for single in chunk:
            translated_single = None
            try:
                time.sleep(0.2)
                u2 = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode({
                    "client": "gtx",
                    "sl": source_lang,
                    "tl": target_lang,
                    "dt": "t",
                    "q": single,
                })
                r2 = urllib.request.Request(u2, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(r2, timeout=6) as resp2:
                    d2 = json.loads(resp2.read().decode("utf-8"))
                translated_single = "".join(p[0] for p in (d2[0] or []) if p and p[0]).strip()
            except Exception:
                pass
            out.append(translated_single or single)
    return out


def translate_srt(srt_text: str, target_lang: str = "en", bilingual: bool = False) -> str:
    """Translate an SRT string while preserving all timestamps."""
    cues = parse_srt(srt_text)
    if not cues:
        return srt_text
    orig_texts = [c["text"] for c in cues]
    try:
        translated = translate_lines(orig_texts, target_lang=target_lang)
    except Exception:
        translated = orig_texts
    new_cues = []
    for cue, trans in zip(cues, translated):
        wrapped_en = wrap_subtitle_line(trans)
        if bilingual:
            orig_flat = " ".join(cue["text"].split())
            trans_flat = " ".join(trans.split())
            combined = f"{orig_flat}\n{trans_flat}" if orig_flat != trans_flat else orig_flat
            new_cues.append({**cue, "text": combined})
        else:
            new_cues.append({**cue, "text": wrapped_en})
    return format_srt(new_cues)


def generate_translated_srt_files(
    srt_text: str,
    base_output_path: str | Path,
    target_lang: str | None = "en",
    extra_output_dir: str | Path | None = None,
) -> dict[str, str]:
    """Write Original, English (.en.srt), and Bilingual (.de-en.srt) SRT files.
    Always writes original SRT first so network issues never block subtitle creation."""
    base = str(base_output_path)
    for ext in (".flac", ".mp3", ".wav", ".srt"):
        if base.lower().endswith(ext):
            base = base[: -len(ext)]
    if base.endswith(" (lines)"):
        base = base[: -len(" (lines)")]

    os.makedirs(os.path.dirname(os.path.abspath(base)), exist_ok=True)

    orig_path = f"{base} (lines).srt"

    # 1. ALWAYS write the original SRT first!
    with open(orig_path, "w", encoding="utf-8") as fh:
        fh.write(srt_text if srt_text.endswith("\n") else srt_text + "\n")

    result = {"orig_srt": orig_path}

    # Helper to copy to export folder
    def _copy_to_export(src_path, dest_filename):
        if extra_output_dir and os.path.isdir(str(extra_output_dir)):
            try:
                import shutil
                shutil.copy2(src_path, os.path.join(extra_output_dir, dest_filename))
            except Exception as ex:
                print(f"[SRT] Copy {dest_filename} to export dir failed:", ex)

    song_basename = os.path.basename(base)
    clean_base = re.sub(r"^render_[a-f0-9]+_", "", song_basename)
    _copy_to_export(orig_path, f"{clean_base} (lines).srt")

    # 2. If target_lang is provided, translate cues safely
    if target_lang:
        en_path = f"{base} (lines).{target_lang}.srt"
        bi_path = f"{base} (lines).bilingual-{target_lang}.srt"

        cues = parse_srt(srt_text)
        orig_texts = [c["text"] for c in cues]
        try:
            translated = translate_lines(orig_texts, target_lang=target_lang)
        except Exception as ex:
            print("[Translate] Translation failed, using original text:", ex)
            translated = orig_texts

        if len(translated) != len(cues):
            translated = orig_texts

        en_cues = []
        bi_cues = []
        for cue, trans in zip(cues, translated):
            en_cues.append({**cue, "text": wrap_subtitle_line(trans)})
            orig_flat = " ".join(cue["text"].split())
            trans_flat = " ".join(trans.split())
            bi_cues.append({**cue, "text": f"{orig_flat}\n{trans_flat}" if orig_flat != trans_flat else orig_flat})

        with open(en_path, "w", encoding="utf-8") as fh:
            fh.write(format_srt(en_cues))
        with open(bi_path, "w", encoding="utf-8") as fh:
            fh.write(format_srt(bi_cues))

        _copy_to_export(en_path, f"{clean_base} (lines).{target_lang}.srt")
        _copy_to_export(bi_path, f"{clean_base} (lines).bilingual-{target_lang}.srt")

        result["en_srt"] = en_path
        result["bilingual_srt"] = bi_path

    return result
