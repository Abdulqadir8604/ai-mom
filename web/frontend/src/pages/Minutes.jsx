import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import TranscriptBlock from "../components/TranscriptBlock";
import SpeakerChip from "../components/SpeakerChip";
import WaveformAnimation from "../components/WaveformAnimation";

const API = import.meta.env.VITE_API_URL || "/api";

const SPEAKER_COLORS = [
  "#E63946", "#2EC4B6", "#F4A261", "#818CF8", "#4CC9F0",
  "#7209B7", "#F72585", "#3A86FF", "#06D6A0", "#FFB703",
];

function formatDuration(seconds) {
  if (!seconds) return "--";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

/* ── Animated CollapsibleCard ── */
function CollapsibleCard({ title, children, defaultOpen = true, delay = 0, accent }) {
  const [open, setOpen] = useState(defaultOpen);
  const prefersReduced = useReducedMotion();

  return (
    <motion.div
      className="rounded-2xl border overflow-hidden mb-4"
      style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 1px 4px var(--shadow)" }}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={prefersReduced ? { duration: 0 } : { delay, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-5 py-3.5 flex items-center justify-between text-left transition-colors"
        style={{ borderBottom: open ? "1px solid var(--border)" : "none" }}
      >
        <div className="flex items-center gap-2.5">
          {accent && (
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: accent }}
            />
          )}
          <h3 className="text-sm font-bold" style={{ fontFamily: "Syne, sans-serif", color: "var(--ink)" }}>
            {title}
          </h3>
        </div>
        <motion.svg
          className="w-4 h-4 shrink-0"
          style={{ color: "var(--ink3)" }}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </motion.svg>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            style={{ overflow: "hidden" }}
          >
            <div className="px-5 py-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Animated talk-time bar ── */
function TalkBar({ pct, color, delay }) {
  return (
    <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: "var(--surface2)" }}>
      <motion.div
        className="h-full rounded-full"
        style={{ background: color }}
        initial={{ width: "0%" }}
        animate={{ width: `${pct}%` }}
        transition={{ delay, type: "spring", stiffness: 60, damping: 18 }}
      />
    </div>
  );
}

