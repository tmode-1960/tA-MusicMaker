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


def enforce_resolve_compatibility(cues: list[dict], min_gap: float = 0.08, min_duration: float = 0.5) -> list[dict]:
    """Guarantee 100% DaVinci Resolve compatibility on the Subtitle Track:
    - Strictly monotonic cue start times.
    - Absolute ZERO overlapping timecodes: every cue ends at least `min_gap` (default 80ms / ~2 frames) before next cue starts.
    - Every cue has a valid duration >= min_duration.
    - Eliminates any frame rounding collisions when imported into DaVinci Resolve timelines.
    """
    if not cues:
        return []
    clean: list[dict] = []
    for c in cues:
        txt = str(c.get("text", "")).strip()
        if not txt:
            continue
        t0 = float(c.get("start", 0.0))
        t1 = float(c.get("end", t0 + min_duration))
        if t1 < t0:
            t1 = t0 + min_duration
        clean.append({"start": max(0.0, t0), "end": max(t0 + 0.2, t1), "text": txt})

    if not clean:
        return []

    clean.sort(key=lambda x: x["start"])

    # Pass 1: Ensure monotonic starts with minimum duration buffer
    for i in range(len(clean) - 1):
        if clean[i + 1]["start"] < clean[i]["start"] + 0.3 + min_gap:
            clean[i + 1]["start"] = clean[i]["start"] + 0.3 + min_gap

    # Pass 2: Guarantee strictly non-overlapping end times with min_gap safety buffer
    for i in range(len(clean) - 1):
        if clean[i]["end"] > clean[i + 1]["start"] - min_gap:
            clean[i]["end"] = clean[i + 1]["start"] - min_gap
        if clean[i]["end"] < clean[i]["start"] + 0.3:
            clean[i]["end"] = clean[i]["start"] + 0.3
            if clean[i + 1]["start"] < clean[i]["end"] + min_gap:
                clean[i + 1]["start"] = clean[i]["end"] + min_gap

    # Final pass: Ensure end > start for last cue
    if clean[-1]["end"] <= clean[-1]["start"]:
        clean[-1]["end"] = clean[-1]["start"] + 0.8

    return clean


def extend_cues_until_next_sentence(cues: list[dict], pause_before_next: float = 1.0, max_duration: float = 6.0) -> list[dict]:
    """Extend each cue's display time until `pause_before_next` seconds before the next cue starts,
    providing a calm, professional subtitle pacing without any overlapping timecodes."""
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
            # Strict safety: never overlap with next cue!
            max_allowed = max(t0 + 0.2, next_start - 0.08)
            if max_allowed > next_start - 0.08:
                max_allowed = max(t0 + 0.1, next_start - 0.08)
            cues[i]["end"] = min(t0 + max_duration, cues[i]["end"], max_allowed)
        else:
            # Last cue of song
            cues[i]["end"] = min(t0 + max_duration, cues[i]["end"] + 1.5)
    return enforce_resolve_compatibility(cues, min_gap=0.08)


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


_whisper_cache: dict[str, tuple[list[dict], list[dict], float]] = {}


def find_vocal_audio_path(flac_path: str | Path) -> str | None:
    """Find isolated vocal stem audio file if available (e.g. from UVR or separate stems),
    drastically improving Whisper's recognition and timing accuracy."""
    try:
        p = Path(flac_path).resolve()
        base_dir = p.parent
        stem = p.stem
        clean_stem = re.sub(r"^(?:render|input)_[a-f0-9]+_", "", stem)

        for folder in (base_dir, base_dir / "uvr_stems", Path("data/renders/uvr_stems"), Path("dist/data/renders/uvr_stems")):
            if not folder.is_dir():
                continue
            for pattern in (
                f"*{stem}*(Vocals)*", f"*{clean_stem}*(Vocals)*",
                f"*{stem}*_vocals*", f"*{clean_stem}*_vocals*",
                f"*{stem}*_voice*", f"*{clean_stem}*_voice*"
            ):
                for cand in folder.glob(pattern):
                    if cand.is_file() and cand.suffix.lower() in (".flac", ".wav", ".mp3", ".ogg"):
                        return str(cand)
    except Exception:
        pass
    return None


def get_auto_translation_target(lyrics_text: str) -> str:
    """Returns 'en' if song is in German, or 'de' if song is in English/other."""
    brief = (rec or {}).get("brief") or {}
    v_lang = str(brief.get("vocals.language") or brief.get("vocals_language") or "").strip().lower()
    if any(k in v_lang for k in ("engl", "en")):
        lang = "en"
    elif any(k in v_lang for k in ("deut", "germ", "de")):
        lang = "de"
    else:
        lang = detect_lyrics_language(lyrics_text)
    return "en" if lang == "de" else "de"


