"""Shared envelope for all Pod Delta Kafka events."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventEnvelope(BaseModel):
    """Versioned envelope present on every event."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    event_id: str = Field(..., min_length=1, max_length=128)
    event_version: str = Field(default="1.0", pattern=r"^\d+\.\d+$")
    event_type: str = Field(..., min_length=1, max_length=128)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    correlation_id: str = Field(..., min_length=1, max_length=128)
    occurred_at: datetime
    source: str = Field(default="unknown", min_length=1, max_length=128)

    @field_validator("occurred_at")
    @classmethod
    def ensure_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def tenant_scope(self) -> str:
        return self.tenant_id


class StrictPublishedEvent(BaseModel):
    """Published events reject unknown fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_version: str = Field(default="1.0", pattern=r"^\d+\.\d+$")
    event_type: str
    tenant_id: str = Field(..., min_length=1, max_length=128)
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = Field(default_factory=utc_now)
    source: str = Field(default="pod-delta")


def dump_event(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
