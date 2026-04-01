/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // CSS variable bridge — works in both themes
        bg:        "var(--bg)",
        surface:   "var(--surface)",
        surface2:  "var(--surface2)",
        border:    "var(--border)",
        ink:       "var(--ink)",
        ink2:      "var(--ink2)",
        ink3:      "var(--ink3)",
        primary:   "var(--primary)",
        secondary: "var(--secondary)",
        gold:      "var(--gold)",
      },
      fontFamily: {
        display: ["Syne", "sans-serif"],
        sans:    ["DM Sans", "system-ui", "sans-serif"],
        mono:    ["JetBrains Mono", "Fira Code", "monospace"],
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        card:   "0 1px 3px 0 var(--shadow), 0 1px 2px -1px var(--shadow)",
        lift:   "0 4px 24px 0 var(--shadow-lift)",
        glow:   "0 0 20px -4px var(--primary)",
        "glow-teal": "0 0 20px -4px var(--secondary)",
      },
      animation: {
        "wave-1":    "wave 1.4s ease-in-out infinite",
        "wave-2":    "wave 1.4s ease-in-out 0.1s infinite",
        "wave-3":    "wave 1.4s ease-in-out 0.2s infinite",
        "wave-4":    "wave 1.4s ease-in-out 0.3s infinite",
        "wave-5":    "wave 1.4s ease-in-out 0.4s infinite",
        "wave-6":    "wave 1.4s ease-in-out 0.5s infinite",
        "wave-7":    "wave 1.4s ease-in-out 0.6s infinite",
        "wave-8":    "wave 1.4s ease-in-out 0.7s infinite",
        "pulse-dot": "pulse-dot 2s ease-in-out infinite",
        "slide-up":  "slide-up 0.6s cubic-bezier(0.16,1,0.3,1) both",
        "fade-in":   "fade-in 0.4s ease both",
        "spin-slow": "spin 3s linear infinite",
        "shimmer":   "shimmer 2s linear infinite",
        "rec-pulse": "rec-pulse 1.4s ease-in-out infinite",
      },
      keyframes: {
        wave: {
          "0%, 100%": { transform: "scaleY(0.3)" },
          "50%":       { transform: "scaleY(1)" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "0.4", transform: "scale(1)" },
          "50%":       { opacity: "1",   transform: "scale(1.15)" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(20px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        shimmer: {
          from: { backgroundPosition: "-400px 0" },
          to:   { backgroundPosition: "400px 0" },
        },
        "rec-pulse": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(230,57,70,0.5)" },
          "50%":       { boxShadow: "0 0 0 8px rgba(230,57,70,0)" },
        },
      },
    },
  },
  plugins: [],
};