def detect_lyrics_language(text: str) -> str:
    """Detect whether lyrics are predominantly German ('de') or other ('en', etc.)
    to guide Whisper and prevent incorrect language hallucinations on sung vocals."""
    if not text:
        return "de"
    if any(c in text for c in "äöüÄÖÜß"):
        return "de"
    de_distinct = {
        "der", "die", "das", "und", "den", "von", "zu", "mit", "sich", "des",
        "auf", "für", "ist", "im", "dem", "nicht", "ein", "eine", "einer", "einen",
        "einem", "auch", "werden", "aus", "hat", "dass", "sie", "nach", "wird",
        "bei", "sind", "noch", "wie", "über", "ich", "du", "wir", "ihr",
        "mein", "dein", "uns", "unsere", "eure", "warum", "wenn", "aber", "schon",
        "immer", "doch", "nie", "leben", "liebe", "herz", "wieder", "heute", "nacht"
    }
    en_distinct = {
        "the", "and", "you", "that", "with", "this", "they", "from", "have", "are",
        "not", "what", "but", "his", "her", "she", "for", "out", "about", "all",
        "would", "there", "their", "will", "my", "one", "get", "which", "like",
        "time", "know", "just", "could", "them", "see", "than", "then", "now",
        "look", "only", "come", "its", "over", "think", "also", "back", "after",
        "how", "our", "work", "well", "way", "even", "want", "because", "any", "these"
    }
    words = set(re.findall(r"\b\w+\b", text.lower()))
    de_count = len(words & de_distinct)
    en_count = len(words & en_distinct)
    if en_count > de_count:
        return "en"
    if de_count >= 2:
        return "de"
    return "en"


def get_whisper_transcription(flac_path: str | Path, prompt: str = "", language: str | None = None) -> tuple[list[dict], list[dict], float]:
    """Transcribe audio with faster-whisper, returning (segments, words, duration) with local caching.
    Automatically prioritizes clean isolated vocal stems and language guidance for max precision."""
    fpath = str(Path(flac_path).resolve())
    cache_key = f"{fpath}::{language or 'auto'}"
    if cache_key in _whisper_cache:
        return _whisper_cache[cache_key]

    try:
        from faster_whisper import WhisperModel
    except Exception as ex:
        print(f"[Whisper] faster-whisper nicht verfuegbar: {ex}")
        return [], [], 0.0

    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    model_dir = get_whisper_model_dir()
    try:
        model = WhisperModel("base", device="cpu", compute_type="int8", download_root=model_dir)
    except Exception:
        try:
            model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root=model_dir)
        except Exception as ex:
            print(f"[Whisper] Modell konnte nicht geladen werden: {ex}")
            return [], [], 0.0

    # If isolated vocal stem is available, prefer it for transcription!
    target_audio = find_vocal_audio_path(flac_path) or str(flac_path)
    if target_audio != str(flac_path):
        print(f"[Whisper] Nutze isolierte Gesangsspur fuer maximale Praezision: {os.path.basename(target_audio)}")

    transcribe_kwargs = {
        "word_timestamps": True,
        "initial_prompt": prompt or None,
        "condition_on_previous_text": False,
        "beam_size": 5,
    }
    if language:
        transcribe_kwargs["language"] = language

    # Attempt with VAD first, fallback to no-VAD if silent or over-filtered on full music tracks
    raw_segments = []
    audio_dur = 0.0
    try:
        raw_iter, info = model.transcribe(
            str(target_audio),
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400, speech_pad_ms=150),
            **transcribe_kwargs
        )
        raw_segments = list(raw_iter)
        audio_dur = float(info.duration) if hasattr(info, "duration") and info.duration else 0.0
    except Exception as ex:
        print(f"[Whisper] VAD-Transkription fehlgeschlagen, versuche Standard: {ex}")

    speech_coverage = sum((float(s.end) - float(s.start)) for s in raw_segments)
    if not raw_segments or (audio_dur > 30.0 and (len(raw_segments) < 8 or speech_coverage < 0.25 * audio_dur)):
        try:
            raw_iter, info = model.transcribe(
                str(target_audio),
                vad_filter=False,
                **transcribe_kwargs
            )
            raw_segments = list(raw_iter)
            audio_dur = float(info.duration) if hasattr(info, "duration") and info.duration else 0.0
        except Exception as ex:
            print(f"[Whisper] Transkription ohne VAD fehlgeschlagen: {ex}")
            if not raw_segments:
                return [], [], 0.0

    segments = []
    words = []
    for seg in raw_segments:
        segments.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "text": seg.text.strip(),
        })
        if seg.words:
            for w in seg.words:
                if w.end - w.start >= 0.05:
                    cw = re.sub(r"[^\w]", "", w.word.lower())
                    if cw:
                        words.append({
                            "clean": cw,
                            "start": float(w.start),
                            "end": float(w.end),
                            "raw": w.word,
                        })

    _whisper_cache[cache_key] = (segments, words, audio_dur)
    return segments, words, audio_dur


