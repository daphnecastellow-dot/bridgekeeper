#!/usr/bin/env python3
"""Preserve compact continuity handoffs without silently rewriting prior state."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

FORMAT = "bridgekeeper/0.1"
AUTHORITY_KINDS = (
    "tool-record", "document", "repository", "commit",
    "specification", "conversation", "other",
)


class BridgekeeperError(Exception):
    pass


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_handoff(project: str, bridge_id: str) -> dict[str, Any]:
    project = project.strip()
    bridge_id = bridge_id.strip()
    if not project:
        raise BridgekeeperError("project cannot be empty")
    if not bridge_id:
        raise BridgekeeperError("bridge id cannot be empty")
    return {
        "format": FORMAT,
        "project": project,
        "bridge_id": bridge_id,
        "created_at": now_utc(),
        "supersedes": [],
        "authorities": [],
        "canonical": [],
        "changes": [],
        "corrections": [],
        "unresolved": [],
    }


def unique(values: list[str] | None) -> list[str]:
    return list(dict.fromkeys(values or []))


def authority_ids(data: dict[str, Any]) -> set[str]:
    return {item["id"] for item in data["authorities"]}


def require_authorities(data: dict[str, Any], refs: list[str] | None) -> list[str]:
    refs = unique(refs)
    known = authority_ids(data)
    unknown = [ref for ref in refs if ref not in known]
    if unknown:
        raise BridgekeeperError("unknown authority: " + ", ".join(unknown))
    return refs


def add_authority(
    data: dict[str, Any],
    authority_id: str,
    label: str,
    location: str,
    kind: str = "other",
    note: str = "",
) -> None:
    authority_id = authority_id.strip()
    label = label.strip()
    location = location.strip()
    if not authority_id or not label or not location:
        raise BridgekeeperError("authority id, label, and location cannot be empty")
    if kind not in AUTHORITY_KINDS:
        raise BridgekeeperError(f"invalid authority kind: {kind}")
    if authority_id in authority_ids(data):
        raise BridgekeeperError(f"duplicate authority id: {authority_id}")
    data["authorities"].append({
        "id": authority_id,
        "label": label,
        "location": location,
        "kind": kind,
        "note": note,
    })


def set_canonical(
    data: dict[str, Any],
    key: str,
    value: Any,
    authorities: list[str] | None = None,
    note: str = "",
) -> None:
    key = key.strip()
    if not key:
        raise BridgekeeperError("canonical key cannot be empty")
    refs = require_authorities(data, authorities)
    for item in data["canonical"]:
        if item["key"] == key:
            raise BridgekeeperError(f"canonical key already exists: {key}")
    data["canonical"].append({
        "key": key,
        "value": value,
        "authorities": refs,
        "note": note,
    })


def add_transition(
    data: dict[str, Any],
    bucket: str,
    key: str,
    before: Any,
    after: Any,
    reason: str,
    authorities: list[str] | None = None,
) -> None:
    key = key.strip()
    reason = reason.strip()
    if bucket not in ("changes", "corrections"):
        raise BridgekeeperError("invalid transition bucket")
    if not key:
        raise BridgekeeperError("transition key cannot be empty")
    if not reason:
        raise BridgekeeperError("transition reason cannot be empty")
    refs = require_authorities(data, authorities)
    data[bucket].append({
        "key": key,
        "before": before,
        "after": after,
        "reason": reason,
        "authorities": refs,
    })


def add_unresolved(
    data: dict[str, Any],
    key: str,
    question: str,
    authorities: list[str] | None = None,
    reopen_when: str = "",
    note: str = "",
) -> None:
    key = key.strip()
    question = question.strip()
    if not key or not question:
        raise BridgekeeperError("unresolved key and question cannot be empty")
    if any(item["key"] == key for item in data["unresolved"]):
        raise BridgekeeperError(f"unresolved key already exists: {key}")
    refs = require_authorities(data, authorities)
    data["unresolved"].append({
        "key": key,
        "question": question,
        "authorities": refs,
        "reopen_when": reopen_when,
        "note": note,
    })


def add_supersedes(data: dict[str, Any], bridge_id: str) -> None:
    bridge_id = bridge_id.strip()
    if not bridge_id:
        raise BridgekeeperError("superseded bridge id cannot be empty")
    if bridge_id == data["bridge_id"]:
        raise BridgekeeperError("a handoff cannot supersede itself")
    if bridge_id not in data["supersedes"]:
        data["supersedes"].append(bridge_id)


def validate(data: dict[str, Any]) -> None:
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise BridgekeeperError("unsupported handoff format")
    if not isinstance(data.get("project"), str) or not data["project"].strip():
        raise BridgekeeperError("handoff requires project")
    if not isinstance(data.get("bridge_id"), str) or not data["bridge_id"].strip():
        raise BridgekeeperError("handoff requires bridge_id")
    if not isinstance(data.get("created_at"), str) or not data["created_at"].strip():
        raise BridgekeeperError("handoff requires created_at")

    for key in ("supersedes", "authorities", "canonical", "changes", "corrections", "unresolved"):
        if not isinstance(data.get(key), list):
            raise BridgekeeperError(f"handoff requires {key} list")

    if data["bridge_id"] in data["supersedes"]:
        raise BridgekeeperError("handoff cannot supersede itself")
    if len(data["supersedes"]) != len(set(data["supersedes"])):
        raise BridgekeeperError("duplicate superseded bridge id")

    known: set[str] = set()
    for item in data["authorities"]:
        aid = item.get("id")
        if not isinstance(aid, str) or not aid.strip() or aid in known:
            raise BridgekeeperError("invalid or duplicate authority id")
        known.add(aid)
        if not isinstance(item.get("label"), str) or not item["label"].strip():
            raise BridgekeeperError(f"{aid}: authority label cannot be empty")
        if not isinstance(item.get("location"), str) or not item["location"].strip():
            raise BridgekeeperError(f"{aid}: authority location cannot be empty")
        if item.get("kind") not in AUTHORITY_KINDS:
            raise BridgekeeperError(f"{aid}: invalid authority kind")
        if not isinstance(item.get("note"), str):
            raise BridgekeeperError(f"{aid}: authority note must be a string")

    canonical_keys: set[str] = set()
    for item in data["canonical"]:
        key = item.get("key")
        if not isinstance(key, str) or not key.strip() or key in canonical_keys:
            raise BridgekeeperError("invalid or duplicate canonical key")
        canonical_keys.add(key)
        _validate_refs(item, known, key)
        if not isinstance(item.get("note"), str):
            raise BridgekeeperError(f"{key}: canonical note must be a string")

    for bucket in ("changes", "corrections"):
        for index, item in enumerate(data[bucket], start=1):
            key = item.get("key")
            if not isinstance(key, str) or not key.strip():
                raise BridgekeeperError(f"{bucket}[{index}]: missing key")
            if "before" not in item or "after" not in item:
                raise BridgekeeperError(f"{bucket}[{index}]: before and after are required")
            if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                raise BridgekeeperError(f"{bucket}[{index}]: reason is required")
            _validate_refs(item, known, f"{bucket}[{index}]")

    unresolved_keys: set[str] = set()
    for item in data["unresolved"]:
        key = item.get("key")
        if not isinstance(key, str) or not key.strip() or key in unresolved_keys:
            raise BridgekeeperError("invalid or duplicate unresolved key")
        unresolved_keys.add(key)
        if not isinstance(item.get("question"), str) or not item["question"].strip():
            raise BridgekeeperError(f"{key}: unresolved question cannot be empty")
        _validate_refs(item, known, key)
        if not isinstance(item.get("reopen_when"), str):
            raise BridgekeeperError(f"{key}: reopen_when must be a string")
        if not isinstance(item.get("note"), str):
            raise BridgekeeperError(f"{key}: unresolved note must be a string")


def _validate_refs(item: dict[str, Any], known: set[str], label: str) -> None:
    refs = item.get("authorities")
    if not isinstance(refs, list):
        raise BridgekeeperError(f"{label}: authorities must be a list")
    if len(refs) != len(set(refs)):
        raise BridgekeeperError(f"{label}: duplicate authority reference")
    for ref in refs:
        if ref not in known:
            raise BridgekeeperError(f"{label}: unknown authority {ref}")


def audit(data: dict[str, Any]) -> list[str]:
    findings: list[str] = []

    if data["bridge_id"] in data["supersedes"]:
        findings.append("handoff supersedes itself")

    for item in data["canonical"]:
        if not item["authorities"]:
            findings.append(f"canonical {item['key']}: no authority pointer")

    for index, item in enumerate(data["changes"], start=1):
        if item["before"] == item["after"]:
            findings.append(f"change {index} ({item['key']}): before and after are identical")
        if not item["authorities"]:
            findings.append(f"change {index} ({item['key']}): no authority pointer")

    for index, item in enumerate(data["corrections"], start=1):
        if item["before"] == item["after"]:
            findings.append(f"correction {index} ({item['key']}): before and after are identical")
        if not item["authorities"]:
            findings.append(f"correction {index} ({item['key']}): no authority pointer")

    for item in data["unresolved"]:
        if not item["reopen_when"].strip():
            findings.append(f"unresolved {item['key']}: no reopen condition")

    return findings


def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise BridgekeeperError(f"handoff not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BridgekeeperError(f"invalid JSON: {exc}") from exc
    validate(data)
    return data


def save(path: str | Path, data: dict[str, Any]) -> None:
    validate(data)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def render_markdown(data: dict[str, Any]) -> str:
    authority_map = {item["id"]: item for item in data["authorities"]}
    lines = [
        f"# {data['project']} continuity handoff",
        "",
        f"**Bridge:** {data['bridge_id']}  ",
        f"**Created:** {data['created_at']}",
        "",
    ]

    if data["supersedes"]:
        lines += ["**Supersedes:** " + ", ".join(data["supersedes"]), ""]

    lines += ["## Canonical now", ""]
    if not data["canonical"]:
        lines += ["_No canonical entries recorded._", ""]
    for item in data["canonical"]:
        lines += [f"### {item['key']}", "", f"**Value:** {json.dumps(item['value'], ensure_ascii=False)}", ""]
        if item["note"]:
            lines += [item["note"], ""]
        lines += _render_authorities(item["authorities"], authority_map)

    lines += ["## Changes", ""]
    if not data["changes"]:
        lines += ["_No changes recorded._", ""]
    for item in data["changes"]:
        lines += [
            f"### {item['key']}",
            "",
            f"- Before: {json.dumps(item['before'], ensure_ascii=False)}",
            f"- After: {json.dumps(item['after'], ensure_ascii=False)}",
            f"- Reason: {item['reason']}",
            "",
        ]
        lines += _render_authorities(item["authorities"], authority_map)

    lines += ["## Corrections", ""]
    if not data["corrections"]:
        lines += ["_No corrections recorded._", ""]
    for item in data["corrections"]:
        lines += [
            f"### {item['key']}",
            "",
            f"- Incorrect/earlier: {json.dumps(item['before'], ensure_ascii=False)}",
            f"- Corrected: {json.dumps(item['after'], ensure_ascii=False)}",
            f"- Reason: {item['reason']}",
            "",
        ]
        lines += _render_authorities(item["authorities"], authority_map)

    lines += ["## Unresolved", ""]
    if not data["unresolved"]:
        lines += ["_No unresolved items recorded._", ""]
    for item in data["unresolved"]:
        lines += [f"### {item['key']}", "", item["question"], ""]
        if item["reopen_when"]:
            lines += [f"**Reopen when:** {item['reopen_when']}", ""]
        if item["note"]:
            lines += [item["note"], ""]
        lines += _render_authorities(item["authorities"], authority_map)

    lines += ["## Structural audit", ""]
    findings = audit(data)
    lines += [f"- {finding}" for finding in findings] if findings else ["_No structural audit flags._"]
    return "\n".join(lines).rstrip() + "\n"


def _render_authorities(refs: list[str], authority_map: dict[str, dict[str, Any]]) -> list[str]:
    if not refs:
        return []
    lines = ["**Authority:**"]
    for ref in refs:
        item = authority_map[ref]
        lines.append(f"- {ref}: {item['label']} ({item['location']})")
    lines.append("")
    return lines


def render_mermaid(data: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    current = "CURRENT"
    current_label = f"{data['bridge_id']} · {data['project']}".replace('"', "'")
    lines.append(f'  {current}["{current_label}"]')

    for index, old in enumerate(data["supersedes"], start=1):
        node = f"OLD{index:03d}"
        label = old.replace('"', "'")
        lines.append(f'  {node}["{label}"]')
        lines.append(f'  {node} -->|"superseded by"| {current}')

    for index, item in enumerate(data["canonical"], start=1):
        node = f"C{index:03d}"
        label = f"{item['key']} = {item['value']}".replace('"', "'").replace("\n", " ")
        lines.append(f'  {current} -->|"canonical"| {node}["{label}"]')

    for index, item in enumerate(data["corrections"], start=1):
        node = f"X{index:03d}"
        label = f"{item['key']}: {item['before']} → {item['after']}".replace('"', "'").replace("\n", " ")
        lines.append(f'  {current} -->|"correction"| {node}["{label}"]')

    for index, item in enumerate(data["unresolved"], start=1):
        node = f"U{index:03d}"
        label = f"{item['key']}: {item['question']}".replace('"', "'").replace("\n", " ")
        lines.append(f'  {current} -->|"unresolved"| {node}["{label}"]')

    return "\n".join(lines) + "\n"


def summary(data: dict[str, Any]) -> str:
    return (
        f"{data['project']} / {data['bridge_id']}: "
        f"{len(data['canonical'])} canonical, "
        f"{len(data['changes'])} change(s), "
        f"{len(data['corrections'])} correction(s), "
        f"{len(data['unresolved'])} unresolved, "
        f"{len(audit(data))} audit flag(s)"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bridgekeeper", description="Preserve compact continuity handoffs across time.")
    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("new")
    q.add_argument("file")
    q.add_argument("--project", required=True)
    q.add_argument("--bridge-id", required=True)

    q = sub.add_parser("authority")
    q.add_argument("file")
    q.add_argument("authority_id")
    q.add_argument("--label", required=True)
    q.add_argument("--location", required=True)
    q.add_argument("--kind", choices=AUTHORITY_KINDS, default="other")
    q.add_argument("--note", default="")

    q = sub.add_parser("canonical")
    q.add_argument("file")
    q.add_argument("key")
    q.add_argument("value")
    q.add_argument("--authority", action="append", default=[])
    q.add_argument("--note", default="")

    for name in ("change", "correction"):
        q = sub.add_parser(name)
        q.add_argument("file")
        q.add_argument("key")
        q.add_argument("--before", required=True)
        q.add_argument("--after", required=True)
        q.add_argument("--reason", required=True)
        q.add_argument("--authority", action="append", default=[])

    q = sub.add_parser("unresolved")
    q.add_argument("file")
    q.add_argument("key")
    q.add_argument("question")
    q.add_argument("--authority", action="append", default=[])
    q.add_argument("--reopen-when", default="")
    q.add_argument("--note", default="")

    q = sub.add_parser("supersede")
    q.add_argument("file")
    q.add_argument("bridge_id")

    for name in ("show", "validate", "audit"):
        q = sub.add_parser(name)
        q.add_argument("file")

    for name in ("render", "mermaid"):
        q = sub.add_parser(name)
        q.add_argument("file")
        q.add_argument("-o", "--output")

    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "new":
            if Path(args.file).exists():
                raise BridgekeeperError(f"refusing to overwrite existing file: {args.file}")
            save(args.file, new_handoff(args.project, args.bridge_id))
            print(f"created {args.file}")
            return 0

        data = load(args.file)

        if args.command == "authority":
            add_authority(data, args.authority_id, args.label, args.location, args.kind, args.note)
            save(args.file, data)
            print(args.authority_id)
        elif args.command == "canonical":
            set_canonical(data, args.key, parse_value(args.value), args.authority, args.note)
            save(args.file, data)
            print(args.key)
        elif args.command in ("change", "correction"):
            add_transition(
                data,
                "changes" if args.command == "change" else "corrections",
                args.key,
                parse_value(args.before),
                parse_value(args.after),
                args.reason,
                args.authority,
            )
            save(args.file, data)
            print(args.key)
        elif args.command == "unresolved":
            add_unresolved(data, args.key, args.question, args.authority, args.reopen_when, args.note)
            save(args.file, data)
            print(args.key)
        elif args.command == "supersede":
            add_supersedes(data, args.bridge_id)
            save(args.file, data)
            print(args.bridge_id)
        elif args.command == "show":
            print(summary(data))
        elif args.command == "validate":
            print(f"ok: {args.file}")
        elif args.command == "audit":
            findings = audit(data)
            print("\n".join(findings) if findings else "no structural audit flags")
        else:
            output = render_markdown(data) if args.command == "render" else render_mermaid(data)
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
                print(args.output)
            else:
                print(output, end="")
        return 0
    except BridgekeeperError as exc:
        print(f"bridgekeeper: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
