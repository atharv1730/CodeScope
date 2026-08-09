// Realistic mock data matching the backend API response shapes.
// Used when VITE_USE_MOCKS=true so the whole UI is visible without a backend.

const REPO = {
  id: "a1b2c3d4-0000-4000-8000-000000000001",
  repo_url: "https://github.com/pallets/flask.git",
  repo_name: "pallets/flask",
};

const FILES = [
  ["src/flask/app.py", "Python", 1180, 62, 210, 48.0, 34, 40, "David Lord"],
  ["src/flask/helpers.py", "Python", 420, 20, 95, 22.0, 18, 22, "Armin Ronacher"],
  ["src/flask/blueprints.py", "Python", 260, 12, 60, 14.0, 10, 9, "David Lord"],
  ["src/flask/cli.py", "Python", 640, 30, 120, 31.0, 22, 15, "David Lord"],
  ["src/flask/ctx.py", "Python", 380, 18, 70, 19.0, 12, 12, "Armin Ronacher"],
  ["src/flask/wrappers.py", "Python", 210, 10, 45, 9.0, 8, 7, "Grey Li"],
  ["src/flask/json/__init__.py", "Python", 300, 15, 55, 16.0, 14, 6, "David Lord"],
  ["src/flask/sessions.py", "Python", 340, 16, 62, 17.0, 11, 8, "Armin Ronacher"],
  ["src/flask/testing.py", "Python", 290, 14, 48, 12.0, 10, 5, "Grey Li"],
  ["src/flask/views.py", "Python", 160, 8, 30, 7.0, 6, 4, "David Lord"],
  ["tests/test_basic.py", "Python", 980, 40, 20, 26.0, 60, 31, "David Lord"],
  ["tests/test_reqctx.py", "Python", 300, 12, 8, 11.0, 20, 9, "Armin Ronacher"],
  ["docs/quickstart.rst", "reStructuredText", 420, 60, 0, null, 0, 14, "David Lord"],
  ["README.rst", "reStructuredText", 120, 22, 0, null, 0, 6, "David Lord"],
  ["package.json", "JSON", 30, 0, 0, null, 0, 3, "David Lord"],
  ["src/flask/static/app.js", "JavaScript", 240, 20, 30, null, 0, 5, "Grey Li"],
  ["src/flask/static/style.css", "CSS", 180, 24, 12, null, 0, 4, "Grey Li"],
];

function fileMetric(row) {
  const [file_path, language, loc, blank, comment, complexity, funcs, change, top] = row;
  return {
    file_path,
    language,
    lines_of_code: loc,
    blank_lines: blank,
    comment_lines: comment,
    complexity_score: complexity,
    function_count: funcs,
    change_frequency: change,
    last_changed: "2026-06-14T10:00:00+00:00",
    top_contributor: top,
    bus_factor: complexity != null ? (change > 20 ? 1 : 3) : 2,
  };
}

const METRICS = FILES.map(fileMetric);

function languageBreakdown() {
  const agg = {};
  for (const m of METRICS) {
    agg[m.language] = agg[m.language] || { language: m.language, files: 0, lines_of_code: 0 };
    agg[m.language].files += 1;
    agg[m.language].lines_of_code += m.lines_of_code;
  }
  return Object.values(agg).sort((a, b) => b.lines_of_code - a.lines_of_code);
}

function treemap() {
  const root = { name: "", path: "", size: 0, children: {} };
  for (const m of METRICS) {
    const parts = m.file_path.split("/");
    let node = root;
    parts.forEach((part, i) => {
      const leaf = i === parts.length - 1;
      if (leaf) {
        node.children[part] = {
          name: part,
          path: m.file_path,
          size: m.lines_of_code,
          language: m.language,
          change_frequency: m.change_frequency,
        };
      } else {
        node.children[part] = node.children[part] || {
          name: part,
          path: parts.slice(0, i + 1).join("/"),
          size: 0,
          children: {},
        };
        node = node.children[part];
      }
    });
  }
  const finalize = (n) => {
    if (!n.children) return n;
    const kids = Object.values(n.children).map(finalize);
    return { name: n.name, path: n.path, size: kids.reduce((s, k) => s + k.size, 0), children: kids };
  };
  return finalize(root);
}

const CONTRIBUTORS = [
  ["David Lord", "davidism@gmail.com", 326, 92, 5, "2019-01-04", "2026-06-14"],
  ["Armin Ronacher", "armin@example.com", 465, 78, 380, "2010-04-06", "2025-05-20"],
  ["Grey Li", "grey@example.com", 139, 44, 20, "2019-08-10", "2026-05-30"],
  ["Adrian Mönnich", "adrian@example.com", 60, 22, 95, "2015-03-11", "2026-03-10"],
  ["Keyan Pishdadian", "keyan@example.com", 28, 14, 210, "2016-07-01", "2025-11-02"],
  ["Joël Charles", "joel@example.com", 18, 9, 60, "2018-02-19", "2026-04-18"],
];

