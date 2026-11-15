# Guardrails validate the finished answer, not the incoming question

The coach's Guardrails are deterministic checks applied after the Responses API loop ends, not a
classification pass applied before it. Two checks run on every answer: a Scope rule on the
tool-usage signature and a Grounding rule on the numbers in the answer text. They live in
`app/engine/guardrails.py` as pure functions; `coach.py` orchestrates what happens next — a retry,
or a canned Rejection. Issue #9 settled this mechanism; issue #29 builds it.

## Why not a scope classifier

A cheap classification pass before the loop was the leading alternative. The calibration evidence
against it: the six data-question routing negatives retrieve corpus passages at distance
0.4420-0.5930, far under the production cutoff of 0.606
([ADR 0003](0003-retrieval-fallback-cutoff.md)), so retrieval similarity cannot separate a data
question from a coaching question — and a classifier makes the same judgment with the same failure
surface while adding a model call to every question and turning each misclassification into a hard
rejection of a valid question. PR #28's evidence says routing is the measured weak point (8 of 70
positives never called `search_coaching_docs` in the Phase 3 sample). A post-hoc validator retries
the model's own misroutes and rescues exactly those cases; a front gate would have rejected them
up front.

## Why not prompt-only

The instructions already direct the model to retrieve before answering, refuse what the corpus
does not cover, and never invent citations — but instructions verify nothing at runtime. The map's
goal is an enforcement claim: data answers exclusively from tool results, coaching answers
exclusively from retrieved Passages, anything else rejected. Under prompt-only enforcement a
hallucinated number ships to the user, and an offline answer-level evaluation would report the
failure after it happened. Only the citation half was already enforced
([ADR 0002](0002-citations-record-consulted-passages.md) collects citations server-side from actual
tool output); this decision extends that pattern from citations to scope and numbers.

## The Scope rule

An answer is legitimate only if substantive tool output backs it: data rows, an exercise list, or
retrieved Passages. When the loop ends with zero tool calls, or with every tool result empty
(`no_match`, "No matching workout data found", `empty_corpus`), the engine discards the model's
final text and returns a canned message. Distinguishing a genuine refusal from a from-memory
answer in free text is the same classification problem the scope classifier was rejected for;
replacing both with the same canned message makes the distinction unnecessary. Greetings land on
the capabilities message, which teaches the boundary.

## The Grounding rule

Every numeral in the answer needs a Receipt. A receipt is either the number appearing in tool
output after format normalization (`12,400` matches `12400.0`), or the validator deriving it from
output numbers with a closed whitelist of derivations: difference, percentage change, sum,
average. The validator computes the derivations itself — the model's arithmetic is never trusted,
only re-derived. Rounding to whole percent is accepted for derived values. Spelled-out numbers are
not checked. There is no tolerance band: a number near a real one is not the real one. Each new
derivation form is a deliberate decision, added only after real traffic shows a legitimate answer
was blocked.

## Violations, retry, rejection

A fixable Violation — a number without a receipt, or an answer with no tool calls — gets exactly
one retry: a new turn carrying the specific evidence ("12,400 is not present in or derivable from
the tool results"), chained with `previous_response_id` and the re-sent tool menu and
instructions, consuming one loop iteration. A second violation is rejected. Outcomes the model
cannot fix (every tool legitimately empty) normalize immediately without a retry.

Rejections are static strings written by the app: out-of-scope (naming what the coach can
answer), nothing-found, and couldn't-complete. A canned rejection carries no citations, because a
Citation records a passage consulted for an answer and a rejection has no answer
([ADR 0002](0002-citations-record-consulted-passages.md)).

## Loop repairs that ride with this

An unknown tool name receives an explicit error output instead of being silently skipped — every
`function_call` must get its `function_call_output`. The 5-iteration cap returns the
couldn't-complete message and logs the tools in flight instead of failing silently. Both live in
`coach.py`, the same file the Guardrail orchestration lands in; they are part of issue #29, not
separate work. Case-sensitive exercise-name matching is a data bug outside this mechanism,
triaged in the roadmap.

## Residual risks accepted

- A data question answered from corpus Passages passes the Grounding rule when its numbers trace
  to those passages: grounded in the wrong source, invisible to the receipts check. The
  instructions mitigate; intent-checking is out of the MVP.
- Spelled-out numbers ("twenty percent") bypass Grounding.
- Whitelist gaps reject legitimate answers under the two-strike rule until tuned; unit
  conversions, for example, are not whitelisted.
- The Scope rule assumes one-question turns, as
  [ADR 0004](0004-retrieval-searches-the-users-question.md) does. Follow-ups ("why?") can
  legitimately use no tools and would be wrongly normalized; the persisted-conversations work item
  must revisit this rule.

## Verification

Unit tests cover the pure validators: each Violation type, each derivation recipe, the
normalization rule. Mocked-loop functional tests script the failure paths — a hallucinating model
triggers the retry and then the rejection; a clean model's answer ships unchanged. Behavioral
routing is verified by dogfooding, which is issue #29's mandate. An offline answer-level
evaluation harness remains a roadmap item, not part of this mechanism.

## Consequences

- `app/engine/helpers.py` keeps its single purpose; Guardrails get their own pure module that
  `app/eval` can import offline.
- `AskResponse` is unchanged: a rejection is an answer value with empty citations, so no client
  change is forced.
- Reversal toward a classifier or prompt-only means deleting tested machinery and re-deciding the
  rejection UX; this document is the record of why that should not be casual.
