"""
Feu Sacre - Veille concurrentielle YouTube
Scanne les top videos de la niche dev perso / motivation FR
"""

import datetime
import logging
from googleapiclient.discovery import build
from config import (
    YOUTUBE_API_KEY,
    COMPETITORS,
    SEARCH_QUERIES,
    MAX_RESULTS_PER_QUERY,
)

log = logging.getLogger(__name__)


def get_youtube_client():
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


# ── Resolution des handles ───────────────────────────────────────────────


def resolve_competitor_ids(youtube) -> dict[str, str]:
    """Resout les handles (@xxx) en channel IDs. Retourne {nom: channel_id}."""
    resolved = {}
    for name, identifier in COMPETITORS.items():
        if identifier.startswith("UC") and len(identifier) == 24:
            resolved[name] = identifier
            continue
        # Handle format: @handle -> search via channels().list(forHandle=...)
        handle = identifier.lstrip("@")
        try:
            resp = (
                youtube.channels()
                .list(part="id", forHandle=handle)
                .execute()
            )
            items = resp.get("items", [])
            if items:
                resolved[name] = items[0]["id"]
                log.info("Resolved @%s -> %s", handle, items[0]["id"])
            else:
                log.warning("Handle @%s not found, trying search", handle)
                resp2 = (
                    youtube.search()
                    .list(part="snippet", q=handle, type="channel", maxResults=1)
                    .execute()
                )
                items2 = resp2.get("items", [])
                if items2:
                    resolved[name] = items2[0]["snippet"]["channelId"]
                    log.info("Resolved %s via search -> %s", handle, resolved[name])
                else:
                    log.warning("Could not resolve %s", name)
        except Exception as e:
            log.warning("Error resolving %s: %s", name, e)
    return resolved


# ── Analyse des concurrents ──────────────────────────────────────────────


def fetch_channel_stats(youtube, channel_ids: list[str]) -> list[dict]:
    """Recupere les stats de base de chaque chaine concurrente."""
    results = []
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i : i + 50]
        resp = (
            youtube.channels()
            .list(part="snippet,statistics,brandingSettings", id=",".join(batch))
            .execute()
        )
        for ch in resp.get("items", []):
            stats = ch.get("statistics", {})
            results.append(
                {
                    "channel_id": ch["id"],
                    "title": ch["snippet"]["title"],
                    "subscribers": int(stats.get("subscriberCount", 0)),
                    "total_views": int(stats.get("viewCount", 0)),
                    "video_count": int(stats.get("videoCount", 0)),
                    "description": ch["snippet"].get("description", "")[:200],
                    "thumbnail": ch["snippet"]["thumbnails"].get("high", {}).get(
                        "url", ""
                    ),
                }
            )
    return sorted(results, key=lambda x: x["subscribers"], reverse=True)


def fetch_channel_top_videos(
    youtube, channel_id: str, max_results: int = 10, order: str = "viewCount"
) -> list[dict]:
    """Recupere les top videos d'une chaine par vues ou date."""
    search_resp = (
        youtube.search()
        .list(
            part="id",
            channelId=channel_id,
            type="video",
            order=order,
            maxResults=max_results,
        )
        .execute()
    )
    video_ids = [
        item["id"]["videoId"]
        for item in search_resp.get("items", [])
        if item["id"].get("videoId")
    ]
    if not video_ids:
        return []
    return _enrich_videos(youtube, video_ids)


# ── Recherche par mots-cles ─────────────────────────────────────────────


