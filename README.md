# Voice-to-Visual AI Agent

> Speak your idea. Watch an AI pipeline transcribe, enhance, and generate an image or video — live.

![Demo](demo/demo.gif)

---

## What This Demonstrates

| Skill Area | What's Showcased | Why It Matters |
|------------|-----------------|----------------|
| **AI/ML Engineering** | Whisper STT, Stable Diffusion v1.5, ModelScope text-to-video, model singleton loading, CUDA/CPU device-aware inference | Runs 4 ML models locally — no API keys, real inference |
| **Backend Engineering** | Async job queue, WebSocket real-time streaming, FastAPI, graceful Ollama fallback | Production patterns: queue → worker → event stream |
| **Frontend Engineering** | Next.js 16 App Router, WebSocket client, live pipeline progress UI, TypeScript | Real-time state management across async phases |
| **System Design** | Model preloading, lazy loading (7GB video model), sequential worker for GPU contention | Designed with a clear scaling path (asyncio → Celery + Redis) |
| **Testing** | 40 tests, pytest + httpx + Playwright, GPU-optional CI (`pytest -m "not slow"`) | Full test pyramid: unit + integration + E2E |
| **DevOps** | Docker + docker-compose, structured `activity.log`, env-configurable model IDs | One-command deployment, production-ready logging |

---

## Part of a Series

This is **Part 4** of my "What I built this week" series — each project explores a different layer of AI engineering:

| Week | Project | What I Learned |
|------|---------|---------------|
| 1 | **Resume Analyzer** — AI match scoring | Using AI APIs, Hugging Face Agents |
| 2 | **SpecFix AI** — Requirement intelligence | Agent orchestration (Google ADK), agent → agent flow |
| 3 | **Voice Agent Studio** — Real-time voice AI | Shared pipelines (STT → LLM → TTS), behavior-driven agents |
| **4** | **Voice-to-Visual** — This project | **Full local ML inference**, job queues, WebSocket streaming, 40 tests |

**The progression**: API calls → agent orchestration → real-time voice → owning the full inference pipeline.

---

## Quick Start

```bash
docker-compose up --build
```

Open http://localhost:3000, speak an idea, watch the pipeline run live.

> First run downloads AI models from HuggingFace (~8 GB). Subsequent runs start in seconds.

---

## Architecture

```
Browser (Next.js 16)
  │
  ├── POST /generate ──► FastAPI
  │   { audio, mode }    │
  │                      ├── enqueue → asyncio.Queue
  │                      └── return { job_id }  (HTTP 202)
  │
  └── WS /ws/{job_id} ◄── WebSocket handler
      live phase events    │
                           └── background worker
                                    │
                              stt → enhancer → image_gen | video_gen
                                    │
                              outputs/ + activity.log
```

### Key Design Decisions

**Job Queue Pattern** — `POST /generate` returns a `job_id` immediately (HTTP 202). AI inference runs in a background worker. This mirrors how production AI APIs work (Replicate, RunPod).
*Scaling path:* swap `asyncio.Queue` → Celery + Redis. Worker interface unchanged.

**Model Singletons** — All models load **once at startup** via `models/loader.py`. No per-request model loading — eliminates the 30-second cold start.

**Lazy Video Loading** — The video model (7 GB) loads on first video request, not at startup. Keeps startup fast for the common case (image generation).

**Graceful Degradation** — If Ollama is unavailable, the enhancer returns the raw transcript and the pipeline continues. The user sees a warning but still gets a generated image.

**Sequential Worker** — One worker, one job at a time. No GPU contention, predictable memory. To parallelize: run multiple worker processes behind a shared queue.

### WebSocket Events

```json
{ "phase": "stt",        "status": "complete",  "data": "a dog on a hill" }
{ "phase": "enhancing",  "status": "complete",  "data": "golden hour cinematic, 8k..." }
{ "phase": "generating", "status": "complete",  "output_url": "/outputs/gen_123.png" }
{ "phase": "done",       "status": "complete",  "transcript": "...", "enhanced_prompt": "..." }
```

Full protocol: [docs/websocket-protocol.md](docs/websocket-protocol.md)

---

## Tech Stack

**Backend:** Python 3.11, FastAPI, asyncio, openai-whisper, diffusers, torch, Ollama
**Frontend:** Next.js 16, React 19, TypeScript 5, Tailwind CSS 4
**Models:** Whisper base (74M) · Stable Diffusion v1.5 · damo-vilab/text-to-video-ms-1.7b
**Testing:** pytest (40 tests), pytest-asyncio, httpx, Playwright
**Infra:** Docker, docker-compose

All models run **fully local** — no API keys, no cloud costs at inference time.

---

## Running Tests

```bash
# Fast tests — no GPU required (mocked pipelines)
cd backend && pytest -m "not slow" -v

# Full suite including SD inference (GPU recommended)
cd backend && pytest -v -s

# Frontend E2E
cd frontend && npx playwright test
```

---

## Project Structure

```
├── backend/
│   ├── main.py              FastAPI app, /generate + /ws routes
│   ├── worker.py            Async background job worker
│   ├── job_queue.py         Global job queue + per-job event queues
│   ├── models/loader.py     Startup model loading (singletons)
│   ├── pipeline/
│   │   ├── stt.py           Whisper speech-to-text
│   │   ├── enhancer.py      Ollama prompt enhancement (auto-detects model)
│   │   ├── image_gen.py     Stable Diffusion image generation
│   │   └── video_gen.py     ModelScope text-to-video generation
│   └── tests/               40 tests (unit + integration)
├── frontend/
│   ├── src/app/page.tsx     Main page with WebSocket client
│   └── src/components/
│       ├── PipelineProgress.tsx  Live phase progress indicator
│       ├── VoiceCapture.tsx      Audio recording
│       └── ResultDisplay.tsx     Output display + download + copy
├── docs/                    Architecture, pipeline, stack, testing guides
├── activity.log             Append-only runtime pipeline trace
└── docker-compose.yml       One-command deployment
```

---

## Docs

- [Architecture](docs/architecture.md)
- [Pipeline](docs/pipeline.md)
- [Tech Stack](docs/stack.md)
- [WebSocket Protocol](docs/websocket-protocol.md)
- [Testing](docs/testing.md)
- [Setup Guide](docs/setup.md)
