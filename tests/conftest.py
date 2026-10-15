from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.core.config import settings


ORIGINAL_TESTCLIENT_INIT = TestClient.__init__


def create_test_access_token(
    tenant_id: str = "pytest-admin-tenant",
    role: str = "admin",
    subject: str = "pytest-admin-user",
) -> str:
    now = datetime.now(timezone.utc)

    return jwt.encode(
        {
            "sub": subject,
            "tenant_id": tenant_id,
            "role": role,
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _secured_testclient_init(
    self,
    *args,
    **kwargs,
):
    token = create_test_access_token()

    supplied_headers = kwargs.get("headers") or {}

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Service-API-Key": settings.SERVICE_API_KEY,
    }

    headers.update(supplied_headers)
    kwargs["headers"] = headers

    ORIGINAL_TESTCLIENT_INIT(
        self,
        *args,
        **kwargs,
    )


TestClient.__init__ = _secured_testclient_init
