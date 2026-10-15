"""Tenant data-contract validation and Redis key helpers."""

from __future__ import annotations

import re

TENANT_ID_REGEX = re.compile(r"^CORP-0(?:0[1-9]|[1-4][0-9]|50)$")

VALID_INDUSTRIES = {
    "finance",
    "healthcare",
    "technology",
    "manufacturing",
    "retail",
}

VALID_REGIONS = {
    "north_america",
    "europe",
    "apac",
    "latam",
}

VALID_SIZES = {
    "1-50",
    "51-500",
    "501-5000",
    "5000+",
}


def validate_tenant_id(tenant_id: str) -> str:
    tenant_id = tenant_id.strip().upper()

    if not TENANT_ID_REGEX.fullmatch(tenant_id):
        raise ValueError("tenant_id must be between CORP-001 and CORP-050")

    return tenant_id


def validate_industry(industry: str) -> str:
    value = industry.strip().lower()

    if value not in VALID_INDUSTRIES:
        raise ValueError(
            f"industry must be one of: {', '.join(sorted(VALID_INDUSTRIES))}"
        )

    return value


def validate_region(region: str) -> str:
    value = region.strip().lower()

    if value not in VALID_REGIONS:
        raise ValueError(
            f"region must be one of: {', '.join(sorted(VALID_REGIONS))}"
        )

    return value


def validate_size(size: str) -> str:
    value = size.strip()

    if value not in VALID_SIZES:
        raise ValueError(
            f"size must be one of: {', '.join(sorted(VALID_SIZES))}"
        )

    return value


def global_key() -> str:
    return "lb:global:absolute"


def industry_key(industry: str) -> str:
    return f"lb:industry:{validate_industry(industry)}:absolute"


def region_key(region: str) -> str:
    return f"lb:region:{validate_region(region)}:absolute"


def size_key(size: str) -> str:
    return f"lb:size:{validate_size(size)}:absolute"


def improvement_global_key() -> str:
    return "lb:global:improvement"


def improvement_industry_key(industry: str) -> str:
    return f"lb:industry:{validate_industry(industry)}:improvement"


def improvement_region_key(region: str) -> str:
    return f"lb:region:{validate_region(region)}:improvement"


def improvement_size_key(size: str) -> str:
    return f"lb:size:{validate_size(size)}:improvement"


def tenant_members_key(tenant_id: str) -> str:
    return f"lb:tenant:{validate_tenant_id(tenant_id)}:members"