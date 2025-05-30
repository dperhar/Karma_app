from app.crud.base import CRUDBase
from app.models.channel import Channel
from app.schemas.channel import ChannelCreate, ChannelUpdate

class CRUDChannel(CRUDBase[Channel, ChannelCreate, ChannelUpdate]):
    pass

channel = CRUDChannel(Channel) 