"""Refactored Telethon Client Service using connection pool and session manager."""

import asyncio
import logging
from typing import Any, Optional

from telethon import TelegramClient
from telethon.errors import FloodWaitError, AuthKeyError, SessionPasswordNeededError

from .connection_pool import TelethonConnectionPool
from .session_manager import TelethonSessionManager
from .connection_monitor import ConnectionMonitor
from services.repositories.user_repository import UserRepository
from services.base.base_service import BaseService


class RefactoredTelethonClientService(BaseService):
    """
    Refactored Telethon client service with connection pooling,
    session management, and health monitoring.
    """
    
    def __init__(
        self, 
        user_repository: UserRepository,
        container: Any,
        max_connections: int = 50,
        connection_timeout: int = 30
    ):
        super().__init__()
        self.user_repository = user_repository
        self.container = container
        
        # Initialize components
        self.connection_pool = TelethonConnectionPool(
            max_connections=max_connections,
            connection_timeout=connection_timeout
        )
        self.session_manager = TelethonSessionManager(user_repository)
        self.connection_monitor = ConnectionMonitor()
        
        # Service state
        self._is_started = False
        
    async def start(self):
        """Start all components."""
        if self._is_started:
            return
            
        await self.connection_pool.start()
        await self.connection_monitor.start()
        
        # Setup alert callbacks
        self.connection_monitor.add_alert_callback(self._handle_alert)
        
        self._is_started = True
        self.logger.info("RefactoredTelethonClientService started")
        
    async def stop(self):
        """Stop all components."""
        if not self._is_started:
            return
            
        await self.connection_pool.stop()
        await self.connection_monitor.stop()
        
        self._is_started = False
        self.logger.info("RefactoredTelethonClientService stopped")
        
    async def get_client(self, user_id: str) -> Optional[TelegramClient]:
        """
        Get Telegram client for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            TelegramClient instance or None if failed
        """
        try:
            # Record connection attempt
            await self.connection_monitor.record_connection_event(
                user_id, 'connect_attempt'
            )
            
            # Get session for user
            session_string = await self.session_manager.get_session(user_id)
            if not session_string:
                await self.connection_monitor.record_connection_event(
                    user_id, 'connect_failed', {'reason': 'no_session'}
                )
                self.logger.warning(f"No valid session found for user {user_id}")
                return None
                
            # Get connection from pool
            client = await self.connection_pool.get_connection(user_id, session_string)
            if client:
                await self.connection_monitor.record_connection_event(
                    user_id, 'connect_success'
                )
                self.logger.debug(f"Successfully obtained client for user {user_id}")
                return client
            else:
                await self.connection_monitor.record_connection_event(
                    user_id, 'connect_failed', {'reason': 'pool_failed'}
                )
                self.logger.warning(f"Failed to get client from pool for user {user_id}")
                return None
                
        except Exception as e:
            await self.connection_monitor.record_connection_event(
                user_id, 'error', {'error': str(e), 'error_type': type(e).__name__}
            )
            self.logger.error(f"Error getting client for user {user_id}: {e}")
            return None
            
    async def disconnect_client(self, user_id: str):
        """Disconnect client for user."""
        try:
            await self.connection_pool.remove_connection(user_id)
            await self.connection_monitor.record_connection_event(
                user_id, 'disconnect'
            )
            self.logger.debug(f"Disconnected client for user {user_id}")
        except Exception as e:
            self.logger.error(f"Error disconnecting client for user {user_id}: {e}")
            
    async def handle_client_error(self, user_id: str, error: Exception):
        """
        Handle error from client operation.
        
        Args:
            user_id: User identifier
            error: Exception that occurred
        """
        # Record error event
        error_details = {
            'error': str(error),
            'error_type': type(error).__name__
        }
        
        if isinstance(error, FloodWaitError):
            error_details['wait_seconds'] = error.seconds
            await self.connection_monitor.record_connection_event(
                user_id, 'flood_wait', error_details
            )
        else:
            await self.connection_monitor.record_connection_event(
                user_id, 'error', error_details
            )
            
        # Handle error in connection pool
        await self.connection_pool.handle_error(user_id, error)
        
        # Handle session-related errors
        if isinstance(error, (AuthKeyError, SessionPasswordNeededError)):
            await self.session_manager.remove_session(user_id)
            self.logger.warning(f"Removed invalid session for user {user_id} due to {type(error).__name__}")
            
    async def store_user_session(self, user_id: str, session_string: str) -> bool:
        """
        Store session for user.
        
        Args:
            user_id: User identifier
            session_string: Telegram session string
            
        Returns:
            True if stored successfully
        """
        try:
            success = await self.session_manager.store_session(user_id, session_string)
            if success:
                self.logger.info(f"Stored session for user {user_id}")
            return success
        except Exception as e:
            self.logger.error(f"Error storing session for user {user_id}: {e}")
            return False
            
    async def remove_user_session(self, user_id: str) -> bool:
        """
        Remove session for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if removed successfully
        """
        try:
            # Disconnect client first
            await self.disconnect_client(user_id)
            
            # Remove session
            success = await self.session_manager.remove_session(user_id)
            if success:
                self.logger.info(f"Removed session for user {user_id}")
            return success
        except Exception as e:
            self.logger.error(f"Error removing session for user {user_id}: {e}")
            return False
            
    async def validate_user_session(self, user_id: str) -> bool:
        """
        Validate session for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if session is valid
        """
        try:
            session_string = await self.session_manager.get_session(user_id)
            if not session_string:
                return False
                
            return await self.session_manager.validate_session(user_id, session_string)
        except Exception as e:
            self.logger.error(f"Error validating session for user {user_id}: {e}")
            return False
            
    async def get_service_stats(self) -> dict:
        """Get comprehensive service statistics."""
        try:
            pool_stats = await self.connection_pool.get_stats()
            session_stats = await self.session_manager.get_session_stats()
            monitor_stats = await self.connection_monitor.get_global_stats()
            
            return {
                'connection_pool': pool_stats,
                'session_manager': session_stats,
                'connection_monitor': monitor_stats,
                'service_status': {
                    'is_started': self._is_started,
                    'components_healthy': True  # TODO: Add health checks
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting service stats: {e}")
            return {}
            
    async def get_health_report(self) -> dict:
        """Get detailed health report."""
        try:
            return await self.connection_monitor.get_health_report()
        except Exception as e:
            self.logger.error(f"Error getting health report: {e}")
            return {}
            
    async def cleanup_invalid_sessions(self):
        """Cleanup invalid sessions."""
        try:
            await self.session_manager.cleanup_invalid_sessions()
            self.logger.info("Completed session cleanup")
        except Exception as e:
            self.logger.error(f"Error during session cleanup: {e}")
            
    async def _handle_alert(self, alert_data: dict):
        """Handle alerts from connection monitor."""
        alert_type = alert_data.get('type')
        user_id = alert_data.get('user_id')
        
        self.logger.warning(f"Connection alert [{alert_type}] for user {user_id}: {alert_data}")
        
        if alert_type == 'high_error_rate':
            # Consider disconnecting problematic client
            self.logger.warning(f"High error rate detected for user {user_id}, considering disconnect")
            # Could implement automatic disconnect logic here
            
        elif alert_type == 'long_flood_wait':
            wait_seconds = alert_data.get('wait_seconds', 0)
            self.logger.warning(f"Long flood wait ({wait_seconds}s) for user {user_id}")
            # Could implement exponential backoff or rate limiting here
            
    # Legacy compatibility methods
    async def has_client(self, user_id: str) -> Optional[TelegramClient]:
        """Legacy method for compatibility."""
        return await self.get_client(user_id)
        
    async def get_or_create_client(self, user_id: str) -> Optional[TelegramClient]:
        """Legacy method for compatibility."""
        return await self.get_client(user_id)
        
    async def disconnect_all(self):
        """Legacy method for compatibility."""
        await self.stop()
        
    def set_container(self, container: Any):
        """Set container for compatibility."""
        self.container = container 