"""Prints every token needed for the Integration + Security tests.
Run:  python make_test_tokens.py
Then copy each line into the top of the SECURITY section in api_requests.http.
"""
from datetime import datetime, timedelta, timezone
from jose import jwt

SECRET_KEY = "change-me-in-production"   # must match SECRET_KEY in .env
now = datetime.now(timezone.utc)


def make(payload, key=SECRET_KEY):
    return jwt.encode(payload, key, algorithm="HS256")


tokens = {
    # normal token for tenant_123
    "tok_valid": make({"sub": "1", "tenant_id": "tenant_123",
                       "exp": now + timedelta(hours=24)}),
    # signed with the wrong secret
    "tok_wrong_secret": make({"sub": "1", "tenant_id": "tenant_123",
                              "exp": now + timedelta(hours=24)}, key="wrong-key"),
    # expired an hour ago
    "tok_expired": make({"sub": "1", "tenant_id": "tenant_123",
                         "exp": now - timedelta(hours=1)}),
    # valid, but for a different tenant
    "tok_other_tenant": make({"sub": "2", "tenant_id": "tenant_999",
                              "exp": now + timedelta(hours=24)}),
    # no "exp" claim at all
    "tok_no_exp": make({"sub": "1", "tenant_id": "tenant_123"}),
    # no tenant_id; sub happens to look like a tenant name
    "tok_no_tenant": make({"sub": "tenant_123",
                           "exp": now + timedelta(hours=24)}),
}

for name, value in tokens.items():
    print(f"@{name} = {value}")
