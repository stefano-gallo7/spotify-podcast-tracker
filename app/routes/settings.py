from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.db_models import AppState
from app.schemas import Settings, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_state(session: Session) -> AppState:
    state = session.query(AppState).first()
    if state is None:
        raise HTTPException(
            status_code=500,
            detail="AppState not initialized; run `python -m scripts.init_db`.",
        )
    return state


@router.get("", response_model=Settings)
def get_settings(session: Session = Depends(get_session)):
    return _get_state(session)


@router.patch("", response_model=Settings)
def update_settings(update: SettingsUpdate, session: Session = Depends(get_session)):
    state = _get_state(session)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(state, field, value)
    session.commit()
    session.refresh(state)
    return state
