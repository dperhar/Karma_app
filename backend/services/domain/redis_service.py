"""Redis service implementation."""

from typing import Any, Optional

from services.base.redis_service import RedisService


class RedisDataService(RedisService):
    """Service for working with Redis database in the application."""

    def __init__(self):
        """Initialize Redis service."""
        super().__init__()

    def save_user_data(
        self, user_id: int, data: dict[str, Any], expire: Optional[int] = None
    ) -> bool:
        """
        Save user data to Redis.

        Args:
            user_id: User ID
            data: User data
            expire: Optional expiration time in seconds

        Returns:
            bool: True if successful
        """
        key = f"user:{user_id}"
        return self.set(key, data, expire)

    def get_user_data(self, user_id: int) -> Optional[dict[str, Any]]:
        """
        Get user data from Redis.

        Args:
            user_id: User ID

        Returns:
            Optional[Dict[str, Any]]: User data or None if not found
        """
        key = f"user:{user_id}"
        return self.get(key)

    def save_session(
        self, session_id: str, data: dict[str, Any], expire: int = 3600
    ) -> bool:
        """
        Save session data to Redis.

        Args:
            session_id: Session ID
            data: Session data
            expire: Expiration time in seconds (default: 1 hour)

        Returns:
            bool: True if successful
        """
        key = f"session:{session_id}"
        return self.set(key, data, expire)

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """
        Get session data from Redis.

        Args:
            session_id: Session ID

        Returns:
            Optional[Dict[str, Any]]: Session data or None if not found
        """
        key = f"session:{session_id}"
        return self.get(key)

    def delete_session(self, session_id: str) -> int:
        """
        Delete session data from Redis.

        Args:
            session_id: Session ID

        Returns:
            int: 1 if deleted, 0 if not found
        """
        key = f"session:{session_id}"
        return self.delete(key)

    def save_cache(self, cache_key: str, data: Any, expire: int = 300) -> bool:
        """
        Save data to cache.

        Args:
            cache_key: Cache key
            data: Data to cache
            expire: Expiration time in seconds (default: 5 minutes)

        Returns:
            bool: True if successful
        """
        key = f"cache:{cache_key}"
        return self.set(key, data, expire)

    def get_cache(self, cache_key: str) -> Optional[Any]:
        """
        Get data from cache.

        Args:
            cache_key: Cache key

        Returns:
            Optional[Any]: Cached data or None if not found
        """
        key = f"cache:{cache_key}"
        return self.get(key)

    def invalidate_cache(self, cache_key: str) -> int:
        """
        Invalidate cache.

        Args:
            cache_key: Cache key

        Returns:
            int: 1 if deleted, 0 if not found
        """
        key = f"cache:{cache_key}"
        return self.delete(key)

    def add_to_list(self, list_name: str, value: Any) -> int:
        """
        Add value to a list.

        Args:
            list_name: List name
            value: Value to add

        Returns:
            int: Length of list after adding value
        """
        key = f"list:{list_name}"
        return self.rpush(key, value)

    def get_list(self, list_name: str, start: int = 0, end: int = -1) -> list[Any]:
        """
        Get list values.

        Args:
            list_name: List name
            start: Start index (default: 0)
            end: End index (default: -1, meaning all elements)

        Returns:
            List[Any]: List values
        """
        key = f"list:{list_name}"
        return self.lrange(key, start, end)

    def increment_counter(self, counter_name: str, amount: int = 1) -> int:
        """
        Increment counter.

        Args:
            counter_name: Counter name
            amount: Amount to increment by (default: 1)

        Returns:
            int: New counter value
        """
        key = f"counter:{counter_name}"
        return self.incr(key, amount)

    def get_counter(self, counter_name: str) -> int:
        """
        Get counter value.

        Args:
            counter_name: Counter name

        Returns:
            int: Counter value or 0 if not found
        """
        key = f"counter:{counter_name}"
        value = self.get(key)
        return int(value) if value is not None else 0

    def set_hash_field(self, hash_name: str, field: str, value: Any) -> int:
        """
        Set hash field.

        Args:
            hash_name: Hash name
            field: Field name
            value: Field value

        Returns:
            int: 1 if field is new, 0 if field existed
        """
        key = f"hash:{hash_name}"
        return self.hset(key, field, value)

    def get_hash_field(self, hash_name: str, field: str, default: Any = None) -> Any:
        """
        Get hash field.

        Args:
            hash_name: Hash name
            field: Field name
            default: Default value if field doesn't exist

        Returns:
            Any: Field value or default
        """
        key = f"hash:{hash_name}"
        return self.hget(key, field, default)

    def get_hash(self, hash_name: str) -> dict[str, Any]:
        """
        Get all hash fields.

        Args:
            hash_name: Hash name

        Returns:
            Dict[str, Any]: Hash fields and values
        """
        key = f"hash:{hash_name}"
        return self.hgetall(key)

    # Methods for working with active tag cloud
    def set_active_tagcloud(
        self, tagcloud_id: str, tagcloud_data: dict[str, Any]
    ) -> bool:
        """
        Устанавливает активное облако тегов.

        Args:
            tagcloud_id: ID облака тегов
            tagcloud_data: Данные облака тегов (название, статус и т.д.)

        Returns:
            bool: True если успешно
        """
        # Сохраняем ID активного облака тегов
        self.set("active_tagcloud_id", tagcloud_id)

        # Сохраняем данные облака тегов
        key = f"tagcloud:{tagcloud_id}"
        return self.set(key, tagcloud_data)

    def get_active_tagcloud_id(self) -> Optional[str]:
        """
        Получает ID активного облака тегов.

        Returns:
            Optional[str]: ID активного облака тегов или None, если нет активного облака
        """
        return self.get("active_tagcloud_id")

    def get_active_tagcloud_data(self) -> Optional[dict[str, Any]]:
        """
        Получает данные активного облака тегов.

        Returns:
            Optional[Dict[str, Any]]: Данные активного облака тегов или None, если нет активного облака
        """
        tagcloud_id = self.get_active_tagcloud_id()
        if not tagcloud_id:
            return None

        key = f"tagcloud:{tagcloud_id}"
        return self.get(key)

    def clear_active_tagcloud(self) -> bool:
        """
        Очищает активное облако тегов.

        Returns:
            bool: True если успешно
        """
        # Получаем ID активного облака тегов
        tagcloud_id = self.get_active_tagcloud_id()
        if tagcloud_id:
            # Удаляем данные облака тегов
            key = f"tagcloud:{tagcloud_id}"
            self.delete(key)

        # Удаляем ID активного облака тегов
        return bool(self.delete("active_tagcloud_id"))
