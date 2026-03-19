"""
Feu Sacre - Pipeline Automatise
Veille -> Script LLM -> Images AI -> TTS -> Sous-titres -> Video -> Publication
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone, timedelta

from config import SCRIPT_SECTIONS_COUNT, DATA_DIR

log = logging.getLogger(__name__)


def run_full_pipeline(
    report: dict | None = None,
    days_back: int = 7,
    notify: bool = True,
    video_type: str = "long",
) -> dict:
    """
    Execute le pipeline complet:
    1. Veille concurrentielle (si pas de report fourni)
    2. Generation de script via LLM
    3. Generation d'images AI
    4. TTS avec timing mot-par-mot
    5. Sous-titres ASS modernes
    6. Composition video FFmpeg
    7. Persistence Supabase + planning publication
    8. Notification Telegram
    """
    from youtube_scanner import generate_full_report
    from script_generator import generate_script_from_veille, generate_title_and_metadata
    from image_generator import generate_images_for_script
    from tts_engine import generate_tts, get_duration
    from subtitle_engine import generate_ass, validate_sync
    from video_composer import build_segment, concatenate_segments
    import supabase_client as sb
    from notifier import send_telegram

    pipeline_start = datetime.now(timezone.utc)
    vertical = video_type == "short"
    w, h = (1080, 1920) if vertical else (1920, 1080)

    result = {
        "status": "running",
        "started_at": pipeline_start.isoformat(),
        "video_type": video_type,
        "steps": {},
    }

    tmp = tempfile.mkdtemp(prefix=f"feusacre_{video_type}_")
    log.info("Pipeline started: type=%s, tmp=%s", video_type, tmp)

    try:
        # ── Step 1: Veille ────────────────────────────────────────────
        if report is None:
            log.info("Step 1/7: Running veille...")
            report = generate_full_report(days_back=days_back)
            result["steps"]["veille"] = {
                "status": "ok",
                "videos_scanned": report.get("total_videos_scanned", 0),
            }
        else:
            result["steps"]["veille"] = {"status": "skipped (report provided)"}

        # ── Step 2: Script Generation ─────────────────────────────────
        log.info("Step 2/7: Generating script from veille data...")
        sections = generate_script_from_veille(report, video_type=video_type)
        metadata = generate_title_and_metadata(sections, report)

        total_words = sum(len(s["narration"].split()) for s in sections)
        total_images = sum(len(s["images"]) for s in sections)
        result["steps"]["script"] = {
            "status": "ok",
            "sections": len(sections),
            "words": total_words,
            "images_planned": total_images,
            "title": metadata.get("title", ""),
        }
        log.info("Script: %d sections, %d words, title='%s'",
                 len(sections), total_words, metadata.get("title", ""))

        # ── Step 3: Image Generation ──────────────────────────────────
        log.info("Step 3/7: Generating %d AI images...", total_images)
        section_images = generate_images_for_script(sections, tmp, vertical=vertical)
        result["steps"]["images"] = {
            "status": "ok",
            "total": sum(len(imgs) for imgs in section_images),
        }

        # ── Step 4+5: TTS + Subtitles per section ────────────────────
        log.info("Step 4-5/7: TTS + subtitles per section...")
        segment_paths = []
        total_duration = 0

        for sec_i, section in enumerate(sections):
            narration = section.get("narration", "").strip()
            images = section_images[sec_i] if sec_i < len(section_images) else []

            if not narration or not images:
                log.warning("Section %d: skip (no narration or images)", sec_i)
                continue

            # TTS
            audio_path = os.path.join(tmp, f"audio_{sec_i:02d}.mp3")
            words_timing = generate_tts(narration, audio_path)
            duration = get_duration(audio_path)

            # Validate and fix sync
            words_timing = validate_sync(words_timing, duration)

            # ASS subtitles (modern style)
            ass_path = os.path.join(tmp, f"subs_{sec_i:02d}.ass")
            generate_ass(words_timing, ass_path, width=w, height=h, vertical=vertical)

            # Build video segment
            seg_path = os.path.join(tmp, f"seg_{sec_i:02d}.mp4")
            log.info("Section %d/%d: %.1fs, %d images",
                     sec_i + 1, len(sections), duration, len(images))
            d = build_segment(images, audio_path, ass_path, seg_path, w=w, h=h)
            segment_paths.append(seg_path)
            total_duration += d

        result["steps"]["tts_subtitles"] = {
            "status": "ok",
            "segments": len(segment_paths),
            "total_duration": round(total_duration, 1),
        }

        # ── Step 6: Final Assembly ────────────────────────────────────
        log.info("Step 6/7: Assembling final video...")
        os.makedirs(os.path.join(DATA_DIR, "videos"), exist_ok=True)
        timestamp = pipeline_start.strftime("%Y%m%d_%H%M")
        filename = f"feu_sacre_{video_type}_{timestamp}.mp4"
        output_path = os.path.join(DATA_DIR, "videos", filename)

        final_duration = concatenate_segments(segment_paths, output_path)
        file_size_mb = round(os.path.getsize(output_path) / (1024 * 1024), 1)

        result["steps"]["assembly"] = {
            "status": "ok",
            "duration_seconds": round(final_duration, 1),
            "duration_human": f"{int(final_duration // 60)}min {int(final_duration % 60)}s",
            "file_size_mb": file_size_mb,
            "output": output_path,
        }
        log.info("Video: %s (%.1f MB, %s)",
                 filename, file_size_mb,
                 result["steps"]["assembly"]["duration_human"])

        # ── Step 7: Upload to YouTube ────────────────────────────────
        log.info("Step 7/8: Uploading to YouTube as private...")
        youtube_result = None
        try:
            from youtube_uploader import upload_video
            youtube_result = upload_video(
                video_path=output_path,
                title=metadata.get("title", f"Feu Sacre {video_type}"),
                description=metadata.get("description", ""),
                tags=metadata.get("tags", []),
                video_type=video_type,  # "short" or "long" -> proper categorization
                privacy="private",
            )
            result["steps"]["youtube_upload"] = {
                "status": "ok",
                "video_id": youtube_result["video_id"],
                "url": youtube_result["url"],
                "type": youtube_result["type"],
            }
            log.info("YouTube upload OK: %s (%s)", youtube_result["url"], video_type)
        except Exception as e:
            log.error("YouTube upload failed: %s", e)
            result["steps"]["youtube_upload"] = {"status": "failed", "error": str(e)}

        # ── Step 8: Persist + Schedule ────────────────────────────────
        log.info("Step 8/8: Saving to Supabase + scheduling...")

        # Save script
        narration_full = " ".join(s["narration"] for s in sections)
        script_record = sb.save_script(
            script_type=video_type,
            title=metadata.get("title", f"Feu Sacre {video_type}"),
            sections=[{"titre": s["titre"], "nb_images": len(s["images"])} for s in sections],
            narration_text=narration_full,
        )

        # Save video
        script_id = script_record.get("id") if script_record else None
        video_record = sb.save_generated_video(
            script_id=script_id,
            video_type=video_type,
            filename=filename,
            duration_seconds=round(final_duration, 1),
            file_size_mb=file_size_mb,
            nb_images=sum(len(imgs) for imgs in section_images),
        )

        # Schedule publication (next available slot: tomorrow 17h Paris time)
        if video_record and video_record.get("id"):
            scheduled_at = (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).replace(hour=16, minute=0, second=0).isoformat()

            sb.schedule_publication(
                video_id=video_record["id"],
                video_type=video_type,
                scheduled_at=scheduled_at,
                title=metadata.get("title", ""),
                description=metadata.get("description", ""),
                tags=metadata.get("tags", []),
                seo_title=metadata.get("title", ""),
                seo_description=metadata.get("description", ""),
            )

        result["steps"]["persistence"] = {"status": "ok"}

        # Save veille report too
        if report:
            try:
                sb.save_competitors(report.get("competitors", []))
                sb.save_trending_videos(report.get("trending_videos", []))
                sb.save_top_tags(report.get("top_tags", []))
                sb.save_veille_report(report)
            except Exception as e:
                log.warning("Supabase veille save error: %s", e)

        # Notification
        if notify:
            yt_url = youtube_result["url"] if youtube_result else "Upload echoue"
            yt_type = "SHORT" if video_type == "short" else "VIDEO"
            msg = (
                f"<b>FEU SACRE - {yt_type} UPLOADEE</b>\n\n"
                f"<b>{metadata.get('title', 'Nouvelle video')}</b>\n\n"
                f"Type: {video_type}\n"
                f"Duree: {result['steps']['assembly']['duration_human']}\n"
                f"Taille: {file_size_mb} MB\n"
                f"Images: {sum(len(imgs) for imgs in section_images)}\n"
                f"Mots: {total_words}\n\n"
                f"YouTube: {yt_url}\n"
                f"Statut: Privee (review avant publication)"
            )
            send_telegram(msg)

        result["status"] = "completed"
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        result["output"] = {
            "video_path": output_path,
            "filename": filename,
            "title": metadata.get("title", ""),
            "duration": result["steps"]["assembly"]["duration_human"],
            "size_mb": file_size_mb,
        }

        log.info("Pipeline completed successfully: %s", filename)

    except Exception as e:
        log.error("Pipeline failed: %s", e, exc_info=True)
        result["status"] = "failed"
        result["error"] = str(e)

        if notify:
            send_telegram(f"<b>ERREUR PIPELINE FEU SACRE:</b>\n{e}")

    return result


def run_veille_and_adapt(days_back: int = 7, notify: bool = True) -> dict:
    """
    Execute la veille ET applique automatiquement les modifications.
    C'est cette fonction qui est appelee par le cron quotidien.

    Flow:
    1. Veille concurrentielle
    2. Analyse des insights -> adapte les prochaines videos
    3. Lance la generation video automatique
    4. Notifie le resultat
    """
    from youtube_scanner import generate_full_report
    from notifier import send_telegram, format_report_telegram
    import supabase_client as sb

    log.info("=== VEILLE + PIPELINE AUTOMATIQUE ===")

    # 1. Veille
    report = generate_full_report(days_back=days_back)

    # Save report locally
    os.makedirs(os.path.join(DATA_DIR, "reports"), exist_ok=True)
    filename = os.path.join(DATA_DIR, "reports", f"veille_{report['generated_at'][:10]}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 2. Notify veille results
    if notify:
        msg = format_report_telegram(report)
        send_telegram(msg)

    # 3. Generate video from veille data
    log.info("Launching video pipeline from veille data...")
    pipeline_result = run_full_pipeline(
        report=report,
        days_back=days_back,
        notify=notify,
        video_type="long",
    )

    return {
        "veille": {
            "generated_at": report["generated_at"],
            "videos_scanned": report["total_videos_scanned"],
            "competitors": len(report.get("competitors", [])),
        },
        "pipeline": pipeline_result,
    }
