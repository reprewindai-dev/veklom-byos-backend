import json
import os
import sys

# Add backend root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.apps.api.routers.internal_operators import WORKER_REGISTRY

def main():
    print(json.dumps(WORKER_REGISTRY, indent=2))

if __name__ == "__main__":
    main()
