import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useSection } from "../hooks/useSection";
import { Card, Empty, Spinner, Stat } from "../components/ui";
import { colorForIndex, fmtCompact, fmtNumber } from "../lib/format";

export default function OverviewTab({ id, summary }) {
  const { data, loading, error } = useSection(id, "structure");
  if (loading) return <Spinner />;
  if (error) return <Empty title="Couldn’t load structure" hint={error} />;

  const langs = data.languages || [];
  const topLangs = langs.slice(0, 8);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="Total files" value={fmtNumber(data.total_files)} />
        <Stat label="Lines of code" value={fmtCompact(data.total_lines_of_code)} />
        <Stat label="Languages" value={fmtNumber(langs.length)} />
        <Stat label="Primary language" value={summary.primary_language || "—"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Lines of code by language" subtitle="Top languages by code volume">
          {topLangs.length === 0 ? (
            <Empty title="No recognized code files" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={topLangs} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" tickFormatter={fmtCompact} stroke="#94a3b8" fontSize={12} />
                <YAxis
                  type="category"
                  dataKey="language"
                  width={110}
                  stroke="#94a3b8"
                  fontSize={12}
                />
                <Tooltip
                  formatter={(v) => [fmtNumber(v), "Lines"]}
                  contentStyle={tooltipStyle}
                />
                <Bar dataKey="lines_of_code" radius={[0, 6, 6, 0]}>
                  {topLangs.map((_, i) => (
                    <Cell key={i} fill={colorForIndex(i)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card title="File share by language" subtitle="Proportion of files">
          <div className="flex items-center gap-4">
            <ResponsiveContainer width="55%" height={280}>
              <PieChart>
                <Pie
                  data={topLangs}
                  dataKey="files"
                  nameKey="language"
                  innerRadius={55}
                  outerRadius={95}
                  paddingAngle={2}
                >
                  {topLangs.map((_, i) => (
                    <Cell key={i} fill={colorForIndex(i)} />
                  ))}
                </Pie>
                <Tooltip formatter={(v, n) => [fmtNumber(v) + " files", n]} contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
            <ul className="flex-1 space-y-1.5">
              {topLangs.map((l, i) => (
                <li key={l.language} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm" style={{ background: colorForIndex(i) }} />
                    <span className="text-ink-700">{l.language}</span>
                  </span>
                  <span className="text-ink-400 tabular-nums">{fmtNumber(l.files)}</span>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </div>
    </div>
  );
}

export const tooltipStyle = {
  borderRadius: 10,
  border: "1px solid #e6e8ec",
  boxShadow: "0 4px 12px rgba(16,24,40,0.08)",
  fontSize: 12,
};
