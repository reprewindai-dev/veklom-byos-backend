"""Redis-backed Circuit Breaker for local Ollama and Groq Fallback."""
import time
import logging
from backend.core.config.settings import settings
from backend.core.database.redis_client import redis_client

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, service_name: str = "ollama"):
        self.service_name = service_name
        self.state_key = f"circuit_breaker:{service_name}:state"
        self.failures_key = f"circuit_breaker:{service_name}:failures"
        self.cooldown_key = f"circuit_breaker:{service_name}:cooldown"

    async def get_state(self) -> str:
        """Retrieve current state from Redis, processing half-open transition if cooldown elapsed."""
        if not redis_client:
            # Fallback if Redis is down
            return "CLOSED"
            
        state = await redis_client.get(self.state_key) or "CLOSED"
        if state == "OPEN":
            # Check if cooldown has elapsed to transition to HALF_OPEN
            cooldown_expiry = await redis_client.get(self.cooldown_key)
            if cooldown_expiry:
                try:
                    if time.time() >= float(cooldown_expiry):
                        state = "HALF_OPEN"
                        await redis_client.set(self.state_key, "HALF_OPEN")
                except ValueError:
                    pass
            else:
                # If OPEN but no cooldown timestamp is set, default to HALF_OPEN immediately
                state = "HALF_OPEN"
                await redis_client.set(self.state_key, "HALF_OPEN")
                
        return state

    async def record_success(self):
        """Record a successful execution, resetting failures and closing circuit."""
        if not redis_client:
            return
        await redis_client.set(self.state_key, "CLOSED")
        await redis_client.set(self.failures_key, "0")
        await redis_client.delete(self.cooldown_key)

    async def record_failure(self):
        """Record a failure. If threshold exceeded, open circuit and set cooldown."""
        if not redis_client:
            return
            
        state = await redis_client.get(self.state_key) or "CLOSED"
        failures = int(await redis_client.get(self.failures_key) or "0") + 1
        await redis_client.set(self.failures_key, str(failures))

        threshold = int(getattr(settings, "CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3))
        cooldown_sec = int(getattr(settings, "CIRCUIT_BREAKER_COOLDOWN_SECONDS", 60))

        if state == "HALF_OPEN" or failures >= threshold:
            # Transition to OPEN
            await redis_client.set(self.state_key, "OPEN")
            expiry = time.time() + cooldown_sec
            await redis_client.set(self.cooldown_key, str(expiry))
            logger.warning(f"Circuit breaker for {self.service_name} opened. Cooldown set for {cooldown_sec}s.")
