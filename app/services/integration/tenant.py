from __future__ import annotations

import zlib
from typing import Optional


def tenant_to_user_id(tenant_id: str, explicit: Optional[int] = None) -> int:
    if explicit is not None and explicit > 0:
        return explicit
    if tenant_id.isdigit():
        value = int(tenant_id)
        return value if value > 0 else 1
    return (zlib.crc32(tenant_id.encode("utf-8")) % 2_000_000_000) + 1