def align_lyrics_with_whisper(flac_path: str | Path, rec: dict | None = None, fallback_lyrics: str | None = None, resolve_mode: bool = False) -> str | None:
    """Align lyrics with actual audio speech using faster-whisper.
    Uses monotonic high-confidence anchor matching and smooth interpolation.
    - If `resolve_mode=True`: Strictly cut-exact, ending when vocals stop (+0.2s decay) with guaranteed 80ms non-overlapping safety gaps for DaVinci Resolve.
    - If `resolve_mode=False`: Smooth reading pacing with zero-overlap safety.
    """
    if not rec:
        rec = extract_plenio_record_from_flac(flac_path)
    if not rec and not fallback_lyrics:
        return None

    docs = (rec or {}).get("documents") or {}
    lyrics_text = (docs.get("lyrics") or {}).get("text") or (fallback_lyrics or "").strip()
    if not lyrics_text:
        return None

    all_lines: list[str] = []
    for raw in lyrics_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        all_lines.append(line)

    if not all_lines:
        return None

    lang = detect_lyrics_language(lyrics_text)
    prompt = " ".join(" ".join(all_lines).split()[:200])
    segments, words, audio_dur = get_whisper_transcription(flac_path, prompt=prompt, language=lang)
    if not words:
        return None

    files = (rec or {}).get("files") or []
    if files and files[0].get("seconds"):
        audio_dur = max(audio_dur, float(files[0]["seconds"]))
    if audio_dur <= 0.0 and words:
        audio_dur = words[-1]["end"] + 5.0

    # Step 1: Find high-confidence anchor matches monotonically
    anchors: dict[int, dict] = {}
    cur_idx = 0
    total_lines = len(all_lines)

    for l_idx, line in enumerate(all_lines):
        clean_line_words = [re.sub(r"[^\w]", "", w.lower()) for w in line.split() if re.sub(r"[^\w]", "", w.lower())]
        if not clean_line_words:
            continue
        best_span = None
        best_score = 0.0
        target_k = len(clean_line_words)
        search_window = min(len(words), cur_idx + 40)
        for i in range(cur_idx, search_window):
            for k in range(max(1, target_k - 2), min(target_k + 4, len(words) - i + 1)):
                cand = [words[i + m]["clean"] for m in range(k)]
                matched_cnt = 0
                for cw in cand:
                    if any(cw == tw or (len(cw) >= 4 and len(tw) >= 4 and (cw in tw or tw in cw)) for tw in clean_line_words):
                        matched_cnt += 1
                score = matched_cnt / max(len(clean_line_words), len(cand))
                if score > best_score:
                    best_score = score
                    best_span = (i, i + k)
        min_score = 0.55 if len(clean_line_words) >= 3 else 0.75
        if best_span and best_score >= min_score:
            w_start = words[best_span[0]]["start"]
            w_end = words[best_span[1] - 1]["end"]
            cur_idx = best_span[1]
            anchors[l_idx] = {"start": w_start, "end": w_end, "score": best_score}

    # Step 2: Build raw cues with both anchors and smooth interpolation
    cues = []
    for l_idx in range(total_lines):
        if l_idx in anchors:
            cues.append({
                "start": anchors[l_idx]["start"],
                "end": anchors[l_idx]["end"] + (0.20 if resolve_mode else 0.0),
                "text": all_lines[l_idx]
            })
        else:
            prev_idx = None
            for p in range(l_idx - 1, -1, -1):
                if p in anchors:
                    prev_idx = p
                    break
            next_idx = None
            for n in range(l_idx + 1, total_lines):
                if n in anchors:
                    next_idx = n
                    break

            if prev_idx is not None and next_idx is not None:
                t_prev = anchors[prev_idx]["end"]
                t_next = anchors[next_idx]["start"]
                span_lines = next_idx - prev_idx
                step = max(0.5, (t_next - t_prev) / span_lines)
                pos = l_idx - prev_idx
                t0 = t_prev + (pos - 1) * step + 0.15
                t1 = min(t_next - 0.1, t0 + max(1.2, step * 0.85))
            elif prev_idx is not None:
                t_prev = anchors[prev_idx]["end"]
                pos = l_idx - prev_idx
                t0 = t_prev + (pos - 1) * 3.0 + 0.5
                t1 = min(audio_dur - 0.5, t0 + 2.5)
            elif next_idx is not None:
                t_next = anchors[next_idx]["start"]
                pos = next_idx - l_idx
                t1 = max(0.5, t_next - (pos - 1) * 3.0 - 0.5)
                t0 = max(0.0, t1 - 2.5)
            else:
                t0 = l_idx * 3.5
                t1 = t0 + 2.8

            cues.append({
                "start": max(0.0, t0),
                "end": max(t0 + 0.8, t1),
                "text": all_lines[l_idx]
            })

    # Step 3: Pacing vs Cut-Exact Mode
    if resolve_mode:
        cues = enforce_resolve_compatibility(cues, min_gap=0.08)
    else:
        cues = extend_cues_until_next_sentence(cues)

    blocks = []
    for idx, c in enumerate(cues, start=1):
        txt = wrap_subtitle_line(c["text"])
        if txt:
            blocks.append(f"{idx}\n{srt_timestamp(c['start'])} --> {srt_timestamp(c['end'])}\n{txt}")
    return "\n\n".join(blocks) + "\n" if blocks else None


