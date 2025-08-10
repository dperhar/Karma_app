"""WebSocket service for real-time notifications using Centrifugo."""

import logging
import os
import json
import asyncio
from typing import Any, Dict

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class WebSocketService:
    """Service for managing WebSocket connections using Centrifugo."""

    def __init__(self):
        """Initialize the WebSocket service."""
        self.api_key = settings.CENTRIFUGO_API_KEY
        self.api_url = settings.CENTRIFUGO_API_URL.rstrip("/")  # e.g., http://centrifugo:8000/api
        self.publish_url = f"{self.api_url}/publish"

    def _publish_via_http_sync(self, channel: str, data: Dict[str, Any]) -> None:
        """Synchronous HTTP publish to Centrifugo to avoid event loop issues.

        Args:
            channel: Centrifugo channel, e.g., 'user:123'
            data: JSON-serializable payload
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"apikey {self.api_key}",
            }
            payload = {"channel": channel, "data": data}
            resp = requests.post(self.publish_url, headers=headers, data=json.dumps(payload), timeout=3)
            if resp.status_code != 200:
                logger.error("Centrifugo publish failed (%s): %s", resp.status_code, resp.text)
            else:
                logger.info("WS message sent to %s", channel)
        except Exception as e:
            logger.error("HTTP publish to %s failed: %s", channel, e, exc_info=True)

    async def send_user_notification(self, user_id: str, event: str, data: Dict[str, Any]) -> None:
        """Send a notification to a specific user through their private channel."""
        channel = f"user:{user_id}"
        payload = {"event": event, "data": data}
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._publish_via_http_sync, channel, payload)

    async def send_to_user(self, user_id: str, data: Dict[str, Any]) -> None:
        """Send raw payload to user's channel."""
        channel = f"user:{user_id}"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._publish_via_http_sync, channel, data) 