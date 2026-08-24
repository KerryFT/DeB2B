from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient
from sqlalchemy import select

from backend.infrastructure.config import get_settings
from backend.infrastructure.database import SessionFactory
from backend.infrastructure.models import Membership, User


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: UUID
    tenant_id: UUID
    role: str


async def current_actor(
    authorization: Annotated[str | None, Header()] = None,
    x_dev_user_id: Annotated[str | None, Header()] = None,
    x_dev_tenant_id: Annotated[str | None, Header()] = None,
    x_dev_role: Annotated[str, Header()] = "operator",
) -> Actor:
    settings = get_settings()
    if settings.dev_auth_enabled and x_dev_user_id and x_dev_tenant_id:
        if x_dev_role not in {"viewer", "operator", "approver", "admin"}:
            raise HTTPException(403, "invalid role")
        return Actor(UUID(x_dev_user_id), UUID(x_dev_tenant_id), x_dev_role)
    if not authorization:
        raise HTTPException(401, "missing bearer token")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "invalid authorization scheme")
    if not settings.oidc_jwks_uri:
        raise HTTPException(503, "OIDC JWKS is not configured")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        signing_key = PyJWKClient(settings.oidc_jwks_uri).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iat", "iss", "sub", "aud", "tenant_id"]},
        )
        tenant_id = UUID(claims["tenant_id"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(401, "invalid bearer token") from exc

    with SessionFactory() as session:
        membership = session.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(
                User.issuer == claims["iss"],
                User.subject == claims["sub"],
                Membership.tenant_id == tenant_id,
            )
        ).first()
    if not membership:
        raise HTTPException(403, "user is not a member of this tenant")
    member, user = membership
    return Actor(user.id, tenant_id, member.role)


def require_roles(*roles: str):  # type: ignore[no-untyped-def]
    async def dependency(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
        if actor.role not in roles:
            raise HTTPException(403, "insufficient role")
        return actor

    return dependency
