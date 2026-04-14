"use client";
import { useState, useRef } from "react";
import VoiceCapture from "@/components/VoiceCapture";
import PipelineProgress from "@/components/PipelineProgress";
import ResultDisplay from "@/components/ResultDisplay";
import type { PhaseEvent } from "@/components/PipelineProgress";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE  = API_BASE.replace(/^http/, "ws");

type AppState = "landing" | "processing" | "result";

interface ResultData {
  transcript?: string;
  enhancedPrompt?: string;
  imageUrl?: string;
  videoUrl?: string;
  error?: string;
}

export default function Home() {
  const [appState, setAppState]   = useState<AppState>("landing");
  const [events,   setEvents]     = useState<PhaseEvent[]>([]);
  const [result,   setResult]     = useState<ResultData>({});
  const [mode,     setMode]       = useState<"image" | "video">("image");
  const wsRef = useRef<WebSocket | null>(null);

  /* ── kick off a job ──────────────────────────────────────────── */
  const handleProcessAudio = async (audioBlob: Blob) => {
    wsRef.current?.close();
    setEvents([]);
    setResult({});
    setAppState("processing");

    /* 1. POST /generate */
    let jobId: string;
    try {
      const form = new FormData();
      form.append("audio", audioBlob, "recording.webm");
      form.append("mode",  mode);

      const res = await fetch(`${API_BASE}/generate`, { method: "POST", body: form });

      if (res.status === 503) {
        setResult({ error: "Models are still loading — wait a moment and try again." });
        setAppState("result");
        return;
      }
      if (!res.ok) {
        setResult({ error: `Server error ${res.status} — is the backend running?` });
        setAppState("result");
        return;
      }

      jobId = (await res.json()).job_id;
    } catch (err: any) {
      setResult({ error: err?.message || "Could not reach backend. Is it running on port 8000?" });
      setAppState("result");
      return;
    }

    /* 2. Open WebSocket */
    const ws = new WebSocket(`${WS_BASE}/ws/${jobId}`);
    wsRef.current = ws;
    let completed = false;

    ws.onmessage = (e) => {
      const event: PhaseEvent = JSON.parse(e.data);
      setEvents((prev) => [...prev, event]);

      if (event.phase === "done") {
        completed = true;
        const currentMode = mode;          // capture before state updates
        setResult({
          transcript:     event.transcript,
          enhancedPrompt: event.enhanced_prompt,
          imageUrl: currentMode === "image" ? `${API_BASE}${event.output_url}` : undefined,
          videoUrl: currentMode === "video" ? `${API_BASE}${event.output_url}` : undefined,
        });
        setAppState("result");
      }

      if (event.phase === "error") {
        completed = true;
        setResult({ error: event.message || "Pipeline failed" });
        setAppState("result");
      }
    };

    ws.onerror = () => {
      if (!completed) {
        setResult({ error: "WebSocket connection lost. Is the backend running on port 8000?" });
        setAppState("result");
      }
    };

    ws.onclose = () => {
      if (!completed) {
        setResult({ error: "Connection closed unexpectedly. Check backend logs." });
        setAppState("result");
      }
    };
  };

  /* ── reset to landing ────────────────────────────────────────── */
  const handleReset = () => {
    wsRef.current?.close();
    setAppState("landing");
    setEvents([]);
    setResult({});
  };

  /* ── screens ─────────────────────────────────────────────────── */
  if (appState === "processing") {
    return (
      <PipelineProgress events={events} mode={mode} onCancel={handleReset} />
    );
  }

  if (appState === "result") {
    return (
      <ResultDisplay result={result} mode={mode} onReset={handleReset} />
    );
  }

  /* ── landing ─────────────────────────────────────────────────── */
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-[#050507] relative overflow-hidden">
      {/* Background glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[500px] bg-indigo-600/15 blur-[130px] rounded-full pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3  w-[350px] h-[350px] bg-cyan-500/8  blur-[110px] rounded-full pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center gap-8 max-w-xl w-full text-center">

        {/* Badge */}
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-indigo-500/25 bg-indigo-500/8 text-indigo-300 text-xs font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Fully local · No API keys · Open source
        </div>

        {/* Headline */}
        <div className="flex flex-col gap-3">
          <h1 className="text-6xl md:text-7xl font-bold tracking-tight leading-none text-white">
            Voice{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400">
              to Visual
            </span>
          </h1>
          <p className="text-zinc-400 text-base md:text-lg max-w-sm mx-auto leading-relaxed">
            Speak an idea. Whisper transcribes it. Ollama enriches it.
            Stable&nbsp;Diffusion renders it — live.
          </p>
        </div>

        {/* Mode toggle */}
        <div className="flex gap-1 p-1 bg-zinc-900/80 border border-zinc-800 rounded-xl">
          {(["image", "video"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-7 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                mode === m
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/30"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {m === "image" ? "Image" : "Video"}
            </button>
          ))}
        </div>

        {/* Mic */}
        <VoiceCapture onProcess={handleProcessAudio} />

        {/* Tech stack pill row */}
        <div className="flex flex-wrap gap-2 justify-center">
          {[
            "Whisper STT",
            "Ollama LLM",
            "Stable Diffusion",
            "FastAPI",
            "WebSocket",
            "Next.js",
          ].map((t) => (
            <span
              key={t}
              className="px-3 py-1 rounded-lg bg-zinc-900/80 border border-zinc-800/80 text-zinc-500 text-xs"
            >
              {t}
            </span>
          ))}
        </div>

        {/* Subtle footer note */}
        <p className="text-zinc-700 text-xs">
          AI runs entirely on your machine · No data leaves your device
        </p>
      </div>
    </main>
  );
}
