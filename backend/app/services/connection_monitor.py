"""Connection Monitor for tracking Telethon connection health and metrics."""

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json


@dataclass
class ConnectionEvent:
    """Represents a connection event."""
    user_id: str
    event_type: str  # connect, disconnect, error, flood_wait, etc.
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'user_id': self.user_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details or {}
        }


@dataclass
class ConnectionMetrics:
    """Connection metrics for a user."""
    user_id: str
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_reconnections: int = 0
    total_errors: int = 0
    total_flood_waits: int = 0
    last_connection_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    average_connection_duration: float = 0.0
    current_connection_start: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'user_id': self.user_id,
            'total_connections': self.total_connections,
            'successful_connections': self.successful_connections,
            'failed_connections': self.failed_connections,
            'total_reconnections': self.total_reconnections,
            'total_errors': self.total_errors,
            'total_flood_waits': self.total_flood_waits,
            'last_connection_time': self.last_connection_time.isoformat() if self.last_connection_time else None,
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'average_connection_duration': self.average_connection_duration,
            'current_connection_start': self.current_connection_start.isoformat() if self.current_connection_start else None
        }


class ConnectionMonitor:
    """
    Monitor Telethon connections for health, performance metrics, and alerting.
    """
    
    def __init__(self, max_events_per_user: int = 1000, alert_threshold: int = 5):
        self.max_events_per_user = max_events_per_user
        self.alert_threshold = alert_threshold
        self.logger = logging.getLogger(__name__)
        
        # Event storage
        self._events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_events_per_user))
        self._events_lock = asyncio.Lock()
        
        # Metrics storage
        self._metrics: Dict[str, ConnectionMetrics] = {}
        self._metrics_lock = asyncio.Lock()
        
        # Global statistics
        self._global_stats = {
            'total_users_monitored': 0,
            'total_events_recorded': 0,
            'active_connections': 0,
            'total_errors_last_hour': 0,
            'total_flood_waits_last_hour': 0,
            'average_connection_success_rate': 0.0
        }
        
        # Alert callbacks
        self._alert_callbacks = []
        
        # Monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._monitor_interval = 60  # seconds
        
    async def start(self):
        """Start connection monitoring."""
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("ConnectionMonitor started")
        
    async def stop(self):
        """Stop connection monitoring."""
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
                
        self.logger.info("ConnectionMonitor stopped")
        
    async def record_connection_event(
        self, 
        user_id: str, 
        event_type: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Record a connection event.
        
        Args:
            user_id: User identifier
            event_type: Type of event (connect, disconnect, error, etc.)
            details: Additional event details
        """
        event = ConnectionEvent(
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            details=details or {}
        )
        
        async with self._events_lock:
            self._events[user_id].append(event)
            
        await self._update_metrics(user_id, event)
        await self._check_alerts(user_id, event)
        
        self.logger.debug(f"Recorded event for user {user_id}: {event_type}")
        
    async def get_user_events(
        self, 
        user_id: str, 
        event_types: Optional[List[str]] = None,
        since: Optional[datetime] = None
    ) -> List[ConnectionEvent]:
        """
        Get events for a specific user.
        
        Args:
            user_id: User identifier
            event_types: Filter by event types
            since: Only return events after this time
            
        Returns:
            List of connection events
        """
        async with self._events_lock:
            events = list(self._events.get(user_id, []))
            
        # Apply filters
        if event_types:
            events = [e for e in events if e.event_type in event_types]
            
        if since:
            events = [e for e in events if e.timestamp >= since]
            
        return events
        
    async def get_user_metrics(self, user_id: str) -> Optional[ConnectionMetrics]:
        """Get metrics for a specific user."""
        async with self._metrics_lock:
            return self._metrics.get(user_id)
            
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global monitoring statistics."""
        async with self._metrics_lock:
            # Update global stats
            await self._update_global_stats()
            return self._global_stats.copy()
            
    async def get_health_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive health report.
        
        Returns:
            Dictionary with health information
        """
        async with self._metrics_lock:
            now = datetime.utcnow()
            last_hour = now - timedelta(hours=1)
            
            # Get recent error events
            recent_errors = []
            recent_flood_waits = []
            
            for user_id, events in self._events.items():
                for event in events:
                    if event.timestamp < last_hour:
                        continue
                        
                    if event.event_type == 'error':
                        recent_errors.append(event)
                    elif event.event_type == 'flood_wait':
                        recent_flood_waits.append(event)
                        
            # Calculate success rates
            total_connections = sum(m.total_connections for m in self._metrics.values())
            successful_connections = sum(m.successful_connections for m in self._metrics.values())
            success_rate = (successful_connections / total_connections * 100) if total_connections > 0 else 0
            
            # Identify problematic users
            problematic_users = []
            for user_id, metrics in self._metrics.items():
                if metrics.total_connections > 0:
                    user_success_rate = metrics.successful_connections / metrics.total_connections
                    if user_success_rate < 0.8:  # Less than 80% success rate
                        problematic_users.append({
                            'user_id': user_id,
                            'success_rate': user_success_rate * 100,
                            'total_errors': metrics.total_errors,
                            'total_flood_waits': metrics.total_flood_waits
                        })
                        
            return {
                'timestamp': now.isoformat(),
                'summary': {
                    'total_users': len(self._metrics),
                    'total_connections': total_connections,
                    'overall_success_rate': success_rate,
                    'recent_errors_count': len(recent_errors),
                    'recent_flood_waits_count': len(recent_flood_waits)
                },
                'recent_errors': [e.to_dict() for e in recent_errors[-10:]],  # Last 10 errors
                'recent_flood_waits': [e.to_dict() for e in recent_flood_waits[-10:]],  # Last 10 flood waits
                'problematic_users': problematic_users,
                'global_stats': self._global_stats.copy()
            }
            
    def add_alert_callback(self, callback):
        """Add callback function for alerts."""
        self._alert_callbacks.append(callback)
        
    async def _update_metrics(self, user_id: str, event: ConnectionEvent):
        """Update metrics based on event."""
        async with self._metrics_lock:
            if user_id not in self._metrics:
                self._metrics[user_id] = ConnectionMetrics(user_id=user_id)
                
            metrics = self._metrics[user_id]
            
            if event.event_type == 'connect':
                metrics.total_connections += 1
                metrics.last_connection_time = event.timestamp
                metrics.current_connection_start = event.timestamp
                
            elif event.event_type == 'connect_success':
                metrics.successful_connections += 1
                
            elif event.event_type == 'connect_failed':
                metrics.failed_connections += 1
                
            elif event.event_type == 'disconnect':
                if metrics.current_connection_start:
                    duration = (event.timestamp - metrics.current_connection_start).total_seconds()
                    # Update average duration
                    if metrics.average_connection_duration == 0:
                        metrics.average_connection_duration = duration
                    else:
                        metrics.average_connection_duration = (metrics.average_connection_duration + duration) / 2
                    metrics.current_connection_start = None
                    
            elif event.event_type == 'reconnect':
                metrics.total_reconnections += 1
                
            elif event.event_type == 'error':
                metrics.total_errors += 1
                metrics.last_error_time = event.timestamp
                
            elif event.event_type == 'flood_wait':
                metrics.total_flood_waits += 1
                
    async def _check_alerts(self, user_id: str, event: ConnectionEvent):
        """Check if event should trigger alerts."""
        # Count recent errors for this user
        recent_errors = await self.get_user_events(
            user_id, 
            event_types=['error'],
            since=datetime.utcnow() - timedelta(minutes=10)
        )
        
        # Alert if too many errors in short time
        if len(recent_errors) >= self.alert_threshold:
            alert_data = {
                'type': 'high_error_rate',
                'user_id': user_id,
                'error_count': len(recent_errors),
                'time_window': '10 minutes',
                'latest_event': event.to_dict()
            }
            await self._send_alert(alert_data)
            
        # Alert on flood wait
        if event.event_type == 'flood_wait':
            wait_time = event.details.get('wait_seconds', 0) if event.details else 0
            if wait_time > 300:  # More than 5 minutes
                alert_data = {
                    'type': 'long_flood_wait',
                    'user_id': user_id,
                    'wait_seconds': wait_time,
                    'event': event.to_dict()
                }
                await self._send_alert(alert_data)
                
    async def _send_alert(self, alert_data: Dict[str, Any]):
        """Send alert to registered callbacks."""
        self.logger.warning(f"ALERT: {alert_data}")
        
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                self.logger.error(f"Error calling alert callback: {e}")
                
    async def _update_global_stats(self):
        """Update global statistics."""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        
        self._global_stats['total_users_monitored'] = len(self._metrics)
        self._global_stats['total_events_recorded'] = sum(len(events) for events in self._events.values())
        
        # Count active connections (users with current_connection_start)
        active_connections = sum(
            1 for m in self._metrics.values() 
            if m.current_connection_start is not None
        )
        self._global_stats['active_connections'] = active_connections
        
        # Count recent errors and flood waits
        recent_errors = 0
        recent_flood_waits = 0
        
        for events in self._events.values():
            for event in events:
                if event.timestamp < last_hour:
                    continue
                if event.event_type == 'error':
                    recent_errors += 1
                elif event.event_type == 'flood_wait':
                    recent_flood_waits += 1
                    
        self._global_stats['total_errors_last_hour'] = recent_errors
        self._global_stats['total_flood_waits_last_hour'] = recent_flood_waits
        
        # Calculate average success rate
        total_connections = sum(m.total_connections for m in self._metrics.values())
        successful_connections = sum(m.successful_connections for m in self._metrics.values())
        
        if total_connections > 0:
            self._global_stats['average_connection_success_rate'] = (
                successful_connections / total_connections * 100
            )
        else:
            self._global_stats['average_connection_success_rate'] = 0.0
            
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._is_running:
            try:
                await asyncio.sleep(self._monitor_interval)
                
                # Update global stats
                await self._update_global_stats()
                
                # Log summary
                stats = await self.get_global_stats()
                self.logger.info(
                    f"Connection Monitor - Users: {stats['total_users_monitored']}, "
                    f"Active: {stats['active_connections']}, "
                    f"Success Rate: {stats['average_connection_success_rate']:.1f}%, "
                    f"Errors/Hour: {stats['total_errors_last_hour']}, "
                    f"FloodWaits/Hour: {stats['total_flood_waits_last_hour']}"
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}") 