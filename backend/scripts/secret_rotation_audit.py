#!/usr/bin/env python3
"""Audit GitHub Actions secret age and optional database API-key age."""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MAX_AGE_DAYS = 90
DEFAULT_WARN_AGE_DAYS = 75
DEFAULT_REPORT_PATH = "secret-rotation-report.md"
GITHUB_API_VERSION = "2022-11-28"


@dataclasses.dataclass(frozen=True)
class SecretRecord:
    name: str
    updated_at: datetime | None
    scope: str = "repository"


@dataclasses.dataclass(frozen=True)
class Finding:
    severity: str
    title: str
    detail: str


@dataclasses.dataclass
class DbAuditResult:
    status: str
    rows_checked: int = 0
    findings: list[Finding] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class AuditResult:
    generated_at: datetime
    max_age_days: int
    warn_age_days: int
    secrets: list[SecretRecord]
    findings: list[Finding]
    db: DbAuditResult
    organization_secrets_included: bool = False

    @property
    def failed(self) -> bool:
        return any(f.severity == "FAIL" for f in self.findings + self.db.findings)


class GitHubApiError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def safe_exception_detail(exc: Exception, action: str) -> str:
    """Return a report-safe error summary without driver-provided details."""
    return f"{type(exc).__name__}: {action}; raw exception details omitted to avoid leaking credentials."


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_csv_names(value: str | None) -> set[str]:
    if not value:
        return set()
    return {part.strip().upper() for part in value.split(",") if part.strip()}


def secret_from_payload(item: dict[str, Any], scope: str) -> SecretRecord:
    return SecretRecord(
        name=str(item.get("name", "")).strip(),
        updated_at=parse_datetime(item.get("updated_at")),
        scope=scope,
    )


def load_secret_records_from_json(path: Path) -> list[SecretRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        items = payload
    else:
        items = payload.get("secrets", [])
    return [secret_from_payload(item, str(item.get("scope", "fixture"))) for item in items]


def github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def github_get_json(url: str, token: str, timeout: int = 20) -> tuple[dict[str, Any], str | None]:
    request = urllib.request.Request(url, headers=github_headers(token))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body), response.headers.get("Link")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(body).get("message", body)
        except json.JSONDecodeError:
            message = body
        raise GitHubApiError(exc.code, str(message)) from exc
    except urllib.error.URLError as exc:
        raise GitHubApiError(0, str(exc.reason)) from exc


def next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for section in link_header.split(","):
        url_part, _, rel_part = section.strip().partition(";")
        if 'rel="next"' in rel_part:
            return url_part.strip()[1:-1]
    return None


def fetch_paginated_secrets(url: str, token: str, scope: str) -> list[SecretRecord]:
    records: list[SecretRecord] = []
    while url:
        payload, link = github_get_json(url, token)
        records.extend(secret_from_payload(item, scope) for item in payload.get("secrets", []))
        url = next_link(link)
    return records


def fetch_github_secret_records(
    repo: str,
    token: str,
    api_url: str,
    include_organization_secrets: bool = False,
) -> list[SecretRecord]:
    if "/" not in repo:
        raise ValueError("Repository must be in OWNER/REPO format.")
    if not token:
        raise GitHubApiError(
            0,
            "GH_TOKEN/GITHUB_TOKEN is not configured. Provide SECRET_ROTATION_GH_TOKEN with repository Secrets read permission.",
        )
    owner, name = repo.split("/", 1)
    base = api_url.rstrip("/")
    endpoints = [(f"{base}/repos/{owner}/{name}/actions/secrets?per_page=100", "repository")]
    if include_organization_secrets:
        endpoints.append((f"{base}/repos/{owner}/{name}/actions/organization-secrets?per_page=100", "organization"))
    records: list[SecretRecord] = []
    for url, scope in endpoints:
        try:
            records.extend(fetch_paginated_secrets(url, token, scope))
        except GitHubApiError as exc:
            if scope == "organization" and exc.status in (404, 422):
                continue
            raise
    return records


def age_days(updated_at: datetime | None, now: datetime) -> int | None:
    if updated_at is None:
        return None
    return max(0, (now - updated_at).days)


