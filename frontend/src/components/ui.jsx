// Small presentational primitives shared across the dashboard.

export function Card({ title, subtitle, right, className = "", children }) {
  return (
    <section className={`card p-5 ${className}`}>
      {(title || right) && (
        <div className="flex items-start justify-between mb-4">
          <div>
            {title && <h3 className="text-sm font-semibold text-ink-900">{title}</h3>}
            {subtitle && <p className="text-xs text-ink-500 mt-0.5">{subtitle}</p>}
          </div>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint, tone = "default" }) {
  const toneCls =
    tone === "danger" ? "text-danger" : tone === "warn" ? "text-warn" : tone === "good" ? "text-good" : "text-ink-900";
  return (
    <div className="card p-4">
      <div className="stat-label">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${toneCls}`}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-ink-500">{hint}</div>}
    </div>
  );
}

export function Pill({ children, className = "" }) {
  return <span className={`pill ${className}`}>{children}</span>;
}

export function Table({ columns, children }) {
  return (
    <div className="overflow-x-auto -mx-1">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key ?? c.label} className={`th ${c.align === "right" ? "text-right" : ""}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function Empty({ title, hint }) {
  return (
    <div className="text-center py-12">
      <div className="text-ink-700 font-medium">{title}</div>
      {hint && <div className="text-sm text-ink-400 mt-1">{hint}</div>}
    </div>
  );
}

export function Spinner({ label }) {
  return (
    <div className="flex items-center gap-3 text-ink-500 text-sm py-10 justify-center">
      <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="9" stroke="#c7d2fe" strokeWidth="3" />
        <path d="M21 12a9 9 0 0 0-9-9" stroke="#4f46e5" strokeWidth="3" strokeLinecap="round" />
      </svg>
      {label || "Loading…"}
    </div>
  );
}

export function MonoPath({ path }) {
  const parts = (path || "").split("/");
  const name = parts.pop();
  const dir = parts.join("/");
  return (
    <span className="font-mono text-xs">
      {dir && <span className="text-ink-400">{dir}/</span>}
      <span className="text-ink-900">{name}</span>
    </span>
  );
}
