"""
Feu Sacre - Video Composer
FFmpeg assembly with responsive image scaling, Ken Burns, transitions,
audio mixing, and ASS subtitle burn-in.
"""

import json
import logging
import math
import os
import subprocess

from config import FPS, ZOOM_MAX, XFADE_DUR, MUSIC_VOLUME, VOICE_VOLUME

log = logging.getLogger(__name__)


def _find_music() -> str | None:
    """Find background music file."""
    candidates = [
        "/app/music/epic_ambient.mp3",
        os.path.join(os.path.dirname(__file__), "music", "epic_ambient.mp3"),
        "/data/music/epic_ambient.mp3",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def get_duration(path: str) -> float:
    """Get media duration via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True,
    )
    return float(json.loads(r.stdout)["format"]["duration"])


def build_segment(
    images: list[str],
    audio_path: str,
    ass_path: str,
    output_path: str,
    w: int = 1920,
    h: int = 1080,
    music_path: str | None = None,
) -> float:
    """
    Build one video section:
    - Images with Ken Burns zoom (alternating in/out)
    - Dissolve transitions between images
    - Voice overlay (boosted)
    - Background music (quiet)
    - ASS subtitles burned in
    - Proper aspect ratio: images scaled with pad (no stretching)
    """
    duration = get_duration(audio_path)
    n = len(images)
    seg_dur = (duration + (n - 1) * XFADE_DUR) / n if n > 1 else duration + 0.5
    frames = max(1, math.ceil(seg_dur * FPS))
    zoom_step = (ZOOM_MAX - 1.0) / frames

    if music_path is None:
        music_path = _find_music()

    cmd = ["ffmpeg", "-y"]

    # Input: images (with proper scaling via lavfi)
    for img in images:
        cmd.extend(["-loop", "1", "-t", f"{seg_dur + 1:.2f}", "-i", img])
    # Input: voice audio
    cmd.extend(["-i", audio_path])
    # Input: background music (if available)
    has_music = music_path and os.path.exists(music_path)
    if has_music:
        cmd.extend(["-stream_loop", "-1", "-i", music_path])

    audio_idx = n
    music_idx = n + 1

    filters = []

    # Scale each image to exact resolution (preserve aspect ratio + pad)
    # Then apply Ken Burns zoom
    for i in range(n):
        # Alternating zoom direction
        if i % 2 == 0:
            z = f"'min(zoom+{zoom_step:.6f},{ZOOM_MAX})'"
        else:
            z = f"'if(eq(on,0),{ZOOM_MAX},max(zoom-{zoom_step:.6f},1.0))'"

        filters.append(
            f"[{i}:v]"
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,"
            f"zoompan=z={z}:d={frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s={w}x{h}:fps={FPS},setsar=1[v{i}]"
        )

    # Crossfade transitions between images
    if n == 1:
        filters.append(f"[v0]null[vout0]")
    else:
        prev = "[v0]"
        for i in range(1, n):
            offset = max(0, round(i * seg_dur - i * XFADE_DUR, 2))
            out_label = "[vout0]" if i == n - 1 else f"[x{i:02d}]"
            filters.append(
                f"{prev}[v{i}]xfade=transition=dissolve"
                f":duration={XFADE_DUR}:offset={offset}{out_label}"
            )
            prev = out_label if i < n - 1 else ""

    # Burn ASS subtitles
    ass_escaped = ass_path.replace("\\", "/").replace(":/", "\\:/")
    filters.append(f"[vout0]ass='{ass_escaped}',format=yuv420p[vfinal]")

    # Audio mixing: voice (loud) + music (quiet)
    if has_music:
        filters.append(
            f"[{music_idx}:a]atrim=0:{math.ceil(duration) + 1},"
            f"volume={MUSIC_VOLUME}[bgm];"
            f"[{audio_idx}:a]volume={VOICE_VOLUME}[voice];"
            f"[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
    else:
        filters.append(f"[{audio_idx}:a]volume={VOICE_VOLUME}[aout]")

    filter_complex = ";".join(filters)

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vfinal]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-t", str(math.ceil(duration)),
        "-shortest", output_path,
    ])

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace")[-2000:]
        log.error("FFmpeg error:\n%s", err)
        raise RuntimeError(f"FFmpeg failed (code {result.returncode})")

    log.info("Segment built: %.1fs -> %s", duration, output_path)
    return duration


def concatenate_segments(segments: list[str], output_path: str) -> float:
    """Concatenate multiple video segments into final video."""
    if not segments:
        raise ValueError("No segments to concatenate")

    if len(segments) == 1:
        import shutil
        shutil.copy2(segments[0], output_path)
        return get_duration(output_path)

    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace")[-1500:]
        log.error("Concat error:\n%s", err)
        raise RuntimeError("FFmpeg concat failed")

    # Cleanup
    if os.path.exists(concat_file):
        os.remove(concat_file)

    total = get_duration(output_path)
    log.info("Final video: %.0fs (%.1f min) -> %s",
             total, total / 60, output_path)
    return total
