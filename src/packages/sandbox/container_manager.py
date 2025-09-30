"""
Container Manager for reusing Docker containers to improve response time.
Containers are kept alive for TTL seconds and reused for subsequent messages.
"""

import asyncio
import time
from typing import Dict, Optional, Tuple
from loguru import logger
from .cc import ClaudeSandbox, ClaudeSandboxSession


class ContainerManager:
    """Manages Docker containers with TTL-based lifecycle."""
    
    def __init__(self, ttl: int = 600):
        """
        Initialize container manager.
        
        Args:
            ttl: Time-to-live in seconds (default 600 = 10 minutes)
        """
        self.ttl = ttl
        self._containers: Dict[str, Tuple[ClaudeSandbox, float]] = {}  # {user_id: (container, last_used_time)}
        self._sessions: Dict[str, ClaudeSandboxSession] = {}  # {user_id: session}
        self._lock = None  # Will be created lazily in the correct event loop
        
    def _get_lock(self):
        """Get or create lock in the current event loop."""
        try:
            loop = asyncio.get_running_loop()
            # Create a new lock if we don't have one or if it's from a different loop
            if self._lock is None or self._lock._loop != loop:
                self._lock = asyncio.Lock()
        except RuntimeError:
            # No running loop, create a new lock
            self._lock = asyncio.Lock()
        return self._lock
        
    async def get_or_create_session(
        self, 
        user_id: str, 
        envd_port: int,
        on_creating: Optional[callable] = None
    ) -> ClaudeSandboxSession:
        """
        Get existing session or create a new one.
        
        Args:
            user_id: User identifier
            envd_port: Port for envd service
            on_creating: Callback when creating new container
            
        Returns:
            ClaudeSandboxSession ready for use
        """
        async with self._get_lock():
            # Check if container exists and is not expired
            if user_id in self._containers:
                container, last_used = self._containers[user_id]
                if time.time() - last_used < self.ttl:
                    # Container is still valid, update last used time
                    logger.info(f"Reusing container for user {user_id}")
                    self._containers[user_id] = (container, time.time())
                    return self._sessions[user_id]
                else:
                    # Container expired, clean it up
                    logger.info(f"Container for user {user_id} expired, cleaning up")
                    await self._cleanup_container(user_id)
            
            # Create new container
            logger.info(f"Creating new container for user {user_id}")
            if on_creating:
                await on_creating()  # Notify that we're creating a container
                
            # Create sandbox with keep_alive flag
            sandbox = ClaudeSandbox(
                id=user_id,
                envd_port=envd_port,
                keep_alive=True,  # Important: keep container alive
                ttl=self.ttl
            )
            
            # Create session with named parameter
            session = ClaudeSandboxSession(sandbox=sandbox)
            
            # Start the sandbox
            await sandbox.start()
            
            # Store container and session
            self._containers[user_id] = (sandbox, time.time())
            self._sessions[user_id] = session
            
            logger.info(f"New container created for user {user_id}")
            return session
    
    async def _cleanup_container(self, user_id: str):
        """Clean up a specific container."""
        if user_id in self._containers:
            container, _ = self._containers[user_id]
            try:
                await container.stop()
                logger.info(f"Container for user {user_id} stopped and removed")
            except Exception as e:
                logger.error(f"Error stopping container for user {user_id}: {e}")
            del self._containers[user_id]
            
        if user_id in self._sessions:
            del self._sessions[user_id]
    
    async def cleanup_expired(self) -> int:
        """
        Clean up all expired containers.
        
        Returns:
            Number of containers cleaned up
        """
        async with self._get_lock():
            current_time = time.time()
            expired_users = [
                user_id 
                for user_id, (_, last_used) in self._containers.items()
                if current_time - last_used >= self.ttl
            ]
            
            for user_id in expired_users:
                await self._cleanup_container(user_id)
            
            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired containers")
            
            return len(expired_users)
    
    async def cleanup_all(self):
        """Clean up all containers (for shutdown)."""
        async with self._get_lock():
            user_ids = list(self._containers.keys())
            for user_id in user_ids:
                await self._cleanup_container(user_id)
            logger.info(f"All {len(user_ids)} containers cleaned up")
    
    def get_stats(self) -> Dict:
        """Get statistics about managed containers."""
        current_time = time.time()
        stats = {
            "total_containers": len(self._containers),
            "containers": {}
        }
        
        for user_id, (_, last_used) in self._containers.items():
            age = current_time - last_used
            stats["containers"][user_id] = {
                "age_seconds": int(age),
                "remaining_ttl": max(0, int(self.ttl - age)),
                "expired": age >= self.ttl
            }
        
        return stats


# Global instance
_container_manager: Optional[ContainerManager] = None


def get_container_manager(ttl: int = 600) -> ContainerManager:
    """Get or create the global container manager instance."""
    global _container_manager
    if _container_manager is None:
        _container_manager = ContainerManager(ttl=ttl)
    return _container_manager


async def cleanup_task(interval: int = 60):
    """
    Background task to periodically clean up expired containers.
    
    Args:
        interval: Check interval in seconds (default 60)
    """
    manager = get_container_manager()
    while True:
        try:
            await asyncio.sleep(interval)
            await manager.cleanup_expired()
        except asyncio.CancelledError:
            # Task is being cancelled, clean up all containers
            await manager.cleanup_all()
            break
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")