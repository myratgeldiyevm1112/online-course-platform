import json
import logging
import os
import subprocess
import tempfile
import uuid

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
BUCKET_VIDEOS = "courses-videos"
BUCKET_THUMBNAILS = "course-thumbnails"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://course_user:course_pass@localhost:5432/course_db"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _get_minio():
    from minio import Minio
    return Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def _get_redis():
    import redis as _redis
    return _redis.from_url(REDIS_URL, decode_responses=True)


def _set_status(upload_id: str, status: str):
    r = _get_redis()
    r.set(f"upload:status:{upload_id}", status, ex=3600 * 24)


def _db_get_upload(upload_id: str):
    """Sync DB query using psycopg2 directly."""
    import psycopg2
    db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, lesson_id, object_key, status FROM media_uploads WHERE id = %s",
        (upload_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "lesson_id": row[1], "object_key": row[2], "status": row[3]}


def _db_update_upload_status(upload_id: str, status: str):
    import psycopg2
    db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(
        "UPDATE media_uploads SET status = %s, updated_at = NOW() WHERE id = %s",
        (status, upload_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def _db_update_lesson(lesson_id: str, content_url: str, duration_seconds: int):
    import psycopg2
    db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(
        "UPDATE lessons SET content_url = %s, duration_seconds = %s, updated_at = NOW() WHERE id = %s",
        (content_url, duration_seconds, lesson_id)
    )
    conn.commit()
    cur.close()
    conn.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def transcode_video(self, upload_id: str):
    logger.info(f"[transcode_video] Starting for upload_id={upload_id}")
    _set_status(upload_id, "PROCESSING")

    try:
        upload = _db_get_upload(upload_id)
        if not upload:
            _set_status(upload_id, "FAILED")
            return {"status": "failed", "reason": "upload not found"}

        object_key = str(upload["object_key"])
        lesson_id = str(upload["lesson_id"])
        minio = _get_minio()

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Download source video
            source_path = os.path.join(tmpdir, "source.mp4")
            minio.fget_object(BUCKET_VIDEOS, object_key, source_path)
            logger.info(f"[transcode_video] Downloaded source to {source_path}")

            # 2. Get duration via ffprobe
            duration_seconds = 0
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-print_format", "json",
                     "-show_format", source_path],
                    capture_output=True, text=True,
                )
                if probe.returncode == 0:
                    info = json.loads(probe.stdout)
                    duration_seconds = int(float(info.get("format", {}).get("duration", 0)))
            except Exception as e:
                logger.warning(f"ffprobe failed: {e}")

            # 3. Transcode to HLS
            hls_dir = os.path.join(tmpdir, "hls")
            os.makedirs(hls_dir, exist_ok=True)

            qualities = [
                ("360p", "640x360", "800k"),
                ("720p", "1280x720", "2500k"),
                ("1080p", "1920x1080", "5000k"),
            ]

            base_key = object_key.rsplit(".", 1)[0]
            master_lines = ["#EXTM3U", "#EXT-X-VERSION:3"]

            for name, size, bitrate in qualities:
                out_dir = os.path.join(hls_dir, name)
                os.makedirs(out_dir, exist_ok=True)
                playlist = os.path.join(out_dir, "index.m3u8")

                result = subprocess.run(
                    [
                        "ffmpeg", "-i", source_path,
                        "-vf", f"scale={size}",
                        "-b:v", bitrate,
                        "-hls_time", "6",
                        "-hls_playlist_type", "vod",
                        "-hls_segment_filename", os.path.join(out_dir, "seg%03d.ts"),
                        playlist,
                    ],
                    capture_output=True,
                )

                if result.returncode != 0:
                    logger.error(f"ffmpeg failed for {name}: {result.stderr.decode()}")
                    continue

                # 4. Upload segments to MinIO
                for fname in os.listdir(out_dir):
                    fpath = os.path.join(out_dir, fname)
                    obj_name = f"{base_key}/hls/{name}/{fname}"
                    ct = "application/vnd.apple.mpegurl" if fname.endswith(".m3u8") else "video/mp2t"
                    minio.fput_object(BUCKET_VIDEOS, obj_name, fpath, content_type=ct)

                bandwidth = int(bitrate.replace("k", "")) * 1000
                master_lines.append(f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={size}")
                master_lines.append(f"{base_key}/hls/{name}/index.m3u8")

            # 5. Upload master playlist
            import io
            master_content = "\n".join(master_lines).encode()
            master_key = f"{base_key}/hls/master.m3u8"
            minio.put_object(
                BUCKET_VIDEOS, master_key,
                io.BytesIO(master_content), len(master_content),
                content_type="application/vnd.apple.mpegurl",
            )

            # 6. Update DB
            _db_update_upload_status(upload_id, "READY")
            _db_update_lesson(lesson_id, master_key, duration_seconds)

        _set_status(upload_id, "READY")
        logger.info(f"[transcode_video] Done! master_key={master_key}")
        return {"status": "ready", "upload_id": upload_id, "master_key": master_key}

    except Exception as exc:
        logger.error(f"[transcode_video] Error: {exc}", exc_info=True)
        _set_status(upload_id, "FAILED")
        _db_update_upload_status(upload_id, "FAILED")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_thumbnail(self, upload_id: str, lesson_id: str, object_key: str):
    logger.info(f"[generate_thumbnail] Starting")
    try:
        minio = _get_minio()
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, "source.mp4")
            minio.fget_object(BUCKET_VIDEOS, object_key, source_path)

            thumb_path = os.path.join(tmpdir, "thumbnail.jpg")
            result = subprocess.run(
                ["ffmpeg", "-i", source_path, "-ss", "00:00:05",
                 "-vframes", "1", "-q:v", "2", thumb_path],
                capture_output=True,
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg thumbnail failed")
                return {"status": "failed"}

            thumb_key = f"{object_key.rsplit('.', 1)[0]}/thumbnail.jpg"
            minio.fput_object(BUCKET_THUMBNAILS, thumb_key, thumb_path, content_type="image/jpeg")

        logger.info(f"[generate_thumbnail] Done, thumb_key={thumb_key}")
        return {"status": "ready", "thumb_key": thumb_key}

    except Exception as exc:
        logger.error(f"[generate_thumbnail] Error: {exc}")
        raise self.retry(exc=exc)


@celery_app.task
def cleanup_expired_uploads():
    logger.info("[cleanup_expired_uploads] Running...")
    return {"status": "ok"}


@celery_app.task
def aggregate_analytics():
    logger.info("[aggregate_analytics] Running...")
    return {"status": "ok"}