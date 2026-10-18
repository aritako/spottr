# AGENTS.md

Guidance for AI coding agents working in this repository. Read this fully before making changes.

## Project

Spottr is an AI lifting coach backend. Users log workouts, then ask questions in natural language.
The coach answers by calling tools that query real workout data (and, soon, a RAG tool over a
coaching-knowledge corpus with citations). It must never guess or invent numbers.

Status: backend-only, work in progress. A Next.js frontend comes later; keep all business logic in
this backend so future clients (web, Expo) can reuse it.

## Stack

- Python 3.12, FastAPI, Pydantic v2, pydantic-settings
- PostgreSQL 16 + pgvector (`pgvector/pgvector:pg16`), SQLAlchemy 2.0 (sync, typed `Mapped[...]`)
- Alembic for migrations
- OpenAI Python SDK, **Responses API** (not Chat Completions)
- pytest, httpx (TestClient), ruff
- Docker Compose: `db`, `app` (live reload), `pgadmin`

## Commands

```bash
# Start everything (app on :8000, Swagger at /docs, pgAdmin on :5050)
docker compose up --build

# Apply migrations
docker compose exec app alembic upgrade head

# Create a migration after changing app/core/models.py, then REVIEW the generated file
docker compose exec app alembic revision --autogenerate -m "short_description"

# Local dev tooling (dev deps are NOT installed in the Docker image)
pip install -e ".[dev]"
ruff check . --fix
ruff format .
pytest
```

When running tests or Alembic from the host instead of the container, set
`DATABASE_URL=postgresql+psycopg://coach:coach@localhost:5432/coach`. The default in
`app/core/config.py` uses the `db` hostname, which only resolves inside Docker.

## Architecture

Requests flow one way: **controller → handler → repository → ORM model**.

```
app/
├── main.py                  # FastAPI app, router registration, /health
├── api/
│   ├── controllers/         # FastAPI routers: HTTP concerns only
│   ├── handlers/            # Business logic, class-based (e.g. WorkoutsHandler(db))
│   └── repository/          # All database access via SQLAlchemy select()
├── core/
│   ├── config.py            # Settings (env / .env)
│   ├── db.py                # engine, SessionLocal, Base, get_db dependency
│   ├── models.py            # All ORM models
│   └── openai/client.py     # Shared OpenAI client
├── engine/
│   ├── coach.py             # Coach: tool schemas, registry, Responses API loop
│   ├── tools.py             # Tool implementations (call handlers, not repositories)
│   └── helpers.py           # PURE functions only: metrics and time bucketing
└── shared/
    ├── enums/               # StrEnum definitions
    ├── errors/              # Domain exceptions
    └── schemas/             # Pydantic request/response models
```

Layer rules:

- **Controllers** parse requests, call one handler method, and map domain errors to
  `HTTPException`. No queries, no business logic.
- **Handlers** hold business logic and validation that needs the database (e.g. checking that
  exercise IDs exist). Convert ORM objects to schemas with `Schema.model_validate(obj)`.
- **Repositories** are the only place that touches `Session` queries, commits, and rollbacks.
- **Errors:** raise domain exceptions from `app/shared/errors/` in handlers and map them to HTTP
  status codes in controllers (see `create_workout` in `controllers/workouts.py`). Some existing
  handlers raise `HTTPException` directly; follow the domain-error pattern in new code, but don't
  refactor existing handlers unless the task asks for it.
- **`engine/helpers.py` must stay pure:** no ORM imports, no DB, no I/O. Pass plain values or
  dataclasses in, get plain values out. This keeps metrics trivially unit-testable.

## Conventions

- **Enum-backed columns are plain `str` in the database**, not native Postgres enums. Define the
  enum as a `StrEnum` in `app/shared/enums/`, use it in Pydantic schemas, and store `.value` in the
  model. Do not introduce `sqlalchemy.Enum` columns.
- **Numeric columns** (`weight`, `bodyweight`) come back from the ORM as `Decimal`. Convert with
  `float(...)` at the boundary before passing values into `helpers.py`.
