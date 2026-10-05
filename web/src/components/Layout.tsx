import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { GitFork, Moon, Sun } from "lucide-react";
import { useTheme } from "../hooks/useTheme";
import { cn } from "../lib/utils";

function useApiStatus(): "online" | "offline" | "unknown" {
  const [status, setStatus] = useState<"online" | "offline" | "unknown">("unknown");
  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then((res) => {
        if (!cancelled) setStatus(res.ok ? "online" : "offline");
      })
      .catch(() => {
        if (!cancelled) setStatus("offline");
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return status;
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { theme, toggle } = useTheme();
  const api = useApiStatus();
  const location = useLocation();
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    const onScroll = () => setCompact(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const hashActive = (hash: string) =>
    location.pathname === "/" && location.hash === hash;

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-[var(--accent)] focus:px-3 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>
      <header className="cl-nav">
        <div
          className={cn(
            "mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 transition-all",
            compact ? "py-1.5" : "py-2.5",
          )}
        >
          <Link to="/" className="flex items-baseline gap-2 text-[1.05rem] font-semibold tracking-tight">
            ClaimLens
            <span className="hidden font-normal text-[var(--text-2)] sm:inline text-xs">
              research audits
            </span>
          </Link>
          <nav aria-label="Primary" className="flex items-center gap-0.5">
            <NavLink to="/" end className="cl-nav-link hidden sm:inline-block">
              Home
            </NavLink>
            <Link
              to="/#audits"
              aria-current={hashActive("#audits") ? "page" : undefined}
              className="cl-nav-link hidden md:inline-block"
            >
              Audits
            </Link>
            <NavLink to="/demos" className="cl-nav-link hidden sm:inline-block">
              Demos
            </NavLink>
            <Link to="/#how-it-works" className="cl-nav-link hidden lg:inline-block">
              How it works
            </Link>
            <NavLink to="/about" className="cl-nav-link">
              About
            </NavLink>
            <span
              role="status"
              aria-label={api === "online" ? "API connected" : api === "offline" ? "API offline" : "API status unknown"}
              title={api === "online" ? "API connected" : api === "offline" ? "API offline" : "Checking API…"}
              className="ml-1 hidden items-center gap-1.5 rounded-full border border-[var(--border)] px-2 py-1 text-xs text-[var(--text-2)] sm:inline-flex"
            >
              <span
                aria-hidden="true"
                className={cn(
                  "inline-block h-1.5 w-1.5 rounded-full",
                  api === "online" && "bg-[var(--ok)]",
                  api === "offline" && "bg-[var(--bad)]",
                  api === "unknown" && "bg-[var(--muted)]",
                )}
              />
              {api === "online" ? "API Connected" : api === "offline" ? "API Offline" : "API…"}
            </span>
            <a
              href="https://github.com/awdtyo/ClaimLens"
              target="_blank"
              rel="noreferrer"
              aria-label="ClaimLens on GitHub"
              className="ml-1 inline-flex h-9 w-9 items-center justify-center rounded-md text-[var(--text-2)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            >
              <GitFork size={18} aria-hidden="true" />
            </a>
            <button
              type="button"
              onClick={toggle}
              aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              aria-pressed={theme === "dark"}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-[var(--border)] text-[var(--text-2)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            >
              {theme === "dark" ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
            </button>
          </nav>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        {children}
      </main>
      <footer className="border-t border-[var(--border)]">
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-5">
          <p className="text-sm font-medium">ClaimLens</p>
          <p className="cl-meta max-w-2xl">
            ClaimLens performs reduced-scale reproduction experiments. A failed
            reproduction does not automatically prove that the original paper
            is incorrect. Verdicts are computed by the backend; the frontend
            never decides whether results match.
          </p>
        </div>
      </footer>
    </div>
  );
}
