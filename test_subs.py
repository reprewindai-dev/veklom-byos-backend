import httpx
import asyncio

async def test_subs():
    base_url = "https://veklom.com/api/v1"
    
    # We use the previous user's credentials to login
    login_data = {
        "username": "test_workspace_config2@example.com",
        "password": "strongpassword123"
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            r = await client.post(f"{base_url}/auth/login", json=login_data)
            data = r.json()
            token = data.get("access_token")
            
            headers = {"Authorization": f"Bearer {token}"}
            
            print("\nTesting GET /subscriptions/plans ...")
            req = await client.get(f"{base_url}/subscriptions/plans", headers=headers)
            print(f"Status: {req.status_code}")
            
            print("\nTesting GET /subscriptions/current ...")
            req = await client.get(f"{base_url}/subscriptions/current", headers=headers)
            print(f"Status: {req.status_code}")
            print(f"Response: {req.text}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(test_subs())
