#!/usr/bin/env python3
"""Triage helpers for syncing the ZenX Bridge fork with Tencent/BrowserSkill.

Read-only: it never rewrites the target repository. Every subcommand inspects
git state and prints tables you paste into a plan or into
``../zenx-bridge-main/docs/UPSTREAM_SYNC.md``.

Why this exists: the expensive part of a sync batch is deciding *what* to pick
and *in what order*. `git cherry` answers "already ported", `git merge-tree`
answers "how bad is a full merge", and the triage rule of thumb
(frozen paths / unported feature line / overlap with our changes) is easy to
state but tedious to compute by hand over 100+ candidates.

Usage:
    python3 scripts/upstream_sync.py triage [--markdown]
    python3 scripts/upstream_sync.py applied
    python3 scripts/upstream_sync.py order <hash>...
    python3 scripts/upstream_sync.py table [--since YYYY-MM-DD]

Defaults assume the upstream remote is ``Tencent`` and the fork mainline is
``main``; the repo defaults to ``../zenx-bridge-main``.

Zero third-party dependencies.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TARGET = Path("../zenx-bridge-main")

# Paths that are frozen by invariant #2: loopback-only, so upstream's
# standalone server / device pairing is never ported.
FROZEN_PREFIXES = (
    "crates/bsk-cli/src/daemon/remote/",
    "apps/extension/src/transport/remote-",
    "docs/remote-extension-connection.md",
    "crates/bsk-cli/tests/remote_server.rs",
)

CHERRY_MARKER = "cherry picked from commit "


def git(repo: Path, *args: str) -> str:
    """Run a git command and return its stdout, stripped."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def list_lines(repo: Path, *args: str) -> list[str]:
    """Run a git command and return non-empty stdout lines."""
    out = git(repo, *args)
    return [line for line in out.splitlines() if line.strip()]


def merge_base(repo: Path, remote: str, branch: str) -> str:
    return git(repo, "merge-base", "HEAD", f"{remote}/{branch}")


def our_changed_files(repo: Path, base: str) -> set[str]:
    """Files we touched since the last sync baseline."""
    return set(list_lines(repo, "diff", "--name-only", base, "HEAD"))


def already_applied(repo: Path, remote: str, branch: str) -> set[str]:
    """Upstream commits already cherry-picked (different hash, same patch id)."""
    out = list_lines(repo, "cherry", "-v", "HEAD", f"{remote}/{branch}")
    return {line.split()[1] for line in out if line.startswith("- ")}


def classify_files(files: list[str], our_files: set[str]) -> dict:
    """Score one commit: size, frozen-path contact, overlap with our changes."""
    frozen = [f for f in files if any(f.startswith(p) for p in FROZEN_PREFIXES)]
    overlap = [f for f in files if f in our_files]
    return {
        "files": len(files),
        "frozen": len(frozen),
        "overlap": len(overlap),
        "overlap_files": overlap,
    }


def triage_rows(repo: Path, remote: str, branch: str) -> list[dict]:
    base = merge_base(repo, remote, branch)
    ours = our_changed_files(repo, base)
    applied = already_applied(repo, remote, branch)
    rows = []
    for commit in list_lines(repo, "log", "--no-merges", "--pretty=format:%H", f"{base}..{remote}/{branch}"):
        files = list_lines(repo, "show", "--pretty=format:", "--name-only", commit)
        info = classify_files(files, ours)
        rows.append(
            {
                "hash": commit[:7],
                "date": git(repo, "log", "-1", "--format=%ad", "--date=short", commit),
                "subject": git(repo, "log", "-1", "--format=%s", commit),
                "ported": commit in applied,
                **info,
            }
        )
    return rows


def render_triage(rows: list[dict], markdown: bool) -> str:
    pending = [r for r in rows if not r["ported"]]
    lines = [
        f"pending={len(pending)} already-ported={len(rows) - len(pending)} total={len(rows)}",
        "",
    ]
    if markdown:
        lines += ["| Commit | Date | Files | Frozen | Overlap | Subject |", "|---|---|---:|---:|---:|---|"]
        for r in pending:
            lines.append(
                f"| `{r['hash']}` | {r['date']} | {r['files']} | {r['frozen']} | {r['overlap']} | {r['subject']} |"
            )
        return "\n".join(lines)
    for r in pending:
        lines.append(
            f"{r['hash']} {r['date']} files={r['files']} frozen={r['frozen']} "
            f"overlap={r['overlap']} {r['subject']}"
        )
    return "\n".join(lines)


def render_order(repo: Path, commits: list[str]) -> str:
    """Report whether the given hashes are listed in topological order."""
    problems = []
    for earlier, later in zip(commits, commits[1:]):
        try:
            git(repo, "merge-base", "--is-ancestor", earlier, later)
        except RuntimeError:
            problems.append(f"{earlier[:7]} is NOT an ancestor of {later[:7]}")
    if problems:
        return "order problems (date order != topology):\n" + "\n".join(problems)
    return f"ok: {len(commits)} commits are in ancestor order"


def upstream_of_body(body: str) -> str:
    """Extract the upstream hash from a `git cherry-pick -x` trailer."""
    idx = body.find(CHERRY_MARKER)
    if idx < 0:
        return ""
    tail = body[idx + len(CHERRY_MARKER):]
    return tail.split(")")[0].strip()[:7]


def upstream_of(repo: Path, commit: str) -> str:
    return upstream_of_body(git(repo, "log", "-1", "--format=%B", commit))


def render_table_rows(rows: list[tuple[str, str, str]]) -> str:
    """Render `(ours, upstream, subject)` triples as the sync-doc table."""
    lines = ["| Upstream | Ours | Subject |", "|---|---|---|"]
    for ours, upstream, subject in rows:
        lines.append(f"| `{upstream or '—'}` | `{ours}` | {subject} |")
    return "\n".join(lines)


def render_table(repo: Path, since: str | None) -> str:
    args = ["log", "--reverse", "--pretty=format:%H", "main..HEAD"]
    if since:
        args += [f"--since={since}"]
    rows = []
    for commit in list_lines(repo, *args):
        rows.append((commit[:7], upstream_of(repo, commit), git(repo, "log", "-1", "--format=%s", commit)))
    return render_table_rows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["triage", "applied", "order", "table"])
    parser.add_argument("commits", nargs="*", help="hashes for the order check")
    parser.add_argument("--repo", default=str(TARGET), help="fork checkout (default: ../zenx-bridge-main)")
    parser.add_argument("--remote", default="Tencent")
    parser.add_argument("--base", default="main")
    parser.add_argument("--markdown", action="store_true", help="triage as a markdown table")
    parser.add_argument("--since", help="limit the table to commits after this date")
    args = parser.parse_args(argv)

    # Upstream subjects can be non-ASCII (they ship Chinese commit titles);
    # Windows defaults to cp1252 and would crash on print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    repo = Path(args.repo)
    try:
        if args.command == "triage":
            print(render_triage(triage_rows(repo, args.remote, args.base), args.markdown))
        elif args.command == "applied":
            for line in list_lines(repo, "cherry", "-v", "HEAD", f"{args.remote}/{args.base}"):
                if line.startswith("- "):
                    parts = line.split()
                    print(f"{parts[1][:7]} {git(repo, 'log', '-1', '--format=%s', parts[1])}")
        elif args.command == "order":
            if len(args.commits) < 2:
                parser.error("order needs at least two hashes")
            print(render_order(repo, args.commits))
        elif args.command == "table":
            print(render_table(repo, args.since))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
