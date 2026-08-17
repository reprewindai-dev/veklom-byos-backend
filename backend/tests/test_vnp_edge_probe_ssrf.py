"""Regression coverage for the VNP edge probe outbound-target boundary."""

import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException


MODULE_PATH = Path("infra/vnp-edge-probe/vnp_edge_probe.py")


def _load_probe_module(monkeypatch, tmp_path, allowed_urls=None):
    monkeypatch.setenv("VNP_KEY_DIR", str(tmp_path / "vnp-keys"))
    if allowed_urls is None:
        monkeypatch.delenv("VNP_PROBE_ALLOWED_URLS", raising=False)
    else:
        monkeypatch.setenv("VNP_PROBE_ALLOWED_URLS", allowed_urls)

    spec = importlib.util.spec_from_file_location("vnp_edge_probe_ssrf_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "target",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "http://localhost/admin",
        "http://service.local/health",
        "http://127.0.0.1:8080/health",
        "http://0.0.0.0/health",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/internal",
        "http://192.168.1.20/internal",
        "http://[::1]/health",
        "https://user:pass@example.com/health",
        "https://example.com/health#fragment",
    ],
)
def test_probe_target_rejects_unsafe_destinations(monkeypatch, tmp_path, target):
    probe = _load_probe_module(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as exc:
        probe.validate_probe_target_url(target)

    assert exc.value.status_code == 400


def test_probe_target_rejects_public_url_not_on_server_allowlist(monkeypatch, tmp_path):
    probe = _load_probe_module(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as exc:
        probe.validate_probe_target_url("https://example.com/health")

    assert exc.value.status_code == 400
    assert "allowed probe target" in exc.value.detail


def test_probe_target_returns_canonical_server_allowlist_value(monkeypatch, tmp_path):
    probe = _load_probe_module(
        monkeypatch,
        tmp_path,
        "https://api.veklom.com/health,https://status.veklom.com/ping",
    )

    assert probe.validate_probe_target_url("HTTPS://API.VEKLOM.COM:443/health") == (
        "https://api.veklom.com/health"
    )
    assert probe.validate_probe_target_url("https://status.veklom.com/ping") == (
        "https://status.veklom.com/ping"
    )


def test_probe_source_does_not_send_body_target_directly(monkeypatch, tmp_path):
    _load_probe_module(monkeypatch, tmp_path)
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert "client.get(str(body.target_url)" not in source
    assert "target_url = validate_probe_target_url(str(body.target_url))" in source
    assert "client.get(target_url" in source
    assert '"target_url": target_url' in source
