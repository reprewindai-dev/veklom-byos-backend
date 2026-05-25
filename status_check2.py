import urllib.request, urllib.error, ssl

urls = [
    "https://veklom.com/api/v1/openapi.json",
    "https://veklom.com/api/v1/feedback/",
    "https://veklom.com/api/v1/copilot/registry",
    "https://veklom.com/api/v1/sys/health",
    "https://veklom.com/api/v1/sys/gpu",
    "https://veklom.com/api/v1/platform/status-updates",
    "https://veklom.com/api/v1/gpc/stats",
    "https://veklom.com/api/v1/agents/registry",
    "https://veklom.com/api/v1/marketplace/categories",
    "https://veklom.com/api/v1/command-center/users/summary",
    "https://veklom.com/api/v1/agents/monthly-report",
    "https://veklom.com/api/v1/agents/decision-frames",
    "https://veklom.com/api/v1/ai/escalation/stats",
    "https://veklom.com/api/v1/gpc/plans",
    "https://veklom.com/api/v1/workspace/overview",
    "https://veklom.com/api/v1/workspace/overview/live",
    "https://veklom.com/api/v1/auth/me",
    "https://veklom.com/api/v1/auth/eval-session",
    "https://veklom.com/api/v1/agents/hrm/audit",
    "https://veklom.com/api/v1/agents/skills",
    "https://veklom.com/uptime",
    "https://veklom.com/legal/terms",
    "https://veklom.com/legal/privacy",
    "https://veklom.com/legal/security",
    "https://veklom.com/terminal",
    "https://veklom.com/api/v1/platform/pulse",
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for url in urls:
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        ct = resp.headers.get("Content-Type", "")
        print(url + " -> " + str(resp.status) + " (" + ct + ")")
    except urllib.error.HTTPError as e:
        ct = e.headers.get("Content-Type", "") if e.headers else ""
        print(url + " -> " + str(e.code) + " (" + ct + ")")
    except Exception as e:
        print(url + " -> ERROR: " + str(e))

# Check robots.txt and sitemap content type
for url in ["https://veklom.com/robots.txt", "https://veklom.com/sitemap.xml"]:
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        ct = resp.headers.get("Content-Type", "")
        body = resp.read(200)
        print(url + " -> " + str(resp.status) + " (" + ct + ") BODY: " + body.decode("utf-8", errors="replace").replace("\n", " "))
    except urllib.error.HTTPError as e:
        ct = e.headers.get("Content-Type", "") if e.headers else ""
        print(url + " -> " + str(e.code) + " (" + ct + ")")
    except Exception as e:
        print(url + " -> ERROR: " + str(e))
