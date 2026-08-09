# RepoLens

Paste a public GitHub repo URL and get a comprehensive codebase health report —
language & structure breakdown, code complexity, contributor patterns, change
hotspots, dependency health, and interactive visualizations.

> Repo name is `CodeScope`; the product is **RepoLens**.

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
   poll /status│ source of   │  writes│  worker     │  runs analysis passes
              │ truth       │        └─────────────┘
              └─────────────┘
```

- **api** (FastAPI) — receives URLs, creates jobs, serves status + results.
- **worker** (Celery) — clones the repo and runs analysis passes.
- **redis** — job queue between api and worker; short-TTL result cache.
- **postgres** — single source of truth for all analysis data.
- **frontend** (React) — dashboard with charts, treemap, heatmap, dep graph.

Postgres is the source of truth; Celery/Redis carries only job pointers.

## Status of the build

Day 1 (this scaffold) is in place: project structure, full DB schema +
migration, FastAPI app with `/health`, `POST /analyze`, `GET /analyses/{id}`
and `.../status`, Celery wiring, and repo cloning with resource guards.
Analysis passes (structure, git, complexity, dependencies, graph) and the React
dashboard come on later days.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- API:        http://localhost:8000
- Swagger UI:  http://localhost:8000/docs
- Health:      http://localhost:8000/health

Submit a repo:

```bash
curl -X POST http://localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"repo_url": "https://github.com/pallets/flask"}'
```

Then poll:

```bash
curl http://localhost:8000/analyses/<id>/status
```

## API endpoints

| Method | Path                              | Purpose                            |
| ------ | --------------------------------- | ---------------------------------- |
| POST   | `/analyze`                        | Submit a repo URL (returns 202)    |
| GET    | `/analyses/{id}`                  | Full analysis record + summary     |
| GET    | `/analyses/{id}/status`           | Lightweight status for polling     |
| GET    | `/health`                         | DB/Redis health, queue, workers    |

Planned (later days): `/structure`, `/complexity`, `/contributors`,
`/hotspots`, `/dependencies`, `/graph`.

## Local dev without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# point DATABASE_URL / REDIS_URL at local services, then:
alembic upgrade head
uvicorn app.main:app --reload
celery -A app.celery_app.celery_app worker --loglevel=info   # separate shell
```

## Tech stack

Python 3.11 · FastAPI · Celery · Redis · PostgreSQL · SQLAlchemy + Alembic ·
GitPython · radon · httpx · Docker Compose · React + Tailwind · Recharts · D3.js