def search_trending_videos(
    youtube, days_back: int = 7, max_per_query: int = None
) -> list[dict]:
    """Cherche les videos tendance dans la niche sur les N derniers jours."""
    if max_per_query is None:
        max_per_query = MAX_RESULTS_PER_QUERY

    published_after = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=days_back)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    all_video_ids = set()
    for query in SEARCH_QUERIES:
        try:
            resp = (
                youtube.search()
                .list(
                    part="id",
                    q=query,
                    type="video",
                    relevanceLanguage="fr",
                    regionCode="FR",
                    order="viewCount",
                    publishedAfter=published_after,
                    maxResults=max_per_query,
                )
                .execute()
            )
            for item in resp.get("items", []):
                vid = item["id"].get("videoId")
                if vid:
                    all_video_ids.add(vid)
        except Exception as e:
            log.warning("Erreur recherche '%s': %s", query, e)

    if not all_video_ids:
        return []

    return _enrich_videos(youtube, list(all_video_ids))


# ── Enrichissement des videos ────────────────────────────────────────────


def _enrich_videos(youtube, video_ids: list[str]) -> list[dict]:
    """Recupere les details complets d'une liste de video IDs."""
    videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        resp = (
            youtube.videos()
            .list(part="snippet,statistics,contentDetails", id=",".join(batch))
            .execute()
        )
        for v in resp.get("items", []):
            stats = v.get("statistics", {})
            snippet = v["snippet"]
            videos.append(
                {
                    "video_id": v["id"],
                    "title": snippet["title"],
                    "channel": snippet.get("channelTitle", ""),
                    "channel_id": snippet.get("channelId", ""),
                    "published_at": snippet["publishedAt"],
                    "description": snippet.get("description", "")[:300],
                    "tags": snippet.get("tags", [])[:15],
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "duration": v["contentDetails"].get("duration", ""),
                    "thumbnail": snippet["thumbnails"]
                    .get("high", {})
                    .get("url", ""),
                    "url": f"https://youtube.com/watch?v={v['id']}",
                }
            )
    return sorted(videos, key=lambda x: x["views"], reverse=True)


# ── Rapport complet ──────────────────────────────────────────────────────


def generate_full_report(days_back: int = 7) -> dict:
    """Genere un rapport de veille complet."""
    youtube = get_youtube_client()

    # 1) Resolve handles -> channel IDs
    resolved = resolve_competitor_ids(youtube)
    channel_ids = list(resolved.values())

    # 2) Stats des concurrents
    competitors_stats = fetch_channel_stats(youtube, channel_ids) if channel_ids else []

    # 3) Top videos de chaque concurrent (les 5 dernieres par vues)
    competitors_top = {}
    for name, ch_id in resolved.items():
        try:
            top = fetch_channel_top_videos(youtube, ch_id, max_results=5)
            competitors_top[name] = top
        except Exception as e:
            log.warning("Erreur top videos %s: %s", name, e)
            competitors_top[name] = []

    # 4) Videos trending dans la niche
    trending = search_trending_videos(youtube, days_back=days_back, max_per_query=10)

    # 5) Analyse des tags les plus utilises
    tag_count: dict[str, int] = {}
    all_videos = trending[:]
    for vids in competitors_top.values():
        all_videos.extend(vids)
    for v in all_videos:
        for tag in v.get("tags", []):
            t = tag.lower().strip()
            tag_count[t] = tag_count.get(t, 0) + 1
    top_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:30]

    # 6) Meilleurs titres (top 20 par vues)
    best_titles = [
        {"title": v["title"], "views": v["views"], "channel": v["channel"], "url": v["url"]}
        for v in trending[:20]
    ]

    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "period_days": days_back,
        "competitors": competitors_stats,
        "competitors_top_videos": {
            name: [
                {
                    "title": v["title"],
                    "views": v["views"],
                    "likes": v["likes"],
                    "url": v["url"],
                    "published_at": v["published_at"],
                }
                for v in vids[:5]
            ]
            for name, vids in competitors_top.items()
        },
        "trending_videos": [
            {
                "title": v["title"],
                "channel": v["channel"],
                "views": v["views"],
                "likes": v["likes"],
                "comments": v["comments"],
                "tags": v["tags"],
                "url": v["url"],
                "published_at": v["published_at"],
            }
            for v in trending[:50]
        ],
        "top_tags": top_tags,
        "best_titles": best_titles,
        "total_videos_scanned": len(trending),
    }
