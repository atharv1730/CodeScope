import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getStatus, resetMockProgress, submitRepo, usingMocks } from "../api/client";

const STAGE_LABELS = {
  queued: "Queued",
  cloning: "Cloning repository",
  analyzing_structure: "Analyzing file structure",
  analyzing_git: "Parsing git history",
  analyzing_complexity: "Measuring complexity",
  analyzing_dependencies: "Checking dependencies",
  complete: "Complete",
  failed: "Failed",
};

const EXAMPLES = [
  "https://github.com/pallets/flask",
  "https://github.com/psf/requests",
  "https://github.com/tiangolo/fastapi",
];

export default function SubmitPage() {
  const [url, setUrl] = useState("");
  const [phase, setPhase] = useState("idle"); // idle | working | error
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const pollRef = useRef(null);

  useEffect(() => () => clearInterval(pollRef.current), []);

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    setPhase("working");
    resetMockProgress();
    try {
      const created = await submitRepo(url.trim());
      setStatus({ status: created.status, progress: 0 });
      pollRef.current = setInterval(async () => {
        try {
          const s = await getStatus(created.id);
          setStatus(s);
          if (s.status === "complete") {
            clearInterval(pollRef.current);
            navigate(`/analysis/${created.id}`);
          } else if (s.status === "failed") {
            clearInterval(pollRef.current);
            setError(s.error || "Analysis failed.");
            setPhase("error");
          }
        } catch (err) {
          clearInterval(pollRef.current);
          setError(err.message);
          setPhase("error");
        }
      }, usingMocks ? 500 : 1500);
    } catch (err) {
      setError(err.message);
      setPhase("error");
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-6 pt-16 pb-24">
      <div className="text-center">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-ink-900">
          See any codebase at a glance
        </h1>
        <p className="mt-3 text-ink-500 max-w-xl mx-auto">
          Paste a public GitHub repository. CodeScope clones it and reports on structure,
          complexity, contributors, change hotspots, and dependency health.
        </p>
      </div>

      <form onSubmit={onSubmit} className="mt-10 card p-2 flex flex-col sm:flex-row gap-2">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          disabled={phase === "working"}
          className="flex-1 px-4 py-3 rounded-lg bg-canvas border border-hairline text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500"
        />
        <button
          type="submit"
          disabled={phase === "working" || !url.trim()}
          className="px-5 py-3 rounded-lg bg-brand-500 text-white font-medium hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {phase === "working" ? "Analyzing…" : "Analyze"}
        </button>
      </form>

      <div className="mt-3 flex flex-wrap items-center gap-2 justify-center text-sm">
        <span className="text-ink-400">Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => setUrl(ex)}
            className="text-brand-600 hover:underline"
            type="button"
          >
            {ex.replace("https://github.com/", "")}
          </button>
        ))}
      </div>

      {phase === "working" && status && <Progress status={status} />}
      {phase === "error" && (
        <div className="mt-8 card p-4 border-red-200 bg-red-50">
          <div className="text-danger font-medium text-sm">Couldn’t analyze that repository</div>
          <div className="text-sm text-ink-700 mt-1">{error}</div>
        </div>
      )}
    </div>
  );
}

function Progress({ status }) {
  const pct = status.progress ?? 0;
  return (
    <div className="mt-10 card p-6">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-ink-900">
          {STAGE_LABELS[status.status] || status.status}
        </span>
        <span className="text-sm tabular-nums text-ink-500">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-brand-50 overflow-hidden">
        <div
          className="h-full bg-brand-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <ol className="mt-5 grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
        {Object.entries(STAGE_LABELS)
          .filter(([k]) => k !== "failed")
          .map(([key, label]) => {
            const order = Object.keys(STAGE_LABELS).filter((k) => k !== "failed");
            const done = order.indexOf(key) < order.indexOf(status.status);
            const active = key === status.status;
            return (
              <li
                key={key}
                className={`flex items-center gap-1.5 ${
                  active ? "text-brand-600 font-medium" : done ? "text-good" : "text-ink-400"
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    active ? "bg-brand-500" : done ? "bg-good" : "bg-ink-400/40"
                  }`}
                />
                {label}
              </li>
            );
          })}
      </ol>
    </div>
  );
}
