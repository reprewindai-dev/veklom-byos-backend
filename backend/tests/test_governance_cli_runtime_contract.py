from pathlib import Path

from backend.cli.governance.config import GovernanceCliConfig


def test_governance_cli_dashboard_default_uses_control_plane_port() -> None:
    config = GovernanceCliConfig()
    assert config.dashboard_url == "http://localhost:3002"


def test_governance_cli_canonical_defaults_forbid_legacy_ports() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    canonical_cli_files = (
        repo_root / "backend/cli/governance/config.py",
        repo_root / "backend/cli/governance/app.py",
    )

    for path in canonical_cli_files:
        source = path.read_text(encoding="utf-8")
        assert "localhost:3000" not in source
        assert "localhost:8000" not in source

    app_source = canonical_cli_files[1].read_text(encoding="utf-8")
    assert 'default="http://localhost:3002"' in app_source
