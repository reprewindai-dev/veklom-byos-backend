def test_gpc_routes_import_with_package_qualified_modules():
    from backend.apps.gpc.routes import router

    assert router.prefix == "/api/v1/gpc"
