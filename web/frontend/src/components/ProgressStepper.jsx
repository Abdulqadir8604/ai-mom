import { motion, AnimatePresence, useReducedMotion } from "framer-motion";

const STEPS = [
  { key: "loading",     label: "Load",      icon: "🔧" },
  { key: "transcribing",label: "Transcribe", icon: "🎙" },
  { key: "diarizing",   label: "Diarize",   icon: "👥" },
  { key: "summarizing", label: "Summarize", icon: "✨" },
];

const ORDER = ["queued","loading","transcribing","diarizing","summarizing","complete"];

export default function ProgressStepper({ status }) {
  const currentIdx  = ORDER.indexOf(status);
  const prefersReduced = useReducedMotion();
  const isFailed    = status === "failed";

  return (
    <div className="flex items-center gap-0">
      {STEPS.map((step, i) => {
        const stepIdx = ORDER.indexOf(step.key);
        const isActive = status === step.key;
        const isDone   = currentIdx > stepIdx;

        return (
          <div key={step.key} className="flex items-center" style={{ flex: i < STEPS.length - 1 ? "1 1 auto" : "0 0 auto" }}>
            <div className="flex flex-col items-center gap-1.5">
              {/* Circle */}
              <motion.div
                className="relative w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold"
                style={{
                  background: isDone
                    ? "var(--success)"
                    : isActive
                    ? isFailed ? "var(--danger)" : "var(--primary)"
                    : "var(--surface2)",
                  border: isDone || isActive ? "none" : "2px solid var(--border)",
                  color: isDone || isActive ? "white" : "var(--ink3)",
                  boxShadow: isActive && !isFailed && !prefersReduced
                    ? "0 0 0 0 rgba(230,57,70,0.4)"
                    : "none",
                  fontFamily: "Syne, sans-serif",
                }}
                animate={
                  prefersReduced ? {} :
                  isDone   ? { scale: [1, 1.18, 1] } :
                  isActive && !isFailed ? {
                    boxShadow: [
                      "0 0 0 0 rgba(230,57,70,0.4)",
                      "0 0 0 8px rgba(230,57,70,0)",
                      "0 0 0 0 rgba(230,57,70,0)",
                    ],
                  } : { scale: 1 }
                }
                transition={
                  isDone  ? { duration: 0.35, ease: [0.16,1,0.3,1] } :
                  isActive ? { duration: 1.8, repeat: Infinity, ease: "easeOut" } :
                  { duration: 0.2 }
                }
              >
                <AnimatePresence mode="wait" initial={false}>
                  {isDone ? (
                    <motion.svg
                      key="check"
                      className="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      initial={{ opacity: 0, scale: 0.5 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.2 }}
                    >
                      <motion.path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={3}
                        d="M5 13l4 4L19 7"
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        transition={prefersReduced ? { duration: 0 } : { duration: 0.4, ease: [0.65, 0, 0.35, 1] }}
                      />
                    </motion.svg>
                  ) : (
                    <motion.span
                      key="num"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="text-xs"
                    >
                      {i + 1}
                    </motion.span>
                  )}
                </AnimatePresence>
              </motion.div>

              {/* Label */}
              <motion.span
                className="text-[10px] font-semibold uppercase tracking-wider"
                style={{
                  fontFamily: "Syne, sans-serif",
                  color: isDone ? "var(--success)" : isActive ? "var(--primary)" : "var(--ink3)",
                }}
                transition={{ duration: 0.3 }}
              >
                {step.label}
              </motion.span>
            </div>

            {/* Connector */}
            {i < STEPS.length - 1 && (
              <div
                className="flex-1 h-0.5 mx-2 rounded-full overflow-hidden"
                style={{ background: "var(--border)", minWidth: "32px" }}
              >
                <motion.div
                  className="h-full origin-left"
                  style={{ background: "var(--success)" }}
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: isDone ? 1 : 0 }}
                  transition={prefersReduced ? { duration: 0 } : { duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
