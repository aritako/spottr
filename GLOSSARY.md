# Spottr

An AI strength-training coach that answers questions from the user's logged workouts and from a
corpus of coaching material, citing its sources.

## Language

**Coaching corpus**:
The body of coaching material the coach is allowed to answer general training questions from.
_Avoid_: knowledge base, knowledge corpus, RAG corpus

**Document**:
One ingested piece of coaching material, with a title and an optional source (filename or URL).
_Avoid_: file, article, paper

**Chunk**:
A stored excerpt of one Document, with an index that locates it within that Document.
_Avoid_: passage (when referring to the stored row), fragment

**Passage**:
A Chunk returned by retrieval, carrying its Document and Chunk index so it can be cited.
_Avoid_: hit, result, match

**Relevance threshold**:
The distance beyond which a Passage no longer counts as relevant to a question. When every
candidate is beyond it, retrieval reports no match and the coach says the corpus does not cover
the question rather than answering from general knowledge.
_Avoid_: score, similarity cutoff

**Citation**:
A Passage the coach consulted, surfaced in the answer as a source reference. A citation records
that the coach read the passage, not that the answer text depends on it.
_Avoid_: reference, footnote, source (for the object itself), document (for a Document's title)

**Retrieval**:
Finding the Passages most relevant to a question. Distinct from ingestion, which stores them.
_Avoid_: search (as a noun for the concept)

**Metric**:
A named aggregation of logged sets over time — `e1rm` or `tonnage` in the MVP. The `Metric` enum
lists exactly the metrics that are built; nothing else is callable by the coach or the API.
_Avoid_: stat, statistic, measure

**Tonnage**:
Weight × reps, summed over the sets in a bucket. The API term for what lifters call "volume":
the UI may say volume, the API says tonnage.
_Avoid_: volume (as the API or domain term), total work

**e1RM**:
Estimated one-rep max of a set: weight × (1 + reps / 30) (Epley), rounded to two decimals. A
bucket's e1RM is the maximum over its sets. Distinct from an actual 1RM, which the app never
claims to know.
_Avoid_: 1RM, one-rep max (for the estimate), PR

**Time bucket**:
The interval a Series groups by — day, week, month, or year. Identified internally by the tuple
`sort_key()` returns and labeled for display by `get_time_bucket_key()`; sorting happens on the
tuple, never on the label.
_Avoid_: period, window, timeframe

**Series**:
The ordered Time buckets for one Metric — one exercise's buckets, or one bucketed list per
exercise when no exercise is specified. Chronological, each entry a (label, value) pair.
_Avoid_: trend, chart data, results

**Top set**:
The set with the highest e1RM for one exercise within one workout; ties go to the earliest
`set_index`. Session tables and the Best-set card show top sets.
_Avoid_: best set (for the per-workout object), heaviest set

**Additive metric**:
A Metric whose total across exercises is meaningful — tonnage. e1RM is not additive: no
cross-exercise total is ever computed for it, because a max across lifts only picks the
strongest lift.
_Avoid_: sum metric, total metric
