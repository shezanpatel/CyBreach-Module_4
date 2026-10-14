import json
from datetime import datetime, timezone
from jsonschema import validate
from app.engagement.state_machine import EngagementStateMachine, EngagementState
from app.engagement.models import Engagement, LaunchTier


def test_pod_beta_state_machine():
    now = datetime.now(timezone.utc)
    engagement = Engagement(
        engagement_id="test-engagement",
        tenant_id="test-tenant",
        engagement_type=LaunchTier.QUICK_SCAN,
        created_at=now,
        updated_at=now,
    )

    transitioned = EngagementStateMachine.transition_to_scoped(engagement)

    assert transitioned.state == EngagementState.SCOPED


def test_pod_beta_contracts():
    with open("contracts/campaign_schema.json", "r") as f:
        schema = json.load(f)
    with open("fixtures/campaigns/quick_scan_perimeter.json", "r") as f:
        data = json.load(f)
    validate(instance=data, schema=schema)