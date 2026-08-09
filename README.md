# CodeScope

Paste a public GitHub repo URL and get a comprehensive codebase health report —
language & structure breakdown, code complexity, contributor patterns, change
hotspots, dependency health, and interactive visualizations. Built to help an
engineering lead or a new team member understand an unfamiliar codebase at a
glance.

<!-- SCREENSHOTS: add images here once captured, e.g. -->
<!-- ![Overview](docs/screenshots/overview.png) -->
<!-- ![Treemap](docs/screenshots/treemap.png) -->
<!-- ![Dependency graph](docs/screenshots/graph.png) -->

## What it does

A user submits a public GitHub URL. The API validates it, records a `queued`
analysis, and enqueues a job. A Celery worker clones the repo and runs five
analysis passes, updating status as it goes; the React dashboard polls for
progress and then renders the results.

The report covers:

- **Structure** — lines of code and file counts by language, plus a directory
  treemap sized by LOC.
- **Complexity** — cyclomatic complexity and function counts per Python file
  (via radon), ranked, with a green→red heatmap.
- **Contributors** — commits per author over time, first/last activity, files
  touched, active/inactive status, and **bus-factor** warnings (files with a
  single owner).
- **Hotspots** — most-changed files, **churn** (change frequency × complexity),
  and **co-change** coupling (files that change together).
- **Dependencies** — declared vs latest version (PyPI / npm), how many major
  versions behind, and known vulnerabilities from the **OSV** database.
- **Import graph** — an interactive force-directed graph of intra-repo Python
  imports; core files (imported by many) render larger, entry points are
  highlighted.

## Architecture

```
              ┌─────────────┐        ┌─────────────┐
  Browser ───▶│  FastAPI    │───────▶│   Redis     │  (job queue + cache)
   (React)    │  api        │        │  broker     │
      ▲       └──────┬──────┘        └──────┬──────┘
      │              │                      │
      │        reads │ results         jobs │
      │              ▼                      ▼
      │       ┌─────────────┐        ┌─────────────┐
      └───────│ PostgreSQL  │◀───────│  Celery     │  clones repo,
  poll /status│ source of   │  writes│  worker     │  runs 5 analysis passes
              │ truth       │        └─────────────┘
              └─────────────┘
```

- **api** (FastAPI) — receives URLs, creates jobs, serves status + results.
- **worker** (Celery) — clones the repo and runs the analysis passes.
- **redis** — job queue between api and worker; short-TTL result cache.
- **postgres** — single source of truth for all analysis data.
- **frontend** (React + Vite) — dashboard with charts (Recharts) and D3
  visualizations (treemap, force-directed dependency graph, heatmap).

Postgres is the source of truth; Celery/Redis carries only job pointers.

## Performance

Measured with `backend/scripts/benchmark.py` on a laptop. Times are **analysis
compute only** (structure + git history + complexity + import graph) and
exclude the initial `git clone`.

| Repo               | Files | LOC   | Python files | Commits | Analysis time |
| ------------------ | ----: | ----: | -----------: | ------: | ------------: |
| psf/requests       |    91 | 12.6K |           37 |   4,877 |        ~0.7 s |
| pallets/flask      |   210 | 22.5K |           83 |   3,816 |        ~1.0 s |
| pallets/click      |   143 |  26K  |           78 |   2,136 |        ~1.2 s |
| tiangolo/fastapi   | 2,036 | 182K  |        1,136 |   7,634 |       ~18.7 s |

Small-to-medium repos analyze in **~1 second**; a 2,000-file / 182K-line repo
with 7,600 commits in **under 20 seconds** (dominated by reading every file in
the structure pass). Full git history is analyzed with no commit cap.

Run it yourself:

```bash
cd backend
python scripts/benchmark.py /path/to/cloned/repo [more/repos ...]
```

## Quick start (Docker — one command)

```bash
cp .env.example .env
docker compose up --build
```

- Dashboard:  http://localhost:3000
- API:        http://localhost:8000
- Swagger UI: http://localhost:8000/docs

The frontend container serves the built app via nginx and proxies `/api` to the
backend, so no CORS setup is needed. The api container runs migrations on boot.

## Running locally without Docker

Datastores are easiest via Docker even if you run the app in a venv:

```bash
docker compose up -d postgres redis
```

> If host port 5432 is already taken by another Postgres, the compose file maps
> the container to **5433** — point `DATABASE_URL` at that port (see below).

Backend (Python 3.11+ recommended):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Only needed if Postgres is on a non-default port (e.g. 5433):
cat > .env <<'EOF'
DATABASE_URL=postgresql+psycopg2://repolens:repolens@localhost:5433/repolens
REDIS_URL=redis://localhost:6379/0
EOF

alembic upgrade head
python -m uvicorn app.main:app --reload          # terminal 1
python -m celery -A app.celery_app.celery_app worker --loglevel=info  # terminal 2
```

Frontend:

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173, proxies /api to :8000
```

The frontend also ships with a **mock mode** (`VITE_USE_MOCKS=true`, the
default) that renders bundled sample data with no backend — handy for UI work.
Set `VITE_USE_MOCKS=false` in `frontend/.env.local` to hit the live API.

> Note: every new terminal needs `source .venv/bin/activate`, and run Python
> tools as `python -m uvicorn` / `python -m celery` so they use the venv.

## API endpoints

| Method | Path                              | Purpose                              |
| ------ | --------------------------------- | ------------------------------------ |
| POST   | `/analyze`                        | Submit a repo URL (returns 202)      |
| GET    | `/analyses/{id}`                  | Full analysis record + summary       |
| GET    | `/analyses/{id}/status`           | Lightweight status for polling       |
| GET    | `/analyses/{id}/structure`        | Language breakdown + treemap         |
| GET    | `/analyses/{id}/complexity`       | Per-file complexity + heatmap        |
| GET    | `/analyses/{id}/contributors`     | Contributor stats, timeline, bus factor |
| GET    | `/analyses/{id}/hotspots`         | Most-changed, churn, co-change       |
| GET    | `/analyses/{id}/dependencies`     | Versions + OSV vulnerabilities       |
| GET    | `/analyses/{id}/graph`            | Import graph nodes + edges           |
| GET    | `/health`                         | DB/Redis health, queue, workers      |

## Testing

```bash
cd backend
python -m pytest tests/ -q
```

33 tests cover URL validation, line counting, complexity, git-log parsing,
manifest parsing, version comparison, import resolution, the reporting
builders, and request validation. Full pipeline tests that read/write analyses
need Postgres and are exercised via docker-compose.

## Design notes / limits

- **Python-scoped analysis.** Cyclomatic complexity (radon) and the import
  graph are Python-only. For JS-heavy repos those views degrade gracefully
  (clear empty states) rather than showing broken charts.
- **Large-file guard.** radon's tokenizer is superlinear and can hang on very
  large source files, so files above ~100 KB / 2,500 lines skip complexity
  scoring and fall back to a linear line counter. This keeps a single
  pathological file from stalling the whole pipeline.
- **Resource guards on cloning.** Clone timeout and a max-repo-size ceiling,
  since the worker clones arbitrary user-supplied URLs.
- **Caching.** Re-analyzing the same URL within a short TTL returns the existing
  analysis instead of re-cloning.

## Tech stack

Python 3.11 · FastAPI · Celery · Redis · PostgreSQL · SQLAlchemy + Alembic ·
GitPython · radon · httpx · Docker Compose · React + Vite · Tailwind CSS ·
Recharts · D3.js · pytest
