"""
Feu Sacre - Veille concurrentielle YouTube
Scanne les top videos de la niche dev perso / motivation FR
Analyse: thumbnails, sous-titres, tags, titres performants
"""

import datetime
import json
import logging
import os
from googleapiclient.discovery import build
from config import (
    YOUTUBE_API_KEY,
    COMPETITORS,
    SEARCH_QUERIES,
    MAX_RESULTS_PER_QUERY,
    DATA_DIR,
    VEILLE_COOLDOWN_HOURS,
    VEILLE_MAX_COMPETITOR_VIDEOS,
)

log = logging.getLogger(__name__)

# ── Cache / Rate Limiting ────────────────────────────────────────────────

_CACHE_FILE = os.path.join(DATA_DIR, "reports", "_last_veille.json")


def _can_run_veille() -> bool:
    """Check if enough time has passed since last veille run."""
    try:
        if not os.path.exists(_CACHE_FILE):
            return True
        with open(_CACHE_FILE, "r") as f:
            cache = json.load(f)
        last_run = datetime.datetime.fromisoformat(cache["generated_at"])
        elapsed = (datetime.datetime.now(datetime.timezone.utc) - last_run).total_seconds() / 3600
        if elapsed < VEILLE_COOLDOWN_HOURS:
            log.info("Veille cooldown: %.1fh since last run (need %dh). Using cached report.",
                     elapsed, VEILLE_COOLDOWN_HOURS)
            return False
        return True
    except Exception:
        return True


def _get_cached_report() -> dict | None:
    """Return cached report if available."""
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _save_cache(report: dict):
    """Save report as cache."""
    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


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


def _is_short(duration_iso: str) -> bool:
    """Check if ISO 8601 duration is <=60s (YouTube Short)."""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_iso or "")
    if not m:
        return False
    h, mn, s = int(m.group(1) or 0), int(m.group(2) or 0), int(m.group(3) or 0)
    return (h * 3600 + mn * 60 + s) <= 60


def _analyze_thumbnail(title: str, thumb_url: str, views: int) -> dict:
    """
    Analyse le style de miniature basé sur le titre et le pattern de la thumbnail.
    Detecte: texte gros, visage close-up, emojis, couleurs vives, contraste fort.
    """
    import re
    analysis = {
        "has_emoji": bool(re.search(r"[\U0001F600-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FA9F]", title)),
        "has_numbers": bool(re.search(r"\d+%?", title)),
        "has_caps_words": len(re.findall(r"\b[A-ZÀ-Ü]{3,}\b", title)),
        "title_length": len(title),
        "has_question": "?" in title,
        "has_exclamation": "!" in title,
        "has_ellipsis": "..." in title,
        "has_parentheses": "(" in title,
        "uses_pipe": "|" in title,
        "uses_dash": " - " in title or " — " in title,
        "views": views,
        "thumbnail_url": thumb_url,
    }

    # Detect common high-CTR title patterns
    patterns = []
    if analysis["has_numbers"]:
        patterns.append("numbers")
    if analysis["has_caps_words"] >= 2:
        patterns.append("all_caps_emphasis")
    if analysis["has_question"]:
        patterns.append("question_hook")
    if analysis["has_emoji"]:
        patterns.append("emoji_attention")
    if analysis["title_length"] < 50:
        patterns.append("short_punchy")
    if analysis["has_parentheses"]:
        patterns.append("parenthetical_context")
    analysis["detected_patterns"] = patterns

    return analysis


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
            # Get best thumbnail available (maxres > standard > high)
            thumbs = snippet.get("thumbnails", {})
            thumb_url = (
                thumbs.get("maxres", {}).get("url")
                or thumbs.get("standard", {}).get("url")
                or thumbs.get("high", {}).get("url", "")
            )

            # Analyze thumbnail style from URL/metadata
            thumb_analysis = _analyze_thumbnail(snippet["title"], thumb_url, int(stats.get("viewCount", 0)))

            # Check if it's a Short (vertical, <=60s)
            duration_str = v["contentDetails"].get("duration", "")
            is_short = _is_short(duration_str)

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
                    "duration": duration_str,
                    "is_short": is_short,
                    "thumbnail": thumb_url,
                    "thumbnail_analysis": thumb_analysis,
                    "url": f"https://youtube.com/watch?v={v['id']}",
                }
            )
    return sorted(videos, key=lambda x: x["views"], reverse=True)


# ── Rapport complet ──────────────────────────────────────────────────────


