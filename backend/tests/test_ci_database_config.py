from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATHS = (
    ROOT / ".github" / "workflows" / "ci-cache.yml",
    ROOT / ".github" / "workflows" / "self-hosted-ci.yml",
)
INTEGRATION_TEST_PATHS = (
    ROOT / "backend" / "tests" / "test_onboarding_demo.py",
    ROOT / "backend" / "tests" / "test_concurrency.py",
)
CI_DATABASE_URL = "postgresql+asyncpg://veklom:veklom_ci@localhost:5432/veklom_test"


def test_full_ci_workflows_provision_the_postgres_test_database():
    for workflow_path in WORKFLOW_PATHS:
        workflow = workflow_path.read_text(encoding="utf-8")

        assert "services:\n      postgres:" in workflow
        assert "POSTGRES_DB: veklom_test" in workflow
        assert CI_DATABASE_URL in workflow
        assert 'REDIS_ENABLED: "False"' in workflow


def test_postgres_integration_tests_do_not_override_the_ci_database_url():
    for test_path in INTEGRATION_TEST_PATHS:
        assert "sqlite+aiosqlite:///:memory:" not in test_path.read_text(
            encoding="utf-8"
        )
