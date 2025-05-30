"""Base service module providing common service functionality."""

import logging
from abc import ABC, ABCMeta
from typing import ClassVar, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SingletonABCMeta(ABCMeta):
    """Metaclass that combines ABCMeta and Singleton pattern."""

    _instances: ClassVar[dict[type, object]] = {}

    def __call__(cls, *args, **kwargs):
        """Create a new instance or return an existing one."""
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class BaseService(ABC, metaclass=SingletonABCMeta):
    """Базовый класс для всех сервисов"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
