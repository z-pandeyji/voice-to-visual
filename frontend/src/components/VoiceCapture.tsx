"use client";
import { useState, useRef } from "react";

export default function VoiceCapture({ onProcess }: { onProcess: (blob: Blob) => void }) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        onProcess(blob);
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      alert("Microphone access denied. Allow microphone permission and retry.");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative flex items-center justify-center">
        {isRecording && (
          <>
            <span className="absolute w-32 h-32 rounded-full bg-red-500/20 animate-ping" />
            <span className="absolute w-24 h-24 rounded-full bg-red-500/15 animate-ping [animation-delay:300ms]" />
          </>
        )}
        <button
          onClick={isRecording ? stopRecording : startRecording}
          className={`relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 shadow-2xl focus:outline-none ${
            isRecording
              ? "bg-red-500 hover:bg-red-600 shadow-red-500/40 scale-110"
              : "bg-indigo-600 hover:bg-indigo-500 hover:scale-110 shadow-indigo-500/40"
          }`}
        >
          {isRecording ? (
            <span className="w-6 h-6 bg-white rounded-sm" />
          ) : (
            <svg className="w-9 h-9 text-white" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.39-.9.88 0 2.76-2.24 5-5 5s-5-2.24-5-5c0-.49-.41-.88-.9-.88-.49 0-.88.41-.88.9 0 3.19 2.45 5.86 5.56 6.29v2.54c0 .48.39.87.87.87.48 0 .87-.39.87-.87v-2.54c3.12-.42 5.57-3.09 5.57-6.29 0-.49-.39-.9-.88-.9z" />
            </svg>
          )}
        </button>
      </div>

      <p className="text-sm font-medium h-5">
        {isRecording ? (
          <span className="flex items-center gap-2 text-red-400">
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
            Recording… tap to stop
          </span>
        ) : (
          <span className="text-zinc-500">Tap to speak your idea</span>
        )}
      </p>
    </div>
  );
}
