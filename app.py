"""
Feu Sacre - Veille Concurrentielle YouTube
API Flask + Cron scheduler
"""

import json
import logging
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler

from config import PORT, CRON_HOUR, CRON_MINUTE
from youtube_scanner import generate_full_report
from notifier import send_telegram, format_report_telegram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)

# Stockage en memoire du dernier rapport
_latest_report: dict | None = None


def run_veille(days_back: int = 7, notify: bool = True):
    """Execute la veille et stocke le rapport."""
    global _latest_report
    log.info("Lancement veille concurrentielle (period=%d jours)", days_back)
    try:
        report = generate_full_report(days_back=days_back)
        _latest_report = report

        # Sauvegarde locale
        os.makedirs("/data/reports", exist_ok=True)
        filename = f"/data/reports/veille_{report['generated_at'][:10]}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        log.info("Rapport sauvegarde: %s", filename)

        if notify:
            msg = format_report_telegram(report)
            send_telegram(msg)
            log.info("Notification Telegram envoyee")

        return report
    except Exception as e:
        log.error("Erreur veille: %s", e, exc_info=True)
        if notify:
            send_telegram(f"ERREUR VEILLE FEU SACRE:\n{e}")
        raise


# ── Routes API ───────────────────────────────────────────────────────────


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "feu-sacre-veille", "time": datetime.now(timezone.utc).isoformat()})


@app.route("/api/veille", methods=["POST"])
def trigger_veille():
    """Declenche une veille manuellement."""
    days = request.json.get("days_back", 7) if request.is_json else 7
    notify = request.json.get("notify", True) if request.is_json else True
    report = run_veille(days_back=days, notify=notify)
    return jsonify({"status": "ok", "videos_found": report["total_videos_scanned"]})


@app.route("/api/report")
def get_report():
    """Retourne le dernier rapport genere."""
    if _latest_report is None:
        return jsonify({"error": "Aucun rapport disponible. Lancez POST /api/veille"}), 404
    return jsonify(_latest_report)


@app.route("/api/trending")
def get_trending():
    """Retourne les videos trending du dernier rapport."""
    if _latest_report is None:
        return jsonify({"error": "Aucun rapport disponible"}), 404
    limit = request.args.get("limit", 20, type=int)
    return jsonify(_latest_report["trending_videos"][:limit])


@app.route("/api/competitors")
def get_competitors():
    """Retourne les stats des concurrents."""
    if _latest_report is None:
        return jsonify({"error": "Aucun rapport disponible"}), 404
    return jsonify(_latest_report["competitors"])


@app.route("/api/tags")
def get_tags():
    """Retourne les top tags detectes."""
    if _latest_report is None:
        return jsonify({"error": "Aucun rapport disponible"}), 404
    return jsonify(_latest_report["top_tags"])


@app.route("/api/inspiration")
def get_inspiration():
    """Retourne les meilleurs titres pour s'inspirer."""
    if _latest_report is None:
        return jsonify({"error": "Aucun rapport disponible"}), 404
    return jsonify({
        "best_titles": _latest_report["best_titles"],
        "top_tags": _latest_report["top_tags"][:10],
        "competitors_top": _latest_report.get("competitors_top_videos", {}),
    })


# ── Scheduler ────────────────────────────────────────────────────────────


scheduler = BackgroundScheduler(timezone="Europe/Paris")
scheduler.add_job(
    run_veille,
    "cron",
    hour=CRON_HOUR,
    minute=CRON_MINUTE,
    id="daily_veille",
    replace_existing=True,
)


if __name__ == "__main__":
    scheduler.start()
    log.info("Scheduler demarre: veille quotidienne a %02d:%02d", CRON_HOUR, CRON_MINUTE)
    app.run(host="0.0.0.0", port=PORT, debug=False)
