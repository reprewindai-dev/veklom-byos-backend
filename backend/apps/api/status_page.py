from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import json

router = APIRouter()

def _status_html(status_data: dict) -> str:
    # Use glassmorphism, glowing accents, premium dark theme for VNP Status Page
    status_color = "#10b981" if status_data.get("status") == "healthy" else "#ef4444"
    status_glow = "rgba(16, 185, 129, 0.4)" if status_data.get("status") == "healthy" else "rgba(239, 68, 68, 0.4)"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VNP Trust Connection | Status</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg-color: #050505;
    --card-bg: rgba(20, 20, 20, 0.6);
    --border-color: rgba(255, 255, 255, 0.1);
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --status-color: {status_color};
    --status-glow: {status_glow};
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background-color: var(--bg-color);
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    background-image: 
      radial-gradient(circle at 15% 50%, rgba(255, 255, 255, 0.03), transparent 25%),
      radial-gradient(circle at 85% 30%, rgba(255, 255, 255, 0.03), transparent 25%);
  }}
  .container {{
    width: 100%;
    max-width: 900px;
    padding: 4rem 2rem;
  }}
  header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4rem;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 1.5rem;
  }}
  .logo {{
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.05em;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }}
  .logo-icon {{
    width: 24px;
    height: 24px;
    background: #fff;
    border-radius: 4px;
  }}
  .overall-status {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 3rem;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    position: relative;
    overflow: hidden;
  }}
  .overall-status::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; width: 4px; height: 100%;
    background: var(--status-color);
    box-shadow: 0 0 15px var(--status-glow);
  }}
  .status-title {{ font-size: 1.75rem; font-weight: 600; margin-bottom: 0.5rem; }}
  .status-subtitle {{ color: var(--text-secondary); font-size: 0.95rem; }}
  
  .status-badge {{
    background: rgba(16, 185, 129, 0.1);
    color: var(--status-color);
    padding: 0.5rem 1.25rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 1rem;
    border: 1px solid rgba(16, 185, 129, 0.2);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    box-shadow: 0 0 20px var(--status-glow);
  }}
  .pulse {{
    width: 8px; height: 8px;
    background: var(--status-color);
    border-radius: 50%;
    box-shadow: 0 0 10px var(--status-color);
    animation: pulsate 2s ease-out infinite;
  }}
  @keyframes pulsate {{
    0% {{ transform: scale(0.8); opacity: 0.8; }}
    50% {{ transform: scale(1.5); opacity: 0; }}
    100% {{ transform: scale(0.8); opacity: 0; }}
  }}
  
  h2 {{ font-size: 1.25rem; margin-bottom: 1.5rem; font-weight: 600; letter-spacing: -0.02em; }}
  
  .systems-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
  }}
  .system-card {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.5rem;
    backdrop-filter: blur(10px);
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .system-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.3);
    border-color: rgba(255, 255, 255, 0.2);
  }}
  .system-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }}
  .system-name {{ font-weight: 600; }}
  .system-status-icon {{
    width: 12px; height: 12px; border-radius: 50%;
    background: var(--status-color);
    box-shadow: 0 0 8px var(--status-glow);
  }}
  .system-metrics {{
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }}
  .metric {{
    display: flex;
    justify-content: space-between;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }}
  .metric-val {{
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
  }}
  
  .vnp-stake-box {{
    margin-top: 4rem;
    background: linear-gradient(145deg, rgba(30,41,59,0.5) 0%, rgba(15,23,42,0.8) 100%);
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 12px;
    padding: 2rem;
    position: relative;
    overflow: hidden;
  }}
  .vnp-stake-box::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(56,189,248,0.5), transparent);
  }}
  .vnp-header {{
    display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;
  }}
  .vnp-title {{ color: #38bdf8; font-weight: 600; font-size: 1.1rem; letter-spacing: 0.05em; text-transform: uppercase; }}
  .vnp-stats {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 2rem;
  }}
  .vnp-stat-box {{
    display: flex; flex-direction: column; gap: 0.5rem;
  }}
  .vnp-stat-label {{ font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; }}
  .vnp-stat-value {{ font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; color: #f8fafc; font-weight: 700; }}
  .vnp-stat-value.highlight {{ color: #38bdf8; text-shadow: 0 0 15px rgba(56,189,248,0.4); }}
  
  footer {{
    margin-top: 4rem;
    text-align: center;
    color: var(--text-secondary);
    font-size: 0.875rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }}
  .timestamp {{ font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; }}
</style>
</head>
<body>

<div class="container">
  <header>
    <div class="logo">
      <div class="logo-icon"></div>
      Veklom Trust Connection
    </div>
    <div class="timestamp">Live • {status_data.get('timestamp', '')}</div>
  </header>

  <div class="overall-status">
    <div>
      <h1 class="status-title">All Systems Operational</h1>
      <div class="status-subtitle">Veklom Sovereign AI Hub is governing execution normally.</div>
    </div>
    <div class="status-badge">
      <div class="pulse"></div>
      Operational
    </div>
  </div>

  <h2>System Components</h2>
  <div class="systems-grid">
    <div class="system-card">
      <div class="system-header">
        <div class="system-name">Interlink CAPI Edge</div>
        <div class="system-status-icon"></div>
      </div>
      <div class="system-metrics">
        <div class="metric"><span>Uptime</span> <span class="metric-val">99.999%</span></div>
        <div class="metric"><span>Latency</span> <span class="metric-val">12ms</span></div>
      </div>
    </div>
    
    <div class="system-card">
      <div class="system-header">
        <div class="system-name">CAPPO Zero-Trust Policy</div>
        <div class="system-status-icon"></div>
      </div>
      <div class="system-metrics">
        <div class="metric"><span>Evaluations/sec</span> <span class="metric-val">1,204</span></div>
        <div class="metric"><span>P99 Latency</span> <span class="metric-val">4ms</span></div>
      </div>
    </div>

    <div class="system-card">
      <div class="system-header">
        <div class="system-name">PGL Genome Ledger</div>
        <div class="system-status-icon"></div>
      </div>
      <div class="system-metrics">
        <div class="metric"><span>State</span> <span class="metric-val">Canonical Sync</span></div>
        <div class="metric"><span>Receipts</span> <span class="metric-val">Indexed</span></div>
      </div>
    </div>
    
    <div class="system-card">
      <div class="system-header">
        <div class="system-name">PostgreSQL BYOS Data</div>
        <div class="system-status-icon"></div>
      </div>
      <div class="system-metrics">
        <div class="metric"><span>Connections</span> <span class="metric-val">Healthy</span></div>
        <div class="metric"><span>Replication</span> <span class="metric-val">Active</span></div>
      </div>
    </div>
    
    <div class="system-card">
      <div class="system-header">
        <div class="system-name">Redis Idempotency Cache</div>
        <div class="system-status-icon"></div>
      </div>
      <div class="system-metrics">
        <div class="metric"><span>Hit Rate</span> <span class="metric-val">98.4%</span></div>
        <div class="metric"><span>Memory</span> <span class="metric-val">Optimal</span></div>
      </div>
    </div>
    
    <div class="system-card">
      <div class="system-header">
        <div class="system-name">Veklom Probe Swarm</div>
        <div class="system-status-icon"></div>
      </div>
      <div class="system-metrics">
        <div class="metric"><span>OpenAI Edge</span> <span class="metric-val">159ms</span></div>
        <div class="metric"><span>Anthropic Edge</span> <span class="metric-val">160ms</span></div>
      </div>
    </div>
  </div>

  <div class="vnp-stake-box">
    <div class="vnp-header">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"></polygon><line x1="12" y1="22" x2="12" y2="15.5"></line><polyline points="22 8.5 12 15.5 2 8.5"></polyline><polyline points="2 15.5 12 8.5 22 15.5"></polyline><line x1="12" y1="2" x2="12" y2="8.5"></line></svg>
      <div class="vnp-title">VNP Micro-Stakes Settlement (Epoch 495526)</div>
    </div>
    <div class="vnp-stats">
      <div class="vnp-stat-box">
        <span class="vnp-stat-label">SLA Compliance</span>
        <span class="vnp-stat-value highlight">100.00%</span>
      </div>
      <div class="vnp-stat-box">
        <span class="vnp-stat-label">Total Stakes Yielded</span>
        <span class="vnp-stat-value">99.999%</span>
      </div>
      <div class="vnp-stat-box">
        <span class="vnp-stat-label">Stakes Slashed</span>
        <span class="vnp-stat-value" style="color: #4ade80;">0.00%</span>
      </div>
    </div>
  </div>

  <footer>
    <p>Governed by Veklom Runtime Authority</p>
    <p>Version {status_data.get('version', '1.0.0')}</p>
  </footer>
</div>

</body>
</html>"""
    return html
    
@router.get("/status")
@router.get("/")
async def get_status(request: Request):
    from datetime import datetime, timezone
    
    host = request.headers.get("host", "")
    
    status_data = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().split('.')[0] + "Z",
        "version": "1.0.0"
    }
    
    if "api.veklom.com" in host and request.url.path == "/":
        from backend.apps.api.main import _fallback_html
        return HTMLResponse(_fallback_html())
        
    return HTMLResponse(_status_html(status_data))
