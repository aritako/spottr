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

The chunker (`app/engine/rag.py`, `chunk_document`) splits documents by
paragraph. Paragraphs under 40 words merge forward into the next paragraph,
and paragraphs over 300 words are split. Each chunk is embedded with the
document title in front of it; the trailing `## Sources` section is never
embedded. Keep `text` in the ingest payload the whole file. Write so each
paragraph stands alone:

- Plain prose in short, self-contained paragraphs.
- No tables, no code blocks, no nested bullet structures.
- Each paragraph should make sense on its own and name its key terms
  (progressive overload, RIR, deload, tonnage) so it stays retrievable.
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

Every Document needs at least three golden questions pointing at it in
`app/eval/golden/retrieval.yaml`; the default test run enforces this.