function contributorsList() {
  return CONTRIBUTORS.map(([name, email, commits, files, days, first, last]) => {
    const bucket = days <= 30 ? "active_30" : days <= 60 ? "active_60" : days <= 90 ? "active_90" : "inactive";
    return {
      name,
      email,
      commit_count: commits,
      files_touched: files,
      first_commit: first + "T00:00:00+00:00",
      last_commit: last + "T00:00:00+00:00",
      days_since_last_commit: days,
      activity: bucket,
    };
  }).sort((a, b) => b.commit_count - a.commit_count);
}

function timeline() {
  // 26 weeks of activity.
  const out = [];
  const start = new Date("2026-01-05");
  for (let i = 0; i < 26; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i * 7);
    const wave = 8 + Math.round(6 * Math.sin(i / 2) + (i % 4));
    out.push({ week: d.toISOString().slice(0, 10), commits: Math.max(1, wave) });
  }
  return out;
}

export function mockStructure() {
  return {
    total_files: METRICS.length,
    total_lines_of_code: METRICS.reduce((s, m) => s + m.lines_of_code, 0),
    languages: languageBreakdown(),
    treemap: treemap(),
  };
}

export function mockComplexity() {
  const scored = METRICS.filter((m) => m.complexity_score != null).sort(
    (a, b) => b.complexity_score - a.complexity_score
  );
  return {
    summary: {
      python_files_scored: scored.length,
      max_complexity: Math.max(...scored.map((m) => m.complexity_score)),
      avg_complexity: +(scored.reduce((s, m) => s + m.complexity_score, 0) / scored.length).toFixed(2),
      analyzable: true,
    },
    files: scored.map((m) => ({
      file_path: m.file_path,
      language: m.language,
      complexity_score: m.complexity_score,
      function_count: m.function_count,
      lines_of_code: m.lines_of_code,
      avg_complexity_per_function: m.function_count ? +(m.complexity_score / m.function_count).toFixed(2) : null,
    })),
    heatmap: scored.map((m) => ({ file_path: m.file_path, complexity_score: m.complexity_score })),
  };
}

export function mockContributors() {
  const list = contributorsList();
  return {
    summary: {
      contributor_count: list.length,
      commit_count: list.reduce((s, c) => s + c.commit_count, 0),
      active_30: list.filter((c) => c.days_since_last_commit <= 30).length,
      active_60: list.filter((c) => c.days_since_last_commit <= 60).length,
      active_90: list.filter((c) => c.days_since_last_commit <= 90).length,
    },
    contributors: list,
    timeline: timeline(),
    per_contributor_timeline: [],
    bus_factor_warnings: METRICS.filter((m) => m.bus_factor === 1 && m.change_frequency > 0)
      .sort((a, b) => b.change_frequency - a.change_frequency)
      .map((m) => ({
        file_path: m.file_path,
        bus_factor: m.bus_factor,
        change_frequency: m.change_frequency,
        owner: m.top_contributor,
      })),
  };
}

export function mockHotspots() {
  const most = [...METRICS].filter((m) => m.change_frequency > 0)
    .sort((a, b) => b.change_frequency - a.change_frequency)
    .slice(0, 12)
    .map((m) => ({
      file_path: m.file_path,
      change_frequency: m.change_frequency,
      complexity_score: m.complexity_score,
      last_changed: m.last_changed,
      top_contributor: m.top_contributor,
    }));
  const churn = METRICS.filter((m) => m.complexity_score != null && m.change_frequency > 0)
    .map((m) => ({
      file_path: m.file_path,
      change_frequency: m.change_frequency,
      complexity_score: m.complexity_score,
      churn_score: +(m.change_frequency * m.complexity_score).toFixed(1),
    }))
    .sort((a, b) => b.churn_score - a.churn_score)
    .slice(0, 12);
  const co_change = [
    ["src/flask/app.py", "tests/test_basic.py", 24],
    ["src/flask/app.py", "src/flask/helpers.py", 15],
    ["src/flask/cli.py", "tests/test_basic.py", 11],
    ["src/flask/ctx.py", "src/flask/sessions.py", 8],
    ["src/flask/app.py", "docs/quickstart.rst", 6],
  ].map(([s, t, n]) => ({ source_file: s, target_file: t, shared_commits: n }));
  return { most_changed: most, churn, co_change };
}

