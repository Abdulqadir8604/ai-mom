import { motion } from "framer-motion";

export default function SpeakerChip({ name, color = "#E63946" }) {
  const initials = name
    .split(/[_ ]+/)
    .map((w) => w[0] || "")
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <motion.div
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium"
      style={{
        background: color + "1A",
        border: `1px solid ${color}40`,
        color,
        fontFamily: "DM Sans, sans-serif",
      }}
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 20 }}
    >
      <span
        className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold text-white shrink-0"
        style={{ background: color }}
      >
        {initials}
      </span>
      <span>{name}</span>
    </motion.div>
  );
}
