import json
import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._redis = None

    async def enqueue(self, job_id: str) -> None:
        redis = await self.redis()
        if redis is None:
            logger.warning("Redis unavailable; job %s remains queued in PostgreSQL.", job_id)
            return
        await redis.lpush(self.settings.redis_queue_name, job_id)

    async def dequeue(self, *, timeout: int | None = None) -> str | None:
        redis = await self.redis()
        if redis is None:
            return None
        try:
            result = await redis.rpop(self.settings.redis_queue_name)
        except Exception as exc:
            logger.warning("Redis dequeue failed; falling back to PostgreSQL polling. error=%s", exc)
            self._redis = None
            return None
        if not result:
            return None
        return result.decode("utf-8") if isinstance(result, bytes) else str(result)

    async def redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from redis.asyncio import Redis

            self._redis = Redis.from_url(self.settings.redis_url, decode_responses=False)
            await self._redis.ping()
            return self._redis
        except Exception:
            logger.warning("Could not connect to Redis at %s.", self.settings.redis_url)
            self._redis = None
            return None


def serialize_job_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)
