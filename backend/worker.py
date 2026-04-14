import asyncio
import os
import time
import traceback
from datetime import datetime, timezone

from job_queue import job_queue, emit_event, cleanup_job
from models.loader import get_whisper_model, get_sd_pipeline, get_video_pipeline, load_video_pipeline
from pipeline.stt import transcribe_audio
from pipeline.enhancer import enhance_prompt
from pipeline.image_gen import generate_image
from pipeline.video_gen import generate_video

OUTPUTS_DIR = os.getenv(
    "OUTPUTS_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs")),
)
LOG_FILE = os.getenv(
    "LOG_FILE",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "activity.log")),
)


def _log(job_id: str, phase: str, message: str) -> None:
    """Append a structured line to activity.log and print to stdout."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{timestamp}] [job:{job_id}] [{phase:<10}] {message}\n"
    print(line.strip())
    with open(LOG_FILE, "a") as f:
        f.write(line)


def _make_progress_callback(job_id: str, loop: asyncio.AbstractEventLoop):
    """Return a sync callback safe to call from a worker thread.

    Diffusers calls this on every step (step, timestep, latents).
    We schedule an emit_event coroutine on the main event loop via
    run_coroutine_threadsafe so the asyncio loop stays unblocked.
    """
    def callback(step: int, total: int) -> None:
        asyncio.run_coroutine_threadsafe(
            emit_event(job_id, {
                "phase": "generating",
                "status": "progress",
                "step": step,
                "total": total,
            }),
            loop,
        )
    return callback


async def run_worker() -> None:
    """
    Long-running background coroutine.
    Reads one job at a time from the global queue and runs the full pipeline.
    Sequential processing prevents GPU contention.

    IMPORTANT: generate_image / generate_video are synchronous and CPU/GPU
    bound.  They must run in run_in_executor() so the asyncio event loop
    stays alive (and can keep the WebSocket heartbeat / progress events
    flowing) during inference.
    """
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    print("[worker] Started — waiting for jobs.")

    while True:
        job = await job_queue.get()
        job_id: str = job["job_id"]
        audio_path: str = job["audio_path"]
        mode: str = job["mode"]
        loop = asyncio.get_event_loop()

        _log(job_id, "queued", f"Job received mode={mode}")

        try:
            # ── Phase 1: Speech-to-Text ──────────────────────────────────
            _log(job_id, "stt", f"START audio_path={audio_path} exists={os.path.exists(audio_path)}")
            await emit_event(job_id, {
                "phase": "stt", "status": "start", "message": "Transcribing audio..."
            })

            transcript = await loop.run_in_executor(
                None, transcribe_audio, audio_path, get_whisper_model()
            )

            _log(job_id, "stt", f'COMPLETE transcript="{transcript[:80]}"')
            await emit_event(job_id, {
                "phase": "stt", "status": "complete", "data": transcript
            })

            # ── Phase 2: Prompt Enhancement ──────────────────────────────
            _log(job_id, "enhancing", "START")
            await emit_event(job_id, {
                "phase": "enhancing", "status": "start",
                "message": "Enhancing prompt with LLM..."
            })

            enhanced = await loop.run_in_executor(None, enhance_prompt, transcript)

            if enhanced == transcript:
                _log(job_id, "enhancing", "FALLBACK reason=ollama_unavailable")
                await emit_event(job_id, {
                    "phase": "enhancing", "status": "fallback",
                    "message": "LLM unavailable — using raw transcript"
                })
            else:
                _log(job_id, "enhancing", f'COMPLETE prompt="{enhanced[:80]}"')
                await emit_event(job_id, {
                    "phase": "enhancing", "status": "complete", "data": enhanced
                })

            # ── Phase 3: Generation ──────────────────────────────────────
            ext = "png" if mode == "image" else "mp4"
            filename = f"gen_{int(time.time())}_{job_id}.{ext}"
            output_path = os.path.join(OUTPUTS_DIR, filename)

            _log(job_id, "generating", f"START mode={mode} output={output_path}")
            await emit_event(job_id, {
                "phase": "generating", "status": "start",
                "message": f"Generating {mode}..."
            })

            progress_cb = _make_progress_callback(job_id, loop)

            if mode == "image":
                sd = get_sd_pipeline()
                _log(job_id, "generating", f"DEBUG pipeline={type(sd).__name__}")
                await loop.run_in_executor(
                    None,
                    lambda: generate_image(
                        enhanced, output_path,
                        pipeline=sd,
                        step_callback=progress_cb,
                    ),
                )
            else:
                video_pipeline = get_video_pipeline()
                if video_pipeline is None:
                    _log(job_id, "generating", "DEBUG video pipeline not loaded — loading now...")
                    await emit_event(job_id, {
                        "phase": "generating", "status": "start",
                        "message": "Loading video model (first-time, ~2 min on CPU)..."
                    })
                    video_pipeline = await loop.run_in_executor(None, load_video_pipeline)
                    if video_pipeline is None:
                        raise RuntimeError("Video pipeline failed to load — check server logs.")

                _log(job_id, "generating", f"DEBUG pipeline={type(video_pipeline).__name__}")
                await loop.run_in_executor(
                    None,
                    lambda: generate_video(enhanced, output_path, pipeline=video_pipeline),
                )

            size_kb = os.path.getsize(output_path) // 1024
            _log(job_id, "generating", f"COMPLETE file={filename} size={size_kb}KB")
            await emit_event(job_id, {
                "phase": "generating", "status": "complete",
                "output_url": f"/outputs/{filename}"
            })

            # ── Done ─────────────────────────────────────────────────────
            _log(job_id, "done", "SUCCESS")
            await emit_event(job_id, {
                "phase": "done",
                "status": "complete",
                "output_url": f"/outputs/{filename}",
                "transcript": transcript,
                "enhanced_prompt": enhanced,
            })

        except Exception as exc:
            _log(job_id, "error", f"FAILED reason={exc}")
            traceback.print_exc()
            await emit_event(job_id, {
                "phase": "error", "status": "error", "message": str(exc)
            })

        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            await asyncio.sleep(0.5)
            cleanup_job(job_id)

        job_queue.task_done()