- **Timestamps** are timezone-aware (`TIMESTAMP(timezone=True)`). Use `TimestampMixin` for
  `created_at`/`updated_at` on new tables where it makes sense.
- **Date-range filters are inclusive of the end date:** filter with
  `performed_at < end_date + timedelta(days=1)`, never `<= end_date` on a timestamp column.
- **Time bucketing is two-stage:** sort and group on tuple keys from `sort_key()`
  (ISO year/week, year/month, etc.), then attach display labels from `get_time_bucket_key()`.
  Never sort on the display label strings.
- **Pagination** uses `page` (0-based) and `page_size` (1–100) query params.
- Type-hint everything. Use modern syntax (`str | None`, `list[int]`). Line length is 100.
- Don't shadow builtins in new code (e.g. name a loop variable `set_` rather than `set`).
- Keep changes small and focused on the task. No drive-by refactors or renames.

## Coach engine (app/engine)

- The engine uses the OpenAI **Responses API**. Follow-up calls chain with `previous_response_id`
  and **must re-send `tools=self.TOOLS`**, or the model loses its tool menu.
- Adding a tool requires three things that must stay in sync:
  1. The implementation in `engine/tools.py` (calls handlers, returns JSON-serializable data)
  2. The JSON schema in `Coach.TOOLS`
  3. The entry in `Coach.TOOL_REGISTRY`
- Prefer `"strict": True` schemas. With strict mode, every property must be listed in `required`,
  optional values use `["type", "null"]`, and `additionalProperties` must be `False`.
- Never interpolate model-provided strings into SQL. Tool arguments map to fixed query options or
  are passed as bound parameters through SQLAlchemy.
- `build_instructions()` injects today's date. Keep that behavior; relative dates depend on it.
- The model name lives in `Coach.QUERY_MODEL`. Don't change it unless the task asks.
- RAG is implemented **as a tool the model calls** (e.g. `search_coaching_docs`), not as a fixed
  pipeline that runs on every question. Retrieved results must include `document_id` and
  `chunk_index` so answers can cite sources. Embedding dimension is 1536 (`Vector(1536)`); the
  embedding model must match.

## Database and migrations

- All models live in `app/core/models.py`.
- Every schema change needs an Alembic migration. Autogenerate, then read and fix the generated
  file before committing. Never edit a migration that has already been applied; add a new one.
- pgvector indexes (e.g. HNSW with `vector_cosine_ops`) are written manually in migrations.

## Testing

- Pure helpers: plain unit tests with no database.
- API and repository tests: use the transactional-rollback fixture (each test runs inside a
  transaction that is rolled back) once it exists. Don't write tests that leave data behind.
- Tests must never call the real OpenAI API. Mock `client.responses.create` (or inject a fake
  client) and assert on tool calls and final output.
- New behavior needs a test. Bug fixes need a test that fails before the fix.

## Security

- Never read, print, or edit `.env` files, and never hardcode or log API keys.
- Never log full request bodies or LLM prompts that might contain secrets.
- Add new config through `Settings` in `app/core/config.py`, and add the variable (with a
  placeholder value) to `.env.example`.

## Working on a task

Tasks are given as markdown files with a goal and acceptance criteria.

1. Read the task file and the relevant code before writing anything.
2. If the task is ambiguous or conflicts with this file, stop and ask instead of guessing.
3. Stay within the task's scope. Note unrelated problems you find in your summary instead of
   fixing them.
4. Before finishing, run `ruff check .`, `ruff format .`, and `pytest`, and make sure they pass.
5. End with a short summary: files changed, what you did, how it was tested, and anything you
   were unsure about.

## Do not

- Switch the engine to Chat Completions or add an agent framework (LangChain, etc.).
- Put business logic in controllers or queries in handlers.
- Add dependencies without saying so in your summary, and add them to `pyproject.toml`.
- Change `docker-compose.yaml`, `Dockerfile`, or existing migrations unless the task asks.
