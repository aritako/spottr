# Citations record the passages the coach consulted, not the ones it used

`AskResponse.citations` lists every passage returned by `search_coaching_docs` during a request,
deduplicated on `(document_id, chunk_index)`. It does not claim that the answer text depends on
each one.

The alternative — having the model report which passages it used — is more faithful but requires
either parsing inline markers or a structured trailing field, and the coaching model is a small,
fast one that will miscount references. A wrong citation is worse than an extra one, so the API
errs toward over-reporting and the UI labels them "Sources", which is honest about what they are:
material the coach read. The word "citation" therefore means "a passage the coach consulted", and
`GLOSSARY.md` records that.

## Consequences

- A user can see a source the answer did not lean on.
- Answers name the documents they drew on in a closing prose sentence; they never emit numbered
  inline markers, because nothing in the client renders them.
- Making citations exact later is an additive change (a second field), not a breaking one.
