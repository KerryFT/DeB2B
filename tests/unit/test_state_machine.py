import pytest

from backend.domain.state_machine import CaseStatus, IllegalTransition, ensure_transition


def test_allowed_transition() -> None:
    ensure_transition(CaseStatus.IMPORTED, CaseStatus.COLLECTING_DOCUMENTS)


def test_terminal_and_skipped_transition_rejected() -> None:
    with pytest.raises(IllegalTransition):
        ensure_transition(CaseStatus.IMPORTED, CaseStatus.PAID)
    with pytest.raises(IllegalTransition):
        ensure_transition(CaseStatus.PAID, CaseStatus.IMPORTED)
