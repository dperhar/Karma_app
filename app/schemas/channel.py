from typing import Optional
from pydantic import BaseModel

# Shared properties
class ChannelBase(BaseModel):
    telegram_channel_id: str
    name: Optional[str] = None

# Properties to receive on channel creation
class ChannelCreate(ChannelBase):
    pass

# Properties to receive on channel update
class ChannelUpdate(ChannelBase):
    pass

# Properties shared by models stored in DB
class ChannelInDBBase(ChannelBase):
    id: int
    from_attributes: bool = True  # Pydantic V2 orm_mode

# Properties to return to client
class Channel(ChannelInDBBase):
    pass 