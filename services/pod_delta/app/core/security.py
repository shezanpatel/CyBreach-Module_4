"""JWT authentication reused by REST and WebSocket endpoints."""

from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.settings import settings

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedPrincipal:
    def __init__(
        self,
        subject: str,
        tenant_id: str,
        raw_claims: dict[str, Any],
    ) -> None:
        self.subject = subject
        self.tenant_id = tenant_id
        self.raw_claims = raw_claims


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        options: dict[str, Any] = {
            "verify_aud": bool(settings.JWT_AUDIENCE),
            "require_exp": True,
        }        
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            options=options,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def principal_from_claims(payload: dict[str, Any]) -> AuthenticatedPrincipal:
    subject = str(payload.get("sub") or payload.get("user_id") or "")
    tenant_id = str(
        payload.get("tenant_id")
        or payload.get("tid")
        or payload.get("org_id")
        or ""
    )
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing tenant_id",
        )
    return AuthenticatedPrincipal(
        subject=subject or tenant_id,
        tenant_id=tenant_id,
        raw_claims=payload,
    )


def get_current_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthenticatedPrincipal:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    return principal_from_claims(payload)


def decode_websocket_token(token: Optional[str]) -> AuthenticatedPrincipal:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing WebSocket token",
        )
    payload = decode_access_token(token)
    return principal_from_claims(payload)
