from fastapi import FastAPI, Request, Header
import json
import asyncio
import logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)

@app.post("/event_handler")
async def event_handler(request: Request, x_github_event: str = Header(None)):
    payload_bytes = await request.body()
    try:
        # GitHub sends application/x-www-form-urlencoded or application/json
        # If urlencoded, it will be in form data under 'payload'
        content_type = request.headers.get('content-type', '')
        if 'application/x-www-form-urlencoded' in content_type:
            form_data = await request.form()
            payload = json.loads(form_data.get('payload', '{}'))
        else:
            payload = await request.json()
    except Exception as e:
        logging.error(f"Failed to parse payload: {e}")
        return {"error": "Invalid payload"}

    if x_github_event == "pull_request":
        if payload.get("action") == "closed" and payload.get("pull_request", {}).get("merged"):
            logging.info("A pull request was merged! A deployment should start now...")
            asyncio.create_task(start_deployment(payload.get("pull_request")))
            
    elif x_github_event == "deployment":
        asyncio.create_task(process_deployment(payload))
        
    elif x_github_event == "deployment_status":
        update_deployment_status(payload)
        
    return "Well, it worked!"

async def start_deployment(pull_request):
    user = pull_request.get('user', {}).get('login', 'unknown')
    repo_full_name = pull_request.get('head', {}).get('repo', {}).get('full_name', 'unknown')
    sha = pull_request.get('head', {}).get('sha', 'unknown')
    
    deployment_payload = json.dumps({"environment": "production", "deploy_user": user})
    logging.info(f"Starting deployment for {repo_full_name} at {sha} by {user}...")
    
    # In a real app, you would use PyGithub or httpx to call GitHub API:
    # POST /repos/{repo_full_name}/deployments
    # ...

async def process_deployment(payload):
    deployment_payload = json.loads(payload.get('payload', '{}'))
    deploy_user = deployment_payload.get('deploy_user', 'unknown')
    environment = deployment_payload.get('environment', 'unknown')
    description = payload.get('description', 'No description')
    
    logging.info(f"Processing '{description}' for {deploy_user} to {environment}")
    await asyncio.sleep(2) # simulate work
    logging.info("Status: pending")
    # Call GitHub API to create deployment status: pending
    
    await asyncio.sleep(2) # simulate work
    logging.info("Status: success")
    # Call GitHub API to create deployment status: success

def update_deployment_status(payload):
    deployment_id = payload.get('deployment', {}).get('id', 'unknown')
    state = payload.get('deployment_status', {}).get('state', 'unknown')
    logging.info(f"Deployment status for {deployment_id} is {state}")

if __name__ == "__main__":
    import uvicorn
    # Start on port 4567 to match the tutorial
    uvicorn.run(app, host="0.0.0.0", port=4567)
