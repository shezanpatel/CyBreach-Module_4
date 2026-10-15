from datetime import datetime
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str
    tenant_id: str ="default"
    current_streak: int = Field(default=0, ge=0)
    last_completion_time: datetime | None = None
    verified_activity_time: datetime | None = None
    badges: list[str] = Field(default_factory=list)