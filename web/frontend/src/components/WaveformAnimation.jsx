/**
 * WaveformAnimation — animated audio bars.
 * active: bars animate; idle: bars are static/flat.
 */
export default function WaveformAnimation({ active = true, bars = 8, color = "var(--primary)", height = 24, className = "" }) {
  const delays = [0, 0.1, 0.2, 0.3, 0.4, 0.3, 0.2, 0.1, 0, 0.1, 0.2, 0.3];

  return (
    <div
      className={`flex items-center gap-[3px] ${className}`}
      style={{ height }}
      aria-hidden="true"
    >
      {Array.from({ length: bars }).map((_, i) => (
        <div
          key={i}
          className="wave-bar"
          style={{
            height: active ? "100%" : "30%",
            background: color,
            animation: active
              ? `wave 1.4s ease-in-out ${delays[i % delays.length]}s infinite`
              : "none",
            transition: "height 0.3s ease",
            opacity: active ? 1 : 0.3,
          }}
        />
      ))}
    </div>
  );
}