def _format_timing_lines_to_srt(lines: list[dict], resolve_mode: bool = False) -> str | None:
    parsed_cues = []
    for line in lines:
        start = float(line.get("start", 0.0))
        end = float(line.get("end", start + 2.0))
        txt = str(line.get("text") or "").strip()
        if txt:
            parsed_cues.append({"start": start, "end": end, "text": txt})
    if not parsed_cues:
        return None
    if resolve_mode:
        for c in parsed_cues:
            c["end"] = c["end"] + 0.20
        cues = enforce_resolve_compatibility(parsed_cues, min_gap=0.08)
    else:
        cues = extend_cues_until_next_sentence(parsed_cues)
    blocks = []
    for idx, c in enumerate(cues, start=1):
        txt = wrap_subtitle_line(c["text"])
        if txt:
            blocks.append(f"{idx}\n{srt_timestamp(c['start'])} --> {srt_timestamp(c['end'])}\n{txt}")
    if blocks:
        return "\n\n".join(blocks) + "\n"
    return None


def create_resolve_cut_exact_srt(srt_text: str, min_gap: float = 0.08) -> str:
    """Transform an SRT string into a 100% DaVinci Resolve compatible format:
    - Strictly enforces non-overlapping intervals with at least `min_gap` (default 80ms / ~2 frames).
    - Preserves exact millisecond SubRip format (00:00:00,000 --> 00:00:00,000).
    - Guarantees sequential 1-based indexing.
    """
    if not srt_text:
        return ""
    cues = parse_srt(srt_text)
    if not cues:
        return srt_text
    raw_cues = []
    for c in cues:
        t_str = c.get("time") or ""
        if "-->" not in t_str:
            continue
        p1, p2 = [p.strip() for p in t_str.split("-->")]
        t0 = parse_srt_timestamp(p1)
        t1 = parse_srt_timestamp(p2)
        txt = c.get("text", "").strip()
        if txt:
            raw_cues.append({"start": t0, "end": max(t0 + 0.4, t1), "text": txt})

    clean = enforce_resolve_compatibility(raw_cues, min_gap=min_gap)
    return format_srt(clean)


def transcribe_sung_with_whisper(flac_path: str | Path) -> str | None:
    """Fallback: transcribe actually sung lyrics directly from audio via Whisper."""
    segments, _, _ = get_whisper_transcription(flac_path)
    if not segments:
        return None
    cues = []
    for s in segments:
        t0 = float(s["start"])
        t1 = float(s["end"])
        txt = str(s["text"]).strip()
        if txt and t1 - t0 >= 0.4:
            cues.append({"start": t0, "end": t1, "text": txt})
    if not cues:
        return None
    cues = extend_cues_until_next_sentence(cues)
    blocks = []
    for idx, c in enumerate(cues, start=1):
        txt = wrap_subtitle_line(c["text"])
        if txt:
            blocks.append(f"{idx}\n{srt_timestamp(c['start'])} --> {srt_timestamp(c['end'])}\n{txt}")
    return "\n\n".join(blocks) + "\n" if blocks else None


