"""WebSocket service for real-time notifications using Centrifugo."""

import logging
from typing import Any, Dict

from cent import AsyncClient, PublishRequest

from config import CENTRIFUGO_API_KEY, CENTRIFUGO_API_URL

logger = logging.getLogger(__name__)


class WebSocketService:
    """Service for managing WebSocket connections using Centrifugo."""

    def __init__(self):
        """Initialize the WebSocket service."""
        self.api_key = CENTRIFUGO_API_KEY
        self.api_url = CENTRIFUGO_API_URL
        self._client = None

    @property
    async def client(self) -> AsyncClient:
        """Get or create the async client."""
        if self._client is None:
            self._client = AsyncClient(self.api_url, self.api_key)
        return self._client

    async def send_user_notification(
        self, user_id: str, event: str, data: Dict[str, Any]
    ) -> None:
        """
        Send a notification to a specific user through their private channel

        Args:
            user_id: The ID of the user to send the notification to
            event: The type of event/notification
            data: The data to send in the notification
        """
        channel = f"user:{user_id}"
        payload = {"event": event, "data": data}

        try:
            logger.info(f"Sending notification to channel {channel} with data: {data}")
            client = await self.client
            request = PublishRequest(channel=channel, data=payload)
            result = await client.publish(request)
            logger.info(
                f"Successfully sent notification to channel {channel} with result: {result}"
            )
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            raise
