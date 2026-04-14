import os
import time
import shutil
import asyncio

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models.loader import load_all_models, models_ready
from job_queue import create_job, enqueue_job, get_event_queue
from worker import run_worker

app = FastAPI(title="Voice-to-Visual AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR = os.getenv(
    "OUTPUTS_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs")),
)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")


@app.on_event("startup")
async def startup_event() -> None:
    """Start model loading in background (non-blocking) and launch the worker.

    Models load in a thread-pool executor so the server becomes available
    immediately.  Requests to /generate return 503 until models_ready() is True.
    """
    loop = asyncio.get_event_loop()
    # Fire-and-forget: don't await so startup completes instantly
    loop.run_in_executor(None, load_all_models)
    asyncio.create_task(run_worker())


@app.post("/generate", status_code=202)
async def generate(
    audio: UploadFile = File(...),
    mode: str = Form("image"),
):
    """
    Accepts audio + mode, enqueues the job, returns job_id immediately.
    The client then opens WS /ws/{job_id} to receive phase events.
    """
    if not models_ready():
        return JSONResponse(
            status_code=503,
            content={"detail": "models not ready — try again in a moment"},
        )

    temp_path = f"temp_{int(time.time())}_{audio.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    job_id = create_job(mode)
    await enqueue_job(job_id, temp_path, mode)

    return {"job_id": job_id}


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
    """
    Streams phase events to the browser for a given job.
    Closes with code 4004 if the job_id is not found.
    """
    event_queue = await get_event_queue(job_id)
    if event_queue is None:
        await websocket.close(code=4004)
        return

    await websocket.accept()
    try:
        while True:
            event = await asyncio.wait_for(event_queue.get(), timeout=600.0)
            await websocket.send_json(event)
            if event.get("phase") in ("done", "error"):
                break
    except asyncio.TimeoutError:
        await websocket.send_json({
            "phase": "error", "status": "error", "message": "Job timed out after 10 minutes"
        })
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
