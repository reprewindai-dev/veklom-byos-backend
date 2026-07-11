import httpx
import asyncio

async def test_workspace():
    base_url = "http://localhost:80/api/v1"
    
    print("1. Registering new user and workspace...")
    # Register to get token and workspace ID
    register_data = {
        "email": "test_workspace_config@example.com",
        "password": "strongpassword123",
        "full_name": "Test User",
        "workspace_name": "Test Config Workspace"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(f"{base_url}/auth/register", json=register_data)
            data = r.json()
            if r.status_code == 400 and "already exists" in str(data):
                print("User exists, logging in...")
                r = await client.post(f"{base_url}/auth/login", json={"username": register_data["email"], "password": register_data["password"]})
                data = r.json()
            
            token = data.get("access_token")
            workspace_id = data.get("workspace_id")
            print(f"Got Token (length {len(str(token))})")
            
            # Now let's test GET /auth/me
            print("\n2. Testing /auth/me to verify workspace ID matches manual table stuff...")
            headers = {"Authorization": f"Bearer {token}"}
            me_req = await client.get(f"{base_url}/auth/me", headers=headers)
            me_data = me_req.json()
            print(f"Me Endpoint Returns: {me_data}")
            
            # Now let's test GET /workspace/config
            print("\n3. Testing GET /workspace/config ...")
            cfg_req = await client.get(f"{base_url}/workspace/config", headers=headers)
            print(f"Status: {cfg_req.status_code}")
            print(f"Config Data: {cfg_req.json()}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(test_workspace())
