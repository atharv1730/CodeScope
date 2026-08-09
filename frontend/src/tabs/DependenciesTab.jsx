import { Fragment, useState } from "react";
import { useSection } from "../hooks/useSection";
import { Card, Empty, Spinner, Stat, Table } from "../components/ui";
import { fmtNumber, riskPill } from "../lib/format";

export default function DependenciesTab({ id }) {
  const { data, loading, error } = useSection(id, "dependencies");
  const [filter, setFilter] = useState("all"); // all | issues

  if (loading) return <Spinner />;
  if (error) return <Empty title="Couldn’t load dependencies" hint={error} />;
  if (!data.dependencies.length) {
    return <Empty title="No dependencies found" hint="No requirements.txt, pyproject.toml, or package.json detected." />;
  }

  const s = data.summary;
  const rows = data.dependencies.filter((d) =>
    filter === "issues" ? d.has_vulnerability || d.is_outdated : true
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="Dependencies" value={fmtNumber(s.total)} />
        <Stat label="Outdated" value={fmtNumber(s.outdated)} tone="warn" />
        <Stat label="Severely outdated" value={fmtNumber(s.severely_outdated)} tone="warn" />
        <Stat label="Vulnerable" value={fmtNumber(s.vulnerable)} tone={s.vulnerable ? "danger" : "good"} />
      </div>

      <Card
        title="Dependencies"
        subtitle="Version status and known vulnerabilities (OSV)"
        right={
          <div className="flex gap-1 text-xs">
            {["all", "issues"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2.5 py-1 rounded-md ${
                  filter === f ? "bg-brand-50 text-brand-600 font-medium" : "text-ink-500 hover:text-ink-900"
                }`}
              >
                {f === "all" ? "All" : "Issues only"}
              </button>
            ))}
          </div>
        }
      >
        <Table
          columns={[
            { label: "Package" },
            { label: "Current", align: "right" },
            { label: "Latest", align: "right" },
            { label: "Behind", align: "right" },
            { label: "Status", align: "right" },
          ]}
        >
          {rows.map((d) => {
            const pill = riskPill(d.has_vulnerability, d.severely_outdated, d.is_outdated);
            return (
              <Fragment key={d.name}>
                <tr className="hover:bg-canvas">
                  <td className="td">
                    <span className="font-medium text-ink-900">{d.name}</span>
                    <span className="ml-2 text-xs text-ink-400">{d.ecosystem}</span>
                  </td>
                  <td className="td text-right font-mono text-xs">{d.current_version || "—"}</td>
                  <td className="td text-right font-mono text-xs">{d.latest_version || "—"}</td>
                  <td className="td text-right tabular-nums">
                    {d.versions_behind ? `${d.versions_behind} major` : "—"}
                  </td>
                  <td className="td text-right">
                    <span className={`pill ${pill.cls}`}>{pill.label}</span>
                  </td>
                </tr>
                {d.has_vulnerability &&
                  d.vulnerabilities.map((v) => (
                    <tr key={d.name + v.id} className="bg-red-50/40">
                      <td className="td text-xs text-danger" colSpan={5}>
                        <span className="font-mono">{v.id}</span>
                        {v.severity ? <span className="ml-2 pill bg-red-100 text-danger">CVSS {v.severity}</span> : null}
                        {v.summary ? <span className="ml-2 text-ink-700">{v.summary}</span> : null}
                      </td>
                    </tr>
                  ))}
              </Fragment>
            );
          })}
        </Table>
      </Card>
    </div>
  );
}
