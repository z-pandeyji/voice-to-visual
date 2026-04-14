"use client";
import { useMemo, useEffect, useState } from "react";

export interface PhaseEvent {
  phase: string;
  status: string;
  message?: string;
  data?: string;
  output_url?: string;
  transcript?: string;
  enhanced_prompt?: string;
  step?: number;
  total?: number;
}

const STEPS = [
  { id: "stt",        label: "Transcribing", tag: "Whisper STT" },
  { id: "enhancing",  label: "Enhancing",    tag: "Ollama LLM"  },
  { id: "generating", label: "Generating",   tag: "Stable Diffusion" },
] as const;

type StepStatus = "pending" | "active" | "complete" | "fallback";

interface StepState {
  status: StepStatus;
  data?: string;
  step?: number;
  total?: number;
}

function usePhaseStates(events: PhaseEvent[]): Record<string, StepState> {
  return useMemo(() => {
    const state: Record<string, StepState> = {
      stt:        { status: "pending" },
      enhancing:  { status: "pending" },
      generating: { status: "pending" },
    };

    for (const e of events) {
      if (!(e.phase in state)) continue;
      switch (e.status) {
        case "start":
          state[e.phase].status = "active";
          break;
        case "complete":
          state[e.phase] = { status: "complete", data: e.data };
          break;
        case "fallback":
          state[e.phase] = { status: "fallback", data: e.message };
          break;
        case "progress":
          state[e.phase].status = "active";
          state[e.phase].step  = e.step;
          state[e.phase].total = e.total;
          break;
      }
    }
    return state;
  }, [events]);
}

export default function PipelineProgress({
  events,
  mode,
  onCancel,
}: {
  events: PhaseEvent[];
  mode: "image" | "video";
  onCancel: () => void;
}) {
  const phases = usePhaseStates(events);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const formatElapsed = (s: number) =>
    s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 relative bg-[#050507]">
      {/* Ambient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[500px] bg-indigo-600/10 blur-[140px] rounded-full pointer-events-none" />

      <div className="relative z-10 w-full max-w-xl flex flex-col gap-5">

        {/* Header */}
        <div className="flex items-start justify-between mb-1">
          <div>
            <h2 className="text-xl font-bold text-white">Running pipeline</h2>
            <p className="text-zinc-500 text-sm mt-0.5">
              Elapsed: <span className="text-zinc-300 tabular-nums">{formatElapsed(elapsed)}</span>
            </p>
          </div>
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-xl border border-zinc-800 bg-zinc-900/50 text-zinc-400 text-sm hover:border-zinc-600 hover:text-white transition-all"
          >
            Cancel
          </button>
        </div>

        {/* Step cards */}
        {STEPS.map((step, i) => {
          const p = phases[step.id];
          const isActive   = p.status === "active";
          const isDone     = p.status === "complete" || p.status === "fallback";
          const isFallback = p.status === "fallback";

          return (
            <div
              key={step.id}
              className={`rounded-2xl border p-5 transition-all duration-500 ${
                isDone
                  ? "border-indigo-500/30 bg-indigo-950/15"
                  : isActive
                  ? "border-indigo-500/50 bg-indigo-950/25 shadow-[0_0_40px_rgba(99,102,241,0.08)]"
                  : "border-zinc-800/50 bg-zinc-900/20"
              }`}
            >
              {/* Card header row */}
              <div className="flex items-center gap-3">
                {/* Status dot / check / number */}
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${
                    isDone
                      ? "bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.5)]"
                      : isActive
                      ? "bg-indigo-500/30"
                      : "bg-zinc-800"
                  }`}
                >
                  {isDone ? (
                    <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : isActive ? (
                    <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                  ) : (
                    <span className="text-zinc-600 text-xs font-bold">{i + 1}</span>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`font-semibold text-sm transition-colors ${
                        isDone ? "text-white" : isActive ? "text-indigo-200" : "text-zinc-600"
                      }`}
                    >
                      {step.label}
                      {isFallback && (
                        <span className="ml-2 text-xs text-amber-400 font-normal">(fallback)</span>
                      )}
                    </span>
                    <span className="text-[11px] text-zinc-600 flex-shrink-0">{step.tag}</span>
                  </div>
                </div>

                {isActive && step.id !== "generating" && (
                  <span className="text-xs text-indigo-400 animate-pulse flex-shrink-0">In progress…</span>
                )}
              </div>

              {/* Generating: live progress bar */}
              {step.id === "generating" && isActive && (
                <div className="mt-3">
                  {p.step && p.total ? (
                    <>
                      <div className="flex justify-between text-xs text-zinc-500 mb-1.5">
                        <span>Step {p.step} / {p.total}</span>
                        <span>{Math.round((p.step / p.total) * 100)}%</span>
                      </div>
                      <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-500 to-cyan-400 rounded-full transition-all duration-500"
                          style={{ width: `${(p.step / p.total) * 100}%` }}
                        />
                      </div>
                    </>
                  ) : (
                    <div className="mt-1 flex items-center gap-2 text-xs text-indigo-400">
                      <span className="animate-pulse">Starting inference…</span>
                    </div>
                  )}
                </div>
              )}

              {/* Data readout (transcript / enhanced prompt) */}
              {isDone && p.data && (
                <div className="mt-3 px-3 py-2.5 bg-black/40 rounded-xl border border-zinc-800/60">
                  <p className="text-xs font-mono text-zinc-300 leading-relaxed line-clamp-3 break-words">
                    {p.data}
                  </p>
                </div>
              )}
            </div>
          );
        })}

        <p className="text-center text-zinc-600 text-xs pt-1">
          {mode === "image"
            ? "Stable Diffusion on CPU takes 5 – 15 minutes"
            : "Video generation takes 10 – 25 minutes on CPU"}
        </p>
      </div>
    </div>
  );
}
