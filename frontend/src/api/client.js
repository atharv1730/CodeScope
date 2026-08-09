// API client. When VITE_USE_MOCKS is true (default in dev), all calls resolve
// from bundled sample data so the UI is fully visible without a backend.
// Set VITE_USE_MOCKS=false and VITE_API_BASE to hit the live FastAPI server.

import {
  MOCK_REPO,
  mockComplexity,
  mockContributors,
  mockDependencies,
  mockGraph,
  mockHotspots,
  mockStructure,
  mockSummary,
} from "./mocks";

const USE_MOCKS = (import.meta.env.VITE_USE_MOCKS ?? "true") !== "false";
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function http(path, options) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const usingMocks = USE_MOCKS;

export async function submitRepo(repoUrl) {
  if (USE_MOCKS) {
    await delay(400);
    return { ...MOCK_REPO, status: "queued", created_at: new Date().toISOString(), cached: false };
  }
  return http("/analyze", { method: "POST", body: JSON.stringify({ repo_url: repoUrl }) });
}

// Mock status walks through the pipeline stages so the progress UI is exercised.
const STAGES = [
  ["queued", 0],
  ["cloning", 15],
  ["analyzing_structure", 35],
  ["analyzing_git", 55],
  ["analyzing_complexity", 75],
  ["analyzing_dependencies", 90],
  ["complete", 100],
];
let mockTick = 0;

export async function getStatus(id) {
  if (USE_MOCKS) {
    const idx = Math.min(mockTick, STAGES.length - 1);
    mockTick += 1;
    const [status, progress] = STAGES[idx];
    return { id, status, error: null, progress };
  }
  return http(`/analyses/${id}/status`);
}

export function resetMockProgress() {
  mockTick = 0;
}

export async function getSummary(id) {
  if (USE_MOCKS) return { ...mockSummary(), id };
  return http(`/analyses/${id}`);
}

const MOCK_MAP = {
  structure: mockStructure,
  complexity: mockComplexity,
  contributors: mockContributors,
  hotspots: mockHotspots,
  dependencies: mockDependencies,
  graph: mockGraph,
};

export async function getSection(id, section) {
  if (USE_MOCKS) {
    await delay(150);
    return MOCK_MAP[section]();
  }
  return http(`/analyses/${id}/${section}`);
}
