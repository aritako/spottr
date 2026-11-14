# The retrieval cutoff is a documented fallback at 0.606

The calibration sweep cannot meet both bars at `k = 5` on the current corpus. The best recall is
66 of 70 positives (94.3%) even with no cutoff, because four positives do not rank their expected
Document in the top 5. The recall bound `P` is therefore infinite and no cutoff can reach 95%.
Issue #8 requires the harness to say so and a human to decide a documented fallback rather than a
silent pass. The human chose `MAX_COSINE_DISTANCE = 0.606` with `DEFAULT_TOP_K = 5`.

This is a fallback, not a calibrated lock. The closed-form lock still runs and still reports that
no qualifying pair exists; this ADR records the value production uses until a later experiment
changes the evidence.

## Expected performance

On the 96-chunk paragraph corpus, 70 positives, 22 retrieval negatives and 6 routing negatives:

- recall@5 is 65 of 70 = 92.9% [84.3-96.9], below the 95% bar.
- retrieval-negative no_match is 21 of 22 = 95.5% [78.2-99.2]; only the 0.5818 negative (low
  testosterone) leaks.
- 0.606 and 0.610 produce the same recall, but 0.610 also leaks the 0.6094 negative (lifting
  shoes), so 0.606 keeps one more negative clear.

The value is the midpoint of the k=7 qualifying interval (`P = 0.5970`, `D = 0.6151`), applied at
`k = 5`. It is not justified by a k=5 lock, because `P` is infinite there. The 92.9% recall is the
price of keeping the cutoff inside the interval that also holds the no-match bar.

The bars gate on point estimates only. Wilson 95% intervals are printed for run-to-run drift
monitoring and never gate a lock.

## Why not k=7

At `(0.606, 7)` the bars are met: recall is 67 of 70 and no_match is 21 of 22. It is the smallest
pair the lock would return. It is rejected because choosing `k` after seeing the sweep changes the
lock rule, and because ADR 0002 shows every returned passage as a user-visible Source; raising
`DEFAULT_TOP_K` from 5 to 7 would show more material in the client.

## Why not keep 0.55

0.55 was a starting guess, never measured on paragraph chunks. On the current corpus, recall at
the 0.5818 candidate cutoff is already only 88.6%, and lower cutoffs do not improve it. Keeping
0.55 would knowingly use a worse fallback than the one measured here.

## Re-ingestion

The sweep measures the 96 paragraph chunks produced after clearing the old corpus. Ingestion is
not idempotent, and `scripts/ingest_corpus.py` skips Documents that already exist, so the runbook
requires `TRUNCATE chunks, documents RESTART IDENTITY;` before re-ingesting whenever chunking or
the embedding input changes. The dev `coach` database is cleared; `coach_test` is never touched.

## Pre-registered next step

This paragraph is written before the agent-query sweep (Phase 3), so the choice is not made after
seeing its result. If the agent-query sweep still fails the bars, the one change tested next is
`text-embedding-3-large` with `dimensions=1536`. That model keeps `Vector(1536)` and the
closed-form lock, but ingest and query must use the same model and dimensions, and the corpus must
be cleared and re-ingested.

Hybrid lexical search is out of scope until a human approves it. Fused lexical and vector scores
are not distances, so they break the `P`/`D` lock this harness depends on.

## Consequences

- Production retrieves with a cutoff that knowingly misses the 95% recall bar on the authored
  set while meeting the 90% no-match bar.
- Any corpus edit, chunking change, golden-set change, embedding-model change, or completed
  agent-query experiment requires a fresh sweep and a review of this fallback.
- The calibration ADR that ADR 0001 deferred is still owed; this document records a fallback, not
  the calibrated lock.
