import urllib.request, urllib.error, ssl, json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def req(url, method="GET", data=None, headers=None):
    h = headers or {}
    h["User-Agent"] = "Mozilla/5.0"
    if data and isinstance(data, dict):
        data = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
    try:
        r = urllib.request.Request(url, method=method, data=data, headers=h)
        resp = urllib.request.urlopen(r, timeout=15, context=ctx)
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body[:500]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body[:500]
    except Exception as e:
        return -1, str(e)

# Test auth endpoints
endpoints = [
    ("GET", "https://veklom.com/api/v1/auth/me", None),
    ("POST", "https://veklom.com/api/v1/auth/eval-session", {}),
    ("POST", "https://veklom.com/api/v1/auth/eval-session", {"email":"test@example.com","password":"test123"}),
    ("POST", "https://veklom.com/api/v1/auth/signin", {"email":"test@example.com","password":"test123"}),
    ("POST", "https://veklom.com/api/v1/auth/signup", {"email":"test@example.com","password":"test123","name":"Test"}),
    ("POST", "https://veklom.com/api/v1/auth/logout", {}),
    ("GET", "https://veklom.com/api/v1/auth/session", None),
]

for method, url, data in endpoints:
    code, body = req(url, method, data)
    print(f"{method} {url} -> {code}: {body}")
