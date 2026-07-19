import asyncio
import httpx

async def run_vertical_slice():
    async with httpx.AsyncClient() as client:
        # First we need an API key or auth token.
        # But for testing, if auth is required we might need to bypass or mock it.
        # Wait, the endpoint uses `Depends(get_current_user_or_api_key)`.
        # I'll pass a valid API key if there's a test one, or just try it.
        
        # Actually, let's see how demo tests do it. 
        # Usually they use a test client.
        
        response = await client.post(
            "http://localhost:8000/v1/vertical-slice/execute",
            json={
                "agent_id": "test_agent",
                "capability": "some_capability",
                "payload": {}
            }
        )
        print(response.status_code)
        print(response.text)

if __name__ == "__main__":
    asyncio.run(run_vertical_slice())
