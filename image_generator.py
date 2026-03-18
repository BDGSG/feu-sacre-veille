"""
Feu Sacre - Image Generator
FLUX.1-schnell via HuggingFace with proper aspect ratio handling.
Images scale correctly across all screen sizes.
"""

import json
import logging
import os
import subprocess
import time
import urllib.request

from config import HF_TOKEN, CHARACTER_BIBLE, IMAGE_STYLE, IMAGE_STYLE_VERT

log = logging.getLogger(__name__)


def generate_image(
    prompt: str,
    output_path: str,
    vertical: bool = False,
    width: int = 1920,
    height: int = 1080,
    retries: int = 3,
) -> str:
    """
    Generate an AI image with FLUX.1-schnell.
    Output is scaled to exact target resolution while preserving aspect ratio.
    """
    style = IMAGE_STYLE_VERT if vertical else IMAGE_STYLE
    full_prompt = CHARACTER_BIBLE + ", " + prompt + style

    url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = json.dumps({"inputs": full_prompt}).encode("utf-8")

    raw_path = output_path + ".raw.png"

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=90) as resp:
                img_data = resp.read()
                if len(img_data) < 1000:
                    raise ValueError(f"Image too small ({len(img_data)} bytes)")
                with open(raw_path, "wb") as f:
                    f.write(img_data)
                break
        except Exception as e:
            log.warning("Image gen attempt %d/%d: %s", attempt, retries, e)
            if attempt < retries:
                time.sleep(3)
            else:
                raise RuntimeError(f"Image generation failed after {retries} tries: {e}")

    # Scale to exact target resolution while preserving aspect ratio
    # Uses pad to fill remaining space with black (no stretching)
    _scale_image(raw_path, output_path, width, height)

    # Clean up raw
    if os.path.exists(raw_path):
        os.remove(raw_path)

    log.info("Image generated: %s (%dx%d)", output_path, width, height)
    return output_path


def _scale_image(input_path: str, output_path: str, target_w: int, target_h: int):
    """
    Scale image to exact target resolution preserving aspect ratio.
    - scale to fit within target dimensions
    - pad with black to fill remaining space (pillarbox/letterbox)
    - setsar=1 for square pixels
    This ensures proper proportionality on ALL screens.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", (
            f"scale={target_w}:{target_h}"
            f":force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1"
        ),
        "-q:v", "2",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        # Fallback: just copy the raw file
        log.warning("ffmpeg scale failed, using raw image")
        import shutil
        shutil.copy2(input_path, output_path)


def generate_images_for_script(
    sections: list[dict],
    tmp_dir: str,
    vertical: bool = False,
) -> list[list[str]]:
    """
    Generate all images for a script.
    Returns list of image path lists (one list per section).
    """
    w, h = (1080, 1920) if vertical else (1920, 1080)
    all_section_images = []
    img_counter = 0

    for sec_i, section in enumerate(sections):
        prompts = section.get("images", [])
        section_paths = []
        for prompt in prompts:
            img_path = os.path.join(tmp_dir, f"img_{img_counter:03d}.png")
            log.info("Image %d: %s...", img_counter + 1, prompt[:60])
            generate_image(prompt, img_path, vertical=vertical, width=w, height=h)
            section_paths.append(img_path)
            img_counter += 1
            time.sleep(2)  # Rate limiting
        all_section_images.append(section_paths)

    log.info("Generated %d images for %d sections", img_counter, len(sections))
    return all_section_images
