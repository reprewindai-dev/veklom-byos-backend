import json
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.contracts.sse_models import SseEvent, RunAcceptedEvent, RunPhaseEvent, RunTokenEvent, RunArtifactEvent, RunReceiptEvent, RunErrorEvent, RunHeartbeatEvent, RunDoneEvent
from backend.contracts.ledger_models import VnpBlock

def export_schemas():
    contracts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../contracts"))
    
    # Actually SseEvent is a TypeAlias. Let's create a root model for export.
    from pydantic import RootModel
    SseRoot = RootModel(SseEvent)
    
    sse_schema = SseRoot.model_json_schema()
    with open(os.path.join(contracts_dir, "sse-contract.json"), "w") as f:
        json.dump(sse_schema, f, indent=2)
        
    vnp_schema = VnpBlock.model_json_schema()
    with open(os.path.join(contracts_dir, "vnp-ledger-schema.json"), "w") as f:
        json.dump(vnp_schema, f, indent=2)
        
    print(f"Schemas exported successfully to {contracts_dir}")

if __name__ == "__main__":
    export_schemas()
