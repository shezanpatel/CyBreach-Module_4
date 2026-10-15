from datetime import datetime
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str
    current_streak: int = Field(default=0, ge=0)
    last_completion_time: datetime | None = None
    verified_activity_time: datetime | None = None
    badges: list[str] = Field(default_factory=list)

class PlayerEntry(BaseModel):
    rank: int = Field(..., ge=1)
    username: str
    score: float


class LeaderboardResponse(BaseModel):
    dimension: str
    view: str = "absolute"
    total: int
    entries: list[PlayerEntry]


class PlayerEntry(BaseModel):
    rank: int = Field(..., ge=1)
    username: str
    score: float


class LeaderboardResponse(BaseModel):
    dimension: str
    view: str = "absolute"
    total: int
    entries: list[PlayerEntry]


class PlayerEntry(BaseModel):
    rank: int = Field(..., ge=1)
    username: str
    score: float


class LeaderboardResponse(BaseModel):
    dimension: str
    view: str = "absolute"
    total: int
    entries: list[PlayerEntry]

from app.models.schemas import *
