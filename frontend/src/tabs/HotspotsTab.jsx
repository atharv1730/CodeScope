import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { useSection } from "../hooks/useSection";
import { Card, Empty, MonoPath, Spinner, Table } from "../components/ui";
import { basename, fmtNumber } from "../lib/format";
import { tooltipStyle } from "./OverviewTab";

export default function HotspotsTab({ id }) {
  const { data, loading, error } = useSection(id, "hotspots");
  if (loading) return <Spinner />;
  if (error) return <Empty title="Couldn’t load hotspots" hint={error} />;

  const scatter = (data.churn || []).map((c) => ({
    x: c.change_frequency,
    y: c.complexity_score,
    z: c.churn_score,
    name: basename(c.file_path),
    path: c.file_path,
  }));

  return (
    <div className="space-y-6">
      <Card
        title="Churn vs complexity"
        subtitle="Top-right = changed often AND complex — the riskiest files"
      >
        {scatter.length === 0 ? (
          <Empty title="No churn data" hint="Needs Python complexity scores and git history." />
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart margin={{ left: 4, right: 16, top: 8, bottom: 8 }}>
              <CartesianGrid stroke="#eef0f3" />
              <XAxis
                type="number"
                dataKey="x"
                name="Change frequency"
                stroke="#94a3b8"
                fontSize={12}
                label={{ value: "Change frequency", position: "insideBottom", offset: -2, fontSize: 11, fill: "#94a3b8" }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="Complexity"
                stroke="#94a3b8"
                fontSize={12}
                label={{ value: "Complexity", angle: -90, position: "insideLeft", fontSize: 11, fill: "#94a3b8" }}
              />
              <ZAxis type="number" dataKey="z" range={[60, 400]} />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ strokeDasharray: "3 3" }}
                formatter={(v, n) => [v, n]}
                labelFormatter={() => ""}
                content={<ScatterTip />}
              />
              <Scatter data={scatter} fill="#4f46e5" fillOpacity={0.65} />
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Most-changed files" subtitle="Ranked by number of commits touching the file">
          <Table columns={[{ label: "File" }, { label: "Changes", align: "right" }, { label: "Complexity", align: "right" }]}>
            {(data.most_changed || []).map((f) => (
              <tr key={f.file_path} className="hover:bg-canvas">
                <td className="td"><MonoPath path={f.file_path} /></td>
                <td className="td text-right tabular-nums">{f.change_frequency}</td>
                <td className="td text-right tabular-nums">{f.complexity_score ?? "—"}</td>
              </tr>
            ))}
          </Table>
        </Card>

        <Card title="Churn danger list" subtitle="High change frequency × high complexity">
          <Table columns={[{ label: "File" }, { label: "Churn", align: "right" }]}>
            {(data.churn || []).map((f, i) => (
              <tr key={f.file_path} className="hover:bg-canvas">
                <td className="td"><MonoPath path={f.file_path} /></td>
                <td className="td text-right">
                  <span
                    className={`pill tabular-nums ${i < 3 ? "bg-red-50 text-danger" : "bg-amber-50 text-warn"}`}
                  >
                    {fmtNumber(f.churn_score)}
                  </span>
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      </div>

      <Card title="Hidden coupling" subtitle="Files that frequently change together (co-change)">
        {(data.co_change || []).length === 0 ? (
          <Empty title="No strong co-change coupling found" />
        ) : (
          <ul className="space-y-2">
            {data.co_change.map((c, i) => (
              <li key={i} className="flex items-center gap-3 text-sm">
                <MonoPath path={c.source_file} />
                <span className="text-ink-400">↔</span>
                <MonoPath path={c.target_file} />
                <span className="pill bg-brand-50 text-brand-600 ml-auto tabular-nums">
                  {c.shared_commits} shared commits
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function ScatterTip({ payload }) {
  if (!payload || !payload.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-hairline bg-white px-3 py-2 shadow-lift text-xs">
      <div className="font-mono text-ink-900">{p.path}</div>
      <div className="text-ink-500 mt-1">
        {p.x} changes · complexity {p.y} · churn {p.z}
      </div>
    </div>
  );
}
