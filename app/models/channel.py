from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class Channel(Base):
    id = Column(Integer, primary_key=True, index=True)
    telegram_channel_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=True) 