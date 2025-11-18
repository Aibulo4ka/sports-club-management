"""
Payment Service Factory - фабрика для выбора платёжного сервиса

Автоматически выбирает между реальной интеграцией YooKassa и mock-сервисом
в зависимости от настроек проекта.
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def get_payment_service():
    """
    Фабричный метод для получения платёжного сервиса

    Логика выбора:
    1. Если USE_MOCK_PAYMENTS = True в настройках -> MockPaymentService
    2. Если есть YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY -> YooKassaService
    3. Иначе -> MockPaymentService (с предупреждением)

    Returns:
        Экземпляр платёжного сервиса (YooKassaService или MockPaymentService)
    """

    # Проверяем, включен ли mock-режим явно
    use_mock = getattr(settings, 'USE_MOCK_PAYMENTS', False)

    if use_mock:
        logger.info("🎭 Using MockPaymentService (configured via USE_MOCK_PAYMENTS)")
        from .mock_payment_service import get_mock_payment_service
        return get_mock_payment_service()

    # Проверяем наличие ключей YooKassa
    has_yookassa_keys = (
        hasattr(settings, 'YOOKASSA_SHOP_ID') and
        hasattr(settings, 'YOOKASSA_SECRET_KEY') and
        settings.YOOKASSA_SHOP_ID and
        settings.YOOKASSA_SECRET_KEY
    )

    if has_yookassa_keys:
        # Пробуем использовать реальный YooKassa
        try:
            logger.info("💳 Using YooKassaService (real payment gateway)")
            from .yookassa_service import get_yookassa_service
            return get_yookassa_service()
        except Exception as e:
            logger.error(
                f"⚠️  Failed to initialize YooKassaService: {e}. "
                f"Falling back to MockPaymentService"
            )
            from .mock_payment_service import get_mock_payment_service
            return get_mock_payment_service()
    else:
        # Ключи не настроены - используем mock
        logger.warning(
            "⚠️  YooKassa credentials not configured. Using MockPaymentService. "
            "Set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY for real payments."
        )
        from .mock_payment_service import get_mock_payment_service
        return get_mock_payment_service()


# Удобный alias для использования в коде
PaymentService = get_payment_service
