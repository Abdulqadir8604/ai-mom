import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import ProgressStepper from "../components/ProgressStepper";
import WaveformAnimation from "../components/WaveformAnimation";

const API = import.meta.env.VITE_API_URL || "/api";

const STATUS_LABEL = {
  queued:      "Waiting in queue...",
  loading:     "Loading AI model...",
  transcribing:"Transcribing audio...",
  diarizing:   "Detecting speakers...",
  summarizing: "Generating minutes...",
  complete:    "Done!",
  failed:      "Processing failed",
};

const SPEAKER_COLORS = [
  "#E63946", "#2EC4B6", "#F4A261", "#818CF8", "#4CC9F0",
  "#7209B7", "#F72585", "#3A86FF", "#06D6A0", "#FFB703",
];

function speakerColor(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffff;
  return SPEAKER_COLORS[h % SPEAKER_COLORS.length];
}

function formatTime(sec) {
  if (sec == null) return "";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function Processing() {
  const { jobId }  = useParams();
  const nav        = useNavigate();
  const logRef     = useRef(null);
  const transcriptRef = useRef(null);
  const prefersReduced = useReducedMotion();

  const handleCancel = async () => {
    if (!confirm("Cancel this job?")) return;
    try {
      await axios.delete(`${API}/jobs/${jobId}`);
      nav("/");
    } catch {
      nav("/");
    }
  };

  const [job,           setJob]           = useState(null);
  const [logLines,      setLogLines]      = useState([]);
  const [transcriptChunks, setTranscriptChunks] = useState([]);
  const [diarSegments,  setDiarSegments]  = useState([]);   // [{speaker, text, start, end}]
  const [error,         setError]         = useState(null);
  const [showLog,       setShowLog]       = useState(false);

  /* ── Poll job status ── */
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await axios.get(`${API}/jobs/${jobId}`);
        if (!cancelled) setJob(res.data);
      } catch {
        if (!cancelled) setError("Failed to load job");
      }
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => { cancelled = true; clearInterval(id); };
  }, [jobId]);

  /* ── SSE stream ── */
  useEffect(() => {
    const es = new EventSource(`${API}/jobs/${jobId}/events`);

    es.onmessage = (e) => {
      if (e.data === "[DONE]") { es.close(); return; }
      setLogLines((p) => [...p, e.data]);
    };

    es.addEventListener("transcript", (e) => {
      setTranscriptChunks((p) => [...p, e.data]);
    });

    es.addEventListener("diar", (e) => {
      try {
        const seg = JSON.parse(e.data);
        setDiarSegments((p) => [...p, seg]);
      } catch { /* ignore malformed */ }
    });

    es.onerror = () => es.close();
    return () => es.close();
  }, [jobId]);

  /* ── Auto-scroll ── */
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logLines]);
  useEffect(() => {
    if (transcriptRef.current) transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [transcriptChunks, diarSegments]);

  if (error) return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="rounded-2xl p-6 text-sm" style={{ background: "rgba(230,57,70,0.08)", border: "1px solid rgba(230,57,70,0.2)", color: "var(--danger)" }}>
        {error}
      </div>
    </div>
  );
  if (!job) return (
    <div className="p-8 max-w-3xl mx-auto flex items-center gap-3 pt-24">
      <WaveformAnimation active bars={6} height={24} color="var(--ink3)" />
      <span className="text-sm" style={{ color: "var(--ink3)" }}>Loading...</span>
    </div>
  );

  const isComplete = job.status === "complete";
  const isFailed   = job.status === "failed";
  const isActive   = !isComplete && !isFailed;
  const isDiarizing = job.status === "diarizing";
  const hasDiar    = diarSegments.length > 0;
  const hasTranscript = transcriptChunks.length > 0;

  return (
    <div className="p-8 max-w-3xl mx-auto min-h-screen" style={{ background: "var(--bg)" }}>

      {/* ── Header ── */}
      <motion.div
        className="mb-8"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <button
          onClick={() => nav("/")}
          className="flex items-center gap-1.5 text-sm mb-5 transition-colors"
          style={{ color: "var(--ink3)" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "var(--ink)")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "var(--ink3)")}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Dashboard
        </button>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1
              className="text-2xl font-bold leading-tight"
              style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)", letterSpacing: "-0.03em" }}
            >
              {job.title}
            </h1>
            <p className="text-sm mt-1" style={{ color: "var(--ink3)" }}>{job.filename}</p>
          </div>
          {isActive && (
            <div className="shrink-0 pt-1 flex items-center gap-2">
              <div className="rec-badge">
                <span className="dot" />
                LIVE
              </div>
              <button
                onClick={handleCancel}
                className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors shrink-0"
                style={{ color: "var(--danger)", background: "rgba(230,57,70,0.1)", border: "1px solid rgba(230,57,70,0.2)" }}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Cancel Job
              </button>
            </div>
          )}
        </div>
      </motion.div>

      {/* ── Progress card ── */}
      <motion.div
        className="rounded-2xl border p-6 mb-5"
        style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 1px 4px var(--shadow)" }}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <ProgressStepper status={job.status} />

        {/* Waveform during active processing */}
        <AnimatePresence>
          {isActive && (
            <motion.div
              className="mt-6 flex items-center justify-center gap-1.5 h-16"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
            >
              {Array.from({ length: 20 }).map((_, i) => {
                const delay = (i * 0.07) % 1.4;
                return (
                  <div
                    key={i}
                    className="w-[3px] rounded-full"
                    style={{
                      background: "var(--primary)",
                      animation: `wave 1.4s ease-in-out ${delay}s infinite`,
                      height: "100%",
                      transformOrigin: "bottom center",
                      opacity: 0.7 + (i % 4) * 0.075,
                    }}
                  />
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Progress bar */}
        <div className="mt-5">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-medium" style={{ color: "var(--ink2)", fontFamily: "Syne, sans-serif" }}>
              {STATUS_LABEL[job.status] || job.status}
            </span>
            <span
              className="text-xs font-bold tabular-nums"
              style={{ color: isFailed ? "var(--danger)" : "var(--primary)", fontFamily: "Syne, sans-serif" }}
            >
              {job.progress}%
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full overflow-hidden" style={{ background: "var(--surface2)" }}>
            <motion.div
              className="h-full rounded-full"
              style={{ background: isFailed ? "var(--danger)" : "var(--primary)" }}
              initial={{ width: "0%" }}
              animate={{ width: `${job.progress}%` }}
              transition={{ type: "spring", stiffness: 80, damping: 20 }}
            />
          </div>
        </div>

        {/* Completion flash */}
        <AnimatePresence>
          {isComplete && (
            <motion.div
              className="mt-4 flex items-center gap-3 px-4 py-3 rounded-xl"
              style={{ background: "rgba(42,157,110,0.1)", border: "1px solid rgba(42,157,110,0.2)" }}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0" style={{ background: "var(--success)" }}>
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <span className="text-sm font-medium" style={{ color: "var(--success)" }}>
                Processing complete — your minutes are ready.
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* ── Live Transcript / Diarized Transcript — always visible ── */}
      <motion.div
        className="rounded-2xl border mb-5 overflow-hidden"
        style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 1px 4px var(--shadow)" }}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* Panel header */}
        <div className="px-5 py-3.5 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2.5">
            <AnimatePresence mode="wait">
              {hasDiar ? (
                <motion.div
                  key="diar-icon"
                  className="flex items-center gap-2.5"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  <svg className="w-4 h-4 shrink-0" style={{ color: "var(--gold)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span className="text-sm font-semibold" style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)" }}>
                    Speaker Transcript
                  </span>
                </motion.div>
              ) : (
                <motion.div
                  key="transcript-icon"
                  className="flex items-center gap-2.5"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  <WaveformAnimation active={job.status === "transcribing"} bars={5} height={16} color="var(--primary)" />
                  <span className="text-sm font-semibold" style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)" }}>
                    Live Transcript
                  </span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Status badge */}
            <AnimatePresence mode="wait">
              {hasDiar ? (
                <motion.span
                  key="diar-badge"
                  className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
                  style={{ background: "rgba(244,162,97,0.15)", color: "var(--gold)", fontFamily: "Syne, sans-serif" }}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ type: "spring", stiffness: 400, damping: 20 }}
                >
                  {diarSegments.length} segments
                </motion.span>
              ) : job.status === "transcribing" ? (
                <motion.span
                  key="live-badge"
                  className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
                  style={{ background: "rgba(244,162,97,0.15)", color: "var(--gold)", fontFamily: "Syne, sans-serif" }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  Live
                </motion.span>
              ) : isDiarizing ? (
                <motion.span
                  key="diarizing-badge"
                  className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
                  style={{ background: "rgba(129,140,248,0.15)", color: "#818CF8", fontFamily: "Syne, sans-serif" }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  Detecting speakers
                </motion.span>
              ) : null}
            </AnimatePresence>
          </div>

          <span className="text-xs tabular-nums" style={{ color: "var(--ink3)" }}>
            {hasDiar ? `${diarSegments.length} seg` : `${transcriptChunks.length} seg`}
          </span>
        </div>

        {/* Panel body */}
        <div
          ref={transcriptRef}
          className="p-5 overflow-y-auto"
          style={{ maxHeight: "320px" }}
        >
          <AnimatePresence mode="wait">
            {/* ── Diarized view (speaker-attributed) ── */}
            {hasDiar ? (
              <motion.div
                key="diar-view"
                className="space-y-3"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.35 }}
              >
                {diarSegments.map((seg, i) => {
                  const color = speakerColor(seg.speaker);
                  return (
                    <motion.div
                      key={i}
                      className="flex gap-3"
                      initial={prefersReduced ? {} : { opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: Math.min(i * 0.015, 0.6), duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                    >
                      {/* Speaker chip */}
                      <div className="shrink-0 pt-0.5">
                        <div
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap"
                          style={{ background: color + "1A", border: `1px solid ${color}40`, color }}
                        >
                          <span
                            className="w-3.5 h-3.5 rounded-full flex items-center justify-center text-[8px] font-bold text-white shrink-0"
                            style={{ background: color }}
                          >
                            {seg.speaker.slice(-1)}
                          </span>
                          {seg.speaker}
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-[10px] tabular-nums mr-2" style={{ color: "var(--ink3)" }}>
                          {formatTime(seg.start)}
                        </span>
                        <span className="text-sm leading-relaxed" style={{ color: "var(--ink)" }}>
                          {seg.text}
                        </span>
                      </div>
                    </motion.div>
                  );
                })}
              </motion.div>
            ) : (
              /* ── Raw transcript view ── */
              <motion.div
                key="transcript-view"
                className="space-y-2.5"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                {hasTranscript ? (
                  <AnimatePresence initial={false}>
                    {transcriptChunks.map((chunk, i) => (
                      <motion.p
                        key={i}
                        className="text-sm leading-relaxed"
                        style={{ color: "var(--ink)" }}
                        initial={prefersReduced ? {} : { opacity: 0, y: 10, filter: "blur(2px)" }}
                        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                        transition={{ duration: 0.18, ease: [0.25, 0.1, 0.25, 1] }}
                      >
                        {chunk}
                      </motion.p>
                    ))}
                  </AnimatePresence>
                ) : (
                  <div className="flex flex-col items-center gap-3 py-8">
                    {isDiarizing ? (
                      <>
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4" style={{ color: "#818CF8" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                          <span className="text-sm font-medium" style={{ color: "#818CF8", fontFamily: "Syne, sans-serif" }}>
                            Assigning speakers — results appear here when done
                          </span>
                        </div>
                        <p className="text-xs" style={{ color: "var(--ink3)" }}>
                          Transcript will upgrade to speaker view automatically
                        </p>
                      </>
                    ) : (
                      <p className="text-sm" style={{ color: "var(--ink3)" }}>
                        {job.status === "transcribing"
                          ? "Waiting for first segment..."
                          : "Transcript appears here during transcription"}
                      </p>
                    )}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* ── Pipeline Log ── */}
      <motion.div
        className="rounded-2xl border overflow-hidden mb-5"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        <button
          onClick={() => setShowLog((v) => !v)}
          className="w-full px-5 py-3 flex items-center justify-between text-left"
          style={{ borderBottom: showLog ? `1px solid var(--border)` : "none" }}
        >
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
              <div className="w-2.5 h-2.5 rounded-full bg-yellow-400" />
              <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
            </div>
            <span className="text-xs font-medium" style={{ color: "var(--ink2)", fontFamily: "Syne, sans-serif" }}>
              Pipeline Output
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: "var(--ink3)" }}>
              {logLines.length} lines
            </span>
            <motion.svg
              className="w-4 h-4"
              style={{ color: "var(--ink3)" }}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
              animate={{ rotate: showLog ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </motion.svg>
          </div>
        </button>

        <AnimatePresence>
          {showLog && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              style={{ overflow: "hidden" }}
            >
              <div
                ref={logRef}
                className="log-terminal p-4 overflow-y-auto"
                style={{ maxHeight: "200px", background: "var(--surface2)", color: "var(--ink2)" }}
              >
                {logLines.length === 0 ? (
                  <span style={{ color: "var(--ink3)" }}>Waiting for output...</span>
                ) : (
                  logLines.map((line, i) => (
                    <div
                      key={i}
                      style={{ color: line.startsWith("ERROR") ? "var(--danger)" : "var(--ink2)" }}
                    >
                      {line}
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* ── Action ── */}
      <AnimatePresence>
        {isComplete && (
          <motion.button
            onClick={() => nav(`/minutes/${jobId}`)}
            className="w-full py-3.5 rounded-xl font-bold text-sm text-white"
            style={{
              background: "var(--primary)",
              fontFamily: "Syne, sans-serif",
              letterSpacing: "0.02em",
            }}
            initial={prefersReduced ? {} : { opacity: 0, y: 10, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.4, ease: [0, 0, 0.2, 1] }}
            whileHover={{ scale: 1.01, filter: "brightness(1.05)" }}
            whileTap={{ scale: 0.98 }}
          >
            View Meeting Minutes →
          </motion.button>
        )}
        {isFailed && (
          <motion.div
            className="rounded-xl p-4 text-sm"
            style={{ background: "rgba(230,57,70,0.08)", border: "1px solid rgba(230,57,70,0.2)", color: "var(--danger)" }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {job.error || "Processing failed. Check the log above for details."}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
