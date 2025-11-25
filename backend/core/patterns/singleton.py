"""
Singleton Pattern - CacheManager
Based on Lr3/Singleton.py

Используется для управления кешем (Redis) в приложении.
Гарантирует, что существует только один экземпляр менеджера кеша.
"""

import threading
from django.core.cache import cache
from typing import Optional, Any


class CacheManager:
    """
    Потокобезопасный Singleton для управления кешем приложения
    """
    _instance: Optional['CacheManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Двойная проверка для потокобезопасности
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._cache_prefix = 'sportclub:'
        self._default_timeout = 300  # 5 минут

    def get(self, key: str) -> Any:
        """Получить значение из кеша"""
        return cache.get(f"{self._cache_prefix}{key}")

    def set(self, key: str, value: Any, timeout: int = None) -> None:
        """Установить значение в кеш"""
        timeout = timeout or self._default_timeout
        cache.set(f"{self._cache_prefix}{key}", value, timeout)

    def delete(self, key: str) -> None:
        """Удалить значение из кеша"""
        cache.delete(f"{self._cache_prefix}{key}")

    def clear_pattern(self, pattern: str) -> None:
        """Очистить все ключи, соответствующие шаблону"""
        # Специфично для Redis: удаление всех ключей по шаблону
        from django.core.cache import cache as django_cache
        if hasattr(django_cache, 'delete_pattern'):
            django_cache.delete_pattern(f"{self._cache_prefix}{pattern}*")


# Глобальный экземпляр менеджера кеша
cache_manager = CacheManager()
