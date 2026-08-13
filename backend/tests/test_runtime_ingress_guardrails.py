from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_compose_does_not_publish_internal_service_ports() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert '"8088:8088"' not in compose
    assert '"5432:5432"' not in compose
    assert '"6379:6379"' not in compose
    assert '"11434:11434"' not in compose


def test_runtime_cors_has_only_canonical_production_browser_origins() -> None:
    source = (ROOT / "backend" / "apps" / "api" / "main.py").read_text(
        encoding="utf-8"
    )

    assert '"https://veklom.com"' in source
    assert '"https://app.veklom.com"' in source
    assert '"https://control.veklom.com"' not in source
    assert '"https://abide.veklom.com"' not in source


def test_dualstack_server_does_not_trust_every_forwarding_source() -> None:
    source = (ROOT / "backend" / "apps" / "api" / "dualstack_server.py").read_text(
        encoding="utf-8"
    )

    assert 'forwarded_allow_ips="*"' not in source
