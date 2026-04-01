import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import JobCard from "../components/JobCard";
import WaveformAnimation from "../components/WaveformAnimation";
import LiveRecorder from "../components/LiveRecorder";

const API = import.meta.env.VITE_API_URL || "/api";

const MODEL_OPTS = [
  { value: "tiny",   label: "Tiny",   sub: "fastest, rough"         },
  { value: "base",   label: "Base",   sub: "quick, decent"          },
  { value: "small",  label: "Small",  sub: "balanced · recommended" },
  { value: "medium", label: "Medium", sub: "slow, high quality"     },
  { value: "large",  label: "Large",  sub: "slowest, best accuracy" },
];

const LANG_OPTS = [
  { value: "en",   label: "English"             },
  { value: "gu",   label: "Gujarati"            },
  { value: "hi",   label: "Hindi"               },
  { value: "auto", label: "Auto-detect"         },
  { value: "lsd",  label: "Lisan-ud-Dawat",
    hint: "Outputs Arabic script" },
];

export default function Dashboard() {
  const nav = useNavigate();
  const fileInputRef = useRef(null);
  const prefersReduced = useReducedMotion();

  const [jobs,        setJobs]        = useState([]);
  const [speakerCount, setSpeakerCount] = useState(0);
  const [inputMode,   setInputMode]   = useState("upload"); // "upload" | "record"
  const [file,        setFile]        = useState(null);
  const [title,       setTitle]       = useState("");
  const [language,    setLanguage]    = useState("en");
  const [model,       setModel]       = useState("small");
  const [engine,      setEngine]      = useState("whisper");
  const [diarize,     setDiarize]     = useState(false);
  const [translate,   setTranslate]   = useState(false);
  const [numSpeakers, setNumSpeakers] = useState("");
  const [submitting,  setSubmitting]  = useState(false);
  const [dragOver,    setDragOver]    = useState(false);

  const fetchJobs = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/jobs`);
      setJobs(res.data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchJobs();
    const id = setInterval(fetchJobs, 5000);
    return () => clearInterval(id);
  }, [fetchJobs]);

  useEffect(() => {
    axios.get(`${API}/speakers`).then(r => setSpeakerCount(r.data.length)).catch(() => {});
  }, []);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setSubmitting(true);
    const fd = new FormData();
    fd.append("audio", file);
    fd.append("title", title);
    fd.append("language", language);
    fd.append("model", model);
    fd.append("engine", engine);
    fd.append("diarize", diarize);
    fd.append("translate", translate);
    if (numSpeakers) fd.append("num_speakers", numSpeakers);
    try {
      const res = await axios.post(`${API}/jobs`, fd);
      nav(`/processing/${res.data.id}`);
    } catch (err) {
      alert("Upload failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteJob = (id) => setJobs((prev) => prev.filter((j) => j.id !== id));

  const handleExportCsv = () => {
    if (!jobs.length) return;
    const headers = ["Title", "Filename", "Date", "Duration (s)", "Status", "Language", "Model"];
    const rows = jobs.map(j => [
      `"${(j.title || "").replace(/"/g, '""')}"`,
      `"${(j.filename || "").replace(/"/g, '""')}"`,
      j.created_at || "",
      j.duration_seconds || "",
      j.status || "",
      j.language || "",
      j.model || "",
    ].join(","));
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ai-mom-meetings-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatSize = (bytes) => {
    if (!bytes) return "";
    return bytes < 1024 * 1024
      ? (bytes / 1024).toFixed(1) + " KB"
      : (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const containerVariants = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.1, delayChildren: 0.1 } },
  };
  const itemVariants = {
    hidden:   { opacity: 0, y: 16 },
    visible:  { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
  };

  return (
    <div
      className="p-8 max-w-4xl mx-auto min-h-screen"
      style={{ background: "var(--bg)" }}
    >
      {/* ── Header ── */}
      <motion.div
        className="mb-8"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={itemVariants} className="flex items-center gap-3 mb-1">
          <h1
            className="text-3xl font-bold leading-none"
            style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)", letterSpacing: "-0.03em" }}
          >
            Dashboard
          </h1>
          <WaveformAnimation active={jobs.some(j => ["loading","transcribing","diarizing","summarizing"].includes(j.status))} bars={6} height={20} color="var(--primary)" />
        </motion.div>
        <motion.p variants={itemVariants} className="text-sm" style={{ color: "var(--ink2)" }}>
          Upload a meeting recording and get AI-generated minutes instantly.
        </motion.p>
      </motion.div>

      {/* ── Stats Row ── */}
      <motion.div
        className="grid grid-cols-3 gap-4 mb-8"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      >
        {[
          { label: "Total Meetings", value: jobs.length, icon: "📋" },
          { label: "Hours Processed", value: (jobs.reduce((a, j) => a + (j.duration_seconds || 0), 0) / 3600).toFixed(1) + "h", icon: "⏱" },
          { label: "Speakers Enrolled", value: speakerCount, icon: "🎤" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-2xl border p-4 flex items-center gap-3"
            style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 1px 4px var(--shadow)" }}
          >
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center text-base shrink-0"
              style={{ background: "rgba(230,57,70,0.1)" }}
            >
              {stat.icon}
            </div>
            <div>
              <div className="text-xl font-bold leading-none" style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)" }}>
                {stat.value}
              </div>
              <div className="text-[11px] mt-1 font-medium uppercase tracking-wider" style={{ color: "var(--ink3)", fontFamily: "Syne, sans-serif" }}>
                {stat.label}
              </div>
            </div>
          </div>
        ))}
      </motion.div>

      {/* ── Upload Form ── */}
      <motion.form
        onSubmit={handleSubmit}
        className="rounded-2xl border p-6 mb-8"
        style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 1px 4px var(--shadow)" }}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Input mode tab switcher */}
        <motion.div variants={itemVariants} className="flex gap-1 p-1 rounded-xl mb-5" style={{ background: "var(--surface2)" }}>
          {[
            { key: "upload", label: "Upload File", icon: (
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            )},
            { key: "record", label: "Live Record", icon: (
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4z" />
                <path d="M19 10a1 1 0 10-2 0 5 5 0 01-10 0 1 1 0 10-2 0 7 7 0 0013 .83V10zm-7 9a1 1 0 011 1v2a1 1 0 11-2 0v-2a1 1 0 011-1z" />
              </svg>
            )},
          ].map(({ key, label, icon }) => (
            <motion.button
              key={key}
              type="button"
              onClick={() => { setInputMode(key); setFile(null); }}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-colors relative"
              style={{
                fontFamily: "Syne, sans-serif",
                color: inputMode === key ? "var(--ink)" : "var(--ink3)",
              }}
            >
              {inputMode === key && (
                <motion.div
                  layoutId="tab-bg"
                  className="absolute inset-0 rounded-lg"
                  style={{ background: "var(--surface)" }}
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative z-10 flex items-center gap-1.5">
                {icon}
                {label}
                {key === "record" && (
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--primary)", animation: "rec-pulse 1.4s ease-in-out infinite" }} />
                )}
              </span>
            </motion.button>
          ))}
        </motion.div>

        {/* Drop Zone / Live Recorder */}
        <motion.div variants={itemVariants}>
          <AnimatePresence mode="wait">
          {inputMode === "record" ? (
            <motion.div
              key="recorder"
              className="border-2 border-dashed rounded-xl mb-6 overflow-hidden"
              style={{ borderColor: "var(--border)", background: "var(--surface2)" }}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <LiveRecorder onRecordingComplete={(f) => setFile(f)} showTranscript />
            </motion.div>
          ) : (
          <motion.div
            key="uploader"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
          <motion.div
            className={`relative border-2 border-dashed rounded-xl mb-6 cursor-pointer overflow-hidden transition-colors ${
              dragOver ? "drop-active" : ""
            }`}
            style={{
              borderColor: dragOver ? "var(--primary)" : "var(--border)",
              background: dragOver ? "rgba(230,57,70,0.03)" : "var(--surface2)",
            }}
            animate={prefersReduced ? {} : dragOver ? { scale: 1.01 } : { scale: 1 }}
            transition={{ duration: 0.15 }}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            whileHover={{ borderColor: "var(--ink3)" }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".wav,.mp3,.m4a,.flac,.ogg,.wma"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />

            <AnimatePresence mode="wait">
              {file ? (
                <motion.div
                  key="file-loaded"
                  className="p-6 flex items-center gap-4"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.25 }}
                >
                  {/* Audio waveform icon */}
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
                    style={{ background: "rgba(230,57,70,0.1)" }}
                  >
                    <WaveformAnimation active bars={5} height={20} color="var(--primary)" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm truncate" style={{ color: "var(--ink)", fontFamily: "Syne, sans-serif" }}>
                      {file.name}
                    </div>
                    <div className="text-xs mt-0.5" style={{ color: "var(--ink3)" }}>
                      {formatSize(file.size)}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="text-xs font-medium px-3 py-1.5 rounded-lg transition-colors shrink-0"
                    style={{ color: "var(--danger)", background: "rgba(230,57,70,0.08)" }}
                    onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  >
                    Remove
                  </button>
                </motion.div>
              ) : (
                <motion.div
                  key="drop-empty"
                  className="p-10 flex flex-col items-center gap-3"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div
                    className="w-14 h-14 rounded-2xl flex items-center justify-center"
                    style={{ background: "var(--border)" }}
                  >
                    <svg className="w-6 h-6" style={{ color: "var(--ink3)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium" style={{ color: "var(--ink)" }}>
                      Drop audio here or{" "}
                      <span style={{ color: "var(--primary)" }}>browse files</span>
                    </p>
                    <p className="text-xs mt-1" style={{ color: "var(--ink3)" }}>
                      WAV · MP3 · M4A · FLAC · OGG
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
          </motion.div>
          )}
          </AnimatePresence>
        </motion.div>

        {/* Settings */}
        <motion.div variants={itemVariants} className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-5">
          {/* Title */}
          <div className="md:col-span-2">
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--ink2)", fontFamily: "Syne, sans-serif", letterSpacing: "0.03em" }}>
              TITLE
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Meeting title"
              className="w-full rounded-xl px-3 py-2.5 text-sm outline-none transition-colors"
              style={{
                background: "var(--surface2)",
                border: "1.5px solid var(--border)",
                color: "var(--ink)",
              }}
              onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
              onBlur={(e)  => (e.target.style.borderColor = "var(--border)")}
            />
          </div>

          {/* Language */}
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--ink2)", fontFamily: "Syne, sans-serif", letterSpacing: "0.03em" }}>
              LANGUAGE
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full rounded-xl px-3 py-2.5 text-sm outline-none"
              style={{
                background: "var(--surface2)",
                border: "1.5px solid var(--border)",
                color: "var(--ink)",
              }}
            >
              {LANG_OPTS.map((o) => (
                <option key={o.value} value={o.value} title={o.hint}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Engine */}
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--ink2)", fontFamily: "Syne, sans-serif", letterSpacing: "0.03em" }}>
              ENGINE
            </label>
            <select
              value={engine}
              onChange={(e) => setEngine(e.target.value)}
              className="w-full rounded-xl px-3 py-2.5 text-sm outline-none"
              style={{
                background: "var(--surface2)",
                border: "1.5px solid var(--border)",
                color: "var(--ink)",
              }}
            >
              <option value="whisper">Whisper (local)</option>
              <option value="soniox">Soniox (cloud)</option>
            </select>
          </div>

          {/* Model — only for Whisper */}
          {engine === "whisper" && (
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--ink2)", fontFamily: "Syne, sans-serif", letterSpacing: "0.03em" }}>
              MODEL
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full rounded-xl px-3 py-2.5 text-sm outline-none"
              style={{
                background: "var(--surface2)",
                border: "1.5px solid var(--border)",
                color: "var(--ink)",
              }}
            >
              {MODEL_OPTS.map((o) => (
                <option key={o.value} value={o.value}>{o.label} — {o.sub}</option>
              ))}
            </select>
          </div>
          )}

          {/* Diarize */}
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--ink2)", fontFamily: "Syne, sans-serif", letterSpacing: "0.03em" }}>
              SPEAKERS
            </label>
            <div className="flex flex-col gap-2">
              <button
                type="button"
                onClick={() => setDiarize(!diarize)}
                className="flex items-center gap-2 h-10"
              >
                <div
                  className="relative w-10 h-5.5 rounded-full transition-colors duration-200 shrink-0"
                  style={{
                    background: diarize ? "var(--primary)" : "var(--border)",
                    height: "22px",
                    width: "40px",
                  }}
                >
                  <motion.div
                    className="absolute top-0.5 w-4.5 h-4.5 bg-white rounded-full shadow-sm"
                    style={{ height: "18px", width: "18px" }}
                    animate={{ left: diarize ? "20px" : "2px" }}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                </div>
                <span className="text-sm" style={{ color: diarize ? "var(--primary)" : "var(--ink2)" }}>
                  {diarize ? "Detect" : "Off"}
                </span>
              </button>
              {diarize && (
                <motion.input
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  type="number" min="1" max="20"
                  value={numSpeakers}
                  onChange={(e) => setNumSpeakers(e.target.value)}
                  placeholder="# Auto"
                  className="w-full rounded-xl px-3 py-2 text-sm outline-none"
                  style={{ background: "var(--surface2)", border: "1.5px solid var(--border)", color: "var(--ink)" }}
                />
              )}
            </div>
          </div>

          {/* Translate */}
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--ink2)", fontFamily: "Syne, sans-serif", letterSpacing: "0.03em" }}>
              TRANSLATE
            </label>
            <button
              type="button"
              onClick={() => setTranslate(!translate)}
              className="flex items-center gap-2 h-10"
            >
              <div
                className="relative rounded-full transition-colors duration-200 shrink-0"
                style={{
                  background: translate ? "var(--primary)" : "var(--border)",
                  height: "22px",
                  width: "40px",
                }}
              >
                <motion.div
                  className="absolute top-0.5 bg-white rounded-full shadow-sm"
                  style={{ height: "18px", width: "18px" }}
                  animate={{ left: translate ? "20px" : "2px" }}
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              </div>
              <span className="text-sm" style={{ color: translate ? "var(--primary)" : "var(--ink2)" }}>
                {translate ? "→ EN" : "Off"}
              </span>
            </button>
          </div>
        </motion.div>

        {/* Submit */}
        <motion.div variants={itemVariants}>
          <motion.button
            type="submit"
            disabled={!file || submitting}
            className="w-full py-3 rounded-xl font-semibold text-sm text-white relative overflow-hidden"
            style={{
              background: file && !submitting ? "var(--primary)" : "var(--border)",
              color: file && !submitting ? "white" : "var(--ink3)",
              fontFamily: "Syne, sans-serif",
              letterSpacing: "0.02em",
              cursor: !file || submitting ? "not-allowed" : "pointer",
            }}
            whileHover={file && !submitting ? { scale: 1.01 } : {}}
            whileTap={file && !submitting ? { scale: 0.99 } : {}}
          >
            <AnimatePresence mode="wait">
              {submitting ? (
                <motion.span
                  key="uploading"
                  className="flex items-center justify-center gap-2"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <WaveformAnimation active bars={5} height={16} color="white" />
                  Uploading...
                </motion.span>
              ) : (
                <motion.span
                  key="process"
                  className="flex items-center justify-center gap-2"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  {file && <span className="rec-badge mr-1"><span className="dot" />REC</span>}
                  Process Meeting
                </motion.span>
              )}
            </AnimatePresence>
          </motion.button>
        </motion.div>
      </motion.form>

      {/* ── Jobs Table ── */}
      <motion.div
        className="rounded-2xl border overflow-hidden"
        style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 1px 4px var(--shadow)" }}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
          <h2
            className="font-bold text-base"
            style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)", letterSpacing: "-0.02em" }}
          >
            Recent Jobs
          </h2>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium px-2 py-1 rounded-lg" style={{ background: "var(--surface2)", color: "var(--ink2)" }}>
              {jobs.length} total
            </span>
            {jobs.length > 0 && (
              <button
                onClick={handleExportCsv}
                className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
                style={{ color: "var(--primary)", background: "rgba(230,57,70,0.08)", border: "1px solid rgba(230,57,70,0.15)" }}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                </svg>
                Export CSV
              </button>
            )}
          </div>
        </div>

        <AnimatePresence initial={false}>
          {jobs.length === 0 ? (
            <motion.div
              key="empty"
              className="py-16 flex flex-col items-center gap-3"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <WaveformAnimation active={false} bars={8} height={32} color="var(--border)" />
              <p className="text-sm" style={{ color: "var(--ink3)" }}>
                No recordings yet — upload one above to get started.
              </p>
            </motion.div>
          ) : (
            <motion.table key="table" className="w-full" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <thead>
                <tr
                  className="text-left border-b"
                  style={{ borderColor: "var(--border)" }}
                >
                  {["Title", "Date", "Duration", "Status", "Actions"].map((h) => (
                    <th
                      key={h}
                      className="px-5 py-3 text-[11px] font-semibold uppercase tracking-wider"
                      style={{ color: "var(--ink3)", fontFamily: "Syne, sans-serif" }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <AnimatePresence initial={false}>
                  {jobs.map((job) => (
                    <JobCard key={job.id} job={job} onDelete={handleDeleteJob} />
                  ))}
                </AnimatePresence>
              </tbody>
            </motion.table>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
