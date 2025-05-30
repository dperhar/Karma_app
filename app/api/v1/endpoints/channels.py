from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()

@router.post("/", response_model=schemas.Channel)
def create_channel(
    *,
    db: Session = Depends(deps.get_db),
    channel_in: schemas.ChannelCreate,
) -> Any:
    """
    Create new channel.
    """
    channel = crud.channel.create(db=db, obj_in=channel_in)
    return channel

@router.get("/", response_model=List[schemas.Channel])
def read_channels(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve channels.
    """
    channels = crud.channel.get_multi(db, skip=skip, limit=limit)
    return channels

@router.get("/{channel_id}", response_model=schemas.Channel)
def read_channel_by_id(
    channel_id: int,
    db: Session = Depends(deps.get_db),
) -> Any:
    channel = crud.channel.get(db, id=channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel 