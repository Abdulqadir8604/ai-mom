import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";

function formatTime(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatTs(ms) {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export default function LiveRecorder({ onRecordingComplete, showTranscript = false }) {
  const [recState, setRecState] = useState("idle");
  const [duration, setDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [error, setError] = useState(null);
  const [entries, setEntries] = useState([]);
  const [interim, setInterim] = useState("");
  const prefersReduced = useReducedMotion();

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const analyserRef = useRef(null);
  const canvasRef = useRef(null);
  const rafRef = useRef(null);
  const audioCtxRef = useRef(null);
  const mountedRef = useRef(true);
  const recognitionRef = useRef(null);
  const recStartRef = useRef(0);
  const transcriptEndRef = useRef(null);
  const stoppedRef = useRef(false);  // explicit stop flag

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      stoppedRef.current = true;
      cancelAnimationFrame(rafRef.current);
      if (timerRef.current) clearInterval(timerRef.current);
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
      if (audioCtxRef.current?.state !== "closed") audioCtxRef.current?.close();
      if (recognitionRef.current) { try { recognitionRef.current.abort(); } catch {} }
    };
  }, []);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, interim]);

  /* ── Waveform ── */
  const drawWaveform = useCallback(() => {
    const analyser = analyserRef.current;
    const canvas = canvasRef.current;
    if (!analyser || !canvas) {
      if (!stoppedRef.current) rafRef.current = requestAnimationFrame(drawWaveform);
      return;
    }
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    if (canvas.width !== Math.round(rect.width * dpr)) {
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
    }
    const ctx = canvas.getContext("2d");
    const len = analyser.frequencyBinCount;
    const data = new Uint8Array(len);
    analyser.getByteFrequencyData(data);
    const W = canvas.width / dpr, H = canvas.height / dpr;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.scale(dpr, dpr);
    const gap = 2, bw = Math.max(2, (W - gap * (len - 1)) / len);
    for (let i = 0; i < len; i++) {
      const r = data[i] / 255, bh = Math.max(3, r * H);
      ctx.fillStyle = i < len / 3
        ? `rgba(230,57,70,${0.6 + r * 0.4})`
        : i < (len * 2) / 3
        ? `rgba(204,41,54,${0.5 + r * 0.4})`
        : `rgba(244,162,97,${0.5 + r * 0.4})`;
      ctx.fillRect(i * (bw + gap), H - bh, bw, bh);
    }
    ctx.restore();
    if (!stoppedRef.current) rafRef.current = requestAnimationFrame(drawWaveform);
  }, []);

  /* ── Speech Recognition — single-shot mode, auto-restart ── */
  const spawnRecognition = useCallback(() => {
    if (stoppedRef.current) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;

    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
    }

    const r = new SR();
    // Use single-shot mode — more reliable than continuous
    r.continuous = false;
    r.interimResults = true;
    r.lang = "en-US";

    r.onresult = (event) => {
      if (!mountedRef.current) return;
      const now = Date.now();
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        const text = res[0].transcript.trim();
        if (!text) continue;
        if (res.isFinal) {
          setEntries((prev) => [...prev, { text, time: now - recStartRef.current }]);
          setInterim("");
        } else {
          setInterim(text);
        }
      }
    };

    // Single-shot mode ends after each phrase — just respawn immediately
    r.onend = () => {
      if (!stoppedRef.current && mountedRef.current) {
        setTimeout(spawnRecognition, 100);
      }
    };

    r.onerror = (e) => {
      if (e.error === "not-allowed") return; // mic denied, don't retry
      if (!stoppedRef.current && mountedRef.current) {
        // Wait longer on no-speech to avoid spinning
        const delay = e.error === "no-speech" ? 500 : 200;
        setTimeout(spawnRecognition, delay);
      }
    };

    try { r.start(); } catch {}
    recognitionRef.current = r;
  }, []);

  /* ── Start ── */
  const startRecording = async () => {
    try {
      setError(null);
      setEntries([]);
      setInterim("");
      stoppedRef.current = false;

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      streamRef.current = stream;

      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      audioCtx.createMediaStreamSource(stream).connect(analyser);

      // Single-chunk recording — no timeslice for clean audio output
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;

      mr.ondataavailable = (e) => {
        if (e.data.size > 0 && mountedRef.current) {
          setAudioBlob(e.data);
        }
      };

      mr.start(); // no timeslice = one clean blob on stop
      recStartRef.current = Date.now();
      if (mountedRef.current) { setRecState("recording"); setDuration(0); }

      timerRef.current = setInterval(() => {
        if (mountedRef.current) setDuration((d) => d + 1);
      }, 1000);

      if (!prefersReduced) rafRef.current = requestAnimationFrame(drawWaveform);
      if (showTranscript) spawnRecognition();
    } catch {
      if (mountedRef.current)
        setError("Microphone access denied. Please allow microphone access and try again.");
    }
  };

  /* ── Stop ── */
  const stopRecording = () => {
    stoppedRef.current = true; // signal all loops to stop
    if (mediaRecorderRef.current?.state !== "inactive") mediaRecorderRef.current?.stop();
    if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    if (timerRef.current) clearInterval(timerRef.current);
    cancelAnimationFrame(rafRef.current);
    if (audioCtxRef.current?.state !== "closed") audioCtxRef.current?.close();
    if (recognitionRef.current) { try { recognitionRef.current.abort(); } catch {} }
    setInterim("");
    if (mountedRef.current) setRecState("stopped");
  };

  const resetRecording = () => {
    setAudioBlob(null); setDuration(0); setError(null);
    setEntries([]); setInterim("");
    stoppedRef.current = false;
    if (mountedRef.current) setRecState("idle");
  };

  const handleUse = () => {
    if (!audioBlob) return;
    const ext = audioBlob.type?.includes("ogg") ? "ogg" : "webm";
    const file = new File([audioBlob], `live-recording-${Date.now()}.${ext}`, { type: audioBlob.type || "audio/webm" });
    onRecordingComplete(file);
  };

  return (
    <div className="w-full">
      <AnimatePresence mode="wait">

        {/* ── IDLE ── */}
        {recState === "idle" && (
          <motion.div key="idle" className="flex flex-col items-center justify-center gap-5 py-10"
            initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }} transition={{ duration: 0.25 }}>
            {error && <p className="text-xs text-center px-4" style={{ color: "var(--danger)" }}>{error}</p>}
            <motion.button type="button" onClick={startRecording}
              className="relative w-20 h-20 rounded-full flex items-center justify-center"
              style={{ background: "var(--primary)" }} whileHover={{ scale: 1.06 }} whileTap={{ scale: 0.94 }}>
              {!prefersReduced && (
                <motion.div className="absolute inset-0 rounded-full"
                  style={{ border: "2px solid var(--primary)", opacity: 0.5 }}
                  animate={{ scale: [1, 1.5, 1.8], opacity: [0.5, 0.25, 0] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }} />
              )}
              <svg className="w-8 h-8 text-white relative z-10" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4z" />
                <path d="M19 10a1 1 0 10-2 0 5 5 0 01-10 0 1 1 0 10-2 0 7 7 0 0013 .83V10zm-7 9a1 1 0 011 1v2a1 1 0 11-2 0v-2a1 1 0 011-1z" />
              </svg>
            </motion.button>
            <div className="text-center">
              <p className="text-sm font-semibold" style={{ color: "var(--ink)", fontFamily: "Syne, sans-serif" }}>
                Tap to start recording</p>
              <p className="text-xs mt-1" style={{ color: "var(--ink3)" }}>
                Uses your microphone{showTranscript ? " · Live transcript" : ""}</p>
            </div>
          </motion.div>
        )}

        {/* ── RECORDING ── */}
        {recState === "recording" && (
          <motion.div key="recording" className="flex flex-col gap-4 py-6 px-4"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>

            <div className="w-full rounded-xl overflow-hidden relative" style={{ height: "64px", background: "var(--surface2)" }}>
              <canvas ref={canvasRef} style={{ width: "100%", height: "100%", display: "block" }} />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="rec-badge"><span className="dot" />REC</div>
                <span className="text-lg font-bold tabular-nums" style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)" }}>
                  {formatTime(duration)}</span>
              </div>
              <motion.button type="button" onClick={stopRecording}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm text-white"
                style={{ background: "var(--primary)", fontFamily: "Syne, sans-serif" }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.96 }}>
                <div className="w-3 h-3 rounded-sm bg-white" />
                Stop
              </motion.button>
            </div>

            {showTranscript && (
              <div className="rounded-xl overflow-y-auto space-y-0.5" style={{ maxHeight: "260px" }}>
                {entries.length === 0 && !interim && (
                  <motion.div className="flex items-center gap-2 py-3 justify-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <motion.div className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--ink3)" }}
                      animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.5, repeat: Infinity }} />
                    <span className="text-xs" style={{ color: "var(--ink3)" }}>Listening...</span>
                  </motion.div>
                )}
                <AnimatePresence initial={false}>
                  {entries.map((entry, i) => (
                    <motion.div key={i} className="flex gap-2.5 items-start py-1.5"
                      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}>
                      <span className="text-[10px] tabular-nums shrink-0 mt-1 w-10"
                        style={{ color: "var(--ink3)" }}>{formatTs(entry.time)}</span>
                      <p className="text-sm leading-relaxed" style={{ color: "var(--ink)" }}>{entry.text}</p>
                    </motion.div>
                  ))}
                </AnimatePresence>
                {interim && (
                  <motion.div className="flex gap-2.5 items-start py-1.5" initial={{ opacity: 0 }} animate={{ opacity: 0.5 }}>
                    <span className="text-[10px] shrink-0 mt-1 w-10" style={{ color: "var(--ink3)" }}>···</span>
                    <p className="text-sm italic" style={{ color: "var(--ink3)" }}>{interim}</p>
                  </motion.div>
                )}
                <div ref={transcriptEndRef} />
              </div>
            )}
          </motion.div>
        )}

        {/* ── STOPPED ── */}
        {recState === "stopped" && (
          <motion.div key="stopped" className="flex flex-col gap-5 py-6 px-4"
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: "rgba(230,57,70,0.08)" }}>
                <svg className="w-5 h-5" style={{ color: "var(--primary)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
              </div>
              <div>
                <p className="text-sm font-bold" style={{ color: "var(--ink)", fontFamily: "Syne, sans-serif" }}>Recording complete</p>
                <p className="text-xs" style={{ color: "var(--ink3)" }}>
                  {formatTime(duration)}{audioBlob ? ` · ${(audioBlob.size / (1024 * 1024)).toFixed(1)} MB` : ""}
                  {entries.length > 0 ? ` · ${entries.length} phrases` : ""}</p>
              </div>
            </div>

            {showTranscript && entries.length > 0 && (
              <div className="rounded-xl overflow-y-auto space-y-1 px-3 py-2"
                style={{ maxHeight: "200px", background: "var(--surface2)", border: "1px solid var(--border)" }}>
                {entries.map((e, i) => (
                  <div key={i} className="flex gap-2 items-start py-0.5">
                    <span className="text-[10px] tabular-nums shrink-0 mt-0.5 w-10" style={{ color: "var(--ink3)" }}>{formatTs(e.time)}</span>
                    <p className="text-xs" style={{ color: "var(--ink2)" }}>{e.text}</p>
                  </div>
                ))}
              </div>
            )}

            {audioBlob && <audio controls className="w-full rounded-xl" style={{ height: "36px" }} src={URL.createObjectURL(audioBlob)} />}

            <div className="flex gap-3 w-full">
              <motion.button type="button" onClick={resetRecording}
                className="flex-1 py-2.5 rounded-xl font-semibold text-sm"
                style={{ background: "var(--surface2)", color: "var(--ink2)", fontFamily: "Syne, sans-serif" }}
                whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }}>Re-record</motion.button>
              <motion.button type="button" onClick={handleUse}
                className="flex-2 flex-grow py-2.5 rounded-xl font-bold text-sm text-white"
                style={{ background: "var(--primary)", fontFamily: "Syne, sans-serif" }}
                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>Use this recording →</motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
