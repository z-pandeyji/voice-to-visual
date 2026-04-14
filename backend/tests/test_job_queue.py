import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
import asyncio
import job_queue as jq
from job_queue import create_job, enqueue_job, emit_event, get_event_queue, cleanup_job


@pytest.fixture(autouse=True)
def reset_job_queue_state():
    """Reset shared module-level state between tests to prevent cross-test pollution."""
    jq._event_queues.clear()
    # Drain the global queue to ensure test_enqueue test starts with empty queue
    while not jq.job_queue.empty():
        try:
            jq.job_queue.get_nowait()
        except Exception:
            break
    yield
    jq._event_queues.clear()


async def test_create_job_returns_string_id():
    job_id = create_job("image")
    assert isinstance(job_id, str)
    assert len(job_id) > 0


async def test_event_queue_exists_after_create():
    job_id = create_job("image")
    q = await get_event_queue(job_id)
    assert q is not None


async def test_emit_event_puts_to_queue():
    job_id = create_job("video")
    await emit_event(job_id, {"phase": "stt", "status": "start"})
    q = await get_event_queue(job_id)
    event = await asyncio.wait_for(q.get(), timeout=1.0)
    assert event["phase"] == "stt"


async def test_cleanup_removes_job():
    job_id = create_job("image")
    cleanup_job(job_id)
    q = await get_event_queue(job_id)
    assert q is None


async def test_enqueue_puts_job_on_global_queue():
    job_id = create_job("image")
    await enqueue_job(job_id, "/tmp/audio.webm", "image")
    job = await asyncio.wait_for(jq.job_queue.get(), timeout=1.0)
    assert job["job_id"] == job_id
    assert job["audio_path"] == "/tmp/audio.webm"
    assert job["mode"] == "image"
