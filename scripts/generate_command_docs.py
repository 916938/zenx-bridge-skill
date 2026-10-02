#!/usr/bin/env python3
"""Generate (or verify) the command tables in SKILL.md and references/protocol.md.

Single source of truth: skill/references/command-registry.json.

Usage:
    python3 scripts/generate_command_docs.py            # rewrite the marked blocks
    python3 scripts/generate_command_docs.py --check    # verify only; exit 1 on drift

Only the lines between <!-- BEGIN GENERATED: <id> --> and
<!-- END GENERATED: <id> --> are replaced. Everything the humans wrote
(decision trees, red lines, caveats) is left untouched.

Why `cli` and `protocol_purpose` exist: the same command is documented twice
with different intent — SKILL.md shows the CLI invocation (with `--session`),
protocol.md shows the protocol shape (bare subcommand + wire arguments). One
field cannot express both, so the registry carries both forms and the
generator picks per block.

Zero third-party dependencies; each file keeps its original line endings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "skill" / "references" / "command-registry.json"

SKILL = ROOT / "skill" / "SKILL.md"
PROTOCOL = ROOT / "skill" / "references" / "protocol.md"

# block id -> (file, style)
#   "table"   : markdown table with the given header
#   "bullets" : `- \`cmd\` - purpose` list
#   "pairs"   : table without the Action column
BLOCKS: dict[str, dict] = {
    "skill-action-map": {"file": SKILL, "style": "table", "header": ("Action", "BrowserSkill Command", "Use when")},
    "skill-additional": {"file": SKILL, "style": "bullets"},
    "protocol-actions": {"file": PROTOCOL, "style": "table", "header": ("Action", "BrowserSkill Command", "Arguments", "Purpose")},
    "protocol-additional": {"file": PROTOCOL, "style": "table", "header": ("Action", "Command", "Purpose")},
}

BEGIN = "<!-- BEGIN GENERATED:"
END = "<!-- END GENERATED:"


class RegistryError(Exception):
    """Raised when the registry is malformed or a marker is missing."""


def load_registry(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RegistryError(f"registry not found: {path}")
    except json.JSONDecodeError as exc:
        raise RegistryError(f"registry is not valid JSON: {exc}")

    if not isinstance(data, dict):
        raise RegistryError("registry root must be an object")
    tiers = data.get("tiers")
    if not isinstance(tiers, dict) or not tiers:
        raise RegistryError("registry must define a non-empty 'tiers' object")
    actions = data.get("actions")
    if not isinstance(actions, list) or not actions:
        raise RegistryError("registry must define a non-empty 'actions' list")

    seen: set[str] = set()
    for e in actions:
        if not isinstance(e, dict):
            raise RegistryError("each action must be an object")
        for field in ("action", "command", "tier", "purpose"):
            if not isinstance(e.get(field), str) or not e[field].strip():
                raise RegistryError(f"action {e.get('action')!r}: missing/empty '{field}'")
        if e["tier"] not in tiers:
            raise RegistryError(f"action {e['action']!r}: unknown tier {e['tier']!r}")
        if e["action"] in seen:
            raise RegistryError(f"duplicate action: {e['action']!r}")
        seen.add(e["action"])

        blocks = e.get("blocks", [])
        if not isinstance(blocks, list) or not blocks or not all(b in BLOCKS for b in blocks):
            raise RegistryError(f"action {e['action']!r}: 'blocks' must list known block ids")
        args = e.get("args", [])
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise RegistryError(f"action {e['action']!r}: 'args' must be a list of strings")
        e.setdefault("args", [])

    known = set(seen)
    for block_id in BLOCKS:
        if not any(block_id in e["blocks"] for e in actions):
            raise RegistryError(f"block '{block_id}' has no actions pointing at it")
    del known
    return data


def cell(text: str) -> str:
    return text.replace("|", r"\|").replace("\n", " ").strip()


def command_for(entry: dict, block_id: str) -> str:
    """SKILL.md blocks use the CLI form; protocol blocks use the bare form."""
    if block_id.startswith("skill-"):
        return entry.get("cli") or entry["command"]
    return entry["command"]


def purpose_for(entry: dict, block_id: str) -> str:
    if block_id.startswith("protocol-"):
        return entry.get("protocol_purpose") or entry["purpose"]
    return entry["purpose"]


def render_block(block_id: str, registry: dict) -> list[str]:
    spec = BLOCKS[block_id]
    entries = [e for e in registry["actions"] if block_id in e["blocks"]]

    if spec["style"] == "bullets":
        return [f"- `{command_for(e, block_id)}` - {purpose_for(e, block_id).strip()}" for e in entries]

    header = spec["header"]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for e in entries:
        action = f"`{e['action']}`"
        command = f"`{command_for(e, block_id)}`"
        purpose = cell(purpose_for(e, block_id))
        if len(header) == 4:
            # `ref`/`selector` means "either one"; quote each slash-separated
            # alternative, but leave plain names bare to match the existing prose.
            def quote(arg: str) -> str:
                if "/" in arg:
                    return "/".join(f"`{part}`" for part in arg.split("/"))
                return arg if arg.startswith("optional ") else f"`{arg}`"

            args = ", ".join(quote(a) for a in e["args"]) if e["args"] else "none"
            lines.append(f"| {action} | {command} | {args} | {purpose} |")
        else:
            lines.append(f"| {action} | {command} | {purpose} |")
    return lines


def split_lines(text: str) -> tuple[list[str], str]:
    if "\r\n" in text:
        return text.split("\r\n"), "\r\n"
    return text.split("\n"), "\n"


def replace_block(text: str, block_id: str, rendered: list[str]) -> str:
    lines, newline = split_lines(text)
    begin = next((i for i, l in enumerate(lines) if l.strip().startswith(BEGIN) and block_id in l), None)
    if begin is None:
        raise RegistryError(f"missing BEGIN marker for '{block_id}'")
    end = next((i for i, l in enumerate(lines) if l.strip().startswith(END) and block_id in l and i > begin), None)
    if end is None:
        raise RegistryError(f"missing END marker for '{block_id}' (or it precedes BEGIN)")
    return newline.join(lines[: begin + 1] + rendered + lines[end:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify only; exit 1 when a block is out of date")
    args = parser.parse_args()

    try:
        registry = load_registry(REGISTRY)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    grouped: dict[Path, list[tuple[str, list[str]]]] = {}
    for block_id, spec in BLOCKS.items():
        grouped.setdefault(spec["file"], []).append((block_id, render_block(block_id, registry)))

    drift: list[str] = []
    for path, blocks in grouped.items():
        original = path.read_text(encoding="utf-8")
        updated = original
        for block_id, rendered in blocks:
            updated = replace_block(updated, block_id, rendered)
        if updated == original:
            continue
        if args.check:
            drift.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(updated, encoding="utf-8", newline="")
            print(f"updated {path.relative_to(ROOT)}")

    if drift:
        for name in drift:
            print(f"out of date: {name}", file=sys.stderr)
        print(
            "\ncommand tables drifted from command-registry.json; run "
            "`python3 scripts/generate_command_docs.py`",
            file=sys.stderr,
        )
        return 1
    if args.check:
        print("command tables match command-registry.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
