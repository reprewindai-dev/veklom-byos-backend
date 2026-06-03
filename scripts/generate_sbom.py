#!/usr/bin/env python3
"""Generate a CycloneDX 1.5 SBOM from requirements.txt (stdlib only).

Usage:
    python scripts/generate_sbom.py

Writes sbom/veklom-backend.cdx.json. No external dependencies required, so it
runs in CI, locally, or inside the container without installing anything.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQ = ROOT / "requirements.txt"
OUT_DIR = ROOT / "sbom"
OUT = OUT_DIR / "veklom-backend.cdx.json"

# name[extras]==version  | name>=version  | name
_LINE_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9._-]+)"
    r"(?:\[(?P<extras>[^\]]+)\])?"
    r"\s*(?P<op>==|>=|<=|~=|!=|>|<)?\s*(?P<version>[A-Za-z0-9.*+!-]+)?"
)


def parse_requirements(path: Path) -> list[dict]:
    comps: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        name = m.group("name")
        version = m.group("version") or ""
        op = m.group("op") or ""
        purl = f"pkg:pypi/{name.lower()}" + (f"@{version}" if op == "==" and version else "")
        comp = {
            "type": "library",
            "name": name,
            "bom-ref": f"pypi:{name.lower()}",
            "purl": purl,
        }
        if version:
            comp["version"] = (f"{op}{version}" if op and op != "==" else version)
        if m.group("extras"):
            comp["properties"] = [
                {"name": "pip:extras", "value": m.group("extras")}
            ]
        comps.append(comp)
    return comps


def build_sbom(components: list[dict]) -> dict:
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "tools": [{"vendor": "Veklom", "name": "generate_sbom.py", "version": "1.0"}],
            "component": {
                "type": "application",
                "name": "veklom-byos-backend",
                "version": "1.0",
                "description": "Veklom Sovereign AI Hub backend (FastAPI).",
                "bom-ref": "veklom-byos-backend",
            },
        },
        "components": components,
    }


def main() -> int:
    if not REQ.exists():
        print(f"requirements.txt not found at {REQ}", file=sys.stderr)
        return 1
    components = parse_requirements(REQ)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build_sbom(components), indent=2), encoding="utf-8")
    print(f"SBOM written: {OUT} ({len(components)} components)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
