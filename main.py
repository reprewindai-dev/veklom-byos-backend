from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

# Load the real landing page HTML at startup
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LANDING_PATH = os.path.join(_BASE_DIR, "frontend", "landing", "index.html")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            with open(_LANDING_PATH, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = "<html><body><h1>Veklom BYOS Backend</h1><p>Landing page not found.</p></body></html>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Serving on http://0.0.0.0:{port}")
    server.serve_forever()
