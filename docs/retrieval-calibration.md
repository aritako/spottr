# Retrieval calibration sweep

Internal runbook for calibrating the retrieval constants in `app/engine/rag.py`
(`MAX_COSINE_DISTANCE` and `DEFAULT_TOP_K`) against the authored golden set in
`app/eval/golden/retrieval.yaml`.

This is maintainer tooling, not a user-facing command. Keep it out of the README; it is an
internal runbook. It needs a **real** `OPENAI_API_KEY` (CI only has a dummy key), a local
database with the corpus ingested, and the project's dependencies installed on the host
(`pip install -e ".[dev]"`).

## Run it

From the repository root:

```bash
# 1. Start the database and API, then apply migrations.
docker compose up -d db app
docker compose exec app alembic upgrade head

# 2. Ingest the corpus (host script; needs the API on http://localhost:8000).
python scripts/ingest_corpus.py

# 3. Run the sweep against the published database port.
DATABASE_URL=postgresql+psycopg://coach:coach@localhost:5432/coach \
    python scripts/eval_retrieval.py
```

Pass `--database-url` instead of the environment prefix if you prefer, and `--golden-set PATH`
to sweep a different golden set. The run costs one embedding call for all ~80 questions
(pennies) and one local pgvector query per question per candidate configuration; it never calls
the HTTP API.

## When to run it

- **When calibrating**, then update the constants in `app/engine/rag.py` in the same reviewed
  change as the report evidence (and record the values in the ADR).
- **After any corpus change** — a new, edited or removed document moves chunk distances. The
  sweep is trusted but not gated: it does not have to pass to merge a corpus PR, but it is a
  checklist item on one.
- **After editing the golden set**, since the ground truth changed.

## Reading the report

The report prints one row per candidate cutoff at `k=5` and one row per `k` at the locked
cutoff, with recall@k, Negative no_match, precision and the distance margins. It then names the
recommended `MAX_COSINE_DISTANCE` and `DEFAULT_TOP_K` with their evidence, or states plainly that
the bars cannot be met and why. Per-entry failures name the question and the Passages that were
retrieved instead, and a summary highlights Documents hijacking retrievals. It fails with an
actionable message when the corpus has not been ingested, and exits non-zero when no pair meets
the bars.

## Caveats

- The runner issues one local query per question per candidate cutoff. On the current corpus that
  can be tens of thousands of tiny pgvector queries: negligible in money, but potentially a few
  minutes of local time.
- Zero chunks fails clearly before embedding. A partially ingested corpus still runs and surfaces
  missing Documents as recall failures rather than aborting.
- It is not part of the default test suite. The unit tier covers the metrics, lock rules and the
  report with synthetic vectors, so normal `pytest` runs never need a real key.
