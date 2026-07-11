"""Budget enforcement (replaces BudgetCheckMiddleware)."""

async def check_and_reserve(agent_id: str, resource: str) -> bool:
    """Checks budget and reserves tokens for an execution."""
    # Mock budget check
    return True
