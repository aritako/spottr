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
| API | http://localhost:8000 | Swagger UI at http://localhost:8000/docs |
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
