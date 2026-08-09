import { Link, Outlet } from "react-router-dom";
import { usingMocks } from "./api/client";

export default function App() {
  return (
    <div className="min-h-full flex flex-col">
      <header className="sticky top-0 z-20 bg-surface/80 backdrop-blur border-b border-hairline">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <Logo />
            <span className="font-semibold tracking-tight text-ink-900">CodeScope</span>
            <span className="text-ink-400 text-sm hidden sm:inline">· repository health</span>
          </Link>
          <div className="flex items-center gap-3">
            {usingMocks && (
              <span className="pill bg-amber-50 text-warn" title="Rendering bundled sample data">
                demo data
              </span>
            )}
            <a
              href="https://github.com/atharv1730/CodeScope"
              className="text-sm text-ink-500 hover:text-ink-900"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
          </div>
        </div>
      </header>
      <main className="flex-1 w-full">
        <Outlet />
      </main>
      <footer className="border-t border-hairline">
        <div className="max-w-7xl mx-auto px-6 py-4 text-xs text-ink-400">
          CodeScope · clone → analyze → visualize
        </div>
      </footer>
    </div>
  );
}

function Logo() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="1.5" y="1.5" width="21" height="21" rx="6" fill="#eef2ff" stroke="#c7d2fe" />
      <circle cx="10.5" cy="10.5" r="4.5" stroke="#4f46e5" strokeWidth="2" />
      <line x1="14" y1="14" x2="18" y2="18" stroke="#4f46e5" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
