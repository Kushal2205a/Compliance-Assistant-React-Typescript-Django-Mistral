import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import AsyncGenerator

from app.models.enums import EventType


class EventBus(ABC):
    @abstractmethod
    async def publish(self, job_id: str, event_type: EventType, **data) -> None:
        ...

    @abstractmethod
    def subscribe(self, job_id: str) -> AsyncGenerator[str, None]:
        ...

    @abstractmethod
    def cleanup(self, job_id: str) -> None:
        ...


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[str]] = {}
        self._done: dict[str, asyncio.Event] = {}
        self._history: dict[str, list[str]] = {}

    async def publish(self, job_id: str, event_type: EventType, **data) -> None:
        if job_id not in self._queues:
            self._queues[job_id] = asyncio.Queue()
            self._done[job_id] = asyncio.Event()

        payload = {
            "job_id": job_id,
            "event_type": event_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        serialized = json.dumps(payload)

        # Keep history for late subscribers
        if job_id not in self._history:
            self._history[job_id] = []
        self._history[job_id].append(serialized)

        await self._queues[job_id].put(serialized)

    async def subscribe(self, job_id: str) -> AsyncGenerator[str, None]:
        if job_id not in self._queues:
            self._queues[job_id] = asyncio.Queue()
            self._done[job_id] = asyncio.Event()

            # Replay history for already-completed jobs
            if job_id in self._history:
                for event in self._history[job_id]:
                    await self._queues[job_id].put(event)

        queue = self._queues[job_id]
        done = self._done[job_id]

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {event}\n\n"
                if json.loads(event).get("event_type") in (
                    EventType.JOB_COMPLETED.value,
                    EventType.JOB_FAILED.value,
                ):
                    done.set()
                    return
            except asyncio.TimeoutError:
                yield f": keepalive\n\n"

    def cleanup(self, job_id: str) -> None:
        self._queues.pop(job_id, None)
        self._done.pop(job_id, None)
        self._history.pop(job_id, None)


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = InMemoryEventBus()
    return _event_bus
