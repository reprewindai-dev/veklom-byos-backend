"""Source-truth guard for the historical embedded control plane."""

import json
from pathlib import Path


def test_embedded_control_plane_is_non_deployable_reference():
    package = json.loads(Path("apps/control-plane/package.json").read_text(encoding="utf-8"))

    assert package.get("private") is True
    assert "Reference-only" in package.get("deprecated", "")

    for command in ("dev", "build", "start"):
        script = package["scripts"][command]
        assert "process.exit(1)" in script
        assert "next dev" not in script
        assert "next start" not in script
        assert "3000" not in script


def test_embedded_control_plane_readme_points_to_canonical_frontend():
    readme = Path("apps/control-plane/README.md").read_text(encoding="utf-8")

    assert "reprewindai-dev/veklom-FRONTEND" in readme
    assert "non-deployable" in readme.lower()
    assert "localhost:3000" not in readme
