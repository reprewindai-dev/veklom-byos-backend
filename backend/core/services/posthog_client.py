"""PostHog analytics client for server-side telemetry."""

import logging
from typing import Optional, Dict, Any
from posthog import Posthog as PosthogClient
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)


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
