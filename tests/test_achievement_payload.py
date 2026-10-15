import pytest
from pydantic import ValidationError

from app.main import AchievementCheckPayload


@pytest.mark.parametrize(
    "evidence_ref",
    [
        "mod2:rule123:tenant_001:run001",
        "mod2:verdict:outcome001",
        "mod3:streak:tenant_001:milestone001",
    ],
)
def test_valid_evidence_ref_formats(evidence_ref):
    payload = AchievementCheckPayload(
        type="streak",
        key="badge_7_day_streak",
        tenant_id="tenant_001",
        evidence_ref=evidence_ref,
    )

    assert payload.evidence_ref == evidence_ref


@pytest.mark.parametrize(
    "evidence_ref",
    [
        "random-value",
        "mod2:",
        "mod2:rule123",
        "mod3:streak",
        "mod4:test:tenant:run",
    ],
)
def test_invalid_evidence_ref_formats(evidence_ref):
    with pytest.raises(ValidationError):
        AchievementCheckPayload(
            type="streak",
            key="badge_7_day_streak",
            tenant_id="tenant_001",
            evidence_ref=evidence_ref,
        )


def test_evidence_ref_can_be_none():
    payload = AchievementCheckPayload(
        type="streak",
        key="badge_7_day_streak",
        tenant_id="tenant_001",
    )

    assert payload.evidence_ref is None