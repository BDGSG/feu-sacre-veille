"""
Feu Sacre - TTS Engine
Edge-TTS with WordBoundary events for perfect subtitle sync.
"""

import asyncio
import json
import logging
import subprocess

import edge_tts

from config import VOICE, VOICE_RATE, VOICE_PITCH
from pronunciation import normalize_pronunciation

log = logging.getLogger(__name__)


def get_duration(path: str) -> float:
    """Get audio duration via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True,
    )
    return float(json.loads(r.stdout)["format"]["duration"])


async def _generate_tts_async(text: str, audio_path: str) -> list[dict]:
    """
    Generate TTS audio and extract word-level timing.
    Uses WordBoundary events from edge-tts for perfect sync.
    Falls back to SentenceBoundary + character-weighted split.
    """
    # Pre-process pronunciation
    text = normalize_pronunciation(text)

    communicate = edge_tts.Communicate(text, VOICE, rate=VOICE_RATE, pitch=VOICE_PITCH)

    word_boundaries = []
    sentence_boundaries = []

    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append({
                    "text": chunk["text"],
                    "offset": chunk["offset"] / 10_000_000,   # ticks -> seconds
                    "duration": chunk["duration"] / 10_000_000,
                })
            elif chunk["type"] == "SentenceBoundary":
                sentence_boundaries.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "duration": chunk["duration"] / 10_000_000,
                })

    total_dur = get_duration(audio_path)

    # Strategy 1: WordBoundary events (perfect sync)
    if word_boundaries:
        words_timing = []
        for i, wb in enumerate(word_boundaries):
            word = wb["text"]
            start = wb["offset"]
            # Duration: use next word's offset - current offset, or edge-tts duration
            if i + 1 < len(word_boundaries):
                duration = word_boundaries[i + 1]["offset"] - start
            else:
                duration = min(wb["duration"], total_dur - start)
            # Clamp
            duration = max(0.05, min(duration, total_dur - start))
            words_timing.append({"word": word, "start": start, "duration": duration})
        log.info("TTS: %d words with WordBoundary sync", len(words_timing))
        return words_timing

    # Strategy 2: SentenceBoundary + character-weighted split
    if sentence_boundaries:
        words_timing = []
        for sent in sentence_boundaries:
            sent_words = sent["text"].split()
            if not sent_words:
                continue
            weights = [max(len(w), 1) for w in sent_words]
            total_weight = sum(weights)
            cursor = sent["start"]
            for w_i, word in enumerate(sent_words):
                w_dur = (weights[w_i] / total_weight) * sent["duration"]
                words_timing.append({"word": word, "start": cursor, "duration": w_dur})
                cursor += w_dur
        log.info("TTS: %d words with SentenceBoundary sync", len(words_timing))
        return words_timing

    # Strategy 3: Full text character-weighted fallback
    all_words = text.split()
    weights = [max(len(w), 1) for w in all_words]
    total_weight = sum(weights)
    cursor = 0.0
    words_timing = []
    for w_i, word in enumerate(all_words):
        w_dur = (weights[w_i] / total_weight) * total_dur
        words_timing.append({"word": word, "start": cursor, "duration": w_dur})
        cursor += w_dur
    log.warning("TTS: fallback timing for %d words", len(words_timing))
    return words_timing


def generate_tts(text: str, audio_path: str) -> list[dict]:
    """Synchronous wrapper for TTS generation. Returns word timing list."""
    return asyncio.run(_generate_tts_async(text, audio_path))


def generate_tts_multi(sections: list[dict], tmp_dir: str) -> list[dict]:
    """
    Generate TTS for multiple sections.
    Returns list of {audio_path, words_timing, duration} per section.
    """
    results = []
    for i, section in enumerate(sections):
        import os
        audio_path = os.path.join(tmp_dir, f"audio_{i:02d}.mp3")
        narration = section.get("narration", "")
        if not narration.strip():
            continue
        log.info("TTS section %d/%d: %s...", i + 1, len(sections),
                 narration[:50])
        words_timing = generate_tts(narration, audio_path)
        duration = get_duration(audio_path)
        results.append({
            "section_index": i,
            "audio_path": audio_path,
            "words_timing": words_timing,
            "duration": duration,
        })
    return results
