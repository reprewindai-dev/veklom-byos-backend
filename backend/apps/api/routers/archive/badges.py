import uuid
import math
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.future import select

from backend.core.database.database import get_db_session
from backend.db.models.vnp import Api, RegionalTelemetry

router = APIRouter(prefix="/badges", tags=["vnp-badges"])

def generate_svg_badge(api_name: str, score: float, tier: str, date_str: str) -> str:
    """Generates an XML-compliant SVG badge for VNP."""
    
    color = "#FF6B35" # Default Orange
    if tier == "GOLD":
        color = "#FFD700"
    elif tier == "SILVER":
        color = "#C0C0C0"
    elif tier == "BRONZE":
        color = "#CD7F32"
    elif tier == "FAILING":
        color = "#EF4444"

    return f"""<svg width="250" height="60" viewBox="0 0 250 60" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="250" height="60" rx="8" fill="#1F2937"/>
  <rect x="1" y="1" width="248" height="58" rx="7" stroke="{color}" stroke-opacity="0.3" stroke-width="2"/>
  
  <!-- Left Side: VNP Logo / Score -->
  <path d="M0 8C0 3.58172 3.58172 0 8 0H80V60H8C3.58172 60 0 56.4183 0 52V8Z" fill="{color}"/>
  <text x="40" y="22" fill="#000000" font-family="system-ui, -apple-system, sans-serif" font-size="12" font-weight="bold" text-anchor="middle">VNP SCORE</text>
  <text x="40" y="48" fill="#000000" font-family="system-ui, -apple-system, sans-serif" font-size="28" font-weight="900" text-anchor="middle">{score:.1f}</text>

  <!-- Right Side: API Info -->
  <text x="95" y="24" fill="#FFFFFF" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="bold">{api_name}</text>
  
  <text x="95" y="44" fill="#9CA3AF" font-family="system-ui, -apple-system, sans-serif" font-size="11">CERTIFIED</text>
  <text x="160" y="44" fill="{color}" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="bold">{tier}</text>
  
  <text x="95" y="55" fill="#6B7280" font-family="system-ui, -apple-system, sans-serif" font-size="8">Updated: {date_str}</text>
</svg>"""

@router.get("/{api_id}.svg")
async def get_api_badge_svg(api_id: str):
    """Serve a dynamically generated SVG badge for the API."""
    async with get_db_session() as db:
        # Resolve API
        if api_id.startswith("did:vnp:api:"):
            api = (await db.execute(select(Api).where(Api.api_did == api_id))).scalars().first()
        else:
            try:
                api_uuid = uuid.UUID(api_id)
                api = await db.get(Api, api_uuid)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid API ID format")

        if not api:
            raise HTTPException(status_code=404, detail="API not found")

        # Fetch latest telemetry score (fallback to Api.current_composite_score)
        telemetry = (await db.execute(
            select(RegionalTelemetry)
            .where(RegionalTelemetry.api_id == api.id)
            .order_by(RegionalTelemetry.measured_at.desc())
            .limit(1)
        )).scalars().first()

        score = float(telemetry.trust_score) if telemetry else float(api.current_composite_score)
        
        if score >= 85:
            tier = "GOLD"
        elif score >= 75:
            tier = "SILVER"
        elif score >= 65:
            tier = "BRONZE"
        else:
            tier = "FAILING"

        date_str = telemetry.measured_at.strftime("%Y-%m-%d %H:%M") if telemetry else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        svg_content = generate_svg_badge(api.name, score, tier, date_str)
        return Response(content=svg_content, media_type="image/svg+xml", headers={
            "Cache-Control": "public, max-age=300" # 5 minute cache
        })
