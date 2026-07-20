#!/usr/bin/env python3
"""
Deploy GPC Standalone to Coolify
This script automates the deployment of the GPC standalone application to Coolify
"""

import requests
import json
import sys
import time
import os

# Coolify Configuration
COOLIFY_URL = os.getenv("COOLIFY_URL", "http://5.78.135.11:8000")
COOLIFY_API_TOKEN = os.getenv("COOLIFY_API_TOKEN")

if not COOLIFY_API_TOKEN:
    print("❌ Error: COOLIFY_API_TOKEN environment variable is not set.", file=sys.stderr)
    print("Please set it before running this script: export COOLIFY_API_TOKEN='your_token_here'", file=sys.stderr)
    sys.exit(1)

# Application Configuration
APP_CONFIG = {
    "name": "veklom-gpc",
    "description": "Veklom GPC Black Box - Standalone Governed Plan Compiler",
    "build_pack": "dockerfile",
    "dockerfile_location": "/Dockerfile",
    "base_directory": "/gpc-standalone",
    "ports_exposes": "80",
    "domains": "https://gpc.veklom.com,https://veklom-gpc.com"
}

def create_coolify_application():
    """Create the GPC application in Coolify"""
    
    headers = {
        "Authorization": f"Bearer {COOLIFY_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("🚀 Creating GPC application in Coolify...")
    
    # Create application
    app_data = {
        "name": APP_CONFIG["name"],
        "description": APP_CONFIG["description"],
        "build_pack": APP_CONFIG["build_pack"],
        "dockerfile_location": APP_CONFIG["dockerfile_location"],
        "base_directory": APP_CONFIG["base_directory"],
        "ports_exposes": APP_CONFIG["ports_exposes"],
        "domains": APP_CONFIG["domains"]
    }
    
    try:
        response = requests.post(
            f"{COOLIFY_URL}/api/v1/applications",
            headers=headers,
            json=app_data
        )
        
        if response.status_code == 201:
            app = response.json()
            print(f"✅ Application created successfully: {app['id']}")
            return app
        else:
            print(f"❌ Failed to create application: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating application: {e}")
        return None

def deploy_application(app_id):
    """Trigger deployment of the application"""
    
    headers = {
        "Authorization": f"Bearer {COOLIFY_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"🔄 Triggering deployment for application {app_id}...")
    
    try:
        response = requests.post(
            f"{COOLIFY_URL}/api/v1/applications/{app_id}/deploy",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Deployment triggered successfully")
            return True
        else:
            print(f"❌ Failed to trigger deployment: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error triggering deployment: {e}")
        return False

def check_deployment_status(app_id):
    """Check the deployment status"""
    
    headers = {
        "Authorization": f"Bearer {COOLIFY_API_TOKEN}"
    }
    
    print("⏳ Checking deployment status...")
    
    for i in range(30):  # Check for up to 5 minutes
        try:
            response = requests.get(
                f"{COOLIFY_URL}/api/v1/applications/{app_id}/deployments",
                headers=headers
            )
            
            if response.status_code == 200:
                deployments = response.json()
                if deployments:
                    latest = deployments[0]
                    status = latest.get('status', 'unknown')
                    print(f"📊 Deployment status: {status}")
                    
                    if status == 'running':
                        print("✅ Deployment completed successfully!")
                        return True
                    elif status == 'failed':
                        print("❌ Deployment failed!")
                        return False
                    
            time.sleep(10)  # Wait 10 seconds before checking again
            
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            time.sleep(10)
    
    print("⏰ Deployment check timeout")
    return False

def main():
    """Main deployment function"""
    
    print("🎯 Veklom GPC Standalone Deployment to Coolify")
    print("=" * 50)
    
    # Step 1: Create application
    app = create_coolify_application()
    if not app:
        sys.exit(1)
    
    app_id = app['id']
    
    # Step 2: Trigger deployment
    if not deploy_application(app_id):
        sys.exit(1)
    
    # Step 3: Monitor deployment
    if check_deployment_status(app_id):
        print("\n🎉 GPC Standalone deployed successfully!")
        print(f"📍 Application URL: https://gpc.veklom.com")
        print(f"🔧 Coolify Dashboard: {COOLIFY_URL}/applications/{app_id}")
    else:
        print("\n❌ Deployment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
