# Coaching Corpus

Seed corpus for the `search_coaching_docs` retrieval tool. Each file is one
coaching topic, written to be ingested through `POST /docs/ingest` as a
`DocumentIngest` payload.

## Conventions (the contract for ingestion tooling)

- One topic per file, `kebab-case.md`, under `docs/corpus/`.
- The H1 line of each file is the document title. It maps to `title` in the
  ingest payload and is the name the coach cites in answers.
- `source` in the ingest payload is the corpus filename (for example
  `progressive-overload.md`), giving each database row a direct pointer back
  to the repo file that produced it.
- `text` is the entire file contents, including the H1 and the trailing
  Sources section.
- Each file ends with a `## Sources` section listing the papers and articles
  it is grounded in, with DOIs or URLs. Provenance is for human review; the
  retrieval tool does not return the source field to the model.

## Writing constraints

The chunker (`app/engine/rag.py`, `chunk_text`) splits on whitespace into
500-word chunks with 50 words of overlap. It ignores markdown structure, so
corpus files are written to survive naive chunking:

- Plain prose in short, self-contained sections under a few H2 headings.
- No tables, no code blocks, no nested bullet structures.
- Key terms (progressive overload, RIR, deload, tonnage) are repeated
  naturally so any 500-word window stands alone and stays retrievable.
- External docs run roughly 600-800 words; internal docs are shorter.

## Contents

External coaching topics: progressive overload, volume landmarks, rep ranges
and load, training frequency, periodization, autoregulation with RIR and RPE,
deloads, fatigue and recovery, exercise selection and ordering, strength vs
hypertrophy, main-lift technique, warm-ups and injury prevention.

Internal topics (current app capabilities only, extended when new metrics
ship): reading your Spottr numbers, judging trends in your training data.

## Extending

Follow the same conventions. Ground every new document in sources that can be
verified online (title plus DOI or URL), and never cite a reference that has
not been checked. Write to the metrics and tools that actually exist in the
app at the time of writing.
