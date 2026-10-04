# Bridgekeeper 0.1 handoff specification

Bridgekeeper stores compact continuity snapshots.

## Top-level object

```json
{
  "format": "bridgekeeper/0.1",
  "project": "North Reach research",
  "bridge_id": "bridge-015",
  "created_at": "2026-10-04T22:30:00Z",
  "supersedes": ["bridge-014"],
  "authorities": [],
  "canonical": [],
  "changes": [],
  "corrections": [],
  "unresolved": []
}
```

## Authority

```json
{
  "id": "A001",
  "label": "Sourceweave record S004",
  "location": "sourceweave:north-reach:S004",
  "kind": "tool-record",
  "note": ""
}
```

Suggested authority kinds:

- `tool-record`
- `document`
- `repository`
- `commit`
- `specification`
- `conversation`
- `other`

The location field is deliberately a string. Bridgekeeper does not assume every authoritative reference is a URL.

## Canonical entry

```json
{
  "key": "event-date",
  "value": "1903",
  "authorities": ["A001"],
  "note": "Current working date."
}
```

Keys must be unique inside one handoff.

## Change

```json
{
  "key": "source-classification",
  "before": "reference",
  "after": "later-retelling",
  "reason": "Reclassified after provenance review.",
  "authorities": ["A002"]
}
```

A change does not imply the previous state was erroneous.

## Correction

```json
{
  "key": "event-date",
  "before": "1904",
  "after": "1903",
  "reason": "Earlier transcription was wrong.",
  "authorities": ["A001"]
}
```

A correction explicitly identifies an earlier state as requiring replacement.

## Unresolved item

```json
{
  "key": "witness-identity",
  "question": "Identity of the second witness remains unverified.",
  "authorities": [],
  "reopen_when": "A contemporaneous named source is found.",
  "note": ""
}
```

Keys must be unique inside the unresolved set.

## Supersession

`supersedes` contains bridge IDs, not filenames.

A newer handoff may supersede one or more older handoffs. Older handoffs remain valid historical records of earlier state.

## Structural rules

A valid Bridgekeeper file must:

1. use format `bridgekeeper/0.1`
2. have a non-empty project name and bridge ID
3. not supersede itself
4. use unique authority IDs
5. use unique canonical keys
6. use unique unresolved keys
7. ensure every cited authority exists
8. keep change/correction keys and values explicit
9. keep unresolved questions explicit

The audit may warn about structurally thin records that are still valid JSON, such as canonical state with no authority pointer.

## Boundary rule

Bridgekeeper records declared continuity state.

It must never infer a canonical value merely because:

- it is newest
- it appears most often
- it has the most sources
- another tool assigned it a high confidence
- an earlier bridge omitted competing values

Canonicality is an explicit project decision and should remain visibly so.
