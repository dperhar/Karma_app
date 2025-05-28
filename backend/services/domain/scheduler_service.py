"""Service for managing background scheduled tasks."""

import asyncio
import logging
import random
from typing import Optional, Callable

from services.base.base_service import BaseService


class SchedulerService(BaseService):
    """Service for managing background scheduled tasks."""

    def __init__(self):
        super().__init__()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start_periodic_task(
        self,
        task_func: Callable,
        min_interval_minutes: int = 30,
        max_interval_minutes: int = 240,
        task_name: str = "periodic_task"
    ):
        """Start a periodic task with random intervals.
        
        Args:
            task_func: Async function to execute periodically
            min_interval_minutes: Minimum interval between executions
            max_interval_minutes: Maximum interval between executions
            task_name: Name for logging purposes
        """
        if self._running:
            self.logger.warning(f"Scheduler for {task_name} is already running")
            return

        self._running = True
        self.logger.info(f"Starting periodic scheduler for {task_name}")
        
        async def periodic_worker():
            """Worker function that runs the periodic task."""
            while self._running:
                try:
                    # Calculate random interval in seconds
                    interval_minutes = random.randint(min_interval_minutes, max_interval_minutes)
                    interval_seconds = interval_minutes * 60
                    
                    self.logger.info(
                        f"Next {task_name} execution in {interval_minutes} minutes "
                        f"({interval_seconds} seconds)"
                    )
                    
                    # Wait for the interval
                    await asyncio.sleep(interval_seconds)
                    
                    if not self._running:
                        break
                    
                    # Execute the task
                    self.logger.info(f"Executing {task_name}")
                    try:
                        await task_func()
                        self.logger.info(f"Successfully completed {task_name}")
                    except Exception as e:
                        self.logger.error(
                            f"Error executing {task_name}: {str(e)}", 
                            exc_info=True
                        )
                        # Continue running even if task fails
                        
                except asyncio.CancelledError:
                    self.logger.info(f"Scheduler for {task_name} was cancelled")
                    break
                except Exception as e:
                    self.logger.error(
                        f"Unexpected error in scheduler for {task_name}: {str(e)}", 
                        exc_info=True
                    )
                    # Wait a bit before retrying
                    await asyncio.sleep(60)
            
            self.logger.info(f"Scheduler for {task_name} stopped")

        # Start the background task
        self._task = asyncio.create_task(periodic_worker())
        return self._task

    async def stop(self):
        """Stop the periodic task."""
        if not self._running:
            return
        
        self.logger.info("Stopping scheduler")
        self._running = False
        
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running 