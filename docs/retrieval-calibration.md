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

# 2. Clear the old corpus. Ingestion is not idempotent and scripts/ingest_corpus.py skips
#    Documents that already exist, so this is required whenever chunking or the embedding
#    input changes. It clears the dev coach database only, never coach_test.
docker compose exec db psql -U coach -d coach -c "TRUNCATE chunks, documents RESTART IDENTITY;"

# 3. Ingest the corpus (host script; needs the API on http://localhost:8000).
python scripts/ingest_corpus.py

# 4. Run the sweep against the published database port.
DATABASE_URL=postgresql+psycopg://coach:coach@localhost:5432/coach \
    python scripts/eval_retrieval.py
```

Pass `--database-url` instead of the environment prefix if you prefer, `--golden-set PATH`
to sweep a different golden set, and `--agent-queries PATH` to embed the coach-written queries
from a captured fixture instead of the raw questions. Capture the fixture with
`python scripts/capture_agent_queries.py` (needs a real key). The run costs one embedding call
for at most 98 questions (pennies) and one local pgvector query per question per candidate
configuration; it never calls the HTTP API.

## When to run it

- **When calibrating**, then update the constants in `app/engine/rag.py` in the same reviewed
  change as the report evidence (and record the values in the ADR).
- **After any corpus change** - a new, edited or removed document moves chunk distances. The
  sweep is trusted but not gated: it does not have to pass to merge a corpus PR, but it is a
  checklist item on one.
- **After editing the golden set**, since the ground truth changed.
- **After any chunking or embedding-input change**, after clearing and re-ingesting the corpus
  as in step 2. Otherwise the database keeps the old chunks and the sweep measures stale data.

## Reading the report

The report starts with a recommendation: it either names the recommended
`MAX_COSINE_DISTANCE` and `DEFAULT_TOP_K` with their evidence, or states plainly that the bars
cannot be met and why. It exits non-zero when no pair meets the bars.

**Cutoff sweep.** One row per candidate cutoff at `k=5`, showing recall@5 and retrieval-negative
no_match with 95% Wilson intervals, pooled document precision, and passage precision. Above the
table, the `P`/`D` line gives the recall bound `P` and the negative bound `D`: every cutoff in
`(P, D]` meets both bars. `P=none` means some positives do not rank their expected Document in
the top 5, so no cutoff can reach the recall bar; `D=none` means no retrieval negative returned a
Passage. The intervals are printed for run-to-run drift monitoring only; the bars gate on the
point estimates, never on the interval bounds.

**Top-k sweep.** When a cutoff locks, one row per `k` at that cutoff, with the same rates and
intervals, document and passage precision, and the `P` bound at each `k`. The smallest `k` that
reaches the recall bar is marked `<- locked`.

**Ranking ceiling.** The recall@k table at the discovery cutoff with no relevance cutoff, for
`k = 1..10`. It shows whether a failure is a ranking problem or a cutoff problem.

**Per-entry failures.** Each positive that missed its expected Document and each retrieval
negative that leaked, at the pair whose failures are most useful: the recommendation if there is
one, otherwise the locked cutoff with a failing top-k, otherwise the most permissive candidate.
Recall failures also print the expected Document's nearest Passage, and its true rank and
distance across every chunk when the runner had the corpus.

**Distances.** Every retrieval negative sorted by nearest distance, then the ten positives with
the largest distance at `k=5`. A negative is marked `<- leaks` when it falls below the
recommended cutoff.

**Routing negatives.** Reported, not gated. These are questions the coach is expected to route
to the data tools, so the sweep lists whether each would leak at the reported cutoff and leaves
the routing judgment to the agent eval (#17).

**Agent queries.** With `--agent-queries`, the header lists the fixture's model, capture date and
instructions SHA, plus the rule counts: positives and negatives with no docs call, entries with
more than one call, calls that set `k`, and routing negatives that called docs. The sweep embeds
the first query per entry; no call is a recall miss for a positive and a correct no_match for a
negative. The agent's `k` is ignored; the sweep still controls `k`.

## Caveats

- The runner issues one local query per question per candidate cutoff. On the current corpus that
  can be tens of thousands of tiny pgvector queries: negligible in money, but potentially a few
  minutes of local time.
- Zero chunks fails clearly before embedding. A partially ingested corpus still runs and surfaces
  missing Documents as recall failures rather than aborting.
- It is not part of the default test suite. The unit tier covers the metrics, lock rules and the
  report with synthetic vectors, so normal `pytest` runs never need a real key.
