from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import (
    create_access_token,
    get_authenticated_principal,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models import (
    AuditEvent,
    CandidateProfile,
    Organization,
    OrganizationMembership,
    User,
)
from app.schemas import LoginRequest, RecruiterCreate, TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


def _issue_token(db: Session, user: User) -> TokenResponse:
    try:
        token, expires_at = create_access_token(db, user)
    except ValueError as exc:
        raise HTTPException(
            status_code=503, detail="Authentication signing key is not configured"
        ) from exc
    return TokenResponse(
        access_token=token,
        expires_at=expires_at,
        user=UserResponse(
            id=user.id, email=user.email, display_name=user.display_name, role=user.role
        ),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_candidate(payload: UserCreate, db: Session = Depends(get_db)) -> TokenResponse:
    user = User(
        email=str(payload.email).lower(),
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role="candidate",
    )
    db.add(user)
    try:
        db.flush()
        db.add(CandidateProfile(user_id=user.id))
        db.add(
            AuditEvent(
                actor_id=user.id,
                action="account.registered",
                entity_type="user",
                entity_id=user.id,
            )
        )
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with that email already exists"
        ) from exc
    return _issue_token(db, user)


@router.post("/register/recruiter", response_model=TokenResponse, status_code=201)
def register_recruiter(payload: RecruiterCreate, db: Session = Depends(get_db)) -> TokenResponse:
    user = User(
        email=str(payload.email).lower(),
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role="recruiter",
    )
    organization = Organization(name=payload.organization_name.strip())
    db.add_all([user, organization])
    try:
        db.flush()
        db.add(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=user.id,
                role="owner",
            )
        )
        db.add(
            AuditEvent(
                actor_id=user.id,
                action="recruiter.registered",
                entity_type="organization",
                entity_id=organization.id,
            )
        )
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with that email already exists"
        ) from exc
    return _issue_token(db, user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _issue_token(db, user)


@router.get("/session", response_model=UserResponse)
def current_session(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=user.id, email=user.email, display_name=user.display_name, role=user.role
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    principal: tuple[User, object] = Depends(get_authenticated_principal),
    db: Session = Depends(get_db),
) -> Response:
    _, auth_session = principal
    auth_session.revoked_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
