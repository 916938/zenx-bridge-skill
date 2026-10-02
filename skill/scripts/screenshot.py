#!/usr/bin/env python3

import argparse
import shutil
import tempfile
from pathlib import Path

from bsk_client import configure_utf8_output, bsk


def parse_args():
    parser = argparse.ArgumentParser(
        description="Capture a BrowserSkill screenshot and return a local path."
    )
    parser.add_argument("--session", help="BrowserSkill session ID")
    parser.add_argument("--output", type=Path, help="Optional destination path")
    parser.add_argument("--format", choices=("png", "jpeg"), default="png")
    parser.add_argument("--quality", type=int, default=80)
    parser.add_argument("--selector", help="Optional @e ref or CSS selector")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Stitch a full-page PNG (bsk 0.2.3+); mutually exclusive with --selector",
    )
    return parser.parse_args()


def default_output_path(image_format):
    directory = Path(tempfile.gettempdir()) / "browserskill-screenshots"
    directory.mkdir(parents=True, exist_ok=True)
    suffix = ".jpg" if image_format == "jpeg" else ".png"
    handle = tempfile.NamedTemporaryFile(
        suffix=suffix,
        prefix="screenshot_",
        dir=directory,
        delete=False,
    )
    handle.close()
    return Path(handle.name)


def main():
    configure_utf8_output()
    args = parse_args()
    if not 0 <= args.quality <= 100:
        raise SystemExit("--quality must be between 0 and 100.")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be a positive number of seconds.")
    if args.selector and args.full_page:
        raise SystemExit("--selector and --full-page are mutually exclusive.")

    kwargs = {}
    if args.selector:
        kwargs["ref"] = args.selector
    if args.output:
        kwargs["out"] = str(args.output)
    if args.full_page:
        kwargs["full-page"] = True
        kwargs["timeout"] = f"{args.timeout}s"

    try:
        response = bsk("screenshot", args.session, **kwargs)
    except RuntimeError as error:
        raise SystemExit(str(error)) from error

    data = response or {}
    source = Path(data.get("path")).expanduser() if data.get("path") else None
    if source and not source.exists():
        raise SystemExit(f"Screenshot path does not exist: {source}")

    if source and args.output is None:
        print(source.resolve())
        return

    output = args.output or default_output_path(args.format)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if source:
        shutil.copyfile(source, output)
    else:
        raise SystemExit("BrowserSkill returned no screenshot path.")
    print(output)


if __name__ == "__main__":
    main()