"""
Shared context management for discussion sessions.

Manages discussion state, messages, and participants using Redis as the backend.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from redis.asyncio import Redis, ConnectionPool
from contextlib import asynccontextmanager

from .config import settings, RedisKeys
from .models import (
    DiscussionSession,
    Message,
    Participant,
    DiscussionStatus,
    MessageType
)

logger = logging.getLogger(__name__)


class SharedContext:
    """
    Manages shared context for discussion sessions using Redis.

    Provides methods to store and retrieve discussion state, messages,
    and participant information with atomic operations.
    """

    def __init__(self, redis_client: Redis):
        """
        Initialize SharedContext with Redis client.

        Args:
            redis_client: Async Redis client instance
        """
        self.redis = redis_client
        self.ttl = settings.session_timeout

    async def create_session(self, session: DiscussionSession) -> bool:
        """
        Create a new discussion session.

        Args:
            session: DiscussionSession object to create

        Returns:
            bool: True if created successfully

        Raises:
            Exception: If session creation fails
        """
        try:
            session_key = RedisKeys.discussion_session(session.id)

            # Check if session already exists
            exists = await self.redis.exists(session_key)
            if exists:
                logger.warning(f"Session {session.id} already exists")
                return False

            # Store session data
            session_data = session.model_dump_json()
            await self.redis.set(session_key, session_data, ex=self.ttl)

            # Initialize empty message list
            messages_key = RedisKeys.discussion_messages(session.id)
            await self.redis.delete(messages_key)  # Ensure clean state

            # Store participants
            await self._store_participants(session.id, session.participants)

            # Add to active discussions set
            await self.redis.sadd(RedisKeys.active_discussions(), session.id)

            logger.info(f"Created discussion session: {session.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create session {session.id}: {e}")
            raise

    async def get_session(self, discussion_id: str) -> Optional[DiscussionSession]:
        """
        Retrieve a discussion session.

        Args:
            discussion_id: Discussion session ID

        Returns:
            DiscussionSession object or None if not found
        """
        try:
            session_key = RedisKeys.discussion_session(discussion_id)
            session_data = await self.redis.get(session_key)

            if not session_data:
                logger.warning(f"Session {discussion_id} not found")
                return None

            session = DiscussionSession.model_validate_json(session_data)

            # Refresh TTL on access
            await self.redis.expire(session_key, self.ttl)

            return session

        except Exception as e:
            logger.error(f"Failed to get session {discussion_id}: {e}")
            return None

    async def update_session(self, session: DiscussionSession) -> bool:
        """
        Update an existing discussion session.

        Args:
            session: DiscussionSession object with updated data

        Returns:
            bool: True if updated successfully
        """
        try:
            session.updated_at = datetime.utcnow()
            session_key = RedisKeys.discussion_session(session.id)

            session_data = session.model_dump_json()
            await self.redis.set(session_key, session_data, ex=self.ttl)

            logger.debug(f"Updated session: {session.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update session {session.id}: {e}")
            return False

    async def add_message(
        self,
        discussion_id: str,
        message: Message
    ) -> bool:
        """
        Add a message to the discussion.

        Args:
            discussion_id: Discussion session ID
            message: Message object to add

        Returns:
            bool: True if message added successfully
        """
        try:
            messages_key = RedisKeys.discussion_messages(discussion_id)
            message_data = message.model_dump_json()

            # Add message to list
            await self.redis.rpush(messages_key, message_data)
            await self.redis.expire(messages_key, self.ttl)

            # Update session timestamp
            session = await self.get_session(discussion_id)
            if session:
                session.updated_at = datetime.utcnow()
                await self.update_session(session)

            logger.debug(f"Added message to discussion {discussion_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add message to {discussion_id}: {e}")
            return False

    async def get_history(
        self,
        discussion_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """
        Get discussion message history.

        Args:
            discussion_id: Discussion session ID
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip from the start

        Returns:
            List of Message objects
        """
        try:
            messages_key = RedisKeys.discussion_messages(discussion_id)

            # Get message range
            end = -1 if limit is None else offset + limit - 1
            message_strings = await self.redis.lrange(messages_key, offset, end)

            messages = [
                Message.model_validate_json(msg_str)
                for msg_str in message_strings
            ]

            logger.debug(f"Retrieved {len(messages)} messages from {discussion_id}")
            return messages

        except Exception as e:
            logger.error(f"Failed to get history for {discussion_id}: {e}")
            return []

    async def get_participants(self, discussion_id: str) -> List[Participant]:
        """
        Get all participants in a discussion.

        Args:
            discussion_id: Discussion session ID

        Returns:
            List of Participant objects
        """
        try:
            participants_key = RedisKeys.discussion_participants(discussion_id)
            participant_data = await self.redis.hgetall(participants_key)

            participants = [
                Participant.model_validate_json(data)
                for data in participant_data.values()
            ]

            return participants

        except Exception as e:
            logger.error(f"Failed to get participants for {discussion_id}: {e}")
            return []

    async def _store_participants(
        self,
        discussion_id: str,
        participants: List[Participant]
    ) -> None:
        """
        Store participants in Redis.

        Args:
            discussion_id: Discussion session ID
            participants: List of Participant objects
        """
        participants_key = RedisKeys.discussion_participants(discussion_id)

        # Store each participant as a hash field
        participant_dict = {
            p.participant_id: p.model_dump_json()
            for p in participants
        }

        if participant_dict:
            await self.redis.hset(
                participants_key,
                mapping=participant_dict
            )
            await self.redis.expire(participants_key, self.ttl)

    async def update_status(
        self,
        discussion_id: str,
        status: DiscussionStatus
    ) -> bool:
        """
        Update discussion status.

        Args:
            discussion_id: Discussion session ID
            status: New DiscussionStatus

        Returns:
            bool: True if updated successfully
        """
        try:
            session = await self.get_session(discussion_id)
            if not session:
                return False

            session.status = status

            # Update timestamps based on status
            if status == DiscussionStatus.ACTIVE and not session.started_at:
                session.started_at = datetime.utcnow()
            elif status in [DiscussionStatus.COMPLETED, DiscussionStatus.FAILED]:
                session.completed_at = datetime.utcnow()
                # Remove from active set
                await self.redis.srem(RedisKeys.active_discussions(), discussion_id)

            await self.update_session(session)

            logger.info(f"Updated discussion {discussion_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update status for {discussion_id}: {e}")
            return False

    async def delete_session(self, discussion_id: str) -> bool:
        """
        Delete a discussion session and all associated data.

        Args:
            discussion_id: Discussion session ID

        Returns:
            bool: True if deleted successfully
        """
        try:
            keys_to_delete = [
                RedisKeys.discussion_session(discussion_id),
                RedisKeys.discussion_messages(discussion_id),
                RedisKeys.discussion_state(discussion_id),
                RedisKeys.discussion_participants(discussion_id),
                RedisKeys.discussion_lock(discussion_id),
            ]

            await self.redis.delete(*keys_to_delete)
            await self.redis.srem(RedisKeys.active_discussions(), discussion_id)

            logger.info(f"Deleted discussion session: {discussion_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {discussion_id}: {e}")
            return False

    async def get_active_discussions(self) -> List[str]:
        """
        Get list of active discussion IDs.

        Returns:
            List of discussion IDs
        """
        try:
            discussion_ids = await self.redis.smembers(RedisKeys.active_discussions())
            return list(discussion_ids)
        except Exception as e:
            logger.error(f"Failed to get active discussions: {e}")
            return []


class RedisConnectionManager:
    """Manages Redis connection pool and lifecycle."""

    def __init__(self):
        """Initialize connection manager."""
        self.pool: Optional[ConnectionPool] = None
        self.redis: Optional[Redis] = None

    async def connect(self) -> Redis:
        """
        Create Redis connection pool and client.

        Returns:
            Redis client instance
        """
        if self.redis is not None:
            return self.redis

        try:
            redis_config = settings.get_redis_config()

            self.pool = ConnectionPool.from_url(
                redis_config["url"],
                max_connections=redis_config["max_connections"],
                socket_timeout=redis_config["socket_timeout"],
                socket_connect_timeout=redis_config["socket_connect_timeout"],
                decode_responses=redis_config["decode_responses"]
            )

            self.redis = Redis(connection_pool=self.pool)

            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis successfully")

            return self.redis

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection and cleanup resources."""
        try:
            if self.redis:
                await self.redis.close()
                logger.info("Redis connection closed")

            if self.pool:
                await self.pool.disconnect()
                logger.info("Redis connection pool closed")

        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")

    async def get_client(self) -> Redis:
        """
        Get Redis client, creating connection if needed.

        Returns:
            Redis client instance
        """
        if self.redis is None:
            await self.connect()
        return self.redis


# Global connection manager instance
redis_manager = RedisConnectionManager()
