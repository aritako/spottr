> *_Work in Progress!_*

# Spottr 🏋️

> An AI lifting coach — a spotter for your training data.

Spottr is a local-first, Dockerized backend that lets you log your workouts and then *talk
to your training history* in plain English. Ask it "How's my squat trending?" and it queries
your actual data. Ask it "Should I deload?" and it answers using a corpus of strength-training
knowledge — with citations back to the source.

It combines two AI techniques under one clean API:

- **Tool-calling** over your structured workout data, so answers are grounded in your real
  numbers instead of hallucinated.
- **Retrieval-Augmented Generation (RAG)** over a coaching-knowledge corpus, so advice is
  grounded in real training principles and cited.

---

## Why this exists

Most training logs are just databases with a UI. Spottr adds a reasoning layer: it decides
whether a question needs *your data*, *coaching knowledge*, or *both*, fetches what it needs,
and synthesizes a personalized, cited answer.

It's also a portfolio project demonstrating practical AI application engineering: REST APIs,
structured/unstructured JSON processing, LLM tool-calling, RAG with a vector database,
containerization, and an evaluation harness.

---

## Features

- 📓 **Workout logging** — sets, reps, weight, RPE, bodyweight, notes.
- 📈 **Natural-language analytics** — "What's my bench e1RM trend over 12 weeks?" answered
  from your real data via LLM tool-calling.
- 📚 **Cited coaching Q&A** — ingest training articles and guides; ask questions and get
  answers grounded in retrieved passages with source citations.
- 🔀 **Hybrid answers** — questions like "Given my recent volume, should I deload?" combine
  your data *and* coaching principles in one response.
- ✅ **Evaluation harness** — automated checks for tool-use accuracy and retrieval quality.
- 🐳 **Fully Dockerized** — `docker compose up` and you're running.

---

## Architecture

Requests flow one way: **controller → handler → repository → ORM model**.

```
app/
├── main.py               # FastAPI app, router registration
├── api/
│   ├── controllers/      # FastAPI routers (HTTP concerns only)
│   ├── handlers/         # business logic, class-based
│   └── repository/       # all database access via SQLAlchemy
├── core/
│   ├── config.py         # settings from env / .env
│   ├── db.py             # engine, session, get_db dependency
│   ├── models.py         # ORM models
│   └── openai/client.py  # shared OpenAI client
├── engine/
│   ├── coach.py          # tool schemas + Responses API loop
│   ├── tools.py          # tool implementations
│   └── helpers.py        # pure functions (metrics, time bucketing)
└── shared/
    ├── enums/            # StrEnum definitions
    ├── errors/           # domain exceptions
    └── schemas/          # Pydantic request/response models
```

The coach uses the OpenAI **Responses API**: it exposes tools (`query_workouts`,
`query_exercises`) the model can call, loops until the model stops requesting tools, and
returns a structured `{answer, used_tools, citations}` result.

---

## Getting started

### Prerequisites

- [Docker](https://www.docker.com/) with Docker Compose (Docker Desktop on Windows/macOS).
- An OpenAI API key.
- Python 3.12 (only needed to run the seed script / tests from the host).

### 1. Configure environment

```bash
cp .env.example .env
# then edit .env and set OPENAI_API_KEY=sk-...
```

### 2. Start the stack

```bash
docker compose up --build
```

| Service | URL | Notes |
|---|---|---|
| API | http://localhost:8000 | Swagger UI at http://localhost:8000/swagger |
| pgAdmin | http://localhost:5050 | `admin@admin.com` / `admin` |
| PostgreSQL | localhost:5432 | user `coach`, password `coach`, db `coach` |

### 3. Run migrations

```bash
docker compose exec app alembic upgrade head
```

### 4. Seed development data

Seeds 5 exercises and 12 weeks of workouts so the coach has real numbers to query. Run it from
the host (with the project installed — see [Local development](#local-development)):

```bash
DATABASE_URL=postgresql+psycopg://coach:coach@localhost:5432/coach python scripts/seed.py
```

Pass `--reset` to wipe and reseed. The `DATABASE_URL` override points at the published port;
the default in `app/core/config.py` uses the `db` hostname, which only resolves inside Docker.

---

## Frontend

The web client lives in `web/` at the repo root, next to the Python service:

```
web/                  Next.js 15 (App Router), React 19, Tailwind CSS v4
packages/api-client   Typed fetch client for this FastAPI service (@spottr/api-client)
```

The root project is the backend; `web/` is a second deployable, not a subproject of an `apps/`
tree. It was scaffolded with [create.t3.gg](https://create.t3.gg/) but deliberately **without
tRPC, Prisma or NextAuth**. Business logic and persistence stay in this Python service, so the
frontend talks to the REST API through `@spottr/api-client`. The client is React-free so a future
Expo app can reuse it as-is; web-only primitives live in `web/src/components/ui`. API types are
hand-written from the Pydantic schemas and can move to generated OpenAPI types once the surface
settles.

### Structure

`web/src` uses vertical slices: routes compose, slices own features.

```
web/src/
├── app/                # thin routes: metadata, AppShell, one slice
├── features/           # coach, home, routines, history, progress, workout-session
│   └── <slice>/        # index.ts, actions.ts, components/, model/, api/
├── components/         # cross-feature chrome
│   └── ui/             # design primitives + Red Lab tokens
├── lib/                # framework-agnostic helpers, query client
└── styles/             # Tailwind entry + @theme tokens
```

Pages import a slice through its `index.ts`; slices never reach into each other's internals.
TanStack Query is wired at the root, with server components prefetching and per-slice query keys
in `features/<slice>/api/keys.ts`. Form commands use server actions, so the coach still works
without JS.

### Run it

```bash
corepack enable
pnpm install
pnpm dev            # http://localhost:3000
```

The coach screen calls FastAPI from a server action. Point it at the API with `SPOTTR_API_URL`
(defaults to `http://localhost:8000`) in `web/.env`; see `web/.env.example`.

| Script | What it does |
|---|---|
| `pnpm dev` | Start the Next.js dev server |
| `pnpm build` | Production build |
| `pnpm lint` | ESLint |
| `pnpm typecheck` | TypeScript across `web/` and `packages/api-client` |
| `pnpm format` | Prettier |

### What is ported

- **Home** — next workout, weekly strip, coach nudge and routines.
- **Routine detail** — plan, last performance and target per exercise.
- **Coach** — start state plus a real `POST /coach/ask` round trip, citations and tool badges.

History, Progress and live workout logging are intentionally placeholders: the API does not
expose those aggregates yet. Fixtures are colocated with their slice
(`web/src/features/*/model/`) until those endpoints exist. Design tokens come from
`web/src/styles/theme.css`, which mirrors `mockups/00-style-guide.html`.

---

## Local development

Dev dependencies are **not** installed in the Docker image, so install them on the host:

```bash
pip install -e ".[dev]"
```

### Lint & format

```bash
ruff check .
ruff format .
```

### Run tests

```bash
pytest
```

Any database-backed command run from the host (seed, Alembic, DB-hitting tests) needs the
`DATABASE_URL` override shown in the seed step above, since the default resolves to the Docker
`db` hostname.

---

## License

MIT
