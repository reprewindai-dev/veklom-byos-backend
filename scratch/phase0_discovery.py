import asyncio
import json
import os
from collections import defaultdict
from playwright.async_api import async_playwright

BASE_URL = "https://api.veklom.com/control-plane-next"
API_BASE = "https://api.veklom.com/api/v1"

PAGES_TO_CRAWL = [
    "/dashboard",
    "/marketplace",
    "/playground",
    "/status",
    "/wallet",
    "/usage",
    "/billing",
    "/routing",
    "/pipelines",
    "/autonomous",
    "/insights",
    "/audit",
    "/kill-switch",
    "/budget",
    "/compliance",
    "/locker",
    "/content-safety",
    "/privacy",
    "/security",
    "/governance",
    "/team",
    "/api-keys",
    "/webhooks",
    "/subscriptions",
    "/workspace",
    "/vendor/onboarding",
    "/vendor/listings",
    "/vendor/payouts",
    "/vendor/stripe",
    "/admin"
]

async def run_discovery():
    print("Starting Phase 0 Contract Discovery...")
    
    endpoint_matrix = defaultdict(list)
    errors = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        # 1. Listen for network requests
        async def handle_response(response):
            req = response.request
            if API_BASE in req.url:
                endpoint = req.url.split(API_BASE)[1].split("?")[0]
                status = response.status
                endpoint_matrix[page.url].append({
                    "method": req.method,
                    "endpoint": endpoint,
                    "status": status,
                    "url": req.url
                })
                if status >= 400:
                    errors.append({
                        "page": page.url,
                        "endpoint": endpoint,
                        "method": req.method,
                        "status": status
                    })

        page.on("response", handle_response)
        
        # 2. Listen for console errors
        page.on("console", lambda msg: errors.append({"page": page.url, "type": "console", "text": msg.text}) if msg.type == "error" else None)
        
        # 3. Register a test user to get a session
        print("Registering test user for discovery...")
        try:
            await page.goto(f"{BASE_URL}/signup")
            await page.fill('input[type="text"]', "Automated Discovery")
            await page.fill('input[type="email"]', "discovery@veklom.com")
            await page.fill('input[type="password"]', "TestPassword123!")
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(2000)
            
            # Verify we are logged in by checking localStorage for token
            token = await page.evaluate("window.localStorage.getItem('veklom.access_token')")
            if not token:
                print("Failed to register. Attempting login...")
                await page.goto(f"{BASE_URL}/login")
                await page.fill('input[type="email"]', "discovery@veklom.com")
                await page.fill('input[type="password"]', "TestPassword123!")
                await page.click('button[type="submit"]')
                await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Auth flow error: {e}")

        # 4. Crawl all pages
        for path in PAGES_TO_CRAWL:
            print(f"Crawling {path}...")
            url = f"{BASE_URL}{path}"
            try:
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(1000) # Wait for any lazy fetched data
            except Exception as e:
                errors.append({"page": url, "type": "navigation_error", "error": str(e)})

        await browser.close()
        
        # Save results
        with open("scratch/discovery_matrix.json", "w") as f:
            json.dump({
                "matrix": endpoint_matrix,
                "errors": errors
            }, f, indent=2)
            
        print("\nDiscovery Complete! Results saved to scratch/discovery_matrix.json")
        print(f"Total API Errors Found: {len([e for e in errors if e.get('status')])}")

if __name__ == "__main__":
    asyncio.run(run_discovery())
