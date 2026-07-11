#!/usr/bin/env python3
"""Validate the public demo pipeline health response used by CI."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from typing import TextIO


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError("expected 'true' or 'false'")


def validation_errors(payload: object, require_groq_fallback: bool) -> list[str]:
    if not isinstance(payload, Mapping):
        return ["health response must be a JSON object"]

    errors: list[str] = []
    if payload.get("status") != "healthy":
        errors.append("status is not healthy")
    if payload.get("llm_ok") is not True:
        errors.append("llm_ok is not true")

    providers = payload.get("providers_configured")
    if not isinstance(providers, Sequence) or isinstance(providers, (str, bytes)):
        errors.append("providers_configured must be a non-empty list")
    elif not any(
        isinstance(provider, str) and provider.strip() for provider in providers
    ):
        errors.append("providers_configured must include at least one provider")

    if require_groq_fallback and payload.get("groq_fallback_enabled") is not True:
        errors.append("groq_fallback_enabled is not true")

    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-groq-fallback",
        default="false",
        help="whether Groq must be configured as the fallback provider (true or false)",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(argv)

    try:
        require_groq_fallback = parse_bool(args.require_groq_fallback)
    except ValueError as exc:
        print(f"Invalid --require-groq-fallback value: {exc}", file=stderr)
        return 2

    try:
        payload = json.load(stdin)
    except json.JSONDecodeError as exc:
        print(f"Model integrity check received invalid JSON: {exc.msg}", file=stderr)
        return 1

    errors = validation_errors(payload, require_groq_fallback)
    if errors:
        print(f"Model integrity check failed: {'; '.join(errors)}", file=stderr)
        return 1

    providers = ", ".join(payload["providers_configured"])
    print(f"Model integrity check passed with providers: {providers}", file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
