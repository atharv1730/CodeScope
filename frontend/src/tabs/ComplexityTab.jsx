import { useMemo, useState } from "react";
import { useSection } from "../hooks/useSection";
import { Card, Empty, MonoPath, Spinner, Stat, Table } from "../components/ui";
import { complexityColor, fmtNumber } from "../lib/format";

export default function ComplexityTab({ id }) {
  const { data, loading, error } = useSection(id, "complexity");
  const [sort, setSort] = useState({ key: "complexity_score", dir: "desc" });

  const files = useMemo(() => {
    if (!data) return [];
    const arr = [...data.files];
    const { key, dir } = sort;
    arr.sort((a, b) => {
      const av = a[key] ?? 0;
      const bv = b[key] ?? 0;
      return dir === "desc" ? bv - av : av - bv;
    });
    return arr;
  }, [data, sort]);

  if (loading) return <Spinner />;
  if (error) return <Empty title="Couldn’t load complexity" hint={error} />;
  if (!data.summary.analyzable) {
    return (
      <Empty
        title="No Python files to analyze"
        hint="Cyclomatic complexity is measured for Python. This repo has no analyzable Python files."
      />
    );
  }

  const max = data.summary.max_complexity || 1;

  function toggleSort(key) {
    setSort((s) => (s.key === key ? { key, dir: s.dir === "desc" ? "asc" : "desc" } : { key, dir: "desc" }));
  }

  const columns = [
    { key: "file_path", label: "File" },
    { key: "complexity_score", label: "Complexity", align: "right" },
    { key: "function_count", label: "Functions", align: "right" },
    { key: "avg_complexity_per_function", label: "Avg / fn", align: "right" },
    { key: "lines_of_code", label: "LOC", align: "right" },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <Stat label="Python files scored" value={fmtNumber(data.summary.python_files_scored)} />
        <Stat label="Max complexity" value={data.summary.max_complexity} tone="danger" />
        <Stat label="Average complexity" value={data.summary.avg_complexity} />
      </div>

      <Card title="Complexity heatmap" subtitle="Each cell is a file · green (simple) → red (complex)">
        <div className="flex flex-wrap gap-1.5">
          {data.heatmap.map((c) => (
            <div
              key={c.file_path}
              title={`${c.file_path} · ${c.complexity_score}`}
              className="w-7 h-7 rounded-md ring-1 ring-black/5 transition-transform hover:scale-110 cursor-default"
              style={{ background: complexityColor(c.complexity_score, max) }}
            />
          ))}
        </div>
        <div className="mt-4 flex items-center gap-2 text-xs text-ink-400">
          <span>Simple</span>
          <div className="h-2 w-40 rounded-full" style={{ background: "linear-gradient(90deg,#16a34a,#d97706,#dc2626)" }} />
          <span>Complex</span>
        </div>
      </Card>

      <Card title="Files by complexity" subtitle="Click a column to sort">
        <Table
          columns={columns.map((c) => ({
            ...c,
            label: (
              <button onClick={() => toggleSort(c.key)} className="hover:text-ink-900">
                {c.label}
                {sort.key === c.key ? (sort.dir === "desc" ? " ↓" : " ↑") : ""}
              </button>
            ),
          }))}
        >
          {files.map((f) => (
            <tr key={f.file_path} className="hover:bg-canvas">
              <td className="td">
                <MonoPath path={f.file_path} />
              </td>
              <td className="td text-right">
                <span
                  className="inline-block min-w-[2.5rem] rounded-md px-2 py-0.5 text-white text-xs font-medium tabular-nums"
                  style={{ background: complexityColor(f.complexity_score, max) }}
                >
                  {f.complexity_score}
                </span>
              </td>
              <td className="td text-right tabular-nums">{f.function_count}</td>
              <td className="td text-right tabular-nums">{f.avg_complexity_per_function ?? "—"}</td>
              <td className="td text-right tabular-nums">{fmtNumber(f.lines_of_code)}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
