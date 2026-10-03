#!/usr/bin/env python3
"""Repoint the unpacked (developer-mode) ZenX Bridge extension across Edge profiles.

Why this exists: the fork used to live in ``browserskill-new``, so every Edge
profile has a "load unpacked" entry whose ``path`` still points at
``D:\\916938\\browserskill-new\\apps\\extension\\dist\\chrome-mv3``. Moving the
checkout to ``zenx-bridge-main`` means 20 profiles would each need a manual
chrome://extensions click. Editing the profile's own load record is the only
way to do it without a browser UI: Chrome/Edge read that record at startup and
resolve the directory, so a path swap is picked up on the next launch.

Mechanics (verified 2026-10-04 on this machine):

- Unpacked extensions are **not** stored under ``User Data\\Extensions`` (that
  directory only holds web-store/CRX installs). They live as an entry in
  each profile's ``Secure Preferences`` under
  ``extensions.settings.<id>.path``, holding an absolute directory.
- All 20 profiles here share one Edge ``User Data`` and one extension id
  (``agcgbdanbihfkcdmgegblkioiiepecln``); only ``profileDirectory`` differs
  (``Default`` + ``Profile 1..19``), as recorded in
  ``D:/916938/zenxbrowser/.zenx/accounts.json``.
- The browser must be **fully closed** before editing: it rewrites these
  files on shutdown and would clobber the edit.

Safety properties:

- Refuses to write while ``msedge.exe`` is running (unless ``--force``).
- Verifies the new directory really is the expected extension (``manifest.json``
  with the matching key) before touching anything.
- Backs up each file it edits (``*.zenx-bak``), and only writes profiles where
  the old path actually matched — so a re-run is a no-op.
- ``--apply`` is required for any write; the default is a dry run.

Usage:
    python3 scripts/switch_extension.py                 # dry run over all profiles
    python3 scripts/switch_extension.py --apply         # write, after Edge exits
    python3 scripts/switch_extension.py --user-data-dir <dir> --profiles Profile 3
    python3 scripts/switch_extension.py --old-path <dir> --new-path <dir>

Zero third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"
DEFAULT_OLD_PATH = Path(r"D:\916938\browserskill-new\apps\extension\dist\chrome-mv3")
DEFAULT_NEW_PATH = Path(r"D:\916938\zenx-bridge-main\apps\extension\dist\chrome-mv3")

# Every extension that is "load unpacked" carries this; web-store entries have a
# versioned relative path instead (e.g. `<id>\3.5.2_0`).
PREF_FILES = ("Secure Preferences", "Preferences")
BACKUP_SUFFIX = ".zenx-bak"
EDGE_PROCESS = "msedge.exe"


def find_profiles(user_data_dir: Path) -> list[str]:
    """Return `Default` plus `Profile N` directories that exist."""
    if not user_data_dir.is_dir():
        raise RuntimeError(f"user data dir not found: {user_data_dir}")
    names = []
    default = user_data_dir / "Default"
    if default.is_dir():
        names.append("Default")
    numbered = [
        (int(p.name.split()[-1]), p.name)
        for p in user_data_dir.iterdir()
        if p.is_dir() and p.name.startswith("Profile ") and p.name.split()[-1].isdigit()
    ]
    names.extend(name for _, name in sorted(numbered))
    return names


def edge_running() -> bool:
    """True when any msedge.exe process is alive (PowerShell, Windows-only)."""
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"(Get-Process -Name {EDGE_PROCESS[:-4]} -ErrorAction SilentlyContinue | Measure-Object).Count"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return out.stdout.strip().isdigit() and int(out.stdout.strip()) > 0
    except (subprocess.SubprocessError, ValueError):
        # Cannot tell: treat as running so we do not corrupt a live profile.
        return True


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".zenx-tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def validate_extension_dir(path: Path, label: str) -> None:
    """Refuse to point a profile at a directory that is not the extension."""
    manifest = path / "manifest.json"
    if not manifest.is_file():
        raise RuntimeError(f"{label} extension dir has no manifest.json: {path}")
    try:
        data = read_json(manifest)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"{label} manifest.json unreadable at {path}: {exc}") from exc
    if not data.get("name") and not data.get("version"):
        raise RuntimeError(f"{label} manifest.json at {path} looks wrong: {data!r}")


def norm(path: str) -> str:
    """Normalise a stored path for comparison (Chrome stores Windows separators)."""
    return os.path.normcase(os.path.normpath(path.replace("/", "\\")))


def plan_profile(profile_dir: Path, old: Path, new: Path) -> dict:
    """Inspect one profile and describe what would change."""
    result = {
        "profile": profile_dir.name,
        "file": None,
        "ids": [],
        "already": [],
        "stale": [],
        "unreadable": [],
    }
    for pref_name in PREF_FILES:
        pref = profile_dir / pref_name
        if not pref.is_file():
            continue
        try:
            data = read_json(pref)
        except (OSError, ValueError):
            result["unreadable"].append(pref_name)
            continue
        settings = data.get("extensions", {}).get("settings", {})
        # Match either location: "stale" needs rewriting, "already" proves this
        # profile was switched before (so a re-run stays a no-op).
        matched = [
            ext_id
            for ext_id, entry in settings.items()
            if isinstance(entry, dict)
            and isinstance(entry.get("path"), str)
            and "chrome-mv3" in entry["path"]
            and norm(entry["path"]) in (norm(str(old)), norm(str(new)))
        ]
        if not matched:
            continue
        result["file"] = pref
        result["ids"] = matched
        already = [
            ext_id
            for ext_id in matched
            if norm(settings[ext_id].get("path", "")) == norm(str(new))
        ]
        result["already"] = already
        result["stale"] = [i for i in matched if i not in already]
        if matched:
            break
    return result


def apply_profile(plan: dict, new: Path, backup: bool) -> list[str]:
    """Rewrite the stored path for every matched id. Returns applied ids."""
    pref: Path = plan["file"]
    data = read_json(pref)
    settings = data.setdefault("extensions", {}).setdefault("settings", {})
    applied = []
    for ext_id in plan["stale"]:
        entry = settings[ext_id]
        entry["path"] = str(new)
        # A load-unpacked entry keeps its id; clearing the cached install hints
        # makes the browser re-read the manifest on next start instead of
        # trusting the old location's cached copy.
        for stale_key in ("manifest", "state", "location", "from_webstore"):
            if stale_key in entry and stale_key != "state":
                entry.pop(stale_key, None)
        applied.append(ext_id)
    if backup and not pref.with_name(pref.name + BACKUP_SUFFIX).exists():
        shutil.copy2(pref, pref.with_name(pref.name + BACKUP_SUFFIX))
    write_json(pref, data)
    return applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user-data-dir", type=Path, default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--old-path", type=Path, default=DEFAULT_OLD_PATH)
    parser.add_argument("--new-path", type=Path, default=DEFAULT_NEW_PATH)
    parser.add_argument("--profiles", nargs="*", help="limit to these profile directory names")
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    parser.add_argument("--no-backup", action="store_true", help="skip the .zenx-bak backup copy")
    parser.add_argument("--force", action="store_true", help="edit even if Edge is running (unsafe)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        validate_extension_dir(args.new_path, "new")
        if not args.apply:
            # Old path may already be gone after a successful switch; only
            # require it when we might rewrite it.
            if args.old_path.is_dir():
                validate_extension_dir(args.old_path, "old")

        if not args.force and edge_running():
            print(
                "error: Edge is still running. Close every Edge window (all 20 instances) "
                "and rerun; the browser rewrites these files on exit and would undo the edit. "
                "Use --force only if you know the target profiles are not loaded.",
                file=sys.stderr,
            )
            return 2

        names = args.profiles or find_profiles(args.user_data_dir)
        plans = [plan_profile(args.user_data_dir / n, args.old_path, args.new_path) for n in names]

        if args.apply:
            for plan in plans:
                if plan["file"] and plan["stale"]:
                    plan["applied"] = apply_profile(plan, args.new_path, backup=not args.no_backup)
                else:
                    plan["applied"] = []

        if args.json:
            print(json.dumps({"profiles": [{k: (str(v) if isinstance(v, Path) else v) for k, v in p.items()} for p in plans]}, indent=2, ensure_ascii=False))
            return 0

        todo = [p for p in plans if p["stale"]]
        done = [p for p in plans if p["already"] and not p["stale"]]
        missing = [p for p in plans if not p["file"]]
        print(f"user data dir : {args.user_data_dir}")
        print(f"old path      : {args.old_path}")
        print(f"new path      : {args.new_path}")
        print(f"profiles      : {len(plans)}  to-change={len(todo)} already-new={len(done)} no-unpacked-entry={len(missing)}")
        for plan in plans:
            if plan["stale"]:
                state = "applied" if args.apply else "would change"
            elif plan["already"]:
                state = "already new"
            else:
                state = "no unpacked entry"
            print(f"  {plan['profile']:<12} {state}  ({', '.join(plan['ids']) or '-'})")
        if args.apply:
            print(f"\napplied to {len(todo)} profile(s). Start Edge again; the extension reloads from the new path.")
        elif todo:
            print("\ndry run - re-run with --apply after closing Edge.")
        return 0
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
