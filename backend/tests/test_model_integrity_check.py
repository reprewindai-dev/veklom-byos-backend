import importlib.util
import io
import json
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "check_model_integrity.py"
)
SPEC = importlib.util.spec_from_file_location("check_model_integrity", SCRIPT_PATH)
assert SPEC and SPEC.loader
check_model_integrity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_model_integrity)


def run_check(payload, *args):
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = check_model_integrity.main(
        args,
        stdin=io.StringIO(json.dumps(payload)),
        stdout=stdout,
        stderr=stderr,
    )
    return exit_code, stdout.getvalue(), stderr.getvalue()


def healthy_payload(**overrides):
    payload = {
        "status": "healthy",
        "llm_ok": True,
        "groq_fallback_enabled": False,
        "providers_configured": ["ollama", "openai_gateway"],
    }
    payload.update(overrides)
    return payload


def test_healthy_public_path_does_not_require_optional_groq_fallback():
    exit_code, stdout, stderr = run_check(healthy_payload())

    assert exit_code == 0
    assert "ollama, openai_gateway" in stdout
    assert stderr == ""


def test_check_rejects_non_object_json_payload():
    exit_code, stdout, stderr = run_check(["ollama"])

    assert exit_code == 1
    assert stdout == ""
    assert "health response must be a JSON object" in stderr


def test_check_rejects_string_typed_providers():
    exit_code, stdout, stderr = run_check(
        healthy_payload(providers_configured="ollama")
    )

    assert exit_code == 1
    assert stdout == ""
    assert "providers_configured must be a non-empty list" in stderr


def test_groq_requirement_is_enforced_when_enabled():
    exit_code, stdout, stderr = run_check(
        healthy_payload(), "--require-groq-fallback", "true"
    )

    assert exit_code == 1
    assert stdout == ""
    assert "groq_fallback_enabled is not true" in stderr


def test_check_rejects_unhealthy_or_unconfigured_llm_path():
    exit_code, _, stderr = run_check(
        healthy_payload(status="degraded", llm_ok=False, providers_configured=[])
    )

    assert exit_code == 1
    assert "status is not healthy" in stderr
    assert "llm_ok is not true" in stderr
    assert "providers_configured must include at least one provider" in stderr


def test_check_rejects_invalid_groq_requirement_value():
    exit_code, stdout, stderr = run_check(
        healthy_payload(), "--require-groq-fallback", "enabled"
    )

    assert exit_code == 2
    assert stdout == ""
    assert "expected 'true' or 'false'" in stderr
