import { Link, NavLink } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "../hooks/useTheme";
import { cn } from "../lib/utils";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/demos", label: "Demos" },
  { to: "/about", label: "About" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { theme, toggle } = useTheme();
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-blue-600 focus:px-3 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>
      <header className="border-b border-gray-200 dark:border-gray-800">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            ClaimLens
          </Link>
          <nav aria-label="Primary" className="flex items-center gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900",
                    "dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100",
                    isActive &&
                      "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
            <button
              type="button"
              onClick={toggle}
              aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              aria-pressed={theme === "dark"}
              className="ml-2 inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-300 hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
            >
              {theme === "dark" ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
            </button>
          </nav>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        {children}
      </main>
      <footer className="border-t border-gray-200 dark:border-gray-800">
        <div className="mx-auto max-w-6xl px-4 py-4 text-sm text-gray-600 dark:text-gray-400">
          <p>
            ClaimLens audits research-paper claims. Verdicts shown here are
            computed by the backend; the frontend never decides whether
            results match.
          </p>
        </div>
      </footer>
    </div>
  );
}
