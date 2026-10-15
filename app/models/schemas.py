"""Pydantic request and response schemas for the leaderboard API."""

from pydantic import BaseModel, Field, field_validator


class ScoreRequest(BaseModel):
    """Request to set a user's leaderboard score."""

    username: str = Field(..., min_length=1, max_length=100)
    score: float = Field(..., ge=0)

    tenant_id: str | None = Field(
        default=None,
        examples=["CORP-001"],
    )
    industry: str | None = Field(
        default=None,
        examples=["technology"],
    )
    region: str | None = Field(
        default=None,
        examples=["apac"],
    )
    size: str | None = Field(
        default=None,
        examples=["51-500"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """Strip whitespace and reject an empty username."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Username cannot be empty or whitespace")
        return cleaned


class IncrementRequest(BaseModel):
    """Request body for atomically incrementing a player score."""

    username: str = Field(..., min_length=1, max_length=128, examples=["player_one"])
    increment: float = Field(..., gt=0, examples=[10.0])

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Username cannot be empty or whitespace")
        return cleaned


class PlayerEntry(BaseModel):
    rank: int = Field(..., ge=1)
    username: str
    score: float


class ScoreResponse(BaseModel):
    success: bool = True
    username: str
    score: float
    message: str = "Score updated successfully"


class IncrementResponse(BaseModel):
    success: bool = True
    username: str
    score: float
    increment: float
    message: str = "Score incremented successfully"


class LeaderboardResponse(BaseModel):
    success: bool = True
    dimension: str = "global"
    view: str = "absolute"
    total_players: int
    limit: int
    entries: list[PlayerEntry]


class RankResponse(BaseModel):
    success: bool = True
    username: str
    score: float
    rank: int = Field(..., ge=1)


class DeleteUserResponse(BaseModel):
    success: bool = True
    username: str
    message: str = "User removed from leaderboard"


class ResetLeaderboardResponse(BaseModel):
    success: bool = True
    message: str = "Leaderboard cleared successfully"


class HealthResponse(BaseModel):
    status: str
    redis: str
    app: str


class MetricsResponse(BaseModel):
    success: bool = True
    metrics: dict[str, str | int | float]


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: str | None = None


class TenantContext(BaseModel):
    """Tenant metadata required for the new leaderboard lifecycle."""

    tenant_id: str = Field(..., examples=["CORP-001"])
    industry: str = Field(..., examples=["technology"])
    region: str = Field(..., examples=["apac"])
    size: str = Field(..., examples=["51-500"])


class OptInRequest(TenantContext):
    """Request to opt a tenant into leaderboard participation."""
    pass


class OptOutRequest(BaseModel):
    """Request to opt a tenant out of leaderboard participation."""

    tenant_id: str = Field(..., examples=["CORP-001"])


class ConsentResponse(BaseModel):
    success: bool = True
    tenant_id: str
    action: str
    message: str


class ImprovementEntry(BaseModel):
    rank: int = Field(..., ge=1)
    tenant_id: str
    delta_score: float


class ImprovementResponse(BaseModel):
    success: bool = True
    total_tenants: int
    limit: int
    entries: list[ImprovementEntry]
