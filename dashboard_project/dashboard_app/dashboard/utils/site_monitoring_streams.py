import asyncio
import contextlib
import logging
import os
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import text

from dashboard_app.dashboard.db.db_engine import engine

logger = logging.getLogger(__name__)


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SITEWATCH_CMD_STREAM = os.getenv("SITEWATCH_CMD_STREAM", "dashboard_monitor_cmd")
SITEWATCH_CMD_MAXLEN = int(os.getenv("SITEWATCH_CMD_MAXLEN", "10000"))
SITEWATCH_EVENTS_STREAM = os.getenv("SITEWATCH_EVENTS_STREAM", "dashboard_monitor_events")
SITEWATCH_EVENTS_GROUP = os.getenv("SITEWATCH_EVENTS_GROUP", "dashboard_app")
SITEWATCH_EVENTS_CONSUMER = os.getenv("SITEWATCH_EVENTS_CONSUMER", "dashboard-1")
SITEWATCH_EVENTS_BLOCK_MS = int(os.getenv("SITEWATCH_EVENTS_BLOCK_MS", "5000"))

_redis: Redis | None = None
_consumer_task: asyncio.Task | None = None
_stop_event = asyncio.Event()


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def ensure_events_group() -> None:
    r = await get_redis()
    try:
        await r.xgroup_create(
            name=SITEWATCH_EVENTS_STREAM,
            groupname=SITEWATCH_EVENTS_GROUP,
            id="0",
            mkstream=True,
        )
    except Exception as e:  # noqa: BLE001
        # BUSYGROUP для redis-py приходит как ResponseError, но импортировать тип не обязательно
        if "BUSYGROUP" not in str(e):
            raise


async def publish_register_monitor_command(
    *,
    user_id: int,
    url: str,
    interval_minutes: int,
) -> str:
    r = await get_redis()
    msg_id = await r.xadd(
        SITEWATCH_CMD_STREAM,
        {
            "type": "register_monitor",
            "user_id": str(user_id),
            "url": url,
            "interval_minutes": str(interval_minutes),
        },
        maxlen=SITEWATCH_CMD_MAXLEN,
        approximate=True,
    )
    return msg_id


async def startup_sitewatch_consumer() -> None:
    global _consumer_task
    _stop_event.clear()
    await ensure_events_group()
    if _consumer_task is None or _consumer_task.done():
        _consumer_task = asyncio.create_task(_run_events_consumer(), name="sitewatch-events-consumer")


async def shutdown_sitewatch_consumer() -> None:
    global _consumer_task, _redis
    _stop_event.set()
    if _consumer_task:
        _consumer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _consumer_task
        _consumer_task = None
    if _redis is not None:
        await _redis.close()
        _redis = None


async def _run_events_consumer() -> None:
    r = await get_redis()
    while not _stop_event.is_set():
        try:
            rows = await r.xreadgroup(
                groupname=SITEWATCH_EVENTS_GROUP,
                consumername=SITEWATCH_EVENTS_CONSUMER,
                streams={SITEWATCH_EVENTS_STREAM: ">"},
                count=100,
                block=SITEWATCH_EVENTS_BLOCK_MS,
            )
            if not rows:
                continue

            for _stream, messages in rows:
                for msg_id, fields in messages:
                    try:
                        await _apply_sitewatch_event(fields)
                    except Exception:  # noqa: BLE001
                        logger.exception("failed to apply sitewatch event", extra={"msg_id": msg_id, "fields": fields})
                        continue
                    await r.xack(SITEWATCH_EVENTS_STREAM, SITEWATCH_EVENTS_GROUP, msg_id)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("sitewatch events consumer loop error")
            await asyncio.sleep(1)


async def _apply_sitewatch_event(fields: dict[str, Any]) -> None:
    event_type = (fields.get("type") or "").strip()
    if event_type == "monitor_registered":
        await _apply_registered(fields)
        return
    if event_type == "monitor_checked":
        await _apply_checked(fields)
        return


async def _apply_registered(fields: dict[str, Any]) -> None:
    user_id_raw = fields.get("user_id")
    monitor_id = (fields.get("monitor_id") or "").strip()
    url = (fields.get("url") or "").strip()
    interval_minutes_raw = fields.get("interval_minutes")
    if not user_id_raw or not monitor_id or not url:
        return

    user_id = int(user_id_raw)
    interval_minutes = int(interval_minutes_raw) if interval_minutes_raw else None

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                UPDATE site_monitors
                SET monitor_id = :monitor_id,
                    interval_minutes = COALESCE(:interval_minutes, interval_minutes),
                    registration_status = 'ready',
                    updated_at = NOW()
                WHERE user_id = :user_id AND url = :url
                """
            ),
            {
                "user_id": user_id,
                "url": url,
                "monitor_id": monitor_id,
                "interval_minutes": interval_minutes,
            },
        )


async def _apply_checked(fields: dict[str, Any]) -> None:
    monitor_id = (fields.get("monitor_id") or "").strip()
    if not monitor_id:
        return

    url = (fields.get("url") or "").strip() or None
    status = (fields.get("status") or "unknown").strip()
    changed_raw = (fields.get("changed") or "false").strip().lower()
    changed = changed_raw in {"1", "true", "yes"}
    error = (fields.get("error") or "").strip() or None
    checked_at_raw = (fields.get("checked_at") or "").strip()
    checked_at = _parse_dt(checked_at_raw)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                UPDATE site_monitors
                SET url = COALESCE(:url, url),
                    last_status = :status,
                    last_checked_at = COALESCE(:checked_at, NOW()),
                    last_changed = :changed,
                    last_error = :error,
                    registration_status = CASE
                        WHEN registration_status = 'pending' THEN 'ready'
                        ELSE registration_status
                    END,
                    updated_at = NOW()
                WHERE monitor_id = :monitor_id
                """
            ),
            {
                "monitor_id": monitor_id,
                "url": url,
                "status": status,
                "checked_at": checked_at,
                "changed": changed,
                "error": error,
            },
        )


def _parse_dt(value: str | None):
    if not value:
        return None
    try:
        # Go time.RFC3339Nano -> Python fromisoformat после замены Z
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None
