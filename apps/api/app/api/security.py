import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class RequestContext:
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    permissions: frozenset[str]

    def require(self, permission: str) -> None:
        if "*" in self.permissions or permission in self.permissions:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"missing permission: {permission}",
        )


def get_request_context(
    tenant_id: Annotated[
        uuid.UUID | None,
        Header(alias="X-ServiceMind-Tenant-Id"),
    ] = None,
    user_id: Annotated[
        uuid.UUID | None,
        Header(alias="X-ServiceMind-User-Id"),
    ] = None,
    permissions_header: Annotated[
        str | None,
        Header(alias="X-ServiceMind-Permissions"),
    ] = None,
) -> RequestContext:
    if tenant_id is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing request context",
        )
    permissions = frozenset(
        permission.strip()
        for permission in (permissions_header or "").split(",")
        if permission.strip()
    )
    return RequestContext(tenant_id=tenant_id, user_id=user_id, permissions=permissions)
