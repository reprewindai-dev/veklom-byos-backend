from backend.services.orchestrator import StateTransitionManager
from backend.db.models.run import VeklomRunStatus

def test_can_transition_valid():
    # INTENT_CAPTURED -> COMPILED is valid
    assert StateTransitionManager.can_transition(
        VeklomRunStatus.INTENT_CAPTURED,
        VeklomRunStatus.COMPILED
    ) is True

def test_can_transition_invalid():
    # INTENT_CAPTURED -> SEALED is invalid
    assert StateTransitionManager.can_transition(
        VeklomRunStatus.INTENT_CAPTURED,
        VeklomRunStatus.SEALED
    ) is False

def test_can_transition_from_terminal_state():
    # ROLLED_BACK has no allowed transitions
    assert StateTransitionManager.can_transition(
        VeklomRunStatus.ROLLED_BACK,
        VeklomRunStatus.INTENT_CAPTURED
    ) is False

def test_all_transitions_exhaustive():
    # Test all possible combinations
    for current_state in VeklomRunStatus:
        allowed_transitions = StateTransitionManager.VALID_TRANSITIONS.get(current_state, set())
        for new_state in VeklomRunStatus:
            is_valid = new_state in allowed_transitions
            assert StateTransitionManager.can_transition(current_state, new_state) == is_valid