def extract_sung_srt_from_flac(flac_path: str | Path) -> str | None:
    """Extract the actually sung lyrics `(sung).srt` from a Plenio FLAC file's embedded timing record,
    or via local Whisper transcription when ASR did not run."""
    rec = extract_plenio_record_from_flac(flac_path)
    timings = (rec or {}).get("timing") or []
    if timings and isinstance(timings, list):
        sung_info = timings[0].get("sung")
        if isinstance(sung_info, dict) and sung_info.get("lines"):
            return _format_timing_lines_to_srt(sung_info.get("lines") or [])
    return transcribe_sung_with_whisper(flac_path)

def extract_srt_from_flac(flac_path: str | Path, fallback_lyrics: str | None = None, prefer_sung: bool = False, resolve_mode: bool = False) -> str | None:
    """Build the original `(lines).srt` or `(sung).srt` content from a Plenio FLAC file's embedded timing record,
    or via local Whisper ASR alignment, or synthesize from score when ASR did not run.
    - If `resolve_mode=True`: Generates 100% DaVinci Resolve cut-exact subtitle timings with zero overlap.
    """
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
            res = _format_timing_lines_to_srt(lines, resolve_mode=resolve_mode)
            if res:
                return res

    # 2. Local Whisper ASR Audio-Alignment (downloads model on demand if not present on PC)
    whisper_srt = align_lyrics_with_whisper(flac_path, rec=rec, fallback_lyrics=fallback_lyrics, resolve_mode=resolve_mode)
    if whisper_srt:
        return whisper_srt

    # 3. Fallback: synthesize from embedded score and lyrics
    score_srt = synthesize_srt_from_record(rec, fallback_lyrics=fallback_lyrics)
    if score_srt and resolve_mode:
        return create_resolve_cut_exact_srt(score_srt, min_gap=0.08)
    return score_srt


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
    blocks = []
    for i, c in enumerate(cues, start=1):
        txt = str(c.get("text") or "").strip()
        t_str = c.get("time")
        if not t_str:
            t0 = float(c.get("start", 0.0))
            t1 = float(c.get("end", t0 + 1.0))
            t_str = f"{srt_timestamp(t0)} --> {srt_timestamp(t1)}"
        if txt:
            blocks.append(f"{i}\n{t_str}\n{txt}")
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
    resolve_srt_text: str | None = None,
) -> dict[str, str]:
    """Write Original (.srt), DaVinci Resolve (.resolve.srt), and optional translated (.en.srt) files.
    All files strictly guarantee zero-overlap and frame-safe gaps for DaVinci Resolve."""
    base = str(base_output_path)
    for ext in (".flac", ".mp3", ".wav", ".srt"):
        if base.lower().endswith(ext):
            base = base[: -len(ext)]
    if base.endswith(" (lines)"):
        base = base[: -len(" (lines)")]

    os.makedirs(os.path.dirname(os.path.abspath(base)), exist_ok=True)

    orig_path = f"{base} (lines).srt"
    resolve_path = f"{base} (lines).resolve.srt"

    # Ensure srt_text itself is cleaned with zero-overlap guarantee
    clean_orig_srt = create_resolve_cut_exact_srt(srt_text, min_gap=0.08) if srt_text else srt_text
    with open(orig_path, "w", encoding="utf-8") as fh:
        fh.write(clean_orig_srt if clean_orig_srt.endswith("\n") else clean_orig_srt + "\n")

    # If resolve_srt_text is provided, use it; otherwise generate from clean_orig_srt
    res_text = resolve_srt_text or clean_orig_srt
    clean_resolve_srt = create_resolve_cut_exact_srt(res_text, min_gap=0.08)
    with open(resolve_path, "w", encoding="utf-8") as fh:
        fh.write(clean_resolve_srt if clean_resolve_srt.endswith("\n") else clean_resolve_srt + "\n")

    result = {
        "orig_srt": orig_path,
        "resolve_srt": resolve_path,
    }

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
    _copy_to_export(resolve_path, f"{clean_base} (lines).resolve.srt")

    if target_lang:
        trans_path = f"{base} (lines).{target_lang}.srt"
        cues = parse_srt(clean_orig_srt)
        orig_texts = [c["text"] for c in cues]
        try:
            translated = translate_lines(orig_texts, target_lang=target_lang)
        except Exception as ex:
            print("[Translate] Translation failed, using original text:", ex)
            translated = orig_texts

        if len(translated) != len(cues):
            translated = orig_texts

        trans_cues = []
        for cue, trans in zip(cues, translated):
            trans_cues.append({**cue, "text": wrap_subtitle_line(trans)})

        with open(trans_path, "w", encoding="utf-8") as fh:
            fh.write(format_srt(trans_cues))

        _copy_to_export(trans_path, f"{clean_base} (lines).{target_lang}.srt")
        result["trans_srt"] = trans_path
        result["target_lang"] = target_lang

    return result
