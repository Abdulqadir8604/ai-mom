import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import WaveformAnimation from "./WaveformAnimation";

const API = import.meta.env.VITE_API_URL || "/api";

const STATUS_CONFIG = {
  queued:      { color: "var(--ink3)",     bg: "var(--surface2)", label: "Queued"       },
  loading:     { color: "#F4A261",         bg: "rgba(244,162,97,0.12)", label: "Loading" },
  transcribing:{ color: "var(--primary)",bg: "rgba(230,57,70,0.12)", label: "Transcribing", wave: true },
  diarizing:   { color: "#818CF8",         bg: "rgba(129,140,248,0.12)", label: "Diarizing", wave: true },
  summarizing: { color: "var(--gold)",     bg: "rgba(244,162,97,0.12)", label: "Summarizing", wave: true },
  complete:    { color: "var(--success)",  bg: "rgba(42,157,110,0.12)", label: "Complete" },
  failed:      { color: "var(--danger)",   bg: "rgba(230,57,70,0.12)", label: "Failed"   },
};

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function formatDuration(seconds) {
  if (!seconds) return "—";
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

export default function JobCard({ job, onDelete }) {
  const nav = useNavigate();
  const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.queued;

  const handleView = () => nav(job.status === "complete" ? `/minutes/${job.id}` : `/processing/${job.id}`);

  const handleDelete = async (e) => {
    e.stopPropagation();
    if (!confirm("Delete this job?")) return;
    try {
      await axios.delete(`${API}/jobs/${job.id}`);
      if (onDelete) onDelete(job.id);
    } catch { /* ignore */ }
  };

  return (
    <motion.tr
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20, transition: { duration: 0.2 } }}
      transition={{
        layout:  { type: "spring", stiffness: 300, damping: 30 },
        opacity: { duration: 0.25 },
        y:       { duration: 0.3, ease: [0.16, 1, 0.3, 1] },
      }}
      className="border-b cursor-pointer group"
      style={{ borderColor: "var(--border)" }}
      onClick={handleView}
      whileHover={{ backgroundColor: "var(--surface2)" }}
    >
      {/* Title */}
      <td className="px-5 py-3.5">
        <div className="font-semibold text-sm leading-tight" style={{ color: "var(--ink)", fontFamily: "Syne, sans-serif" }}>
          {job.title}
        </div>
        <div className="text-xs mt-0.5 truncate max-w-[180px]" style={{ color: "var(--ink3)" }}>
          {job.filename}
        </div>
      </td>

      {/* Date */}
      <td className="px-5 py-3.5 text-sm" style={{ color: "var(--ink2)" }}>
        {formatDate(job.created_at)}
      </td>

      {/* Duration */}
      <td className="px-5 py-3.5 text-sm" style={{ color: "var(--ink2)" }}>
        {formatDuration(job.duration_seconds)}
      </td>

      {/* Status badge */}
      <td className="px-5 py-3.5">
        <motion.div
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold"
          style={{ color: cfg.color, background: cfg.bg, fontFamily: "Syne, sans-serif", letterSpacing: "0.02em" }}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 20 }}
        >
          {cfg.wave ? (
            <WaveformAnimation active bars={4} height={10} color={cfg.color} />
          ) : (
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: cfg.color, flexShrink: 0 }}
            />
          )}
          {cfg.label}
        </motion.div>
      </td>

      {/* Actions */}
      <td className="px-5 py-3.5">
        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => { e.stopPropagation(); handleView(); }}
            className="text-xs font-medium px-2.5 py-1 rounded-lg transition-colors"
            style={{ color: "var(--primary)", background: "rgba(230,57,70,0.08)" }}
          >
            View
          </button>
          <button
            onClick={handleDelete}
            className="text-xs font-medium px-2.5 py-1 rounded-lg transition-colors"
            style={{ color: "var(--ink3)", background: "var(--surface2)" }}
          >
            Delete
          </button>
        </div>
      </td>
    </motion.tr>
  );
}
