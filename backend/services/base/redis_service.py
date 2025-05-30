"""Redis service for working with Redis database."""

import json
from typing import Any, Optional

import redis

from config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT


class RedisService:
    """Service for working with Redis database."""

    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set a key-value pair in Redis.

        Args:
            key: The key to set
            value: The value to set (will be JSON serialized if not a string)
            expire: Optional expiration time in seconds

        Returns:
            bool: True if successful
        """
        if not isinstance(value, str):
            value = json.dumps(value)

        result = self.redis_client.set(key, value)

        if expire is not None:
            self.redis_client.expire(key, expire)

        return result

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from Redis by key.

        Args:
            key: The key to get
            default: Default value if key doesn't exist

        Returns:
            The value or default if key doesn't exist
        """
        value = self.redis_client.get(key)

        if value is None:
            return default

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def delete(self, key: str) -> int:
        """
        Delete a key from Redis.

        Args:
            key: The key to delete

        Returns:
            int: Number of keys deleted
        """
        return self.redis_client.delete(key)

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.

        Args:
            key: The key to check

        Returns:
            bool: True if key exists
        """
        return bool(self.redis_client.exists(key))

    def expire(self, key: str, seconds: int) -> bool:
        """
        Set an expiration time on a key.

        Args:
            key: The key to set expiration on
            seconds: Time in seconds

        Returns:
            bool: True if successful
        """
        return bool(self.redis_client.expire(key, seconds))

    def ttl(self, key: str) -> int:
        """
        Get the time to live for a key.

        Args:
            key: The key to check

        Returns:
            int: TTL in seconds, -1 if no expire, -2 if key doesn't exist
        """
        return self.redis_client.ttl(key)

    def keys(self, pattern: str = "*") -> list[str]:
        """
        Find all keys matching a pattern.

        Args:
            pattern: Pattern to match

        Returns:
            List of matching keys
        """
        return self.redis_client.keys(pattern)

    def hset(self, name: str, key: str, value: Any) -> int:
        """
        Set a hash field to a value.

        Args:
            name: Name of the hash
            key: Key in the hash
            value: Value to set

        Returns:
            int: 1 if field is new, 0 if field existed
        """
        if not isinstance(value, str):
            value = json.dumps(value)

        return self.redis_client.hset(name, key, value)

    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """
        Get the value of a hash field.

        Args:
            name: Name of the hash
            key: Key in the hash
            default: Default value if field doesn't exist

        Returns:
            Value of the field or default
        """
        value = self.redis_client.hget(name, key)

        if value is None:
            return default

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def hgetall(self, name: str) -> dict[str, Any]:
        """
        Get all fields and values in a hash.

        Args:
            name: Name of the hash

        Returns:
            Dict of fields and values
        """
        result = self.redis_client.hgetall(name)

        # Try to JSON decode values
        for key, value in result.items():
            try:
                result[key] = json.loads(value)
            except json.JSONDecodeError:
                pass

        return result

    def hdel(self, name: str, *keys: str) -> int:
        """
        Delete one or more hash fields.

        Args:
            name: Name of the hash
            keys: Keys to delete

        Returns:
            int: Number of fields deleted
        """
        return self.redis_client.hdel(name, *keys)

    def hexists(self, name: str, key: str) -> bool:
        """
        Check if a field exists in a hash.

        Args:
            name: Name of the hash
            key: Key to check

        Returns:
            bool: True if field exists
        """
        return bool(self.redis_client.hexists(name, key))

    def lpush(self, name: str, *values: Any) -> int:
        """
        Push values onto the head of a list.

        Args:
            name: Name of the list
            values: Values to push

        Returns:
            int: Length of list after push
        """
        serialized_values = []
        for value in values:
            if not isinstance(value, str):
                serialized_values.append(json.dumps(value))
            else:
                serialized_values.append(value)

        return self.redis_client.lpush(name, *serialized_values)

    def rpush(self, name: str, *values: Any) -> int:
        """
        Push values onto the tail of a list.

        Args:
            name: Name of the list
            values: Values to push

        Returns:
            int: Length of list after push
        """
        serialized_values = []
        for value in values:
            if not isinstance(value, str):
                serialized_values.append(json.dumps(value))
            else:
                serialized_values.append(value)

        return self.redis_client.rpush(name, *serialized_values)

    def lrange(self, name: str, start: int, end: int) -> list[Any]:
        """
        Get a range of elements from a list.

        Args:
            name: Name of the list
            start: Start index
            end: End index

        Returns:
            List of elements
        """
        result = self.redis_client.lrange(name, start, end)

        # Try to JSON decode values
        for i, value in enumerate(result):
            try:
                result[i] = json.loads(value)
            except json.JSONDecodeError:
                pass

        return result

    def llen(self, name: str) -> int:
        """
        Get the length of a list.

        Args:
            name: Name of the list

        Returns:
            int: Length of the list
        """
        return self.redis_client.llen(name)

    def incr(self, name: str, amount: int = 1) -> int:
        """
        Increment the value of a key.

        Args:
            name: Key to increment
            amount: Amount to increment by

        Returns:
            int: New value
        """
        return self.redis_client.incr(name, amount)

    def decr(self, name: str, amount: int = 1) -> int:
        """
        Decrement the value of a key.

        Args:
            name: Key to decrement
            amount: Amount to decrement by

        Returns:
            int: New value
        """
        return self.redis_client.decr(name, amount)

    def ping(self) -> bool:
        """
        Ping the Redis server.

        Returns:
            bool: True if connected
        """
        return self.redis_client.ping()
