import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSummary } from "../api/client";
import { fmtCompact, fmtNumber } from "../lib/format";
import { Spinner } from "../components/ui";
import OverviewTab from "../tabs/OverviewTab";
import ComplexityTab from "../tabs/ComplexityTab";
import ContributorsTab from "../tabs/ContributorsTab";
import HotspotsTab from "../tabs/HotspotsTab";
import DependenciesTab from "../tabs/DependenciesTab";
import TreemapTab from "../tabs/TreemapTab";
import GraphTab from "../tabs/GraphTab";

const TABS = [
  ["overview", "Overview", OverviewTab],
  ["treemap", "Treemap", TreemapTab],
  ["complexity", "Complexity", ComplexityTab],
  ["contributors", "Contributors", ContributorsTab],
  ["hotspots", "Hotspots", HotspotsTab],
  ["dependencies", "Dependencies", DependenciesTab],
  ["graph", "Graph", GraphTab],
];

export default function AnalysisPage() {
  const { id } = useParams();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    getSummary(id).then(setSummary).catch((e) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-16 text-center text-danger">{error}</div>
    );
  }
  if (!summary) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-16">
        <Spinner label="Loading analysis…" />
      </div>
    );
  }

  const ActiveTab = TABS.find((t) => t[0] === tab)[2];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <RepoHeader summary={summary} />

      <div className="mt-6 border-b border-hairline">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {TABS.map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`tabbtn ${tab === key ? "tabbtn-active" : ""}`}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      <div className="mt-6">
        <ActiveTab id={id} summary={summary} />
      </div>
    </div>
  );
}

function RepoHeader({ summary }) {
  const stats = [
    ["Files", fmtNumber(summary.total_files)],
    ["Lines", fmtCompact(summary.total_lines)],
    ["Commits", fmtNumber(summary.commit_count)],
    ["Contributors", fmtNumber(summary.contributor_count)],
    ["Primary language", summary.primary_language || "—"],
  ];
  return (
    <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
          {summary.repo_name || summary.repo_url}
        </h1>
        <a
          href={summary.repo_url?.replace(/\.git$/, "")}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-brand-600 hover:underline break-all"
        >
          {summary.repo_url}
        </a>
      </div>
      <div className="flex flex-wrap gap-2">
        {stats.map(([label, value]) => (
          <div key={label} className="card px-3.5 py-2">
            <div className="stat-label">{label}</div>
            <div className="text-lg font-semibold text-ink-900 tabular-nums">{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
