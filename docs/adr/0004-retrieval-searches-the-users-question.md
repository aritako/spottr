# Retrieval searches the user's question, not the coach's rewrite

`search_coaching_docs` embeds the user's question verbatim. The coach still decides whether to
search, and still writes the answer from the passages; it no longer writes the search text.

## Evidence

The third calibration experiment (`feat/eval-agent-queries` at `0072489`) captured one first-turn
`gpt-5.4-nano` sample of the query the coach wrote for every golden question. The fixture on that
branch is `app/eval/golden/agent_queries.yaml`: 98 questions and 77 `search_coaching_docs` calls.

- At k=5, coach-written queries recalled 56 of 70 positives, against 66 of 70 for the raw
  questions.
- At the production cutoff 0.606, no_match on coach-written queries was 11 of 22 (50.0%), or 4
  of 15 (26.7%) among the retrieval negatives where the coach actually searched. On raw
  questions it was 21 of 22 (95.5%).
- 26 of the 77 queries contained "autoregulation", 21 contained "deload", and 49 contained
  "guidance", even for questions about triceps or rep ranges. The words come from the tool
  description and instruction topic lists.
- Example: "My triceps are lagging. Should I just tack more sets onto the end of my workout?"
  became a query ending in "autoregulation deload guidance for bringing up a lagging muscle
  group", and `deloads.md` filled all five slots.
- Off-topic questions gained coaching vocabulary too. "Which lifting shoes should I buy?" became
  a shoes query that pulled corpus passages under the cutoff.

The mechanism is a correlation in one sample, not an ablation. The shared vocabulary is visible
in the fixture; it is consistent with the coach copying the tool description and instruction topic
labels.

## What it costs

The coach's rewrite fixed the two autoregulation misses in the raw sweep: "percentage of my max
or how the bar feels" moved from true rank 25 to rank 1, and "when to stop back-off sets" from
17 to 1. Pass-through gives that back. Raw-question recall is 66 of 70 (94.3%) with no cutoff and
65 of 70 (92.9%) at 0.606, below the 95% bar. The fallback in
[ADR 0003](0003-retrieval-fallback-cutoff.md) remains a fallback.

## What the retrieval gate measures from now on

The raw-question sweep over all 70 positives and all 22 retrieval negatives, unchanged. Whether
the coach calls `search_coaching_docs` at all is routing, owned by issue #17; 8 positives did not
call it in the Phase 3 sample. The retrieval gate measures retrieval when the coach calls it, not
end-to-end answer quality, following the precedent that took routing negatives out of the gate in
PR 28.

## Assumption

`ask_coach` takes one question with no conversation history. If chat history is added, a
follow-up such as "what about legs?" loses its topic when searched verbatim, and this decision
must be reopened. Any future query rewriting must be a pre-registered experiment that beats
pass-through on both bars.

## What it does not change

The next retrieval experiment is still the one pre-registered in
[ADR 0003](0003-retrieval-fallback-cutoff.md): `text-embedding-3-large` at `dimensions=1536`, now
run on raw questions. The bars, the lock rule and `CUTOFF_K = 5` are unchanged.
