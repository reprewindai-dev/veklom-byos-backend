import httpx
import json
import sys
import time

BASE_URL = "https://api.veklom.com"

def log_step(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

async def test_gpc_pipeline():
    # Step 1: Create an Authenticated Eval Session
    log_step("STEP 1: Authenticate & Generate Bearer JWT")
    async with httpx.AsyncClient(timeout=120.0) as client:
        auth_resp = await client.post(
            f"{BASE_URL}/api/v1/auth/eval-session",
            json={"fingerprint": "smoketest_client_run"}
        )
        if auth_resp.status_code != 200:
            print(f"Auth failed: {auth_resp.status_code} - {auth_resp.text}")
            return
        
        auth_data = auth_resp.json()
        token = auth_data["access_token"]
        user_email = auth_data["user"]["email"]
        print(f"Successfully Authenticated as: {user_email}")
        print(f"Bearer Token: Bearer {token[:25]}...[truncated]")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Step 2: POST /api/v1/gpc/intent-to-plan (Natural Language to Graph Intent)
        log_step("STEP 2: POST /api/v1/gpc/intent-to-plan (Natural Language to Graph)")
        intent_payload = {
            "intent": "Load active customer accounts from CSV, select columns id and state, group by state and count them, then save as parquet.",
            "provider": "ollama",
            "model": "qwen2.5:3b"
        }
        print(f"Sending Natural Language Intent:\n{json.dumps(intent_payload, indent=2)}")
        
        intent_resp = await client.post(
            f"{BASE_URL}/api/v1/gpc/intent-to-plan",
            json=intent_payload,
            headers=headers
        )
        if intent_resp.status_code != 200:
            print(f"Intent parsing failed: {intent_resp.status_code} - {intent_resp.text}")
            return
            
        intent_data = intent_resp.json()
        pipeline_id = intent_data["id"]
        graph = intent_data["graph"]
        print(f"\nGenerated Pipeline ID: {pipeline_id}")
        print("Generated Graph Nodes:")
        for node in graph["nodes"]:
            print(f"  - [{node['id']}] {node['data']['label']} ({node['data']['nodeType']}) at position {node['position']}")
        print("Generated Graph Edges:")
        for edge in graph["edges"]:
            print(f"  - {edge['source']} ---> {edge['target']}")
        print("Generated Node Configurations:")
        print(json.dumps(graph["node_configs"], indent=2))

        # Step 3: POST /api/v1/gpc/compile (AST Python Compilation)
        log_step("STEP 3: POST /api/v1/gpc/compile (AST Compilation)")
        compile_payload = {
            "pipeline_id": pipeline_id
        }
        compile_resp = await client.post(
            f"{BASE_URL}/api/v1/gpc/compile",
            json=compile_payload,
            headers=headers
        )
        if compile_resp.status_code != 200:
            print(f"Compilation failed: {compile_resp.status_code} - {compile_resp.text}")
            return
            
        compile_data = compile_resp.json()
        print(f"Compilation Success: {compile_data['success']}")
        print(f"Execution Node Order: {compile_data['execution_order']}")
        print("\nGenerated Portable Python AST Output Code:\n")
        print("-" * 60)
        print(compile_data["python_code"])
        print("-" * 60)

        # Step 4: POST /api/v1/gpc/execute (Server-Sent Events Execution)
        log_step("STEP 4: POST /api/v1/gpc/execute (Streaming SSE Canvas Updates)")
        print(f"Initiating stream execution session for pipeline {pipeline_id}...")
        
        # We use a streaming request to read SSE lines
        async with client.stream(
            "POST",
            f"{BASE_URL}/api/v1/gpc/execute?pipeline_id={pipeline_id}",
            headers=headers
        ) as response:
            if response.status_code != 200:
                print(f"Execution failed: {response.status_code}")
                return
                
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line.removeprefix("data: ")
                    event_data = json.loads(data_str)
                    event_type = event_data.get("event")
                    
                    if event_type == "start":
                        print(f"\n[SYSTEM] Execution started! Total nodes to compile & run: {event_data['node_count']}\n")
                    elif event_type == "node_start":
                        print(f"[NODE-START] Running Node: {event_data['node_id']} (Index {event_data['index']})")
                    elif event_type == "node_complete":
                        node_id = event_data["node_id"]
                        preview = event_data["preview"]
                        print(f"[NODE-COMPLETE] Node {node_id} successfully compiled and executed!")
                        print(f"  |-- Rows Processed: {preview.get('rows')}")
                        print(f"  |-- Schema Columns: {preview.get('columns')}")
                        print(f"  |-- Preview Sample Metadata: {preview.get('metadata')}")
                        print(f"  \-- Sample Rows:")
                        for row in preview.get("sample", []):
                            print(f"      \-- {row}")
                        print()
                    elif event_type == "complete":
                        print(f"[SYSTEM] Pipeline Execution completed successfully!")
                        print(f"  \-- Run ID: {event_data.get('run_id')}\n")
                    elif event_type == "error":
                        print(f"[SYSTEM-ERROR] Stream crashed: {event_data.get('message')}")

        # Step 5: GET /api/v1/gpc/audit (Retrieve persisted Law 25 Section 93 trace)
        log_step("STEP 5: GET /api/v1/gpc/audit (Sovereign Compliance Audit Trail)")
        audit_resp = await client.get(
            f"{BASE_URL}/api/v1/gpc/audit?pipeline_id={pipeline_id}",
            headers=headers
        )
        if audit_resp.status_code != 200:
            print(f"Audit lookup failed: {audit_resp.status_code} - {audit_resp.text}")
            return
            
        audit_data = audit_resp.json()
        print(f"Persisted compliance records matching pipeline: {pipeline_id}")
        print(json.dumps(audit_data, indent=2))

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_gpc_pipeline())
