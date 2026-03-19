"""
Feu Sacre - YouTube Auto-Uploader
Upload videos to YouTube with proper categorization:
  - Shorts (<= 60s, vertical 9:16) -> uploaded as YouTube Shorts
  - Long videos -> uploaded as regular YouTube videos
"""

import json
import logging
import os
import time

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

log = logging.getLogger(__name__)

# Token path - fallback chain
TOKEN_PATHS = [
    os.path.join(os.path.dirname(__file__), "token.json"),
    os.path.expanduser(r"~\Documents\MONTAGE VIDEOS\token.json"),
]


def _get_credentials() -> Credentials:
    """Load and refresh YouTube OAuth2 credentials."""
    token_file = None
    for p in TOKEN_PATHS:
        if os.path.exists(p):
            token_file = p
            break

    if not token_file:
        raise FileNotFoundError(
            f"YouTube token.json not found. Checked: {TOKEN_PATHS}"
        )

    credentials = Credentials.from_authorized_user_file(token_file)
    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            with open(token_file, "w") as f:
                f.write(credentials.to_json())
            log.info("YouTube token refreshed")
        else:
            raise RuntimeError("YouTube credentials expired and cannot be refreshed")

    return credentials


def _get_youtube_service():
    """Build YouTube API service with OAuth2."""
    return build("youtube", "v3", credentials=_get_credentials())


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    video_type: str = "long",
    privacy: str = "private",
) -> dict:
    """
    Upload a video to YouTube with proper categorization.

    For shorts:
      - Adds #shorts to title and description
      - YouTube auto-detects vertical + <=60s as Short

    For long videos:
      - Standard upload as regular video

    Returns: {"video_id": "...", "url": "...", "type": "short"|"long"}
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    service = _get_youtube_service()
    is_short = video_type == "short"

    # Prepare title and description based on type
    upload_title = title
    upload_description = description

    if is_short:
        # Ensure #shorts is in title for YouTube Short detection
        if "#shorts" not in upload_title.lower():
            # Add #shorts at end, keep title under 100 chars
            if len(upload_title) > 90:
                upload_title = upload_title[:90]
            upload_title = f"{upload_title} #shorts"

        # Ensure #shorts is in description
        if "#shorts" not in upload_description.lower():
            upload_description = f"{upload_description}\n\n#shorts"

        # Add short-specific tags
        if "shorts" not in [t.lower() for t in tags]:
            tags = ["shorts"] + tags
    else:
        # Long video: remove #shorts if accidentally present
        upload_title = upload_title.replace("#shorts", "").replace("#Shorts", "").strip()
        tags = [t for t in tags if t.lower() != "shorts"]

    body = {
        "snippet": {
            "title": upload_title,
            "description": upload_description,
            "tags": tags[:30],  # YouTube limit
            "categoryId": "22",  # People & Blogs
            "defaultLanguage": "fr",
            "defaultAudioLanguage": "fr",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,
    )

    log.info(
        "Uploading %s (%s) as %s: %s",
        os.path.basename(video_path),
        video_type,
        privacy,
        upload_title[:60],
    )

    request = service.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    start = time.time()
    while response is None:
        status, response = request.next_chunk()
        if status:
            log.info("  Upload progress: %d%%", int(status.progress() * 100))

    video_id = response["id"]
    elapsed = time.time() - start
    url = f"https://www.youtube.com/watch?v={video_id}"

    log.info("Upload OK: %s (%s, %.0fs)", url, video_type, elapsed)

    return {
        "video_id": video_id,
        "url": url,
        "type": video_type,
        "title": upload_title,
        "privacy": privacy,
    }
