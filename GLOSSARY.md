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

**Guardrail**:
A post-hoc check on the coach's finished answer, run before the user sees it. The two Guardrails
are the Scope rule and the Grounding rule; both are deterministic code in the engine.
_Avoid_: safety filter, moderation, classifier

**Scope**:
What the coach may answer: questions about the user's logged data, answered from data tools, and
questions about training principles, answered from retrieved Passages. Enforced by the
tool-usage signature — an answer is in Scope only if substantive tool output backs it. Everything
else is rejected.
_Avoid_: scope gate (implies a classification pass before the coach loop, which was rejected)

**Grounding**:
The rule that every numeral in an answer has a Receipt: it appears in tool output, or the
Guardrail derives it from output numbers via a closed whitelist of derivations (difference,
percentage change, sum, average).
_Avoid_: faithful, factual, hallucination check

**Receipt**:
A number scraped from tool output that licenses one number in the answer. An answer may state a
number only if a Receipt exists for it.
_Avoid_: match, hit

**Rejection**:
The canned response that replaces an answer no Guardrail passed or no substantive tool output
backed. Written as static text by the app rather than the model, and carries no Citations.
_Avoid_: refusal (a model-written decline), error

**Violation**:
A failed Guardrail check, carrying its evidence (for example, which number lacks a Receipt). A
fixable Violation earns one retry; a second is rejected.
_Avoid_: failure, flag
