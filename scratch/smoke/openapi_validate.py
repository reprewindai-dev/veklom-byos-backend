import json
import sys
import traceback
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> int:
    print("=================================================================")
    print("VEKLOM OPENAPI VALIDATION")
    print("=================================================================")

    try:
        from backend.apps.api.main import app  # noqa: WPS433
    except Exception as exc:
        print(f"[FAIL] import backend.apps.api.main failed: {type(exc).__name__}: {exc}")
        print("Install runtime deps with: pip install -r requirements.txt")
        traceback.print_exc()
        print("PASS: 0")
        print("FAIL: 1")
        return 1

    try:
        schema = app.openapi()
        json.dumps(schema)
    except Exception as exc:
        print(f"[FAIL] OpenAPI generation failed: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        print("PASS: 0")
        print("FAIL: 1")
        return 1

    openapi_version = schema.get("openapi")
    title = (schema.get("info") or {}).get("title")
    paths = schema.get("paths") or {}
    components = schema.get("components") or {}
    schemas = components.get("schemas") or {}

    if not openapi_version or not title or not paths:
        print("[FAIL] OpenAPI schema missing required top-level fields")
        print("PASS: 0")
        print("FAIL: 1")
        return 1

    print(f"[PASS] openapi={openapi_version}")
    print(f"[PASS] title={title}")
    print(f"[PASS] paths={len(paths)}")
    print(f"[PASS] components.schemas={len(schemas)}")
    print("PASS: 4")
    print("FAIL: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
