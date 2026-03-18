"""
Feu Sacre - Subtitle Engine
Modern ASS subtitles: shadow on words, no black background, word-by-word highlight.
Responsive sizing for different screen formats (16:9, 9:16).
"""

import logging

from config import (
    SUBTITLE_FONT,
    SUBTITLE_FONTSIZE,
    SUBTITLE_FONTSIZE_VERT,
    SUBTITLE_PRIMARY,
    SUBTITLE_OUTLINE_COLOR,
    SUBTITLE_SHADOW_COLOR,
    SUBTITLE_OUTLINE,
    SUBTITLE_SHADOW,
    SUBTITLE_BORDER_STYLE,
    SUBTITLE_HIGHLIGHT,
    SUBTITLE_MARGIN_V,
    WORDS_PER_GROUP,
)

log = logging.getLogger(__name__)


def _fmt_time(seconds: float) -> str:
    """Format seconds to ASS time: H:MM:SS.CC"""
    seconds = max(0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _compute_fontsize(base_size: int, play_res_x: int, play_res_y: int) -> int:
    """
    Scale font size proportionally to resolution.
    Base sizes are calibrated for 1920x1080.
    This ensures subtitles look the same size on any screen.
    """
    # Reference is 1080p height
    scale = play_res_y / 1080
    return max(24, int(base_size * scale))


def generate_ass(
    words_timing: list[dict],
    ass_path: str,
    width: int = 1920,
    height: int = 1080,
    fontsize: int | None = None,
    vertical: bool = False,
) -> str:
    """
    Generate ASS subtitles with modern style:
    - Big bold text with thick outline (no background box)
    - Drop shadow for depth (not a colored background)
    - Word-by-word karaoke highlight in orange flame
    - Responsive font sizing based on resolution
    """
    if fontsize is None:
        base = SUBTITLE_FONTSIZE_VERT if vertical else SUBTITLE_FONTSIZE
        fontsize = _compute_fontsize(base, width, height)

    # Compute margin proportional to resolution
    margin_v = int(SUBTITLE_MARGIN_V * (height / 1080))

    ass = "[Script Info]\n"
    ass += "Title: Feu Sacre\n"
    ass += "ScriptType: v4.00+\n"
    ass += f"PlayResX: {width}\n"
    ass += f"PlayResY: {height}\n"
    ass += "WrapStyle: 0\n"
    ass += "ScaledBorderAndShadow: yes\n"
    ass += "\n"
    ass += "[V4+ Styles]\n"
    ass += (
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
    )
    # Modern style: outline + drop shadow, NO opaque background box
    # BorderStyle=1 -> outline+shadow (not 3 which is opaque box)
    # BackColour with low opacity = subtle shadow color, not a filled rectangle
    # ScaledBorderAndShadow=yes ensures proportional rendering across resolutions
    ass += (
        f"Style: Default,{SUBTITLE_FONT},{fontsize},"
        f"{SUBTITLE_PRIMARY},&H000000FF,"
        f"{SUBTITLE_OUTLINE_COLOR},{SUBTITLE_SHADOW_COLOR},"
        f"1,0,0,0,100,100,2,0,"
        f"{SUBTITLE_BORDER_STYLE},{SUBTITLE_OUTLINE},{SUBTITLE_SHADOW},"
        f"2,60,60,{margin_v},1\n"
    )
    ass += "\n"
    ass += "[Events]\n"
    ass += (
        "Format: Layer, Start, End, Style, Name, "
        "MarginL, MarginR, MarginV, Effect, Text\n"
    )

    if not words_timing:
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass)
        return ass_path

    # Word-by-word highlight in groups
    # Active word: orange flame + glow outline + scale up
    # Other words: white (default style)
    highlight_tag = (
        r"{\c" + SUBTITLE_HIGHLIGHT + r"&"
        r"\fscx115\fscy115"
        r"\bord" + str(SUBTITLE_OUTLINE + 1) +
        r"\3c&H004488FF&}"  # orange-tinted outline for glow
    )
    reset_tag = (
        r"{\c" + SUBTITLE_PRIMARY + r"&"
        r"\fscx100\fscy100"
        r"\bord" + str(SUBTITLE_OUTLINE) +
        r"\3c" + SUBTITLE_OUTLINE_COLOR + r"&}"
    )

    for g in range(0, len(words_timing), WORDS_PER_GROUP):
        group = words_timing[g:min(g + WORDS_PER_GROUP, len(words_timing))]

        for w_idx, word_info in enumerate(group):
            w_start = word_info["start"]
            w_end = w_start + word_info["duration"]

            # Ensure minimum display time of 80ms
            if w_end - w_start < 0.08:
                w_end = w_start + 0.08

            parts = []
            for idx, tw in enumerate(group):
                if idx == w_idx:
                    parts.append(highlight_tag + tw["word"] + reset_tag)
                else:
                    parts.append(tw["word"])

            text = " ".join(parts)
            ass += (
                f"Dialogue: 0,{_fmt_time(w_start)},{_fmt_time(w_end)},"
                f"Default,,0,0,0,,{text}\n"
            )

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass)

    log.info("ASS subtitles: %d words, font %dpt, %dx%d -> %s",
             len(words_timing), fontsize, width, height, ass_path)
    return ass_path


def validate_sync(words_timing: list[dict], audio_duration: float) -> list[dict]:
    """
    Validate and fix subtitle timing sync issues:
    - Remove overlaps between words
    - Fill gaps > 0.3s
    - Clamp to audio duration
    - Ensure no word starts before previous ends
    """
    if not words_timing:
        return words_timing

    fixed = []
    for i, w in enumerate(words_timing):
        start = w["start"]
        duration = w["duration"]

        # Clamp start to audio bounds
        start = max(0, min(start, audio_duration - 0.05))

        # Ensure no overlap with previous word
        if fixed and start < fixed[-1]["start"] + fixed[-1]["duration"]:
            start = fixed[-1]["start"] + fixed[-1]["duration"]

        # Clamp duration
        duration = max(0.05, min(duration, audio_duration - start))

        fixed.append({"word": w["word"], "start": start, "duration": duration})

    # Fill large gaps: if gap between words > 0.3s, extend previous word
    for i in range(len(fixed) - 1):
        gap = fixed[i + 1]["start"] - (fixed[i]["start"] + fixed[i]["duration"])
        if gap > 0.3:
            fixed[i]["duration"] += gap * 0.5  # extend halfway into gap

    log.info("Sync validated: %d words, audio %.1fs", len(fixed), audio_duration)
    return fixed
