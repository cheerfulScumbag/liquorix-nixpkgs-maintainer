#!/usr/bin/env python3

"""Coordinate the Nixpkgs Liquorix updater without hiding its decisions."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


PACKAGE = Path("pkgs/os-specific/linux/kernel/liquorix-kernel.nix")
UPDATER = Path("pkgs/os-specific/linux/kernel/update-liquorix.py")


def updater(nixpkgs, *arguments):
    result = subprocess.run(
        [sys.executable, UPDATER, *arguments],
        cwd=nixpkgs,
        check=False,
        text=True,
        capture_output=True,
    )
    allowed = {0, 1} if "--config-report" in arguments else {0}
    if result.returncode not in allowed:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )
    return json.loads(result.stdout)


def release_line(version):
    components = version.split(".")
    if len(components) < 2:
        raise ValueError(f"invalid kernel version: {version}")
    return ".".join(components[:2])


def check(nixpkgs):
    result = updater(nixpkgs, "--check")
    result["updateAvailable"] = not result["current"]
    result["newKernelLine"] = release_line(result["oldVersion"]) != release_line(
        result["newVersion"]
    )
    return result


def update(nixpkgs):
    before = check(nixpkgs)
    if not before["updateAvailable"]:
        return {"changed": False, "release": before, "changes": []}

    report = updater(nixpkgs, "--config-report")
    if report["drift"]:
        raise RuntimeError(
            "Liquorix configuration drift requires review:\n"
            + json.dumps(report["drift"], indent=2, sort_keys=True)
        )
    changes = updater(nixpkgs)
    return {"changed": True, "release": before, "changes": changes, "config": report}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "update"))
    parser.add_argument("--nixpkgs", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    nixpkgs = args.nixpkgs.resolve()
    if not (nixpkgs / PACKAGE).is_file() or not (nixpkgs / UPDATER).is_file():
        parser.error(f"{nixpkgs} is not a Nixpkgs checkout containing linux_lqx")

    try:
        result = check(nixpkgs) if args.command == "check" else update(nixpkgs)
    except subprocess.CalledProcessError as error:
        print(error.stderr.strip() or error, file=sys.stderr)
        return 1
    except (RuntimeError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered)
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
