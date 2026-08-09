import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useSection } from "../hooks/useSection";
import { Card, Empty, MonoPath, Spinner, Stat, Table } from "../components/ui";
import { colorForIndex, fmtDate, fmtNumber } from "../lib/format";
import { tooltipStyle } from "./OverviewTab";

export default function ContributorsTab({ id }) {
  const { data, loading, error } = useSection(id, "contributors");
  if (loading) return <Spinner />;
  if (error) return <Empty title="Couldn’t load contributors" hint={error} />;

  const people = data.contributors || [];
  const top = people.slice(0, 10);
  const s = data.summary;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="Contributors" value={fmtNumber(s.contributor_count)} />
        <Stat label="Commits" value={fmtNumber(s.commit_count)} />
        <Stat label="Active (30d)" value={fmtNumber(s.active_30)} tone="good" />
        <Stat label="Active (90d)" value={fmtNumber(s.active_90)} />
      </div>

      <Card title="Commit activity over time" subtitle="Weekly commits across all contributors">
        {(data.timeline || []).length === 0 ? (
          <Empty title="No commit history" />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data.timeline} margin={{ left: 4, right: 8 }}>
              <defs>
                <linearGradient id="commitFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="week" stroke="#94a3b8" fontSize={11} minTickGap={28} />
              <YAxis stroke="#94a3b8" fontSize={11} width={30} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [v, "commits"]} />
              <Area
                type="monotone"
                dataKey="commits"
                stroke="#4f46e5"
                strokeWidth={2}
                fill="url(#commitFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Commits per contributor" subtitle="Top 10 by commit count">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={top} layout="vertical" margin={{ left: 8, right: 16 }}>
              <XAxis type="number" stroke="#94a3b8" fontSize={12} />
              <YAxis type="category" dataKey="name" width={130} stroke="#94a3b8" fontSize={11} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [fmtNumber(v), "commits"]} />
              <Bar dataKey="commit_count" radius={[0, 6, 6, 0]}>
                {top.map((_, i) => (
                  <Cell key={i} fill={colorForIndex(i)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card
          title="Bus factor warnings"
          subtitle="Frequently-changed files with a single owner"
          right={
            <span className="pill bg-amber-50 text-warn">
              {(data.bus_factor_warnings || []).length} at risk
            </span>
          }
        >
          {(data.bus_factor_warnings || []).length === 0 ? (
            <Empty title="No single-owner risks" hint="Every active file has multiple contributors." />
          ) : (
            <ul className="divide-y divide-hairline">
              {data.bus_factor_warnings.map((w) => (
                <li key={w.file_path} className="py-2 flex items-center justify-between gap-3">
                  <MonoPath path={w.file_path} />
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-ink-500">{w.owner}</span>
                    <span className="pill bg-amber-50 text-warn">{w.change_frequency} changes</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="All contributors">
        <Table
          columns={[
            { label: "Contributor" },
            { label: "Commits", align: "right" },
            { label: "Files", align: "right" },
            { label: "First", align: "right" },
            { label: "Last", align: "right" },
            { label: "Status", align: "right" },
          ]}
        >
          {people.map((c) => (
            <tr key={c.email} className="hover:bg-canvas">
              <td className="td">
                <div className="font-medium text-ink-900">{c.name}</div>
                <div className="text-xs text-ink-400">{c.email}</div>
              </td>
              <td className="td text-right tabular-nums">{fmtNumber(c.commit_count)}</td>
              <td className="td text-right tabular-nums">{fmtNumber(c.files_touched)}</td>
              <td className="td text-right">{fmtDate(c.first_commit)}</td>
              <td className="td text-right">{fmtDate(c.last_commit)}</td>
              <td className="td text-right">
                <ActivityPill activity={c.activity} />
              </td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}

function ActivityPill({ activity }) {
  const map = {
    active_30: ["Active", "bg-green-50 text-good"],
    active_60: ["60d", "bg-green-50 text-good"],
    active_90: ["90d", "bg-amber-50 text-warn"],
    inactive: ["Inactive", "bg-slate-100 text-ink-500"],
    unknown: ["—", "bg-slate-100 text-ink-500"],
  };
  const [label, cls] = map[activity] || map.unknown;
  return <span className={`pill ${cls}`}>{label}</span>;
}
