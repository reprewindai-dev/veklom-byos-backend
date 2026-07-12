from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATABASE_MODULE_PATH = ROOT / "backend" / "core" / "database" / "database.py"
WORKFLOW_PATHS = (
    ROOT / ".github" / "workflows" / "ci.yml",
    ROOT / ".github" / "workflows" / "ci-cache.yml",
    ROOT / ".github" / "workflows" / "self-hosted-ci.yml",
)
LOCAL_API_WORKFLOW_PATHS = (
    ROOT / ".github" / "workflows" / "quota-enforcement.yml",
    ROOT / ".github" / "workflows" / "failure-drill.yml",
)
INTEGRATION_TEST_PATHS = (
    ROOT / "backend" / "tests" / "test_onboarding_demo.py",
    ROOT / "backend" / "tests" / "test_concurrency.py",
)
CI_DATABASE_URL = "postgresql+asyncpg://veklom:veklom_ci@localhost:5432/veklom_test"
CI_ARTIFACT_DIR = "${{ github.workspace }}/.ci-artifacts"


def test_full_ci_workflows_provision_the_postgres_test_database():
    for workflow_path in WORKFLOW_PATHS:
        workflow = workflow_path.read_text(encoding="utf-8")

        assert "services:\n      postgres:" in workflow
        assert "POSTGRES_DB: veklom_test" in workflow
        assert CI_DATABASE_URL in workflow
        assert 'REDIS_ENABLED: "False"' in workflow
        assert "APP_ENV: test" in workflow
        assert CI_ARTIFACT_DIR in workflow
        assert "runs-on: ubuntu-latest" in workflow


def test_postgres_integration_tests_do_not_override_the_ci_database_url():
    for test_path in INTEGRATION_TEST_PATHS:
        assert "sqlite+aiosqlite:///:memory:" not in test_path.read_text(
            encoding="utf-8"
        )


def test_test_environment_uses_a_loop_safe_database_pool():
    database_module = DATABASE_MODULE_PATH.read_text(encoding="utf-8")

    assert "from sqlalchemy.pool import NullPool" in database_module
    assert 'if settings.APP_ENV == "test":' in database_module
    assert 'engine_options["poolclass"] = NullPool' in database_module


def test_local_artifact_storage_uses_an_explicit_ci_override():
    storage_module = ROOT / "backend" / "core" / "services" / "local_storage.py"

    assert 'os.environ.get("LOCAL_ARTIFACT_DIR", "/data/artifacts")' in storage_module.read_text(encoding="utf-8")


def test_local_api_workflows_use_writable_artifact_storage_and_fail_fast():
    for workflow_path in LOCAL_API_WORKFLOW_PATHS:
        workflow = workflow_path.read_text(encoding="utf-8")

        assert CI_ARTIFACT_DIR in workflow
        assert "APP_ENV: test" in workflow
        assert 'kill -0 "$api_pid"' in workflow
