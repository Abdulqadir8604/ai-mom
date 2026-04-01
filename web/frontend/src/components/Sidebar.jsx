import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { useTheme } from "../hooks/useTheme";

const links = [
  { to: "/", label: "Dashboard", icon: DashboardIcon },
  { to: "/speakers", label: "Speakers", icon: SpeakersIcon },
  { to: "/docs", label: "Docs", icon: DocsIcon },
];

function DashboardIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  );
}

function SpeakersIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function DocsIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="5" strokeWidth={2} />
      <path strokeLinecap="round" strokeWidth={2}
        d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
    </svg>
  );
}

export default function Sidebar() {
  const { dark, toggle } = useTheme();

  return (
    <aside
      className="w-56 flex flex-col shrink-0 border-r"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border)",
        transition: "background 0.3s ease, border-color 0.3s ease",
      }}
    >
      {/* Logo */}
      <div className="h-14 flex items-center px-5 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-white font-display font-bold text-xs"
            style={{ background: "var(--primary)" }}
          >
            <span style={{ fontFamily: "Syne, sans-serif", letterSpacing: "-0.02em" }}>AI</span>
          </div>
          <div>
            <div
              className="text-sm font-bold leading-none"
              style={{
                fontFamily: "Syne, sans-serif",
                color: "var(--ink)",
                letterSpacing: "-0.02em",
              }}
            >
              MOM
            </div>
            <div className="text-[10px] leading-none mt-0.5" style={{ color: "var(--ink3)", letterSpacing: "0.05em" }}>
              MINUTES
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className="block"
          >
            {({ isActive }) => (
              <motion.div
                className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium cursor-pointer"
                style={{
                  background: isActive ? "rgba(230,57,70,0.1)" : "transparent",
                  color: isActive ? "var(--primary)" : "var(--ink2)",
                }}
                whileHover={{
                  background: isActive ? "rgba(230,57,70,0.1)" : "var(--surface2)",
                  color: isActive ? "var(--primary)" : "var(--ink)",
                }}
                whileTap={{ scale: 0.98 }}
                transition={{ duration: 0.12 }}
              >
                <link.icon />
                <span style={{ fontFamily: "DM Sans, sans-serif" }}>{link.label}</span>
                {isActive && (
                  <motion.div
                    layoutId="sidebar-indicator"
                    className="ml-auto w-1.5 h-1.5 rounded-full"
                    style={{ background: "var(--primary)" }}
                  />
                )}
              </motion.div>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer: theme toggle + version */}
      <div className="px-4 py-4 border-t space-y-3" style={{ borderColor: "var(--border)" }}>
        {/* Theme toggle */}
        <motion.button
          onClick={toggle}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm"
          style={{ color: "var(--ink2)" }}
          whileHover={{ background: "var(--surface2)", color: "var(--ink)" }}
          whileTap={{ scale: 0.97 }}
          transition={{ duration: 0.12 }}
          title={dark ? "Switch to light mode" : "Switch to dark mode"}
        >
          <motion.div
            key={dark ? "moon" : "sun"}
            initial={{ rotate: -30, opacity: 0 }}
            animate={{ rotate: 0, opacity: 1 }}
            transition={{ duration: 0.2 }}
          >
            {dark ? <SunIcon /> : <MoonIcon />}
          </motion.div>
          <span>{dark ? "Light mode" : "Dark mode"}</span>
        </motion.button>

        <p className="text-[10px] px-3" style={{ color: "var(--ink3)", letterSpacing: "0.04em" }}>
          AI MOM v1.0
        </p>
      </div>
    </aside>
  );
}
