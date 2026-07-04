with open("audit.py", "r") as f:
    content = f.read()

search = """            if not (
                isinstance(func, ast.Attribute)
                and func.attr.lower() in HTTP_METHODS
                and isinstance(func.value, ast.Name)
                and func.value.id == "router"
            ):
                continue
            route_path = literal_string(decorator.args[0]) if decorator.args else None
            if route_path and route_path.startswith("/"):
                routes.add((func.attr.upper(), route_path))"""

replace = """            if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "router"):
                continue

            route_path = literal_string(decorator.args[0]) if decorator.args else None
            if not route_path or not route_path.startswith("/"):
                continue

            if func.attr.lower() in HTTP_METHODS:
                routes.add((func.attr.upper(), route_path))
            elif func.attr == "api_route":
                # Extract methods from the keywords (e.g. methods=["GET", "HEAD"])
                methods = []
                for kw in decorator.keywords:
                    if kw.arg == "methods" and isinstance(kw.value, ast.List):
                        for elt in kw.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                methods.append(elt.value.upper())

                if not methods:
                    methods = ["GET"] # Default if not specified, though usually it is

                for m in methods:
                    routes.add((m, route_path))"""

content = content.replace(search, replace)
with open("audit.py", "w") as f:
    f.write(content)