def audit_secret_records(
    records: list[SecretRecord],
    forced_names: set[str],
    now: datetime,
    max_age_days: int,
    warn_age_days: int,
) -> list[Finding]:
    findings: list[Finding] = []
    seen_names = {record.name.upper() for record in records}
    if not records:
        findings.append(
            Finding(
                "WARN",
                "No GitHub Actions secrets returned",
                "The API call succeeded but returned no repository or organization Actions secrets.",
            )
        )
    for record in sorted(records, key=lambda item: (item.scope, item.name)):
        name = record.name.upper()
        days = age_days(record.updated_at, now)
        if not record.name:
            findings.append(Finding("FAIL", "Secret metadata missing name", f"{record.scope} secret has no name."))
        if days is None:
            findings.append(Finding("FAIL", f"{record.name} has no updated_at", "Cannot determine rotation age."))
            continue
        if name in forced_names:
            findings.append(
                Finding(
                    "FAIL",
                    f"{record.name} was forced into rotation",
                    f"{record.scope} secret is {days} days old and was listed in FORCE_ROTATE_SECRETS.",
                )
            )
            continue
        if days > max_age_days:
            findings.append(
                Finding(
                    "FAIL",
                    f"{record.name} exceeds rotation window",
                    f"{record.scope} secret is {days} days old; policy maximum is {max_age_days} days.",
                )
            )
        elif days > warn_age_days:
            findings.append(
                Finding(
                    "WARN",
                    f"{record.name} is nearing rotation window",
                    f"{record.scope} secret is {days} days old; warning threshold is {warn_age_days} days.",
                )
            )
    missing_forced = sorted(forced_names - seen_names)
    for name in missing_forced:
        findings.append(
            Finding(
                "FAIL",
                f"{name} was forced but not found",
                "FORCE_ROTATE_SECRETS names must match an audited Actions secret.",
            )
        )
    return findings


def audit_database_api_keys(
    database_url: str | None,
    skip_db: bool,
    now: datetime,
    max_age_days: int,
) -> DbAuditResult:
    if skip_db:
        return DbAuditResult("skipped: --skip-db")
    if not database_url:
        return DbAuditResult("skipped: DATABASE_URL is not configured")
    try:
        import psycopg2  # type: ignore
    except ImportError:
        return DbAuditResult(
            "failed",
            findings=[
                Finding(
                    "FAIL",
                    "psycopg2 is required for database audit",
                    "Install psycopg2-binary before running database API-key age checks.",
                )
            ],
        )

    queries = [
        (
            "api_keys",
            """
            SELECT id, name, key_prefix, created_at
            FROM api_keys
            WHERE COALESCE(is_active, TRUE) = TRUE
            """,
            "created_at",
        ),
        (
            "provider_keys",
            """
            SELECT id, COALESCE(label, provider), key_prefix, updated_at
            FROM provider_keys
            WHERE COALESCE(is_active, TRUE) = TRUE
            """,
            "updated_at",
        ),
    ]
    findings: list[Finding] = []
    rows_checked = 0
    try:
        with contextlib.closing(psycopg2.connect(database_url, connect_timeout=10)) as conn:
            with conn:
                with conn.cursor() as cursor:
                    for table, query, timestamp_column in queries:
                        try:
                            cursor.execute(query)
                        except Exception as exc:
                            conn.rollback()
                            findings.append(
                                Finding("WARN", f"{table} audit skipped", safe_exception_detail(exc, "query failed"))
                            )
                            continue
                        for key_id, label, prefix, timestamp in cursor.fetchall():
                            rows_checked += 1
                            checked_at = timestamp
                            if checked_at is not None and checked_at.tzinfo is None:
                                checked_at = checked_at.replace(tzinfo=timezone.utc)
                            days = age_days(checked_at, now)
                            if days is None:
                                findings.append(
                                    Finding("FAIL", f"{table}:{key_id} has no {timestamp_column}", "Cannot determine API-key age.")
                                )
                            elif days > max_age_days:
                                findings.append(
                                    Finding(
                                        "FAIL",
                                        f"{table}:{label or key_id} exceeds rotation window",
                                        f"Key prefix {prefix or '<none>'} is {days} days old; policy maximum is {max_age_days} days.",
                                    )
                                )
    except Exception as exc:
        return DbAuditResult(
            "failed",
            rows_checked=rows_checked,
            findings=[
                Finding(
                    "FAIL",
                    "Database API-key audit failed",
                    safe_exception_detail(exc, "connection or audit failed"),
                )
            ],
        )
    return DbAuditResult("checked", rows_checked=rows_checked, findings=findings)


def status_for_secret(record: SecretRecord, forced_names: set[str], now: datetime, max_age_days: int, warn_age_days: int) -> str:
    days = age_days(record.updated_at, now)
    if record.name.upper() in forced_names:
        return "FORCED"
    if days is None:
        return "UNKNOWN"
    if days > max_age_days:
        return "EXPIRED"
    if days > warn_age_days:
        return "WARN"
    return "OK"


