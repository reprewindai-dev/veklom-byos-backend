from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
import httpx
import os
import json
from datetime import datetime
from backend.core.security.auth import get_current_user_optional

router = APIRouter(prefix="", tags=["Diagnostics"])

webhook_logs = []

@router.get("/api/health")
async def diagnostics_health():
    return {"status": "ok"}

@router.post("/api/mock-webhook")
async def mock_webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    log = {
        "id": os.urandom(4).hex(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": body,
        "headers": dict(request.headers)
    }
    webhook_logs.append(log)
    if len(webhook_logs) > 50:
        webhook_logs.pop(0)
    return {"status": "delivered", "id": log["id"]}

@router.get("/api/webhook-logs")
async def get_webhook_logs():
    return webhook_logs

@router.post("/api/trigger-alert")
async def trigger_alert(body: dict):
    url = body.get("url")
    payload = body.get("payload")
    if not url:
        return JSONResponse(status_code=400, content={"status": "error", "error": "Missing webhook target url"})
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=5.0)
            try:
                res_json = res.json()
            except Exception:
                res_json = res.text
            return {
                "status": "success",
                "statusCode": res.status_code,
                "response": res_json
            }
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@router.post("/api/analyze-ledger")
async def analyze_ledger(body: dict):
    prompt = body.get("prompt")
    items = body.get("items")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "MY_GEMINI_API_KEY":
        raise HTTPException(
            status_code=500,
            detail="Gemini API key is not configured. Node degraded."
        )
    try:
        # Dependency-free Google GenAI API request via HTTP POST REST API
        model_name = "gemini-2.5-flash"
        rest_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        full_prompt = (
            "You are the chief auditor for the Veklom Agent Authority Runtime.\n"
            "Here is the operational ledger and system status context for diagnostic review:\n"
            f"{json.dumps(items, indent=2)}\n\n"
            f"User request/diagnostic task:\n{prompt}\n\n"
            "Provide a highly technical, precise, system-level operational review. "
            "Highlight whether there is any violation of agent auth limits, vector smuggling attempts, "
            "or F-distribution deviations. Keep it formatted in raw markdown."
        )
        
        req_payload = {
            "contents": [{"parts": [{"text": full_prompt}]}]
        }
        
        async with httpx.AsyncClient() as client:
            res = await client.post(rest_url, json=req_payload, timeout=20.0)
            if res.status_code == 200:
                res_data = res.json()
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "status": "success",
                    "text": text
                }
            else:
                return {
                    "status": "error",
                    "error": f"API responded with status {res.status_code}: {res.text}"
                }
    except Exception as e:
        return {"status": "error", "error": str(e)}
