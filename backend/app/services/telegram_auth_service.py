"""Service for Telegram Messenger authentication operations."""

import asyncio
import base64
import logging
from typing import Any, Optional

from telethon import TelegramClient, functions, types
from telethon.errors import (
    PasswordHashInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from app.core.config import settings
from app.services.base_service import BaseService
from app.services.redis_service import RedisService as RedisDataService
from app.services.user_service import UserService
# from app.services.telethon_client import TelethonClient as TelethonClientService

logger = logging.getLogger(__name__)


class TelegramMessengerAuthService(BaseService):
    """Service class for Telegram Messenger authentication."""

    def __init__(
        self,
        user_service: UserService,
        # telethon_client: TelethonClientService,
        redis_service: RedisDataService,
    ):
        """Initialize the service with required dependencies."""
        super().__init__()
        self.user_service = user_service
        # self.telethon_client = telethon_client
        self.redis_service = redis_service
        self.session_prefix = "tg_auth:"
        self._cleanup_tasks: set[asyncio.Task] = set()

    async def _cleanup_client(self, key: str):
        """Clean up client session after timeout or completion.

        Args:
            key: Phone number or token used as storage key
        """
        try:
            try:
                session_data = self.redis_service.get_session(f"{self.session_prefix}{key}")
            except Exception:
                # Fallback to memory storage
                if hasattr(self, '_memory_sessions'):
                    session_data = self._memory_sessions.get(f"{self.session_prefix}{key}")
                else:
                    session_data = None
                    
            if session_data and "session_string" in session_data:
                # No need to disconnect as we don't store the client anymore
                pass
        except Exception as e:
            logger.error(f"Error during cleanup for {key}: {e}")
        finally:
            try:
                self.redis_service.delete_session(f"{self.session_prefix}{key}")
            except Exception:
                # Fallback to memory storage
                if hasattr(self, '_memory_sessions'):
                    self._memory_sessions.pop(f"{self.session_prefix}{key}", None)

    async def _delayed_cleanup(self, key: str, delay: int = 300):
        """Cleanup client after delay.

        Args:
            key: Client storage key
            delay: Delay in seconds before cleanup
        """
        await asyncio.sleep(delay)
        await self._cleanup_client(key)

    def _create_cleanup_task(self, key: str, delay: int = 300):
        """Create and store a cleanup task.

        Args:
            key: Client storage key
            delay: Delay in seconds before cleanup
        """
        task = asyncio.create_task(self._delayed_cleanup(key, delay))
        self._cleanup_tasks.add(task)
        task.add_done_callback(self._cleanup_tasks.discard)

    async def _save_client_session(
        self, key: str, data: dict[str, Any], expire: int = 300
    ):
        """Save client session data to Redis.

        Args:
            key: Session key
            data: Session data
            expire: Expiration time in seconds
        """
        # Extract session string from client if it exists
        if "client" in data and isinstance(data["client"], TelegramClient):
            data["session_string"] = data["client"].session.save()
            # Don't store the client object
            data.pop("client", None)

        try:
            self.redis_service.save_session(
                f"{self.session_prefix}{key}",
                data,
                expire=expire,
            )
        except Exception as e:
            logger.warning(f"Redis not available, storing session in memory: {e}")
            # For development, we can store in a simple dict
            if not hasattr(self, '_memory_sessions'):
                self._memory_sessions = {}
            self._memory_sessions[f"{self.session_prefix}{key}"] = data

    async def _get_client_session(self, key: str) -> Optional[dict[str, Any]]:
        """Get client session data from Redis.

        Args:
            key: Session key

        Returns:
            Optional[Dict[str, Any]]: Session data if exists
        """
        try:
            session_data = self.redis_service.get_session(f"{self.session_prefix}{key}")
        except Exception as e:
            logger.warning(f"Redis not available, using memory session: {e}")
            # Fallback to memory storage
            if hasattr(self, '_memory_sessions'):
                session_data = self._memory_sessions.get(f"{self.session_prefix}{key}")
            else:
                session_data = None
                
        if session_data and "session_string" in session_data:
            # Create a new client instance from the stored session string
            client = TelegramClient(
                StringSession(session_data["session_string"]),
                int(settings.TELETHON_API_ID),
                settings.TELETHON_API_HASH,
                device_model="Karma Comments App",
                system_version="9.31.19-tl-e-CUSTOM",
                app_version="1.12.3",
                lang_code="en",
                system_lang_code="en",
            )
            await client.connect()
            session_data["client"] = client
        return session_data

    async def generate_qr_code(self) -> dict[str, str]:
        """Generate QR code for login.

        Returns:
            Token for checking login status
        """
        # Check if API credentials are configured
        if not settings.TELETHON_API_ID or not settings.TELETHON_API_HASH:
            logger.error("Telethon API credentials not configured")
            raise Exception("Telethon API credentials not configured. Please set TELETHON_API_ID and TELETHON_API_HASH in environment variables.")
        
        try:
            logger.info(f"Generating QR code with API_ID: {settings.TELETHON_API_ID}")
            
            client = TelegramClient(
                StringSession(),
                int(settings.TELETHON_API_ID),
                settings.TELETHON_API_HASH,
                device_model="Karma Comments App",
                system_version="9.31.19-tl-e-CUSTOM",
                app_version="1.12.3",
                lang_code="en",
                system_lang_code="en",
            )
            await client.connect()

            # Get QR code data
            qr_login = await client(
                functions.auth.ExportLoginTokenRequest(
                    api_id=int(settings.TELETHON_API_ID),
                    api_hash=settings.TELETHON_API_HASH,
                    except_ids=[],
                )
            )

            # Create token
            token = base64.b64encode(qr_login.token).decode("utf-8")
            logger.info(f"QR token generated successfully for session")

            # Store session data in Redis with enhanced metadata
            session_metadata = {
                "session_string": client.session.save(),
                "created_at": asyncio.get_event_loop().time(),
                "token": token,
                "ip_address": "unknown",  # Should be passed from request context
                "user_agent": "unknown",  # Should be passed from request context
            }

            await self._save_client_session(token, session_metadata)

            # Set 5-minute timeout
            self._create_cleanup_task(token)

            return {
                "token": token,
            }

        except Exception as err:
            logger.error(f"Error generating QR code: {err}", exc_info=True)
            raise Exception(f"Error generating QR code: {str(err)}") from err

    async def check_qr_login(self, token: str, current_user_id: Optional[str]) -> dict[str, Any]:
        """Check if QR code login was successful.

        Args:
            token: QR code token
            current_user_id: ID of the current user (optional)

        Returns:
            Session response with auth data if successful
        """
        try:
            # Validate token format
            if not token or len(token) < 10:
                raise ValueError("Invalid token format")
            
            # Validate base64 format
            try:
                base64.b64decode(token)
            except Exception:
                raise ValueError("Invalid token encoding")

            session_data = await self._get_client_session(token)
            if not session_data:
                logger.warning(f"Session expired or not found for token")
                raise ValueError("Session expired")

            # Check if session is too old (additional safety check)
            created_at = session_data.get("created_at", 0)
            current_time = asyncio.get_event_loop().time()
            if current_time - created_at > 300:  # 5 minutes
                logger.warning(f"Session too old, rejecting")
                await self._cleanup_client(token)
                raise ValueError("Session expired")

            client = session_data["client"]

            try:
                result = await client(
                    functions.auth.ExportLoginTokenRequest(
                        api_id=int(settings.TELETHON_API_ID),
                        api_hash=settings.TELETHON_API_HASH,
                        except_ids=[],
                    )
                )

                if isinstance(result, types.auth.LoginTokenSuccess):
                    try:
                        me = await client.get_me()
                        session_string = client.session.save()

                        logger.info(f"Successful QR login for Telegram user: {me.id}")
                        await self._cleanup_client(token)

                        # Update user session and data if current_user_id is provided
                        if current_user_id:
                            await self.user_service.update_user_tg_session(
                                current_user_id, session_string # current_user_id is db_id
                            )
                            
                            # Update user data from Telegram (handle errors gracefully)
                            try:
                                await self.user_service.update_user_from_telegram(
                                    current_user_id, me
                                )
                            except Exception as e:
                                logger.warning(f"Failed to update user data from Telegram: {e}")
                                # Continue with the flow even if user update fails
                            
                            # Pass db_user_id back for session creation
                            return {"requires_2fa": False, "user_id": me.id, "status": "success", "db_user_id": current_user_id}

                        return {
                            "requires_2fa": False,
                            "user_id": me.id,
                            "status": "success",
                        }
                    except SessionPasswordNeededError:
                        logger.info(f"2FA required for QR login")
                        return {
                            "requires_2fa": True,
                            "user_id": None,
                            "status": "2fa_required",
                        }
                else:
                    return {"requires_2fa": None, "user_id": None, "status": "waiting"}

            except SessionPasswordNeededError:
                logger.info(f"2FA required for QR login")
                return {"requires_2fa": True, "user_id": None, "status": "2fa_required"}
            except Exception as err:
                logger.error(f"Error checking QR login: {err}")
                await self._cleanup_client(token)
                raise ValueError(str(err)) from err

        except ValueError:
            # Re-raise ValueError with original message
            raise
        except Exception as err:
            logger.error(f"Error in QR login check: {err}")
            raise Exception("Error in QR login check") from err

    async def verify_qr_2fa(
        self, password: str, token: str, current_user_id: Optional[str]
    ) -> dict[str, Any]:
        """Verify 2FA password for QR code login.

        Args:
            password: 2FA password
            token: QR code token
            current_user_id: ID of the current user (optional)

        Returns:
            Session response with auth data if successful
        """
        try:
            # Validate inputs
            if not password or len(password) < 3:
                raise ValueError("Invalid 2FA password format")
            
            if not token or len(token) < 10:
                raise ValueError("Invalid token format")
            
            # Validate base64 format
            try:
                base64.b64decode(token)
            except Exception:
                raise ValueError("Invalid token encoding")

            session_data = await self._get_client_session(token)
            if not session_data:
                logger.warning(f"Session expired or not found for 2FA verification")
                raise ValueError("Session expired")

            # Check if session is too old
            created_at = session_data.get("created_at", 0)
            current_time = asyncio.get_event_loop().time()
            if current_time - created_at > 300:  # 5 minutes
                logger.warning(f"Session too old for 2FA verification")
                await self._cleanup_client(token)
                raise ValueError("Session expired")

            client = session_data["client"]

            try:
                await client.sign_in(password=password)
                me = await client.get_me()
                session_string = client.session.save()

                logger.info(f"Successful 2FA verification for Telegram user: {me.id}")

                # Only update telegram session if user_id is provided
                if current_user_id:
                    await self.user_service.update_user_tg_session(
                        current_user_id, session_string
                    )

                # Return response with session string for endpoint to save
                return {
                    "requires_2fa": False,
                    "user_id": me.id,
                    "status": "success",
                    "session_string": session_string  # Include session string for endpoint
                }

            except PasswordHashInvalidError as exc:
                logger.warning(f"Invalid 2FA password attempt")
                raise ValueError("Invalid 2FA password") from exc

        except ValueError:
            # Re-raise ValueError with original message
            raise
        except Exception as err:
            logger.error(f"Error verifying 2FA: {err}")
            raise Exception("Error verifying 2FA") from err
        finally:
            await self._cleanup_client(token)

    async def validate_session(self, session: str) -> dict[str, Any]:
        """Validate if a session string is still valid.

        Args:
            session: Session string to validate

        Returns:
            Validation result with user data if valid
        """
        try:
            client = TelegramClient(
                StringSession(session), int(settings.TELETHON_API_ID), settings.TELETHON_API_HASH
            )
            await client.connect()

            if not await client.is_user_authorized():
                return {"valid": False, "reason": "Session unauthorized"}

            me = await client.get_me()
            return {
                "valid": True,
                "user_id": me.id,
                "username": me.username,
                "first_name": me.first_name,
            }
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            SessionPasswordNeededError,
        ) as e:
            logger.error(f"Error validating session: {e}")
            return {"valid": False, "reason": str(e)}
        finally:
            await client.disconnect()
