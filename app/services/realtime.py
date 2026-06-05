import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)

REALTIME_CHANNEL = "rag:realtime-events"


def realtime_payload(event_type: str, **payload: Any) -> dict[str, Any]:
    return {
        "type": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        **payload,
    }


async def publish_event(settings: Settings, event_type: str, **payload: Any) -> None:
    event = realtime_payload(event_type, **payload)
    try:
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await redis.publish(REALTIME_CHANNEL, json.dumps(event, ensure_ascii=True, default=str))
        finally:
            await redis.aclose()
    except Exception as exc:
        logger.debug("Realtime publish skipped. event=%s error=%s", event_type, exc)


async def iter_events(settings: Settings) -> AsyncIterator[dict[str, Any]]:
    from redis.asyncio import Redis

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(REALTIME_CHANNEL)
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20)
            if message is None:
                yield realtime_payload("heartbeat")
                await asyncio.sleep(0)
                continue
            data = message.get("data")
            if not data:
                continue
            try:
                yield json.loads(str(data))
            except json.JSONDecodeError:
                logger.debug("Invalid realtime payload ignored: %s", data)
    finally:
        await pubsub.unsubscribe(REALTIME_CHANNEL)
        await pubsub.aclose()
        await redis.aclose()
