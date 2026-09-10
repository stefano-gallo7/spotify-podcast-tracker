from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_session
from app.db_models import Tag, show_tags
from app.schemas import TagWithCount

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagWithCount])
def list_tags(session: Session = Depends(get_session)):
    rows = (
        session.query(Tag.name, func.count(show_tags.c.show_id))
        .outerjoin(show_tags, show_tags.c.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(Tag.name)
        .all()
    )
    return [TagWithCount(name=n, show_count=c) for n, c in rows]
