"""
Feu Sacre - Pipeline Automatise Complet
Veille concurrentielle + Generation video automatique
API Flask + Cron scheduler
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler

from config import PORT, CRON_HOUR, CRON_MINUTE, DATA_DIR
from youtube_scanner import generate_full_report
from notifier import send_telegram, format_report_telegram
from pipeline import run_veille_and_adapt, run_full_pipeline
import supabase_client as sb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)

# State
_latest_report: dict | None = None
_pipeline_status: dict | None = None
_pipeline_lock = threading.Lock()


def daily_job():
    """Job quotidien: veille + generation video automatique."""
    global _latest_report, _pipeline_status

    if not _pipeline_lock.acquire(blocking=False):
        log.warning("Pipeline already running, skipping daily job")
        return

    try:
        _pipeline_status = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}
        result = run_veille_and_adapt(days_back=7, notify=True)

        # Store veille report in memory
        if "veille" in result:
            veille_report = result["veille"]
            # Re-fetch full report for API endpoints
            try:
                _latest_report = generate_full_report(days_back=7)
            except Exception:
                pass

        _pipeline_status = result
        log.info("Daily job completed: %s", result.get("pipeline", {}).get("status", "?"))
    except Exception as e:
        log.error("Daily job failed: %s", e, exc_info=True)
        _pipeline_status = {"status": "failed", "error": str(e)}
        send_telegram(f"<b>ERREUR JOB QUOTIDIEN FEU SACRE:</b>\n{e}")
    finally:
        _pipeline_lock.release()


# ── Routes API ───────────────────────────────────────────────────────────


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "feu-sacre-pipeline",
        "time": datetime.now(timezone.utc).isoformat(),
        "pipeline": _pipeline_status.get("status") if _pipeline_status else "idle",
    })


@app.route("/api/veille", methods=["POST"])
def trigger_veille():
    """Declenche une veille seule (sans generation video)."""
    global _latest_report
    try:
        days = request.json.get("days_back", 7) if request.is_json else 7
        notify = request.json.get("notify", True) if request.is_json else True

        report = generate_full_report(days_back=days)
        _latest_report = report

        # Persist
        reports_dir = os.path.join(DATA_DIR, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        filename = os.path.join(reports_dir, f"veille_{report['generated_at'][:10]}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        try:
            sb.save_competitors(report.get("competitors", []))
            sb.save_trending_videos(report.get("trending_videos", []))
            sb.save_top_tags(report.get("top_tags", []))
            sb.save_veille_report(report)
        except Exception as e:
            log.warning("Supabase error: %s", e)

        if notify:
            send_telegram(format_report_telegram(report))

        return jsonify({"status": "ok", "videos_found": report["total_videos_scanned"]})
    except Exception as e:
        log.error("Veille error: %s", e, exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/pipeline", methods=["POST"])
def trigger_pipeline():
    """Declenche le pipeline complet: veille + script + video."""
    global _pipeline_status

    if not _pipeline_lock.acquire(blocking=False):
        return jsonify({"status": "error", "error": "Pipeline already running"}), 409

    try:
        days = request.json.get("days_back", 7) if request.is_json else 7
        notify = request.json.get("notify", True) if request.is_json else True
        video_type = request.json.get("type", "long") if request.is_json else "long"

        # Run in background thread to not block API
        def _run():
            global _pipeline_status
            try:
                _pipeline_status = run_full_pipeline(
                    days_back=days, notify=notify, video_type=video_type,
                )
            except Exception as e:
                _pipeline_status = {"status": "failed", "error": str(e)}
            finally:
                _pipeline_lock.release()

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        return jsonify({"status": "started", "type": video_type})
    except Exception:
        _pipeline_lock.release()
        raise


@app.route("/api/pipeline/status")
def pipeline_status():
    """Retourne le statut du pipeline en cours."""
    if _pipeline_status is None:
        return jsonify({"status": "idle"})
    return jsonify(_pipeline_status)


@app.route("/api/report")
def get_report():
    if _latest_report is None:
        return jsonify({"error": "Aucun rapport disponible. Lancez POST /api/veille"}), 404
    return jsonify(_latest_report)


@app.route("/api/trending")
def get_trending():
    if _latest_report is None:
        return jsonify({"error": "Aucun rapport disponible"}), 404
    limit = request.args.get("limit", 20, type=int)
    return jsonify(_latest_report["trending_videos"][:limit])


@app.route("/api/competitors")
def get_competitors():
    if _latest_report is None:
        return jsonify({"error": "Aucun rapport disponible"}), 404
    return jsonify(_latest_report["competitors"])


@app.route("/api/tags")
def get_tags():
    if _latest_report is None:
        return jsonify({"error": "Aucun rapport disponible"}), 404
    return jsonify(_latest_report["top_tags"])


@app.route("/api/inspiration")
def get_inspiration():
    if _latest_report is None:
        return jsonify({"error": "Aucun rapport disponible"}), 404
    return jsonify({
        "best_titles": _latest_report["best_titles"],
        "top_tags": _latest_report["top_tags"][:10],
        "competitors_top": _latest_report.get("competitors_top_videos", {}),
    })


@app.route("/api/db/report")
def get_db_report():
    report = sb.get_latest_report()
    if not report:
        return jsonify({"error": "Aucun rapport en base"}), 404
    return jsonify(report)


@app.route("/api/db/schedule")
def get_db_schedule():
    return jsonify(sb.get_upcoming_schedule())


@app.route("/api/db/scripts")
def get_db_scripts():
    status = request.args.get("status")
    limit = request.args.get("limit", 10, type=int)
    return jsonify(sb.get_scripts(status=status, limit=limit))


# ── Scheduler ────────────────────────────────────────────────────────────


scheduler = BackgroundScheduler(timezone="Europe/Paris")
scheduler.add_job(
    daily_job,
    "cron",
    hour=CRON_HOUR,
    minute=CRON_MINUTE,
    id="daily_pipeline",
    replace_existing=True,
    misfire_grace_time=3600,
)
scheduler.start()
log.info("Scheduler: pipeline quotidien a %02d:%02d", CRON_HOUR, CRON_MINUTE)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
