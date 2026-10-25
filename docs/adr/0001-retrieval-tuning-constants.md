# Retrieval tuning constants live in the engine, not in Settings

`DEFAULT_TOP_K`, `MAX_TOP_K`, `MAX_COSINE_DISTANCE` and the embedding dimension are module
constants in `app/engine/rag.py` rather than `Settings` fields. They are parameters of the
retrieval algorithm, not deployment configuration: changing one changes answer quality and needs
to be re-tuned against the corpus, while `Settings` exists for values an operator supplies per
environment (credentials, hostnames). `AGENTS.md` requires every new `Settings` field to appear in
`.env.example`; advertising a similarity cutoff there would invite it being tuned blind on a
machine where the corpus is different.

The handler passes `MAX_COSINE_DISTANCE` explicitly into the repository so the data layer never
imports the engine, and the cutoff is applied in SQL rather than by filtering rows in Python.

## Consequences

- Re-tuning is a code change, reviewed like any other, rather than an env edit.
- A future move to per-environment tuning means promoting these to `Settings` deliberately, and
  documenting the cutoff in `.env.example` at that point.
- `scripts/calibrate_retrieval.py` exists because the cutoff cannot be judged without printing
  real distances from the seeded corpus.
