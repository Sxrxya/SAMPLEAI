from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import require_roles
from app.models import CandidateProfile, User, utc_now
from app.schemas import CandidateProfileUpdate

router = APIRouter(prefix="/candidate/profile", tags=["candidate profile"])


@router.get("")
def get_candidate_profile(
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    profile = db.get(CandidateProfile, candidate.id)
    if profile is None:
        profile = CandidateProfile(user_id=candidate.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return {
        "user_id": candidate.id,
        "email": candidate.email,
        "display_name": candidate.display_name,
        "headline": profile.headline,
        "location": profile.location,
        "preferences": profile.preferences_json,
    }


@router.patch("")
def update_candidate_profile(
    payload: CandidateProfileUpdate,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    profile = db.get(CandidateProfile, candidate.id)
    if profile is None:
        profile = CandidateProfile(user_id=candidate.id)
        db.add(profile)
    changes = payload.model_dump(exclude_unset=True)
    if "headline" in changes:
        profile.headline = changes["headline"]
    if "location" in changes:
        profile.location = changes["location"]
    if "preferences" in changes:
        profile.preferences_json = changes["preferences"]
    profile.updated_at = utc_now()
    db.commit()
    return {
        "user_id": candidate.id,
        "email": candidate.email,
        "display_name": candidate.display_name,
        "headline": profile.headline,
        "location": profile.location,
        "preferences": profile.preferences_json,
    }
