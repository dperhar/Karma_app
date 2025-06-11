"""Telethon Connection Pool implementation for efficient connection management."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from uuid import uuid4

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    AuthKeyError, 
    FloodWaitError, 
    NetworkMigrateError,
    PhoneMigrateError,
    SessionPasswordNeededError,
    UserMigrateError
)

from app.core.config import settings


class ConnectionInfo:
    """Information about a connection."""
    
    def __init__(self, client: TelegramClient, user_id: str):
        self.client = client
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.connection_attempts = 0
        self.is_healthy = True
        self.last_error: Optional[Exception] = None
        self.flood_wait_until: Optional[datetime] = None
        
    def mark_used(self):
        """Mark connection as recently used."""
        self.last_used = datetime.utcnow()
        
    def mark_unhealthy(self, error: Exception):
        """Mark connection as unhealthy."""
        self.is_healthy = False
        self.last_error = error
        
    def mark_healthy(self):
        """Mark connection as healthy."""
        self.is_healthy = True
        self.last_error = None
        
    def set_flood_wait(self, seconds: int):
        """Set flood wait timeout."""
        self.flood_wait_until = datetime.utcnow() + timedelta(seconds=seconds)
        
    def is_flood_waiting(self) -> bool:
        """Check if connection is in flood wait."""
        if not self.flood_wait_until:
            return False
        return datetime.utcnow() < self.flood_wait_until
        
    def get_flood_wait_remaining(self) -> float:
        """Get remaining flood wait time in seconds."""
        if not self.flood_wait_until:
            return 0.0
        delta = self.flood_wait_until - datetime.utcnow()
        return max(0.0, delta.total_seconds())


class TelethonConnectionPool:
    """
    Connection pool for Telethon clients with automatic reconnection,
    health monitoring, and flood protection.
    """
    
    def __init__(self, max_connections: int = 50, connection_timeout: int = 30):
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.logger = logging.getLogger(__name__)
        
        # Connection storage
        self._connections: Dict[str, ConnectionInfo] = {}
        self._connection_lock = asyncio.Lock()
        
        # Health monitoring
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = 60  # seconds
        self._is_running = False
        
        # Statistics
        self._stats = {
            'total_connections_created': 0,
            'total_connections_failed': 0,
            'total_reconnections': 0,
            'current_connections': 0,
            'healthy_connections': 0,
            'flood_wait_connections': 0
        }
        
    async def start(self):
        """Start the connection pool and health monitoring."""
        self._is_running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("TelethonConnectionPool started")
        
    async def stop(self):
        """Stop the connection pool and cleanup all connections."""
        self._is_running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
                
        await self._cleanup_all_connections()
        self.logger.info("TelethonConnectionPool stopped")
        
    async def get_connection(self, user_id: str, session_string: str) -> Optional[TelegramClient]:
        """
        Get a connection for user. Creates new if doesn't exist or recreates if unhealthy.
        
        Args:
            user_id: User identifier
            session_string: Telegram session string
            
        Returns:
            TelegramClient instance or None if failed to create/get
        """
        async with self._connection_lock:
            # Check if we have existing healthy connection
            if user_id in self._connections:
                conn_info = self._connections[user_id]
                
                # Check flood wait
                if conn_info.is_flood_waiting():
                    remaining = conn_info.get_flood_wait_remaining()
                    self.logger.warning(f"Connection for user {user_id} is in flood wait for {remaining:.1f}s")
                    return None
                    
                # Check if connection is healthy and authorized
                if conn_info.is_healthy:
                    try:
                        client = conn_info.client
                        
                        # Ensure connection
                        if not client.is_connected():
                            await client.connect()
                            
                        # Check authorization
                        if await client.is_user_authorized():
                            conn_info.mark_used()
                            return client
                        else:
                            self.logger.warning(f"Connection for user {user_id} is not authorized, recreating")
                            await self._remove_connection(user_id)
                    except Exception as e:
                        self.logger.error(f"Error checking connection for user {user_id}: {e}")
                        await self._remove_connection(user_id)
                        
            # Create new connection
            return await self._create_connection(user_id, session_string)
            
    async def remove_connection(self, user_id: str):
        """Remove connection for user."""
        async with self._connection_lock:
            await self._remove_connection(user_id)
            
    async def handle_error(self, user_id: str, error: Exception):
        """Handle error for specific connection."""
        async with self._connection_lock:
            if user_id not in self._connections:
                return
                
            conn_info = self._connections[user_id]
            
            if isinstance(error, FloodWaitError):
                # Set flood wait
                conn_info.set_flood_wait(error.seconds)
                self.logger.warning(f"FloodWait for user {user_id}: {error.seconds}s")
                self._stats['flood_wait_connections'] += 1
                
            elif isinstance(error, (AuthKeyError, SessionPasswordNeededError)):
                # Session issues - remove connection
                self.logger.error(f"Session error for user {user_id}: {error}")
                await self._remove_connection(user_id)
                
            elif isinstance(error, (NetworkMigrateError, PhoneMigrateError, UserMigrateError)):
                # Migration errors - mark for recreation
                self.logger.warning(f"Migration error for user {user_id}: {error}")
                conn_info.mark_unhealthy(error)
                
            else:
                # Other errors - mark unhealthy
                conn_info.mark_unhealthy(error)
                
    async def get_stats(self) -> Dict:
        """Get connection pool statistics."""
        async with self._connection_lock:
            healthy_count = sum(1 for conn in self._connections.values() if conn.is_healthy)
            flood_wait_count = sum(1 for conn in self._connections.values() if conn.is_flood_waiting())
            
            self._stats.update({
                'current_connections': len(self._connections),
                'healthy_connections': healthy_count,
                'flood_wait_connections': flood_wait_count
            })
            
            return self._stats.copy()
            
    async def _create_connection(self, user_id: str, session_string: str) -> Optional[TelegramClient]:
        """Create new connection."""
        try:
            # Check connection limit
            if len(self._connections) >= self.max_connections:
                await self._cleanup_old_connections()
                
            # Create client with optimized settings
            client = TelegramClient(
                StringSession(session_string),
                int(settings.TELETHON_API_ID),
                settings.TELETHON_API_HASH,
                device_model="Karma App",
                system_version="10.0.0",
                app_version="2.0.0",
                lang_code="en",
                system_lang_code="en",
                # Connection optimizations
                connection_retries=3,
                retry_delay=1,
                timeout=self.connection_timeout,
                auto_reconnect=True,
                # Reduce flood wait exposure
                flood_sleep_threshold=60,
            )
            
            # Connect with timeout
            await asyncio.wait_for(client.connect(), timeout=self.connection_timeout)
            
            # Verify authorization
            if not await client.is_user_authorized():
                await client.disconnect()
                self._stats['total_connections_failed'] += 1
                self.logger.warning(f"Failed to authorize client for user {user_id}")
                return None
                
            # Store connection
            conn_info = ConnectionInfo(client, user_id)
            self._connections[user_id] = conn_info
            
            self._stats['total_connections_created'] += 1
            self.logger.info(f"Created new connection for user {user_id}")
            
            return client
            
        except Exception as e:
            self._stats['total_connections_failed'] += 1
            self.logger.error(f"Failed to create connection for user {user_id}: {e}")
            return None
            
    async def _remove_connection(self, user_id: str):
        """Remove connection for user."""
        if user_id in self._connections:
            conn_info = self._connections[user_id]
            try:
                if conn_info.client.is_connected():
                    await conn_info.client.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting client for user {user_id}: {e}")
            finally:
                del self._connections[user_id]
                self.logger.debug(f"Removed connection for user {user_id}")
                
    async def _cleanup_old_connections(self):
        """Cleanup old unused connections."""
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        to_remove = []
        
        for user_id, conn_info in self._connections.items():
            if conn_info.last_used < cutoff_time or not conn_info.is_healthy:
                to_remove.append(user_id)
                
        for user_id in to_remove:
            await self._remove_connection(user_id)
            
        if to_remove:
            self.logger.info(f"Cleaned up {len(to_remove)} old connections")
            
    async def _cleanup_all_connections(self):
        """Cleanup all connections."""
        for user_id in list(self._connections.keys()):
            await self._remove_connection(user_id)
            
    async def _health_check_loop(self):
        """Health check loop for monitoring connections."""
        while self._is_running:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                
    async def _perform_health_checks(self):
        """Perform health checks on all connections."""
        async with self._connection_lock:
            unhealthy_connections = []
            
            for user_id, conn_info in self._connections.items():
                try:
                    client = conn_info.client
                    
                    # Skip if in flood wait
                    if conn_info.is_flood_waiting():
                        continue
                        
                    # Check connection status
                    if not client.is_connected():
                        try:
                            await client.connect()
                        except Exception as e:
                            self.logger.warning(f"Failed to reconnect client for user {user_id}: {e}")
                            unhealthy_connections.append(user_id)
                            continue
                            
                    # Check authorization
                    if not await client.is_user_authorized():
                        self.logger.warning(f"Client for user {user_id} lost authorization")
                        unhealthy_connections.append(user_id)
                        continue
                        
                    # Mark as healthy if all checks passed
                    if not conn_info.is_healthy:
                        conn_info.mark_healthy()
                        self.logger.info(f"Connection for user {user_id} is healthy again")
                        
                except Exception as e:
                    self.logger.error(f"Health check failed for user {user_id}: {e}")
                    unhealthy_connections.append(user_id)
                    
            # Remove unhealthy connections
            for user_id in unhealthy_connections:
                await self._remove_connection(user_id)
                
            if unhealthy_connections:
                self.logger.warning(f"Removed {len(unhealthy_connections)} unhealthy connections") 