def render_report(result: AuditResult, forced_names: set[str]) -> str:
    lines = [
        "# Secret Rotation Audit",
        "",
        f"Status: {'FAIL' if result.failed else 'PASS'}",
        f"Generated at: {result.generated_at.isoformat()}",
        f"Policy: fail after {result.max_age_days} days, warn after {result.warn_age_days} days.",
        "Coverage: repository and organization Actions secrets."
        if result.organization_secrets_included
        else "Coverage: repository Actions secrets only. Set --include-organization-secrets to audit organization secrets.",
        "",
        "## GitHub Actions Secrets",
        "",
        "| Scope | Name | Updated at | Age days | Status |",
        "| --- | --- | --- | ---: | --- |",
    ]
    if result.secrets:
        for record in sorted(result.secrets, key=lambda item: (item.scope, item.name)):
            days = age_days(record.updated_at, result.generated_at)
            updated = record.updated_at.isoformat() if record.updated_at else "unknown"
            lines.append(
                f"| {record.scope} | `{record.name}` | {updated} | {days if days is not None else 'unknown'} | "
                f"{status_for_secret(record, forced_names, result.generated_at, result.max_age_days, result.warn_age_days)} |"
            )
    else:
        lines.append("| repository | _none returned_ | n/a | n/a | WARN |")

    all_findings = result.findings + result.db.findings
    lines.extend(["", "## Findings", ""])
    if all_findings:
        for finding in all_findings:
            lines.append(f"- [{finding.severity}] {finding.title}: {finding.detail}")
    else:
        lines.append("- No rotation findings.")

    lines.extend(
        [
            "",
            "## Database API Key Audit",
            "",
            f"Status: {result.db.status}",
            f"Rows checked: {result.db.rows_checked}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--github-api-url", default=os.getenv("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--github-secrets-json", type=Path, help="Local fixture matching the GitHub secrets API response.")
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT_PATH))
    parser.add_argument("--skip-db", action="store_true")
    parser.add_argument("--max-age-days", type=int, default=int(os.getenv("SECRET_ROTATION_MAX_AGE_DAYS", DEFAULT_MAX_AGE_DAYS)))
    parser.add_argument("--warn-age-days", type=int, default=int(os.getenv("SECRET_ROTATION_WARN_AGE_DAYS", DEFAULT_WARN_AGE_DAYS)))
    parser.add_argument("--force-rotate", default=os.getenv("FORCE_ROTATE_SECRETS", ""))
    parser.add_argument(
        "--include-organization-secrets",
        action="store_true",
        default=os.getenv("SECRET_ROTATION_INCLUDE_ORGANIZATION_SECRETS", "").lower() in {"1", "true", "yes", "on"},
        help="Also audit organization Actions secrets available to this repository.",
    )
    parser.add_argument("--now", default="")
    return parser


def run(args: argparse.Namespace, forced_names: set[str] | None = None) -> AuditResult:
    now = parse_datetime(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        raise ValueError("--now could not be parsed.")
    if forced_names is None:
        forced_names = parse_csv_names(args.force_rotate)
    findings: list[Finding] = []

    try:
        if args.github_secrets_json:
            records = load_secret_records_from_json(args.github_secrets_json)
        else:
            records = fetch_github_secret_records(
                repo=args.repo,
                token=os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or "",
                api_url=args.github_api_url,
                include_organization_secrets=args.include_organization_secrets,
            )
        findings.extend(audit_secret_records(records, forced_names, now, args.max_age_days, args.warn_age_days))
    except (GitHubApiError, ValueError) as exc:
        records = []
        message = exc.message if isinstance(exc, GitHubApiError) else str(exc)
        if isinstance(exc, GitHubApiError) and exc.status in (401, 403):
            permission = "repository and organization Secrets read permissions" if args.include_organization_secrets else "repository Secrets read permission"
            message += f" Configure SECRET_ROTATION_GH_TOKEN with {permission} or classic repo scope."
        findings.append(Finding("FAIL", "GitHub Actions secret metadata audit failed", message))

    db_result = audit_database_api_keys(
        database_url=os.getenv("DATABASE_URL"),
        skip_db=args.skip_db,
        now=now,
        max_age_days=args.max_age_days,
    )
    return AuditResult(
        generated_at=now,
        max_age_days=args.max_age_days,
        warn_age_days=args.warn_age_days,
        secrets=records,
        findings=findings,
        db=db_result,
        organization_secrets_included=args.include_organization_secrets,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    forced_names = parse_csv_names(args.force_rotate)
    result = run(args, forced_names)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(result, forced_names), encoding="utf-8")
    print(f"Secret rotation audit {'failed' if result.failed else 'passed'}. Report: {args.report}")
    return 1 if result.failed else 0


if __name__ == "__main__":
    sys.exit(main())
