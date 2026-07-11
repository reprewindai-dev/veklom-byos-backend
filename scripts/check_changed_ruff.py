#!/usr/bin/env python3
"""Fail CI only for Ruff diagnostics introduced by a Git diff."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HUNK_PATTERN = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def run_git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True)


def changed_python_files(base: str, head: str) -> list[str]:
    if not base or set(base) == {"0"}:
        return run_git("ls-files", "*.py").splitlines()

    return run_git(
        "diff",
        "--name-only",
        "--diff-filter=ACMR",
        base,
        head,
        "--",
        "*.py",
    ).splitlines()


def changed_lines(base: str, head: str, filename: str) -> set[int]:
    if not base or set(base) == {"0"}:
        return set(range(1, len(Path(filename).read_text(encoding="utf-8").splitlines()) + 1))

    diff = run_git("diff", "--unified=0", "--no-color", base, head, "--", filename)
    lines: set[int] = set()
    for line in diff.splitlines():
        match = HUNK_PATTERN.match(line)
        if not match:
            continue

        start = int(match.group(1))
        count = int(match.group(2) or 1)
        lines.update(range(start, start + count))
    return lines


def in_changed_lines(diagnostic: dict[str, Any], lines: set[int]) -> bool:
    start = diagnostic["location"]["row"]
    end = diagnostic["end_location"]["row"]
    return any(line in lines for line in range(start, end + 1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--ruff", nargs="+", default=["ruff"], help="Ruff command to run")
    args = parser.parse_args()

    files = changed_python_files(args.base, args.head)
    if not files:
        print("No changed Python files to lint.")
        return 0

    result = subprocess.run(
        [*args.ruff, "check", "--exit-zero", "--output-format=json", *files],
        check=True,
        capture_output=True,
        text=True,
    )
    lines_by_file = defaultdict(set)
    for filename in files:
        lines_by_file[str(Path(filename).resolve())] = changed_lines(args.base, args.head, filename)

    introduced = [
        diagnostic
        for diagnostic in json.loads(result.stdout)
        if in_changed_lines(diagnostic, lines_by_file[diagnostic["filename"]])
    ]
    for diagnostic in introduced:
        location = diagnostic["location"]
        code = diagnostic["code"]
        message = diagnostic["message"].replace("\n", "%0A")
        print(
            f"::error file={diagnostic['filename']},line={location['row']},"
            f"col={location['column']},title={code}::{message}"
        )

    if introduced:
        print(f"Found {len(introduced)} Ruff diagnostic(s) on changed lines.", file=sys.stderr)
        return 1

    print(f"No Ruff diagnostics on changed lines across {len(files)} Python file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
