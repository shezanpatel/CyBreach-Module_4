from dataclasses import dataclass
from secrets import compare_digest
from typing import Any

import jwt
from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.config import settings


bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="JWT Bearer access token",
)


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject: str
    tenant_id: str
    role: str | None
    claims: dict[str, Any]


def decode_access_token(token: str) -> AuthenticatedPrincipal:
    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "require": ["sub", "tenant_id", "exp"],
            },
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = claims.get("sub")
    tenant_id = claims.get("tenant_id")

    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token subject is invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token tenant is invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = claims.get("role")

    if role is not None and not isinstance(role, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token role is invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedPrincipal(
        subject=subject.strip(),
        tenant_id=tenant_id.strip(),
        role=role.strip().lower() if role else None,
        claims=claims,
    )


def _principal_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
) -> AuthenticatedPrincipal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer access token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer access token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_access_token(token)


def authenticate_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(
        bearer_scheme,
    ),
) -> AuthenticatedPrincipal:
    principal = getattr(request.state, "principal", None)

    if principal is not None:
        return principal

    principal = _principal_from_credentials(credentials)
    request.state.principal = principal

    return principal


def authenticate_middleware_request(
    request: Request,
) -> AuthenticatedPrincipal:
    authorization = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, separator, token = authorization.partition(" ")

    if (
        not separator
        or scheme.lower() != "bearer"
        or not token.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer access token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    principal = decode_access_token(token.strip())
    request.state.principal = principal

    return principal


def get_authenticated_principal(
    request: Request,
) -> AuthenticatedPrincipal:
    principal = getattr(request.state, "principal", None)

    if principal is None:
        principal = authenticate_middleware_request(request)

    return principal


def authorize_tenant(
    request: Request,
    requested_tenant_id: str,
) -> AuthenticatedPrincipal:
    principal = get_authenticated_principal(request)

    if principal.role == "admin":
        return principal

    if principal.tenant_id != requested_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access is forbidden",
        )

    return principal


def require_admin(
    request: Request,
) -> AuthenticatedPrincipal:
    principal = get_authenticated_principal(request)

    if principal.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role is required",
        )

    return principal


def verify_service_api_key(request: Request) -> None:
    supplied_key = request.headers.get("X-Service-API-Key")

    if not supplied_key or not compare_digest(
        supplied_key,
        settings.SERVICE_API_KEY,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid service API key is required",
        )
