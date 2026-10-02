import subprocess
import json
import sys


def configure_utf8_output():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def _append_options(args, kwargs):
    for key, value in kwargs.items():
        if value is True:
            args.append(f"--{key}")
            continue
        args.append(f"--{key}")
        args.append(str(value))


def bsk(command: str, session=None, *pos_args, **kwargs):
    args = ["bsk"]
    args.extend(command.split())
    args.extend(pos_args)
    if session:
        args.extend(["--session", session])
    _append_options(args, kwargs)
    args.append("--json")

    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.stdout:
        try:
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                if data.get("error"):
                    raise RuntimeError(f"bsk command failed: {data['error']}")
                if data.get("success") is False:
                    raise RuntimeError(f"bsk command failed: {data}")
            return data
        except json.JSONDecodeError:
            pass

    if result.returncode != 0:
        raise RuntimeError(f"bsk command failed: {result.stderr}")

    return None


def bsk_with_raw(command: str, session=None, *pos_args, **kwargs):
    args = ["bsk"]
    args.extend(command.split())
    args.extend(pos_args)
    if session:
        args.extend(["--session", session])
    _append_options(args, kwargs)

    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.returncode != 0:
        raise RuntimeError(f"bsk command failed: {result.stderr}")

    return result.stdout