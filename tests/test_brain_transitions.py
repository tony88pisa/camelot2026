# tests/test_brain_transitions.py
# 2026-04-03 01:50 - TDD State Machine
import pytest
from datetime import datetime, timezone

from ai_trader.brain.brain_types import BrainPhase, BrainEventType, BrainState, BrainContext
from ai_trader.brain.brain_transitions import transition
from ai_trader.brain.brain_errors import InvalidBrainTransitionError


@pytest.fixture
def base_ctx():
    return BrainContext(
        settings=None,
        exchange_adapter=None,
        strategy_engine=None,
        guardrail_engine=None,
        execution_preview_engine=None,
        memory_store=None,
        logger=None,
        event_logger=None,
        clock=None,
        now_fn=lambda: datetime.now(timezone.utc).isoformat()
    )


def test_transition_idle_to_observe(base_ctx):
    st = BrainState(BrainPhase.IDLE, "1", "", [], "")
    res = transition(st, BrainEventType.TICK, base_ctx)
    assert res.next_phase == BrainPhase.OBSERVE


def test_transition_observe_to_analyze_and_error(base_ctx):
    st = BrainState(BrainPhase.OBSERVE, "1", "", [], "")
    res1 = transition(st, BrainEventType.OBSERVATION_OK, base_ctx)
    assert res1.next_phase == BrainPhase.ANALYZE
    
    res2 = transition(st, BrainEventType.OBSERVATION_FAILED, base_ctx)
    assert res2.next_phase == BrainPhase.ERROR


def test_transition_analyze_to_propose(base_ctx):
    st = BrainState(BrainPhase.ANALYZE, "1", "", [], "")
    res = transition(st, BrainEventType.ANALYSIS_OK, base_ctx)
    assert res.next_phase == BrainPhase.PROPOSE


def test_propose_blocked_to_review(base_ctx):
    st = BrainState(BrainPhase.PROPOSE, "1", "", [], "")
    res = transition(st, BrainEventType.PROPOSAL_BLOCKED, base_ctx)
    assert res.next_phase == BrainPhase.REVIEW


def test_guardrail_check_to_execution(base_ctx):
    st = BrainState(BrainPhase.GUARDRAIL_CHECK, "1", "", [], "")
    res = transition(st, BrainEventType.PROPOSAL_READY, base_ctx)
    assert res.next_phase == BrainPhase.EXECUTION_PREVIEW


def test_review_and_learn_cycle(base_ctx):
    st1 = BrainState(BrainPhase.REVIEW, "1", "", [], "")
    res1 = transition(st1, BrainEventType.REVIEW_DONE, base_ctx)
    assert res1.next_phase == BrainPhase.LEARN
    
    st2 = BrainState(BrainPhase.LEARN, "1", "", [], "")
    res2 = transition(st2, BrainEventType.LEARN_DONE, base_ctx)
    assert res2.next_phase == BrainPhase.SLEEP


def test_invalid_transition_throws(base_ctx):
    st = BrainState(BrainPhase.IDLE, "1", "", [], "")
    with pytest.raises(InvalidBrainTransitionError):
        # Un evento invalid rispetto alla fase
        transition(st, BrainEventType.LEARN_DONE, base_ctx)
