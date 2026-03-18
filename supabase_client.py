"""
Feu Sacre - Supabase Client
Persiste les donnees de veille, scripts et planning dans Supabase.
"""

import json
import logging
import os
import urllib.request

log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    "https://supabasekong-q0cooggogcogwo4kg00cc8wo.coolify.inkora.art",
)
SUPABASE_KEY = os.getenv(
    "SUPABASE_SERVICE_KEY",
    "",
)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def _request(method: str, path: str, data=None) -> list | dict | None:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except Exception as e:
        log.error("Supabase %s %s failed: %s", method, path, e)
        return None


def upsert(table: str, rows: list[dict], on_conflict: str = "id") -> list | None:
    headers = {**HEADERS, "Prefer": "return=representation,resolution=merge-duplicates"}
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    body = json.dumps(rows).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.error("Supabase upsert %s failed: %s", table, e)
        return None


# ── Veille: Competitors ─────────────────────────────────────────────────


def save_competitors(competitors: list[dict]):
    rows = [
        {
            "channel_id": c["channel_id"],
            "name": c["title"],
            "subscribers": c.get("subscribers", 0),
            "total_views": c.get("total_views", 0),
            "video_count": c.get("video_count", 0),
            "description": c.get("description", ""),
            "thumbnail": c.get("thumbnail", ""),
        }
        for c in competitors
    ]
    if rows:
        result = upsert("fs_competitors", rows, on_conflict="channel_id")
        log.info("Saved %d competitors to Supabase", len(rows))
        return result


# ── Veille: Trending Videos ─────────────────────────────────────────────


def save_trending_videos(videos: list[dict]):
    rows = []
    for v in videos:
        rows.append({
            "video_id": v["video_id"] if "video_id" in v else v.get("url", "").split("v=")[-1],
            "title": v["title"],
            "channel": v.get("channel", ""),
            "channel_id": v.get("channel_id", ""),
            "views": v.get("views", 0),
            "likes": v.get("likes", 0),
            "comments": v.get("comments", 0),
            "tags": v.get("tags", []),
            "duration": v.get("duration", ""),
            "thumbnail": v.get("thumbnail", ""),
            "url": v.get("url", ""),
            "published_at": v.get("published_at"),
        })
    if rows:
        result = upsert("fs_trending_videos", rows, on_conflict="video_id")
        log.info("Saved %d trending videos to Supabase", len(rows))
        return result


# ── Veille: Top Tags ────────────────────────────────────────────────────


def save_top_tags(tags: list[tuple]):
    rows = [{"tag": t[0], "count": t[1]} for t in tags]
    if rows:
        result = upsert("fs_top_tags", rows, on_conflict="tag")
        log.info("Saved %d tags to Supabase", len(rows))
        return result


# ── Veille: Full Report ─────────────────────────────────────────────────


def save_veille_report(report: dict):
    row = {
        "period_days": report.get("period_days", 7),
        "total_videos_scanned": report.get("total_videos_scanned", 0),
        "report_data": report,
        "best_titles": report.get("best_titles", []),
        "top_tags": report.get("top_tags", []),
    }
    result = _request("POST", "fs_veille_reports", [row])
    log.info("Saved veille report to Supabase")
    return result


# ── Scripts ─────────────────────────────────────────────────────────────


def save_script(script_type: str, title: str, sections: list[dict], narration_text: str = ""):
    word_count = len(narration_text.split()) if narration_text else 0
    row = {
        "type": script_type,
        "title": title,
        "sections": sections,
        "narration_text": narration_text,
        "word_count": word_count,
        "status": "generated",
    }
    result = _request("POST", "fs_scripts", [row])
    if result and isinstance(result, list) and len(result) > 0:
        log.info("Saved script '%s' (id=%s) to Supabase", title, result[0].get("id"))
        return result[0]
    return result


# ── Generated Videos ────────────────────────────────────────────────────


def save_generated_video(
    script_id: int | None,
    video_type: str,
    filename: str,
    duration_seconds: float = 0,
    file_size_mb: float = 0,
    nb_images: int = 0,
    version: str = "v2",
):
    row = {
        "script_id": script_id,
        "type": video_type,
        "filename": filename,
        "duration_seconds": duration_seconds,
        "file_size_mb": file_size_mb,
        "nb_images": nb_images,
        "version": version,
        "status": "ready",
    }
    result = _request("POST", "fs_generated_videos", [row])
    if result and isinstance(result, list) and len(result) > 0:
        log.info("Saved video '%s' (id=%s) to Supabase", filename, result[0].get("id"))
        return result[0]
    return result


# ── Publication Schedule ────────────────────────────────────────────────


def schedule_publication(
    video_id: int,
    video_type: str,
    scheduled_at: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    seo_title: str = "",
    seo_description: str = "",
):
    row = {
        "video_id": video_id,
        "type": video_type,
        "scheduled_at": scheduled_at,
        "title": title,
        "description": description,
        "tags": tags or [],
        "seo_title": seo_title,
        "seo_description": seo_description,
        "status": "planned",
    }
    result = _request("POST", "fs_publication_schedule", [row])
    log.info("Scheduled '%s' for %s", title, scheduled_at)
    return result


# ── Queries ─────────────────────────────────────────────────────────────


def get_latest_report():
    result = _request("GET", "fs_veille_reports?order=created_at.desc&limit=1")
    return result[0] if result and len(result) > 0 else None


def get_upcoming_schedule():
    result = _request(
        "GET",
        "fs_publication_schedule?status=eq.planned&order=scheduled_at.asc&limit=10",
    )
    return result or []


def get_scripts(status: str = None, limit: int = 10):
    path = f"fs_scripts?order=created_at.desc&limit={limit}"
    if status:
        path += f"&status=eq.{status}"
    return _request("GET", path) or []
