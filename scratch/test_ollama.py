import asyncio
import httpx
from backend.core.config.settings import settings

async def main():
    base = settings.LLM_BASE_URL
    m = settings.LLM_MODEL_DEFAULT
    print("Base URL:", base)
    print("Model default:", m)
    
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            url = f"{base}/api/generate"
            payload = {
                "model": m,
                "prompt": "hello",
                "stream": False,
                "options": {"num_predict": 512}
            }
            print("Sending POST request to:", url)
            print("Payload:", payload)
            resp = await client.post(url, json=payload)
            print("Status code:", resp.status_code)
            print("Response headers:", resp.headers)
            print("Response body:", resp.text)
    except Exception as e:
        print("EXCEPTION OCCURRED:", e)

asyncio.run(main())
