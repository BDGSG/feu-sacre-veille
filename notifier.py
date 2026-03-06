"""
Notifications Telegram pour les rapports de veille.
"""

import logging
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

log = logging.getLogger(__name__)


def send_telegram(message: str):
    """Envoie un message Telegram (max 4096 chars, split si necessaire)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram non configure (BOT_TOKEN ou CHAT_ID manquant)")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = [message[i : i + 4000] for i in range(0, len(message), 4000)]

    for chunk in chunks:
        try:
            requests.post(
                url,
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
        except Exception as e:
            log.error("Erreur envoi Telegram: %s", e)


def format_report_telegram(report: dict) -> str:
    """Formate le rapport en message Telegram lisible."""
    lines = [
        f"<b>VEILLE FEU SACRE</b> - {report['generated_at'][:10]}",
        f"Periode: {report['period_days']} jours | {report['total_videos_scanned']} videos scannees",
        "",
        "<b>CONCURRENTS</b>",
    ]

    for c in report.get("competitors", [])[:10]:
        lines.append(
            f"  {c['title']}: {c['subscribers']:,} abos | {c['total_views']:,} vues"
        )

    lines.append("")
    lines.append("<b>TOP 10 VIDEOS TRENDING</b>")
    for i, v in enumerate(report.get("trending_videos", [])[:10], 1):
        lines.append(
            f"{i}. <b>{v['title'][:60]}</b>\n"
            f"   {v['channel']} | {v['views']:,} vues | {v['likes']:,} likes\n"
            f"   {v['url']}"
        )

    lines.append("")
    lines.append("<b>TOP TAGS</b>")
    tag_str = ", ".join(f"{t[0]}({t[1]})" for t in report.get("top_tags", [])[:15])
    lines.append(tag_str)

    lines.append("")
    lines.append("<b>MEILLEURS TITRES (inspiration)</b>")
    for t in report.get("best_titles", [])[:5]:
        lines.append(f"  - {t['title'][:70]} ({t['views']:,} vues)")

    return "\n".join(lines)