export function mockDependencies() {
  const deps = [
    ["Werkzeug", "pypi", "2.0.1", "3.0.4", true, 1, false, []],
    ["Jinja2", "pypi", "2.11.3", "3.1.4", true, 1, true, [{ id: "GHSA-h5c8-rqwp-cp95", summary: "XSS via xmlattr filter", severity: "6.1" }]],
    ["click", "pypi", "8.1.7", "8.1.7", false, 0, false, []],
    ["itsdangerous", "pypi", "1.1.0", "2.2.0", true, 1, false, []],
    ["MarkupSafe", "pypi", "2.1.5", "2.1.5", false, 0, false, []],
    ["blinker", "pypi", "1.4", "1.8.2", true, 0, false, []],
    ["react", "npm", "16.14.0", "18.3.1", true, 2, false, []],
    ["lodash", "npm", "4.17.11", "4.17.21", true, 0, true, [{ id: "GHSA-p6mc-m468-83gw", summary: "Prototype pollution", severity: "7.4" }]],
  ];
  const out = deps.map(([name, eco, cur, latest, outdated, behind, vuln, vulns]) => ({
    name,
    ecosystem: eco,
    current_version: cur,
    latest_version: latest,
    is_outdated: outdated,
    versions_behind: behind,
    severely_outdated: behind > 2,
    has_vulnerability: vuln,
    vulnerabilities: vulns,
    source: eco === "npm" ? "package.json" : "requirements.txt",
  }));
  out.sort((a, b) => (a.has_vulnerability === b.has_vulnerability ? b.versions_behind - a.versions_behind : a.has_vulnerability ? -1 : 1));
  return {
    summary: {
      total: out.length,
      outdated: out.filter((d) => d.is_outdated).length,
      severely_outdated: out.filter((d) => d.severely_outdated).length,
      vulnerable: out.filter((d) => d.has_vulnerability).length,
    },
    dependencies: out,
  };
}

export function mockGraph() {
  const py = METRICS.filter((m) => m.language === "Python").map((m) => m.file_path);
  const edgeDefs = [
    ["src/flask/app.py", "src/flask/helpers.py"],
    ["src/flask/app.py", "src/flask/ctx.py"],
    ["src/flask/app.py", "src/flask/sessions.py"],
    ["src/flask/app.py", "src/flask/blueprints.py"],
    ["src/flask/cli.py", "src/flask/app.py"],
    ["src/flask/blueprints.py", "src/flask/helpers.py"],
    ["src/flask/views.py", "src/flask/app.py"],
    ["src/flask/testing.py", "src/flask/app.py"],
    ["tests/test_basic.py", "src/flask/app.py"],
    ["tests/test_reqctx.py", "src/flask/ctx.py"],
    ["src/flask/wrappers.py", "src/flask/helpers.py"],
    ["src/flask/json/__init__.py", "src/flask/app.py"],
  ].filter(([s, t]) => py.includes(s) && py.includes(t));
  const inDeg = {};
  edgeDefs.forEach(([, t]) => (inDeg[t] = (inDeg[t] || 0) + 1));
  const nodePaths = new Set(edgeDefs.flat());
  const entry = new Set(["src/flask/app.py", "src/flask/cli.py"]);
  const cfg = new Set(["package.json"]);
  const metricBy = Object.fromEntries(METRICS.map((m) => [m.file_path, m]));
  const nodes = [...nodePaths].map((p) => ({
    id: p,
    name: p.split("/").pop(),
    in_degree: inDeg[p] || 0,
    size: 1 + (inDeg[p] || 0),
    language: metricBy[p]?.language ?? null,
    lines_of_code: metricBy[p]?.lines_of_code ?? 0,
    complexity_score: metricBy[p]?.complexity_score ?? null,
    change_frequency: metricBy[p]?.change_frequency ?? 0,
    is_entry_point: entry.has(p),
    is_config: cfg.has(p),
  }));
  return {
    nodes,
    edges: edgeDefs.map(([s, t]) => ({ source: s, target: t })),
    entry_points: [...entry],
    summary: { node_count: nodes.length, edge_count: edgeDefs.length, truncated: false },
  };
}

export function mockSummary() {
  return {
    id: REPO.id,
    repo_url: REPO.repo_url,
    repo_name: REPO.repo_name,
    status: "complete",
    error: null,
    commit_count: 2136,
    contributor_count: CONTRIBUTORS.length,
    total_files: METRICS.length,
    total_lines: METRICS.reduce((s, m) => s + m.lines_of_code + m.blank_lines + m.comment_lines, 0),
    primary_language: "Python",
    created_at: "2026-06-14T09:58:00+00:00",
    completed_at: "2026-06-14T09:59:12+00:00",
  };
}

export const MOCK_REPO = REPO;
