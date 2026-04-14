import asyncio
import uuid
from typing import Dict, Optional

# Global queue: worker reads from this
job_queue: asyncio.Queue = asyncio.Queue()

# Per-job event queues: WebSocket handler reads from these
_event_queues: Dict[str, asyncio.Queue] = {}


def create_job(mode: str) -> str:
    """Create a new job entry and return its ID."""
    job_id = str(uuid.uuid4())[:8]
    _event_queues[job_id] = asyncio.Queue()
    return job_id


async def enqueue_job(job_id: str, audio_path: str, mode: str) -> None:
    """Put the job onto the global worker queue."""
    await job_queue.put({"job_id": job_id, "audio_path": audio_path, "mode": mode})


async def emit_event(job_id: str, event: dict) -> None:
    """Push a phase event onto the job's private queue."""
    if job_id in _event_queues:
        await _event_queues[job_id].put(event)


async def get_event_queue(job_id: str) -> Optional[asyncio.Queue]:
    """Return the event queue for a job, or None if job_id is unknown."""
    return _event_queues.get(job_id)


def cleanup_job(job_id: str) -> None:
    """Remove the job's event queue after the WebSocket connection closes."""
    _event_queues.pop(job_id, None)
