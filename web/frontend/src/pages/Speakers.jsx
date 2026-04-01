import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import LiveRecorder from "../components/LiveRecorder";

const API = import.meta.env.VITE_API_URL || "/api";

// Warm red-based palette for speaker avatars
const AVATAR_COLORS = [
  "#E63946", "#CC2936", "#F4A261", "#E76F51",
  "#D62828", "#C1121F", "#FF6B6B", "#FF4D6D",
  "#E85D04", "#DC2F02",
];

const SAMPLE_TEXT = "The quick brown fox jumps over the lazy dog. She sells sea shells by the sea shore. How much wood would a woodchuck chuck.";

function getInitials(n) {
  return n.split(/[_ ]+/).map(w => w[0] || "").join("").toUpperCase().slice(0, 2);
}

function avatarColor(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffff;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

export default function Speakers() {
  const [speakers, setSpeakers]           = useState([]);
  const [search, setSearch]               = useState("");
  const [threshold, setThreshold]         = useState(() => parseInt(localStorage.getItem("voiceThreshold") || "70"));
  const [showEnroll, setShowEnroll]       = useState(false);
  const [inputMode, setInputMode]         = useState("upload"); // "upload" | "record"
  const [name, setName]                   = useState("");
  const [file, setFile]                   = useState(null);
  const [enrolling, setEnrolling]         = useState(false);
  const [message, setMessage]             = useState(null);
  const fileRef = useRef(null);

  const fetchSpeakers = async () => {
    try {
      const res = await axios.get(`${API}/speakers`);
      setSpeakers(res.data);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchSpeakers(); }, []);

  const handleThresholdChange = (v) => {
    setThreshold(v);
    localStorage.setItem("voiceThreshold", String(v));
  };

  const handleEnroll = async (e) => {
    e.preventDefault();
    if (!name.trim() || !file) return;
    setEnrolling(true);
    setMessage(null);
    const fd = new FormData();
    fd.append("name", name.trim());
    fd.append("audio", file);
    try {
      await axios.post(`${API}/speakers/enroll`, fd);
      setMessage({ type: "success", text: `Voice profile saved for ${name}` });
      setName("");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      setShowEnroll(false);
      fetchSpeakers();
    } catch (err) {
      setMessage({ type: "error", text: err.response?.data?.detail || "Enrollment failed" });
    } finally {
      setEnrolling(false);
    }
  };

  const handleDelete = async (speakerName) => {
    if (!confirm(`Delete voice profile for "${speakerName}"?`)) return;
    try {
      await axios.delete(`${API}/speakers/${encodeURIComponent(speakerName)}`);
      fetchSpeakers();
    } catch { alert("Delete failed"); }
  };

  const filtered = speakers.filter(sp => sp.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="p-8 max-w-4xl mx-auto min-h-screen" style={{ background: "var(--bg)" }}>

      {/* ── Header ── */}
      <motion.div className="mb-8" initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold leading-none" style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)", letterSpacing: "-0.03em" }}>
              Speaker Profiles
            </h1>
            <p className="text-sm mt-1" style={{ color: "var(--ink2)" }}>
              Manage voice signatures and identification accuracy
            </p>
          </div>
          <motion.button
            onClick={() => { setShowEnroll(true); setMessage(null); }}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold text-white shrink-0"
            style={{ background: "var(--primary)", fontFamily: "Syne, sans-serif" }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4z M19 10a7 7 0 01-14 0" />
            </svg>
            Enroll New Speaker
          </motion.button>
        </div>
      </motion.div>

      {/* ── Global message ── */}
      <AnimatePresence>
        {message && (
          <motion.div
            className="mb-6 px-4 py-3 rounded-xl text-sm"
            style={{
              background: message.type === "success" ? "rgba(42,157,110,0.1)" : "rgba(230,57,70,0.08)",
              border: `1px solid ${message.type === "success" ? "rgba(42,157,110,0.25)" : "rgba(230,57,70,0.25)"}`,
              color: message.type === "success" ? "var(--success)" : "var(--danger)",
            }}
            initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
          >
            {message.text}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Enrollment Wizard ── */}
      <AnimatePresence>
        {showEnroll && (
          <motion.div
            className="rounded-2xl border p-6 mb-8 overflow-hidden"
            style={{ background: "var(--surface)", borderColor: "var(--primary)", boxShadow: "0 0 0 1px rgba(230,57,70,0.15), 0 4px 24px var(--shadow-lift)" }}
            initial={{ opacity: 0, y: -12, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-base font-bold" style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)" }}>
                  Enrollment Wizard
                </h2>
                {name && (
                  <p className="text-xs mt-0.5" style={{ color: "var(--ink3)" }}>
                    Enrolling: <span style={{ color: "var(--primary)" }}>{name}</span>
                  </p>
                )}
              </div>
              <button onClick={() => setShowEnroll(false)} style={{ color: "var(--ink3)" }}>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleEnroll}>
              {/* Name */}
              <div className="mb-5">
                <label className="block text-xs font-bold mb-1.5 uppercase tracking-wider" style={{ color: "var(--ink2)", fontFamily: "Syne, sans-serif" }}>
                  Speaker Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Sarah Chen"
                  required
                  className="w-full rounded-xl px-3 py-2.5 text-sm outline-none transition-colors"
                  style={{ background: "var(--surface2)", border: "1.5px solid var(--border)", color: "var(--ink)" }}
                  onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                  onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                />
              </div>

              {/* Sample text prompt */}
              <div className="rounded-xl p-4 mb-4" style={{ background: "var(--surface2)", border: "1px solid var(--border)" }}>
                <p className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: "var(--ink3)", fontFamily: "Syne, sans-serif" }}>
                  Sample text — read aloud for best accuracy
                </p>
                <p className="text-sm leading-relaxed italic" style={{ color: "var(--ink2)" }}>
                  "{SAMPLE_TEXT}"
                </p>
              </div>

              {/* Voice sample: Upload / Record tab switcher */}
              <div className="mb-5">
                <label className="block text-xs font-bold mb-2 uppercase tracking-wider" style={{ color: "var(--ink2)", fontFamily: "Syne, sans-serif" }}>
                  Voice Sample (15–20 sec)
                </label>

                {/* Tab row */}
                <div className="flex gap-1 p-1 rounded-xl mb-3" style={{ background: "var(--surface2)" }}>
                  {[
                    { key: "upload", label: "Upload File", icon: (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    )},
                    { key: "record", label: "Record Live", icon: (
                      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4z" />
                        <path d="M19 10a1 1 0 10-2 0 5 5 0 01-10 0 1 1 0 10-2 0 7 7 0 0013 .83V10zm-7 9a1 1 0 011 1v2a1 1 0 11-2 0v-2a1 1 0 011-1z" />
                      </svg>
                    )},
                  ].map(({ key, label, icon }) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => { setInputMode(key); setFile(null); if (fileRef.current) fileRef.current.value = ""; }}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold relative transition-colors"
                      style={{
                        background: inputMode === key ? "var(--surface)" : "transparent",
                        color: inputMode === key ? "var(--ink)" : "var(--ink3)",
                        fontFamily: "Syne, sans-serif",
                        boxShadow: inputMode === key ? "0 1px 3px var(--shadow)" : "none",
                      }}
                    >
                      {icon}
                      {label}
                      {key === "record" && inputMode !== "record" && (
                        <span className="w-1.5 h-1.5 rounded-full ml-0.5" style={{ background: "var(--primary)" }} />
                      )}
                    </button>
                  ))}
                </div>

                {/* Upload input */}
                <AnimatePresence mode="wait">
                  {inputMode === "upload" ? (
                    <motion.div
                      key="upload"
                      initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                      transition={{ duration: 0.18 }}
                    >
                      <input
                        ref={fileRef}
                        type="file"
                        accept="audio/*,.wav,.mp3,.m4a"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                        className="w-full rounded-xl px-3 py-2.5 text-sm outline-none"
                        style={{ background: "var(--surface2)", border: "1.5px solid var(--border)", color: "var(--ink3)" }}
                      />
                      {file && (
                        <p className="text-xs mt-1.5 font-medium" style={{ color: "var(--success)" }}>
                          ✓ {file.name}
                        </p>
                      )}
                    </motion.div>
                  ) : (
                    <motion.div
                      key="record"
                      className="rounded-xl border overflow-hidden"
                      style={{ background: "var(--surface2)", borderColor: "var(--border)" }}
                      initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                      transition={{ duration: 0.18 }}
                    >
                      <LiveRecorder
                        onRecordingComplete={(f) => setFile(f)}
                      />
                      {file && (
                        <p className="text-xs px-4 pb-3 font-medium" style={{ color: "var(--success)" }}>
                          ✓ Recording ready — {(file.size / 1024).toFixed(0)} KB captured
                        </p>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="flex items-center gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowEnroll(false)}
                  className="px-4 py-2 rounded-xl text-sm font-medium"
                  style={{ color: "var(--ink2)", background: "var(--surface2)" }}
                >
                  Cancel
                </button>
                <motion.button
                  type="submit"
                  disabled={enrolling || !name.trim() || !file}
                  className="flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-bold text-white"
                  style={{
                    background: enrolling || !name.trim() || !file ? "var(--border)" : "var(--primary)",
                    color: enrolling || !name.trim() || !file ? "var(--ink3)" : "white",
                    fontFamily: "Syne, sans-serif",
                    cursor: enrolling || !name.trim() || !file ? "not-allowed" : "pointer",
                  }}
                  whileHover={!enrolling && name.trim() && file ? { scale: 1.02 } : {}}
                  whileTap={!enrolling && name.trim() && file ? { scale: 0.97 } : {}}
                >
                  {enrolling ? "Saving..." : "Save Profile"}
                </motion.button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Search ── */}
      <motion.div
        className="rounded-2xl border p-4 mb-6"
        style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 1px 4px var(--shadow)" }}
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4 }}
      >
        <div className="flex items-center gap-3">
          <svg className="w-4 h-4 shrink-0" style={{ color: "var(--ink3)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search speakers..."
            className="flex-1 text-sm bg-transparent outline-none"
            style={{ color: "var(--ink)" }}
          />
          {search && (
            <button onClick={() => setSearch("")} style={{ color: "var(--ink3)" }}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </motion.div>

      {/* ── Voice Matching Threshold ── */}
      <motion.div
        className="rounded-2xl border p-5 mb-6"
        style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 1px 4px var(--shadow)" }}
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15, duration: 0.4 }}
      >
        <div className="flex items-center justify-between mb-1">
          <div>
            <h3 className="text-sm font-bold" style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)" }}>
              Voice Matching Threshold
            </h3>
            <p className="text-xs mt-0.5" style={{ color: "var(--ink3)" }}>
              Higher values reduce false matches but may increase "Unknown Speaker" occurrences
            </p>
          </div>
          <span className="text-lg font-bold tabular-nums" style={{ color: "var(--primary)", fontFamily: "Syne, sans-serif" }}>
            {threshold}%
          </span>
        </div>
        <div className="mt-3 relative">
          <input
            type="range"
            min="0"
            max="100"
            value={threshold}
            onChange={(e) => handleThresholdChange(parseInt(e.target.value))}
            className="w-full h-1.5 rounded-full appearance-none outline-none"
            style={{
              background: `linear-gradient(to right, var(--primary) 0%, var(--primary) ${threshold}%, var(--surface2) ${threshold}%, var(--surface2) 100%)`,
              WebkitAppearance: "none",
            }}
          />
          <div className="flex justify-between mt-1.5">
            {["0%", "25%", "50%", "75%", "100%"].map(l => (
              <span key={l} className="text-[10px]" style={{ color: "var(--ink3)" }}>{l}</span>
            ))}
          </div>
        </div>
      </motion.div>

      {/* ── Speaker Cards ── */}
      {filtered.length === 0 ? (
        <motion.div
          className="rounded-2xl border p-16 text-center"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        >
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-3" style={{ background: "var(--surface2)" }}>
            <svg className="w-7 h-7" style={{ color: "var(--ink3)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <p className="text-sm font-medium" style={{ color: "var(--ink2)" }}>
            {search ? `No speakers matching "${search}"` : "No voice profiles enrolled yet"}
          </p>
          {!search && (
            <p className="text-xs mt-1" style={{ color: "var(--ink3)" }}>
              Click "Enroll New Speaker" to add voice profiles for speaker identification
            </p>
          )}
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <AnimatePresence>
            {filtered.map((sp, i) => {
              const color = avatarColor(sp.name);
              const initials = getInitials(sp.name);
              return (
                <motion.div
                  key={sp.name}
                  className="rounded-2xl border p-5 flex flex-col items-center gap-3 relative"
                  style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 1px 4px var(--shadow)" }}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: i * 0.05, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                  whileHover={{ y: -2, boxShadow: "0 8px 32px var(--shadow-lift)" }}
                >
                  {/* Enrolled badge */}
                  <span
                    className="absolute top-3 right-3 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
                    style={{ background: "rgba(42,157,110,0.12)", color: "var(--success)", fontFamily: "Syne, sans-serif" }}
                  >
                    Enrolled
                  </span>

                  {/* Avatar */}
                  <div
                    className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold text-white shrink-0"
                    style={{ background: color, boxShadow: `0 0 0 3px ${color}30` }}
                  >
                    {initials}
                  </div>

                  <div className="text-center">
                    <h3 className="font-bold text-sm" style={{ color: "var(--ink)", fontFamily: "Syne, sans-serif" }}>
                      {sp.name.replace(/_/g, " ")}
                    </h3>
                    <p className="text-xs mt-0.5" style={{ color: "var(--ink3)" }}>
                      Voice profile active
                    </p>
                  </div>

                  <div className="flex gap-2 mt-1 w-full">
                    <button
                      onClick={() => { setName(sp.name.replace(/_/g, " ")); setShowEnroll(true); setMessage(null); }}
                      className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-colors"
                      style={{ color: "var(--primary)", background: "rgba(230,57,70,0.08)", border: "1px solid rgba(230,57,70,0.15)" }}
                    >
                      Re-enroll
                    </button>
                    <button
                      onClick={() => handleDelete(sp.name)}
                      className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-colors"
                      style={{ color: "var(--ink3)", background: "var(--surface2)" }}
                    >
                      Delete
                    </button>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}

      {/* Slider thumb styling */}
      <style>{`
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: var(--primary);
          cursor: pointer;
          border: 2px solid white;
          box-shadow: 0 1px 4px rgba(230,57,70,0.4);
        }
        input[type="range"]::-moz-range-thumb {
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: var(--primary);
          cursor: pointer;
          border: 2px solid white;
        }
      `}</style>
    </div>
  );
}
