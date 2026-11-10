from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models import AuthSession, User, utc_now

password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def create_access_token(db: Session, user: User) -> tuple[str, datetime]:
    settings = get_settings()
    settings.validate_auth_secret()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_ttl_minutes)
    session_id = str(uuid4())
    token = jwt.encode(
        {"sub": user.id, "role": user.role, "jti": session_id, "exp": expires_at},
        settings.access_token_secret.get_secret_value(),
        algorithm="HS256",
    )
    db.add(AuthSession(id=session_id, user_id=user.id, expires_at=expires_at))
    db.commit()
    return token, expires_at


def get_authenticated_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> tuple[User, AuthSession]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    settings = get_settings()
    settings.validate_auth_secret()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.access_token_secret.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "jti"]},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    auth_session = db.scalar(
        select(AuthSession).where(
            AuthSession.id == payload["jti"],
            AuthSession.user_id == payload["sub"],
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utc_now(),
        )
    )
    user = db.scalar(select(User).where(User.id == payload["sub"], User.is_active.is_(True)))
    if user is None or auth_session is None:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    return user, auth_session


def get_current_user(
    principal: tuple[User, AuthSession] = Depends(get_authenticated_principal),
) -> User:
    return principal[0]


def require_roles(*roles: str):
    def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return role_dependency
