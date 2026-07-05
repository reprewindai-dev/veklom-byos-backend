import contextlib
import io
import json
import os
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

    def test_user_repos_can_skip_missing_organization_secrets_endpoint(self):
        calls = []

        def fake_fetch(url, token, scope):
            calls.append(scope)
            if scope == "organization":
                raise audit.GitHubApiError(422, "Validation Failed")
            return [audit.SecretRecord("REPO_SECRET", audit.parse_datetime("2026-07-01T00:00:00Z"), scope)]

        with patch.object(audit, "fetch_paginated_secrets", side_effect=fake_fetch):
            records = audit.fetch_github_secret_records("FeeeeelixWong/veklom-byos-backend", "token", "https://api.github.com")

        self.assertEqual(["repository", "organization"], calls)
        self.assertEqual(["REPO_SECRET"], [record.name for record in records])


if __name__ == "__main__":
    unittest.main()
