import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.scripts import secret_rotation_audit as audit


class SecretRotationAuditTests(unittest.TestCase):
    def test_secret_age_and_force_rotate_findings(self):
        now = audit.parse_datetime("2026-07-05T00:00:00Z")
        records = [
            audit.SecretRecord("FRESH_KEY", audit.parse_datetime("2026-07-01T00:00:00Z")),
            audit.SecretRecord("WARN_KEY", audit.parse_datetime("2026-04-15T00:00:00Z")),
            audit.SecretRecord("OLD_KEY", audit.parse_datetime("2026-03-01T00:00:00Z")),
            audit.SecretRecord("FORCED_KEY", audit.parse_datetime("2026-07-04T00:00:00Z")),
        ]

        findings = audit.audit_secret_records(
            records=records,
            forced_names={"FORCED_KEY", "MISSING_KEY"},
            now=now,
            max_age_days=90,
            warn_age_days=75,
        )

        failures = [finding.title for finding in findings if finding.severity == "FAIL"]
        warnings = [finding.title for finding in findings if finding.severity == "WARN"]
        self.assertIn("OLD_KEY exceeds rotation window", failures)
        self.assertIn("FORCED_KEY was forced into rotation", failures)
        self.assertIn("MISSING_KEY was forced but not found", failures)
        self.assertIn("WARN_KEY is nearing rotation window", warnings)

    def test_cli_fixture_passes_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "secrets.json"
            report = Path(tmp) / "report.md"
            fixture.write_text(
                json.dumps(
                    {
                        "secrets": [
                            {
                                "name": "FRESH_KEY",
                                "updated_at": "2026-07-01T00:00:00Z",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
                exit_code = audit.main(
                    [
                        "--github-secrets-json",
                        str(fixture),
                        "--skip-db",
                        "--report",
                        str(report),
                        "--now",
                        "2026-07-05T00:00:00Z",
                    ]
                )

            self.assertEqual(exit_code, 0)
            body = report.read_text(encoding="utf-8")
            self.assertIn("Status: PASS", body)
            self.assertIn("`FRESH_KEY`", body)

    def test_cli_fixture_fails_when_forced_secret_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "secrets.json"
            report = Path(tmp) / "report.md"
            fixture.write_text(json.dumps({"secrets": []}), encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
                exit_code = audit.main(
                    [
                        "--github-secrets-json",
                        str(fixture),
                        "--skip-db",
                        "--force-rotate",
                        "MISSING_KEY",
                        "--report",
                        str(report),
                        "--now",
                        "2026-07-05T00:00:00Z",
                    ]
                )

            self.assertEqual(exit_code, 1)
            body = report.read_text(encoding="utf-8")
            self.assertIn("Status: FAIL", body)
            self.assertIn("MISSING_KEY was forced but not found", body)

    def test_github_permission_error_is_actionable(self):
        parser = audit.build_parser()
        args = parser.parse_args(["--repo", "owner/repo", "--skip-db", "--now", "2026-07-05T00:00:00Z"])

        with patch.dict(os.environ, {}, clear=True):
            result = audit.run(args)

        self.assertTrue(result.failed)
        report = audit.render_report(result, set())
        self.assertIn("GH_TOKEN/GITHUB_TOKEN is not configured", report)
        self.assertIn("SECRET_ROTATION_GH_TOKEN", report)

    def test_database_audit_omits_raw_connection_error_from_report(self):
        class FakePsycopg2:
            @staticmethod
            def connect(database_url, connect_timeout):
                raise RuntimeError(f"could not connect to {database_url}")

        database_url = "postgresql://audit_user:super-secret@db.example.com/veklom"

        with patch.dict(sys.modules, {"psycopg2": FakePsycopg2}):
            result = audit.audit_database_api_keys(
                database_url=database_url,
                skip_db=False,
                now=audit.parse_datetime("2026-07-05T00:00:00Z"),
                max_age_days=90,
            )

        report = audit.render_report(
            audit.AuditResult(
                generated_at=audit.parse_datetime("2026-07-05T00:00:00Z"),
                max_age_days=90,
                warn_age_days=75,
                secrets=[],
                findings=[],
                db=result,
            ),
            set(),
        )
        self.assertTrue(result.findings)
        self.assertIn("raw exception details omitted", report)
        self.assertNotIn("super-secret", report)
        self.assertNotIn(database_url, report)

    def test_default_audit_only_requests_repository_secrets(self):
        calls = []

        def fake_fetch(url, token, scope):
            calls.append(scope)
            return [audit.SecretRecord("REPO_SECRET", audit.parse_datetime("2026-07-01T00:00:00Z"), scope)]

        with patch.object(audit, "fetch_paginated_secrets", side_effect=fake_fetch):
            records = audit.fetch_github_secret_records("owner/repo", "token", "https://api.github.com")

        self.assertEqual(["repository"], calls)
        self.assertEqual(["REPO_SECRET"], [record.name for record in records])

    def test_organization_audit_is_explicit_and_requires_its_own_permission(self):
        calls = []

        def fake_fetch(url, token, scope):
            calls.append(scope)
            if scope == "organization":
                raise audit.GitHubApiError(403, "Resource not accessible by integration")
            return [audit.SecretRecord("REPO_SECRET", audit.parse_datetime("2026-07-01T00:00:00Z"), scope)]

        with patch.object(audit, "fetch_paginated_secrets", side_effect=fake_fetch):
            with self.assertRaisesRegex(audit.GitHubApiError, "Resource not accessible"):
                audit.fetch_github_secret_records(
                    "owner/repo",
                    "token",
                    "https://api.github.com",
                    include_organization_secrets=True,
                )

        self.assertEqual(["repository", "organization"], calls)

    def test_organization_permission_error_explains_the_required_scope(self):
        parser = audit.build_parser()
        args = parser.parse_args(
            [
                "--repo",
                "owner/repo",
                "--skip-db",
                "--include-organization-secrets",
                "--now",
                "2026-07-05T00:00:00Z",
            ]
        )

        with patch.dict(os.environ, {"GH_TOKEN": "test-token"}, clear=True):
            with patch.object(
                audit,
                "fetch_github_secret_records",
                side_effect=audit.GitHubApiError(403, "Resource not accessible by integration"),
            ):
                result = audit.run(args)

        report = audit.render_report(result, set())
        self.assertTrue(result.failed)
        self.assertIn("repository and organization Secrets read permissions", report)

    def test_organization_audit_can_be_enabled_from_environment(self):
        with patch.dict(os.environ, {"SECRET_ROTATION_INCLUDE_ORGANIZATION_SECRETS": "true"}, clear=True):
            args = audit.build_parser().parse_args([])

        self.assertTrue(args.include_organization_secrets)

    def test_report_discloses_repository_only_coverage(self):
        result = audit.AuditResult(
            generated_at=audit.parse_datetime("2026-07-05T00:00:00Z"),
            max_age_days=90,
            warn_age_days=75,
            secrets=[],
            findings=[],
            db=audit.DbAuditResult("skipped: --skip-db"),
        )

        self.assertIn("Coverage: repository Actions secrets only", audit.render_report(result, set()))


if __name__ == "__main__":
    unittest.main()