/* ── Bullet list item with stagger ── */
function BulletItem({ children, icon, color, index }) {
  const prefersReduced = useReducedMotion();
  return (
    <motion.li
      className="flex gap-2.5 text-sm leading-relaxed"
      style={{ color: "var(--ink2)" }}
      initial={prefersReduced ? {} : { opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.05 * index, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
    >
      <span className="shrink-0 mt-0.5 font-bold" style={{ color }}>{icon}</span>
      <span>{children}</span>
    </motion.li>
  );
}

export default function Minutes() {
  const { jobId } = useParams();
  const nav = useNavigate();
  const prefersReduced = useReducedMotion();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await axios.get(`${API}/minutes/${jobId}`);
        setData(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load minutes");
      } finally {
        setLoading(false);
      }
    })();
  }, [jobId]);

  const handleDownloadMd = async () => {
    try {
      const res = await axios.get(`${API}/minutes/${jobId}/markdown`, { responseType: "text" });
      const blob = new Blob([res.data], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${data?.title || "minutes"}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Markdown file not available");
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-6xl mx-auto flex items-center gap-3 pt-24">
        <WaveformAnimation active bars={6} height={24} color="var(--ink3)" />
        <span className="text-sm" style={{ color: "var(--ink3)" }}>Loading minutes...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-6xl mx-auto">
        <div
          className="rounded-2xl p-6 text-sm"
          style={{ background: "rgba(230,57,70,0.08)", border: "1px solid rgba(230,57,70,0.2)", color: "var(--danger)" }}
        >
          {error}
        </div>
      </div>
    );
  }

  const speakerTimes = data?.speaker_times || {};
  const speakers = Object.keys(speakerTimes);
  const maxTime = Math.max(...Object.values(speakerTimes), 1);
  const attendance = data?.attendance || {};
  const segments = data?.segments || [];

  return (
    <div className="p-8 max-w-6xl mx-auto min-h-screen" style={{ background: "var(--bg)" }}>

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
              {data?.title || "Meeting Minutes"}
            </h1>
            <div className="flex items-center gap-4 mt-2 flex-wrap">
              {data?.date && (
                <span className="text-sm" style={{ color: "var(--ink3)" }}>{data.date}</span>
              )}
              {data?.language && (
                <span
                  className="text-xs font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider"
                  style={{ background: "rgba(230,57,70,0.1)", color: "var(--primary)", fontFamily: "Syne, sans-serif" }}
                >
                  {data.language}
                </span>
              )}
              {data?.duration_seconds && (
                <span className="text-sm" style={{ color: "var(--ink3)" }}>
                  {formatDuration(data.duration_seconds)}
                </span>
              )}
            </div>
          </div>

          <motion.button
            onClick={handleDownloadMd}
            className="shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold text-white"
            style={{
              background: "var(--primary)",
              fontFamily: "Syne, sans-serif",
              letterSpacing: "0.02em",
            }}
            whileHover={{ scale: 1.02, filter: "brightness(1.05)" }}
            whileTap={{ scale: 0.97 }}
            initial={prefersReduced ? {} : { opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3, duration: 0.4, ease: [0, 0, 0.2, 1] }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download MD
          </motion.button>
        </div>
      </motion.div>

      {/* ── Two-column layout ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left: Summary content */}
        <div className="lg:col-span-2">

          {data?.session_summary && (
            <CollapsibleCard title="Session Summary" delay={0.1} accent="var(--primary)">
              <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--ink2)" }}>
                {data.session_summary}
              </p>
            </CollapsibleCard>
          )}

          {data?.key_decisions?.length > 0 && (
            <CollapsibleCard title="Key Decisions" delay={0.18} accent="var(--gold)">
              <ul className="space-y-2">
                {data.key_decisions.map((item, i) => (
                  <BulletItem key={i} index={i} icon="◆" color="var(--gold)">
                    {typeof item === "string" ? item : item.decision || JSON.stringify(item)}
                  </BulletItem>
                ))}
              </ul>
            </CollapsibleCard>
          )}

          {data?.action_items?.length > 0 && (
            <CollapsibleCard title="Action Items" delay={0.26} accent="var(--primary)">
              {data.action_items[0]?.owner || data.action_items[0]?.due ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b" style={{ borderColor: "var(--border)" }}>
                        {["Owner", "Action", "Due"].map(h => (
                          <th key={h} className="text-left py-2 pr-4 text-xs font-bold uppercase tracking-wider" style={{ color: "var(--ink3)", fontFamily: "Syne, sans-serif" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data.action_items.map((item, i) => (
                        <motion.tr
                          key={i}
                          className="border-b"
                          style={{ borderColor: "var(--surface2)" }}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.05 * i }}
                        >
                          <td className="py-2.5 pr-4 font-medium text-xs whitespace-nowrap" style={{ color: "var(--primary)", fontFamily: "Syne, sans-serif" }}>
                            {item.owner || "—"}
                          </td>
                          <td className="py-2.5 pr-4" style={{ color: "var(--ink2)" }}>
                            {item.action || item.task || (typeof item === "string" ? item : JSON.stringify(item))}
                          </td>
                          <td className="py-2.5 whitespace-nowrap text-xs" style={{ color: "var(--ink3)" }}>
                            {item.due || "—"}
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <ul className="space-y-2">
                  {data.action_items.map((item, i) => (
                    <BulletItem key={i} index={i} icon="▶" color="var(--primary)">
                      {typeof item === "string" ? item : item.action || item.task || JSON.stringify(item)}
                    </BulletItem>
                  ))}
                </ul>
              )}
            </CollapsibleCard>
          )}

          {data?.next_steps?.length > 0 && (
            <CollapsibleCard title="Next Steps" delay={0.34} accent="var(--success)">
              <ul className="space-y-2">
                {data.next_steps.map((item, i) => (
                  <BulletItem key={i} index={i} icon="→" color="var(--success)">
                    {typeof item === "string" ? item : JSON.stringify(item)}
                  </BulletItem>
                ))}
              </ul>
            </CollapsibleCard>
          )}

          {data?.qa_pairs?.length > 0 && (
            <CollapsibleCard title="Q&A" defaultOpen={false} delay={0.42} accent="#818CF8">
              <div className="space-y-4">
                {data.qa_pairs.map((qa, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.04 * i }}
                  >
                    <p className="text-sm font-semibold" style={{ color: "var(--primary)", fontFamily: "Syne, sans-serif" }}>
                      Q: {typeof qa === "string" ? qa : qa.question || ""}
                    </p>
                    {qa.answer && (
                      <p className="text-sm mt-1 pl-4 border-l-2" style={{ color: "var(--ink2)", borderColor: "var(--border)" }}>
                        A: {qa.answer}
                      </p>
                    )}
                  </motion.div>
                ))}
              </div>
            </CollapsibleCard>
          )}

          {/* Transcript */}
          <CollapsibleCard title="Full Transcript" defaultOpen={false} delay={0.5} accent="var(--ink3)">
            <TranscriptBlock segments={segments} />
            {!segments.length && data?.transcript && (
              <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--ink2)" }}>
                {data.transcript}
              </p>
            )}
          </CollapsibleCard>
        </div>

        {/* Right: Speaker stats + attendance */}
        <div>

          {speakers.length > 0 && (
            <CollapsibleCard title="Speaker Talk Time" delay={0.15} accent="var(--primary)">
              <div className="space-y-4">
                {speakers.map((sp, i) => {
                  const secs = speakerTimes[sp] || 0;
                  const pct = (secs / maxTime) * 100;
                  const color = SPEAKER_COLORS[i % SPEAKER_COLORS.length];
                  return (
                    <div key={sp}>
                      <div className="flex items-center justify-between mb-1.5">
                        <SpeakerChip name={sp} color={color} />
                        <span className="text-xs tabular-nums" style={{ color: "var(--ink3)", fontFamily: "Syne, sans-serif" }}>
                          {formatDuration(secs)}
                          <span className="text-xs" style={{ color: "var(--ink3)" }}> · {Math.round((secs / (data.duration_seconds || 1)) * 100)}%</span>
                        </span>
                      </div>
                      <TalkBar pct={pct} color={color} delay={0.1 + i * 0.08} />
                    </div>
                  );
                })}
              </div>
            </CollapsibleCard>
          )}

          {Object.keys(attendance).length > 0 && (
            <CollapsibleCard title="Attendance" delay={0.22} accent="var(--success)">
              <div className="space-y-3">
                {attendance.present?.length > 0 && (
                  <div>
                    <h4 className="text-[10px] font-bold mb-2 uppercase tracking-wider" style={{ color: "var(--success)", fontFamily: "Syne, sans-serif" }}>
                      Present
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {attendance.present.map((name, i) => (
                        <motion.span
                          key={name}
                          className="px-2 py-0.5 rounded-lg text-xs font-medium"
                          style={{ background: "rgba(42,157,110,0.1)", color: "var(--success)", border: "1px solid rgba(42,157,110,0.2)" }}
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.04 * i, type: "spring", stiffness: 400, damping: 20 }}
                        >
                          {name}
                        </motion.span>
                      ))}
                    </div>
                  </div>
                )}
                {attendance.absent?.length > 0 && (
                  <div>
                    <h4 className="text-[10px] font-bold mb-2 uppercase tracking-wider" style={{ color: "var(--danger)", fontFamily: "Syne, sans-serif" }}>
                      Absent
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {attendance.absent.map((name, i) => (
                        <motion.span
                          key={name}
                          className="px-2 py-0.5 rounded-lg text-xs font-medium"
                          style={{ background: "rgba(230,57,70,0.08)", color: "var(--danger)", border: "1px solid rgba(230,57,70,0.2)" }}
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.04 * i, type: "spring", stiffness: 400, damping: 20 }}
                        >
                          {name}
                        </motion.span>
                      ))}
                    </div>
                  </div>
                )}
                {attendance.unknown?.length > 0 && (
                  <div>
                    <h4 className="text-[10px] font-bold mb-2 uppercase tracking-wider" style={{ color: "var(--gold)", fontFamily: "Syne, sans-serif" }}>
                      Unknown
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {attendance.unknown.map((name, i) => (
                        <motion.span
                          key={name}
                          className="px-2 py-0.5 rounded-lg text-xs font-medium"
                          style={{ background: "rgba(244,162,97,0.1)", color: "var(--gold)", border: "1px solid rgba(244,162,97,0.2)" }}
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.04 * i, type: "spring", stiffness: 400, damping: 20 }}
                        >
                          {name}
                        </motion.span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CollapsibleCard>
          )}

          {data?.attendees?.length > 0 && Object.keys(attendance).length === 0 && (
            <CollapsibleCard title="Attendees" delay={0.22} accent="var(--primary)">
              <div className="flex flex-wrap gap-1.5">
                {data.attendees.map((name, i) => (
                  <motion.span
                    key={name}
                    className="px-2 py-0.5 rounded-lg text-xs font-medium"
                    style={{ background: "rgba(230,57,70,0.08)", color: "var(--primary)", border: "1px solid rgba(230,57,70,0.2)" }}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.04 * i, type: "spring", stiffness: 400, damping: 20 }}
                  >
                    {name}
                  </motion.span>
                ))}
              </div>
            </CollapsibleCard>
          )}
        </div>
      </div>
    </div>
  );
}
