"""Autonomous agent for evaluating and pricing marketplace assets."""

import json
from typing import Any, Dict

from backend.core.ai.provider_router import ProviderRouter
from backend.db.models.asset import Asset
from sqlalchemy.orm import Session

class MarketplacePricerWorker:
    """Agent that analyzes uploaded assets and determines fair market pricing."""
    
    def __init__(self):
        self.router = ProviderRouter()
        
    async def evaluate_asset(self, db: Session, asset: Asset) -> Asset:
        """
        Evaluate an asset and determine its category and price.
        """
        prompt = f"""
        You are the Veklom Marketplace Intelligence Agent. 
        Analyze the following uploaded asset and determine a fair market price (in USD).
        
        Asset Metadata:
        - Filename: {asset.original_filename}
        - Content Type: {asset.content_type}
        - Size (Bytes): {asset.file_size}
        
        Return your analysis as a strict JSON object with the following keys:
        - "category": (string) e.g., "Plugin", "Dataset", "Model Weights", "Script"
        - "suggested_price_usd": (integer) The fair market price in whole dollars
        - "confidence_score": (integer 0-100) How confident you are in this pricing
        - "reasoning": (string) Brief justification for the price
        
        Do not include markdown blocks, just raw JSON.
        """
        
        try:
            # We use an inexpensive fast model to evaluate uploads to save reserve
            result = await self.router.route_inference(
                prompt=prompt,
                model_name="qwen2.5:1.5b",
                provider="ollama"
            )
            
            # Parse the AI response
            raw_text = result["text"].strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3]
                
            analysis = json.loads(raw_text)
            
            # Update the asset with intelligence
            asset.category = analysis.get("category", "Uncategorized")
            asset.price_usd = analysis.get("suggested_price_usd", 0)
            asset.intelligence_confidence = analysis.get("confidence_score", 0)
            asset.marketplace_status = "active" if asset.intelligence_confidence > 70 else "pending"
            
            db.commit()
            db.refresh(asset)
            
            return asset
            
        except Exception as e:
            # Fallback if evaluation fails
            asset.marketplace_status = "rejected"
            db.commit()
            db.refresh(asset)
            raise e
