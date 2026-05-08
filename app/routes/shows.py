from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.db_models import Show
from app.schemas import ShowSummary

router = APIRouter(prefix="/api/shows", tags=["shows"])


@router.get("", response_model=list[ShowSummary])
def list_shows(session: Session = Depends(get_session)):
    return session.query(Show).order_by(Show.name).all()
