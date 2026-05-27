import os
import sys

# Add backend to path
sys.path.append(os.path.abspath('.'))

from backend.apps.api.main import app

print("Registered Routes:")
for route in app.routes:
    # Print route path and methods
    methods = getattr(route, "methods", None)
    name = getattr(route, "name", None)
    print(f"  {route.path} (methods: {methods}, name: {name})")
