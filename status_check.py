import ssl
from urllib import error, request

urls = [
    "https://veklom.com/workspace",
    "https://veklom.com/uptime",
    "https://veklom.com/docs",
    "https://veklom.com/terminal",
    "https://veklom.com/command-center",
    "https://veklom.com/api/v1/platform/pulse",
    "https://veklom.com/legal/terms",
    "https://veklom.com/legal/privacy",
    "https://veklom.com/legal/security",
    "https://veklom.com/irongrid",
    "https://veklom.com/gpc-engine",
    "https://veklom.com/api/v1/openapi.json",
    "https://veklom.com/api/v1/feedback/",
    "https://veklom.com/workspace/login",
    "https://veklom.com/og-image.png",
    "https://veklom.com/favicon.svg",
    "https://veklom.com/robots.txt",
    "https://veklom.com/sitemap.xml",
    "https://veklom.com/api/v1/platform/status-updates",
    "https://veklom.com/api/v1/gpc/stats",
    "https://veklom.com/api/v1/agents/registry",
    "https://veklom.com/api/v1/marketplace/categories",
    "https://veklom.com/api/v1/command-center/users/summary",
    "https://veklom.com/api/v1/copilot/registry",
    "https://veklom.com/api/v1/sys/health",
    "https://veklom.com/api/v1/sys/gpu",
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
    "https://lockerphycer.veklom.com",
    "https://veklom.dev"
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for url in urls:
    try:
        req = request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = request.urlopen(req, timeout=15, context=ctx)
        print(url + " -> " + str(resp.status))
    except error.HTTPError as e:
        print(url + " -> " + str(e.code))
    except Exception as e:
        print(url + " -> ERROR: " + str(e))
