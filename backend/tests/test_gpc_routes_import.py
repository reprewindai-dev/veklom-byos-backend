import importlib


def test_gpc_routes_module_imports() -> None:
    importlib.import_module("backend.apps.gpc.gpc_routes")
