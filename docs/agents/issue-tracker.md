# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

**Migration note:** GitHub Issues is now the tracker (migrated 2026-11-02). `.scratch/` remains for
specs and research assets, both gitignored and local to the human's checkout: the spec at
`.scratch/<feature-slug>/spec.md`, and ticket-linked research/prototype files under
`.scratch/<effort>/research/`. Tickets, comments, blocking, assignment and state live on GitHub.

## Conventions

- The spec is `.scratch/<feature-slug>/spec.md` — local and gitignored, never pushed. It is the
  design input for the tickets, not a tracker artifact.
- Research and prototype assets that a ticket links to go under `.scratch/<effort>/research/` and
  stay local. Because they are gitignored and unreachable from GitHub, the ticket must reproduce
  the findings that matter in a comment on the issue (see ticket 07 / issue #13 for the pattern).
- Implementation tickets are GitHub issues, one per ticket — never a single combined tickets file.
- Issue bodies are flowing prose paragraphs. Do not hard-wrap at a fixed column width; GitHub
  soft-wraps, and mid-sentence newlines make the text read as choppy fragments. Use blank lines
  between paragraphs, and headings/lists/tables only where structure demands them.
- Triage roles from `docs/agents/triage-labels.md` apply as GitHub labels (`needs-triage`,
  `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`).

Command reference:

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc or
  `--body-file` for multi-line bodies.
- **Read an issue**: `gh issue view <number> --json number,title,body,labels,comments`.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`
  with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`.
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`.
- **Close**: `gh issue close <number> --comment "..."`.

Infer the repo from `git remote -v`; `gh` does this automatically when run inside a clone.

## Pull requests as a triage surface

**PRs as a request surface: no.**

GitHub shares one number space across issues and PRs, so a bare `#42` may be either: resolve with
`gh pr view 42` and fall back to `gh issue view 42`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue with `gh issue create`, writing the body as flowing prose paragraphs and
applying the relevant triage label.

## When a skill says "fetch the relevant ticket"

Read it with `gh issue view <number> --json number,title,body,labels,comments,assignees,parent`.
The user will normally pass the issue number or URL directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: the issue labelled `wayfinder:map`. It holds the Destination / Notes /
  Decisions-so-far / Not-yet-specified / Out-of-scope body and is the canonical map. Create it
  with `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue:
  `gh issue edit <map> --add-sub-issue <child>`, or `gh issue create --parent <map> ...` when
  creating it. If sub-issues are unavailable, fall back to a task list in the map body plus
  `Part of #<map>` at the top of the child body.
- **Ticket type**: exactly one `wayfinder:<type>` label — `wayfinder:grilling`,
  `wayfinder:research`, `wayfinder:prototype`, or `wayfinder:task`. No other labels on a
  wayfinder ticket unless triage adds one.
- **Blocking**: GitHub's native issue dependencies, the canonical and UI-visible representation.
  Add an edge with `gh issue edit <child> --add-blocked-by <blocker>,<blocker>` (or
  `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`,
  where the database id is `gh api repos/<owner>/<repo>/issues/<n> --jq .id`). Read the edges with
  `gh issue view <n> --json blockedBy,blocking`. Where dependencies are unavailable, fall back to a
  `Blocked by: #<n>, #<n>` line near the top of the child body. A ticket is unblocked when every
  blocker is closed.
- **Frontier**: open sub-issues of the map that are unassigned and have no open blocker; first in
  map order (lowest number) wins.

  ```bash
  gh issue list --state open --json number,title,assignees,parent,blockedBy \
    --jq '[.[]
          | select(.parent.number == <map>)
          | select(.assignees | length == 0)
          | select([.blockedBy.nodes[] | select(.state == "OPEN")] | length == 0)
          | {number, title}]
         | sort_by(.number)'
  ```

- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write. Never start work on
  an unclaimed ticket.
- **Resolve**: post the answer as a resolution comment (`gh issue comment <n> --body "..."`), close
  the issue (`gh issue close <n> --reason completed`), then append a context pointer (gist + `#<n>`
  link) to the map issue's **Decisions so far** with `gh issue edit <map> --body-file ...`.
- **Reopen / re-decide**: comment with what changed, reopen the issue, and move its Decisions-so-far
  entry back out if the gist no longer holds.
