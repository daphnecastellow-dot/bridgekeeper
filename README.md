# Bridgekeeper

**Version:** 0.1  
**Status:** experimental

Bridgekeeper preserves **compact continuity handoffs across time**.

Its job is not to store an entire project history. It records the minimum state needed to return later without losing the difference between:

- what is canonical now
- what changed
- what was corrected
- what remains unresolved
- which earlier handoff is superseded
- where authoritative material can be found

Its central rule:

> **Continuity should preserve state transitions, not silently rewrite the past.**

## The handoff model

A Bridgekeeper file is a snapshot with:

- a project name
- a unique bridge ID
- creation time
- zero or more superseded bridge IDs
- authority pointers
- canonical statements
- changes
- corrections
- unresolved items

Bridgekeeper never decides that something is canonical by itself. Canonical state enters the file only through an explicit command or input record.

## Quick start

```bash
python bridgekeeper.py new handoff.json \
  --project "North Reach research" \
  --bridge-id bridge-015

python bridgekeeper.py authority handoff.json A001 \
  --label "Sourceweave record S004" \
  --location "sourceweave:north-reach:S004" \
  --kind tool-record

python bridgekeeper.py canonical handoff.json \
  "event-date" "1903" \
  --authority A001 \
  --note "Current working date."

python bridgekeeper.py correction handoff.json \
  "event-date" \
  --before "1904" \
  --after "1903" \
  --reason "Earlier transcription was wrong." \
  --authority A001

python bridgekeeper.py unresolved handoff.json \
  "witness-identity" \
  "Identity of the second witness remains unverified." \
  --reopen-when "A contemporaneous named source is found."

python bridgekeeper.py supersede handoff.json bridge-014

python bridgekeeper.py audit handoff.json
python bridgekeeper.py render handoff.json -o handoff.md
python bridgekeeper.py mermaid handoff.json -o handoff.mmd
```

## Authority pointers

Authority pointers are references, not copies of entire source systems.

Examples:

- a Sourceweave record
- an Evidence Ledger item
- a Git commit
- a document section
- a canonical specification
- a local file or external source reference

An authority has:

- an ID local to the handoff
- a label
- a location string
- a kind
- an optional note

Other handoff records may cite one or more authority IDs.

## Canonical state

Canonical entries use explicit keys so later handoffs can identify what changed.

Example:

```json
{
  "key": "event-date",
  "value": "1903",
  "authorities": ["A001"],
  "note": "Current working date."
}
```

Bridgekeeper does not infer canonicality from recency, frequency, or source count.

## Changes and corrections

A **change** records that state moved.

A **correction** records that an earlier state was specifically wrong or superseded by a corrected state.

Those are not interchangeable.

A project may change because a design decision evolved without the earlier state having been erroneous. Bridgekeeper keeps that distinction visible.

## Unresolved items

An unresolved item remains first-class instead of being squeezed into a conclusion.

It can include a `reopen_when` condition so a future session knows what evidence or event would make the question worth revisiting.

## Supersession

A handoff may list earlier bridge IDs that it supersedes.

Supersession means:

> use this handoff as the newer continuity state

It does **not** mean the earlier handoff should be deleted. Older bridges remain useful provenance for how the project arrived here.

## Audit behavior

The structural audit can flag:

- canonical state with no authority pointer
- a correction with no authority pointer
- a change with identical before/after values
- an unresolved item with no reopen condition
- a handoff that supersedes itself

These are structural warnings, not truth judgments.

## Outputs

Bridgekeeper can produce:

- JSON handoff snapshots
- compact Markdown handoffs
- Mermaid continuity graphs
- structural audits

## What Bridgekeeper does not do

Bridgekeeper is not a memory database.

It does not read a project and decide what matters.

It does not infer canonical state.

It does not erase superseded handoffs.

It does not turn unresolved questions into conclusions.

It gives continuity an explicit joint between **before** and **after**.

## Relationship to Tracebridge

Tracebridge moves provenance-aware records **between tools**.

Bridgekeeper moves explicit project state **between moments**.

A Bridgekeeper authority pointer may refer to a Tracebridge ID, but neither tool depends on the other.

## Tests

```bash
python -m unittest discover -s tests -v
```

## License and reuse

**No reuse license has been granted.**

This public build is available for inspection and development by its maintainers. Do not assume that public visibility grants permission to copy, redistribute, modify, sell, incorporate, or relicense the code or documentation.

See [`COPYRIGHT.md`](COPYRIGHT.md).

## Working principle

Keep enough of the bridge that the next state still knows how it got here.
