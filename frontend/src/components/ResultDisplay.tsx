"use client";
import { useState } from "react";

interface ResultData {
  transcript?: string;
  enhancedPrompt?: string;
  imageUrl?: string;
  videoUrl?: string;
  error?: string;
}

export default function ResultDisplay({
  result,
  mode,
  onReset,
}: {
  result: ResultData;
  mode: "image" | "video";
  onReset: () => void;
}) {
  const [underHoodOpen, setUnderHoodOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  /* ── Error state ──────────────────────────────────────────────── */
  if (result?.error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-[#050507]">
        <div className="w-full max-w-md flex flex-col items-center gap-6 text-center">
          <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center">
            <svg className="w-7 h-7 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
          </div>
          <div>
            <p className="text-white font-semibold text-lg mb-1">Pipeline failed</p>
            <p className="text-zinc-500 text-sm leading-relaxed">{result.error}</p>
          </div>
          <button
            onClick={onReset}
            className="px-6 py-3 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white font-medium transition-all"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  /* ── Helpers ──────────────────────────────────────────────────── */
  const handleDownload = async () => {
    if (!result.imageUrl) return;
    const res = await fetch(result.imageUrl);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `voice-to-visual-${Date.now()}.png`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopy = async () => {
    if (!result.enhancedPrompt) return;
    await navigator.clipboard.writeText(result.enhancedPrompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const enhancerFellBack =
    result.transcript &&
    result.enhancedPrompt &&
    result.transcript === result.enhancedPrompt;

  /* ── Success state ────────────────────────────────────────────── */
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 py-16 bg-[#050507] relative">
      {/* Ambient glow behind the image */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-indigo-600/10 blur-[140px] rounded-full pointer-events-none" />

      <div className="relative z-10 w-full max-w-2xl flex flex-col gap-5">

        {/* ── Generated visual ── */}
        {(result.imageUrl || result.videoUrl) && (
          <div className="rounded-2xl overflow-hidden border border-zinc-800/80 bg-zinc-950 shadow-[0_0_80px_rgba(99,102,241,0.12)]">
            {result.imageUrl ? (
              <img
                src={result.imageUrl}
                alt="Generated visual"
                className="w-full h-auto block"
              />
            ) : (
              <video
                src={result.videoUrl}
                autoPlay
                loop
                muted
                playsInline
                className="w-full h-auto block"
              />
            )}
          </div>
        )}

        {/* ── Action buttons ── */}
        <div className="flex flex-wrap gap-2 items-center">
          {result.imageUrl && (
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-all shadow-lg shadow-indigo-500/25"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </button>
          )}

          {result.enhancedPrompt && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 text-sm font-medium transition-all"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              {copied ? "Copied!" : "Copy Prompt"}
            </button>
          )}

          <button
            onClick={onReset}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-white text-sm font-medium transition-all ml-auto"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Generate Another
          </button>
        </div>

        {/* ── Under the hood (collapsible) ── */}
        {result.transcript && (
          <div className="rounded-2xl border border-zinc-800/70 overflow-hidden">
            <button
              onClick={() => setUnderHoodOpen((o) => !o)}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-zinc-900/40 transition-all group"
            >
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-zinc-500 group-hover:text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                <span className="text-sm font-medium text-zinc-400 group-hover:text-zinc-300">Under the hood</span>
              </div>
              <svg
                className={`w-4 h-4 text-zinc-600 transition-transform duration-200 ${underHoodOpen ? "rotate-180" : ""}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {underHoodOpen && (
              <div className="px-5 pb-5 border-t border-zinc-800/60 flex flex-col gap-4">
                {/* Ollama fallback warning */}
                {enhancerFellBack && (
                  <div className="flex items-start gap-2 mt-4 px-3.5 py-2.5 rounded-xl bg-amber-500/8 border border-amber-500/20 text-amber-400 text-xs leading-relaxed">
                    <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                    </svg>
                    Ollama LLM unavailable — prompt was not enhanced. Run{" "}
                    <code className="mx-1 px-1 py-0.5 rounded bg-amber-500/10 font-mono">ollama serve</code>
                    and generate again.
                  </div>
                )}

                {/* Transcript vs Enhanced comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-1">
                  <div>
                    <p className="text-[10px] uppercase tracking-widest text-zinc-600 font-semibold mb-2">
                      You said
                    </p>
                    <div className="p-3.5 bg-zinc-900/60 rounded-xl border border-zinc-800/60">
                      <p className="text-xs text-zinc-400 font-mono leading-relaxed">{result.transcript}</p>
                      <p className="text-zinc-700 text-[10px] mt-2">
                        {result.transcript?.split(" ").length} words
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className={`text-[10px] uppercase tracking-widest font-semibold mb-2 ${
                      enhancerFellBack ? "text-zinc-600" : "text-indigo-500"
                    }`}>
                      AI Enhanced
                    </p>
                    <div className={`p-3.5 rounded-xl border ${
                      enhancerFellBack
                        ? "bg-zinc-900/40 border-zinc-800/40"
                        : "bg-indigo-950/25 border-indigo-500/20"
                    }`}>
                      <p className={`text-xs font-mono leading-relaxed ${
                        enhancerFellBack ? "text-zinc-600" : "text-indigo-200"
                      }`}>
                        {result.enhancedPrompt}
                      </p>
                      {!enhancerFellBack && (
                        <p className="text-indigo-700 text-[10px] mt-2">
                          {result.enhancedPrompt?.split(" ").length} words
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Pipeline info row */}
                <div className="flex flex-wrap gap-2 pt-1">
                  {[
                    { label: "STT",    value: "Whisper small" },
                    { label: "LLM",    value: "Ollama"        },
                    { label: "Model",  value: mode === "image" ? "SD v1.5" : "ModelScope 1.7B" },
                    { label: "Output", value: mode === "image" ? "PNG" : "MP4" },
                  ].map(({ label, value }) => (
                    <div key={label} className="px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs">
                      <span className="text-zinc-600">{label}: </span>
                      <span className="text-zinc-400">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
