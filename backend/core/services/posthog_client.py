"""PostHog analytics client for server-side telemetry."""

import hashlib
import logging
from typing import Optional, Dict, Any
from posthog import Posthog as PosthogClient
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)


def hash_id(value: str) -> str:
    """
    Create a non-reversible hash for distinct_id.
    Never send raw PII (email, wallet, etc.) to PostHog.
    """
    return hashlib.sha256(value.encode()).hexdigest()


class PostHogService:
    """Service for sending events to PostHog analytics."""

    def __init__(self):
        self.client: Optional[PosthogClient] = None
        self.enabled = settings.POSTHOG_ENABLED and bool(settings.POSTHOG_API_KEY)
        
        if self.enabled:
            try:
                self.client = PosthogClient(
                    api_key=settings.POSTHOG_API_KEY,
                    host=settings.POSTHOG_HOST,
                    debug=settings.DEBUG
                )
                logger.info("PostHog client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PostHog client: {e}")
                self.enabled = False
        else:
            logger.info("PostHog analytics disabled")

    def capture(
        self,
        distinct_id: str,
        event: str,
        properties: Optional[Dict[str, Any]] = None,
        groups: Optional[Dict[str, Any]] = None
    ) -> None:
        """Capture an event to PostHog."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.capture(
                distinct_id=distinct_id,
                event=event,
                properties=properties or {},
                groups=groups or {}
            )
            logger.debug(f"Captured event: {event} for user: {distinct_id}")
        except Exception as e:
            logger.error(f"Failed to capture event {event}: {e}")

    def identify(
        self,
        distinct_id: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Identify a user in PostHog."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.identify(
                distinct_id=distinct_id,
                properties=properties or {}
            )
            logger.debug(f"Identified user: {distinct_id}")
        except Exception as e:
            logger.error(f"Failed to identify user {distinct_id}: {e}")

    def alias(
        self,
        distinct_id: str,
        previous_id: str
    ) -> None:
        """Alias a user ID to another ID."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.alias(
                distinct_id=distinct_id,
                previous_id=previous_id
            )
            logger.debug(f"Aliased {previous_id} to {distinct_id}")
        except Exception as e:
            logger.error(f"Failed to alias {previous_id} to {distinct_id}: {e}")

    # Canonical marketplace events
    def hero_cta_click(self, distinct_id: str, placement: str, page: str) -> None:
        """Track hero CTA clicks."""
        self.capture(distinct_id, "hero_cta_click", {
            "placement": placement,
            "page": page
        })

    def demo_signup(
        self,
        distinct_id: str,
        utm_source: str,
        utm_medium: str,
        utm_campaign: str,
        variant: str = "control",
        utm_term: Optional[str] = None,
        utm_content: Optional[str] = None
    ) -> None:
        """Track demo signup with UTM parameters."""
        props = {
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
            "variant": variant
        }
        if utm_term:
            props["utm_term"] = utm_term
        if utm_content:
            props["utm_content"] = utm_content
        self.capture(distinct_id, "demo_signup", props)

    def workspace_opened(self, distinct_id: str, workspace_id: str) -> None:
        """Track workspace opened."""
        self.capture(distinct_id, "workspace_opened", {
            "workspace_id": workspace_id
        })

    def terminal_run_ok(self, distinct_id: str, sample_id: str, latency_ms: int) -> None:
        """Track successful terminal run."""
        self.capture(distinct_id, "terminal_run_ok", {
            "sample_id": sample_id,
            "latency_ms": latency_ms
        })

    def marketplace_listing_view(self, distinct_id: str, listing_id: str, price_usd: float) -> None:
        """Track marketplace listing view."""
        self.capture(distinct_id, "marketplace_listing_view", {
            "listing_id": listing_id,
            "price_usd": price_usd
        })

    def marketplace_purchase(
        self,
        distinct_id: str,
        order_id: str,
        listing_id: str,
        price_cents: int,
        currency: str = "USD"
    ) -> None:
        """Track marketplace purchase (amount in cents)."""
        self.capture(distinct_id, "marketplace_purchase", {
            "order_id": order_id,
            "listing_id": listing_id,
            "price_cents": price_cents,
            "currency": currency
        })

    def payment_initiated(
        self,
        distinct_id: str,
        order_id: str,
        amount_cents: int,
        currency: str,
        payment_method: str,
        tx_placeholder: str
    ) -> None:
        """Track payment initiated (amount in cents)."""
        self.capture(distinct_id, "payment_initiated", {
            "order_id": order_id,
            "amount_cents": amount_cents,
            "currency": currency,
            "payment_method": payment_method,
            "tx_placeholder": tx_placeholder
        })

    def payment_confirmed(
        self,
        distinct_id: str,
        order_id: str,
        tx_hash: str,
        confirmations: int,
        status: str
    ) -> None:
        """Track payment confirmed."""
        self.capture(distinct_id, "payment_confirmed", {
            "order_id": order_id,
            "tx_hash": tx_hash,
            "confirmations": confirmations,
            "status": status
        })

    def shutdown(self) -> None:
        """Flush and shutdown the PostHog client."""
        if self.client:
            try:
                self.client.flush()
                logger.info("PostHog client flushed")
            except Exception as e:
                logger.error(f"Failed to flush PostHog client: {e}")


# Global instance
posthog_service = PostHogService()
