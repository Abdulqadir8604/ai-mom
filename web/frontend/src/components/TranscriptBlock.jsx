import { motion } from "framer-motion";
import SpeakerChip from "./SpeakerChip";

const SPEAKER_COLORS = [
  "#E63946", "#2EC4B6", "#F4A261", "#818CF8", "#4CC9F0",
  "#7209B7", "#F72585", "#3A86FF", "#06D6A0", "#FFB703",
];

function formatTime(seconds) {
  if (seconds == null) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function TranscriptBlock({ segments }) {
  if (!segments || segments.length === 0) {
    return <p className="text-sm" style={{ color: "var(--ink3)" }}>No transcript segments available.</p>;
  }

  const speakers = [...new Set(segments.map((s) => s.speaker || s.speaker_label || "Unknown"))];
  const colorMap = {};
  speakers.forEach((sp, i) => { colorMap[sp] = SPEAKER_COLORS[i % SPEAKER_COLORS.length]; });

  return (
    <div className="space-y-3 overflow-y-auto pr-1" style={{ maxHeight: "600px" }}>
      {segments.map((seg, i) => {
        const speaker = seg.speaker || seg.speaker_label || "Unknown";
        return (
          <motion.div
            key={i}
            className="flex gap-3"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.02, 0.4), duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="shrink-0 pt-0.5">
              <SpeakerChip name={speaker} color={colorMap[speaker]} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-xs tabular-nums" style={{ color: "var(--ink3)", fontFamily: "Syne, sans-serif" }}>
                  {formatTime(seg.start)}
                  {seg.end != null && ` — ${formatTime(seg.end)}`}
                </span>
              </div>
              <p className="text-sm leading-relaxed" style={{ color: "var(--ink2)" }}>
                {seg.text || seg.correct_text || ""}
              </p>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