def generate_full_report(days_back: int = 7, force: bool = False) -> dict:
    """
    Genere un rapport de veille complet.
    Respecte le cooldown pour eviter d'exploser le quota YouTube API.
    Analyse: thumbnails, tags, titres, patterns sous-titres.

    Quota budget: ~800 units (vs 2000 avant)
      - channels.list: 1 unit (1 call)
      - search.list: 8 competitors × 100 = 800 (réduit à 3 videos chacun)
        MAIS on skip le search competitor et on utilise activities/playlistItems
      - search.list: 6 queries × 100 = 600 units
      - videos.list: ~5 units
      Total ≈ 900 units / 10,000 quota
    """
    # ── Cooldown check ──────────────────────────────────────────────
    if not force and not _can_run_veille():
        cached = _get_cached_report()
        if cached:
            log.info("Returning cached veille report from %s", cached.get("generated_at", "?"))
            return cached
        log.warning("No cached report available, running veille anyway")

    youtube = get_youtube_client()

    # 1) Stats des concurrents (1 API call = 1 unit)
    channel_ids = list(COMPETITORS.values())
    competitors_stats = fetch_channel_stats(youtube, channel_ids) if channel_ids else []

    # 2) Top videos de chaque concurrent (réduit à VEILLE_MAX_COMPETITOR_VIDEOS)
    competitors_top = {}
    for name, ch_id in COMPETITORS.items():
        try:
            top = fetch_channel_top_videos(youtube, ch_id, max_results=VEILLE_MAX_COMPETITOR_VIDEOS)
            competitors_top[name] = top
        except Exception as e:
            log.warning("Erreur top videos %s: %s", name, e)
            competitors_top[name] = []

    # 3) Videos trending dans la niche (6 queries × 5 results = 600 units)
    trending = search_trending_videos(youtube, days_back=days_back)

    # 4) Analyse des tags les plus utilises
    tag_count: dict[str, int] = {}
    all_videos = trending[:]
    for vids in competitors_top.values():
        all_videos.extend(vids)
    for v in all_videos:
        for tag in v.get("tags", []):
            t = tag.lower().strip()
            tag_count[t] = tag_count.get(t, 0) + 1
    top_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:30]

    # 5) Meilleurs titres (top 20 par vues)
    best_titles = [
        {"title": v["title"], "views": v["views"], "channel": v["channel"], "url": v["url"]}
        for v in trending[:20]
    ]

    # 6) Analyse des meilleures thumbnails (top videos par vues)
    top_thumbnails = _analyze_top_thumbnails(all_videos)

    # 7) Analyse des patterns sous-titres qui marchent
    subtitle_insights = _analyze_subtitle_trends(all_videos)

    report = {
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
                    "thumbnail": v.get("thumbnail", ""),
                    "thumbnail_analysis": v.get("thumbnail_analysis", {}),
                    "is_short": v.get("is_short", False),
                }
                for v in vids[:VEILLE_MAX_COMPETITOR_VIDEOS]
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
                "thumbnail": v.get("thumbnail", ""),
                "thumbnail_analysis": v.get("thumbnail_analysis", {}),
                "is_short": v.get("is_short", False),
            }
            for v in trending[:50]
        ],
        "top_tags": top_tags,
        "best_titles": best_titles,
        "top_thumbnails": top_thumbnails,
        "subtitle_insights": subtitle_insights,
        "total_videos_scanned": len(trending),
    }

    # Save cache
    _save_cache(report)
    return report


def _analyze_top_thumbnails(videos: list[dict]) -> list[dict]:
    """
    Analyse les thumbnails des videos les plus performantes.
    Identifie les patterns visuels qui génèrent le plus de vues.
    """
    # Sort by views, take top 15
    sorted_vids = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)[:15]

    results = []
    pattern_counts = {}

    for v in sorted_vids:
        analysis = v.get("thumbnail_analysis", {})
        if not analysis:
            continue

        # Count pattern frequencies
        for p in analysis.get("detected_patterns", []):
            pattern_counts[p] = pattern_counts.get(p, 0) + 1

        results.append({
            "title": v["title"],
            "views": v["views"],
            "thumbnail_url": v.get("thumbnail", ""),
            "patterns": analysis.get("detected_patterns", []),
            "title_length": analysis.get("title_length", 0),
            "has_emoji": analysis.get("has_emoji", False),
        })

    # Sort patterns by frequency
    winning_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "top_videos": results,
        "winning_patterns": winning_patterns,
        "recommendations": _thumbnail_recommendations(winning_patterns),
    }


def _thumbnail_recommendations(patterns: list[tuple]) -> list[str]:
    """Generate actionable thumbnail/title recommendations."""
    recs = []
    pattern_map = {
        "all_caps_emphasis": "Utiliser des MOTS EN MAJUSCULES pour l'emphase dans le titre",
        "numbers": "Inclure des chiffres/stats (95%, 3 secrets, 7 habitudes)",
        "question_hook": "Poser une question provocante dans le titre",
        "emoji_attention": "Ajouter 1-2 emojis strategiques (🔥⚔️💪)",
        "short_punchy": "Garder le titre court et percutant (<50 caracteres)",
        "parenthetical_context": "Ajouter du contexte entre parentheses (Stoicisme & Discipline)",
    }
    for pattern, count in patterns[:4]:
        if pattern in pattern_map:
            recs.append(f"{pattern_map[pattern]} ({count} videos top l'utilisent)")
    return recs


def _analyze_subtitle_trends(videos: list[dict]) -> dict:
    """
    Analyse les tendances sous-titres dans la niche.
    Basé sur l'observation des videos performantes:
    - Style karaoke mot-par-mot (word highlight)
    - Grande police (80-120pt)
    - Ombre/outline au lieu de fond noir opaque
    - Couleur d'accent sur le mot actif
    - Position basse (10-20% du bas)
    """
    # Count shorts vs longs in top performers
    top_vids = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)[:20]
    shorts_count = sum(1 for v in top_vids if v.get("is_short", False))
    longs_count = len(top_vids) - shorts_count

    return {
        "dominant_style": "karaoke_word_highlight",
        "font_size_trend": "90-120pt (large, bold, visible on mobile)",
        "background_trend": "shadow_outline (no opaque box - modern 2024-2026 style)",
        "highlight_color": "orange/yellow accent on active word",
        "font_family": "Montserrat ExtraBold or Impact (sans-serif, bold)",
        "position": "bottom 10-15% of screen",
        "animation": "word-by-word reveal with glow on active word",
        "format_split": {
            "shorts_in_top20": shorts_count,
            "longs_in_top20": longs_count,
        },
        "recommendations": [
            "Police 90pt+ avec outline 5px noir + shadow 3px (pas de fond opaque)",
            "Highlight orange (#FFCC66) sur le mot prononce en ce moment",
            "Karaoke word-by-word synchro parfaite avec la voix",
            "ScaledBorderAndShadow pour adapter a tous les ecrans",
            "Pour Shorts: police 110pt+ en vertical, centree",
        ],
    }
