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
