from app.core.celery_app import celery_app
import redis
import json

r = redis.Redis(host="localhost", port=6379, db=1)


@celery_app.task
def transcode_video(upload_id: str):
    r.set(upload_id, json.dumps({"status": "processing"}))

    print(f"[Celery] Processing video {upload_id}")

    import time
    time.sleep(5)

    r.set(upload_id, json.dumps({"status": "done"}))

    return {"status": "processed", "upload_id": upload_id}