"""
Mock Payment Service - заглушка для демонстрации платежной системы

Используется для демо-режима когда реальная интеграция с YooKassa недоступна.
Имитирует все основные операции платёжной системы.

⚠️  ЭТО ЗАГЛУШКА ДЛЯ ДЕМОНСТРАЦИИ!
Для production используйте YooKassaService с реальными ключами API.
"""

import logging
import uuid
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MockPaymentService:
    """
    Mock-сервис для имитации работы платёжной системы

    Полностью совместим с интерфейсом YooKassaService,
    но не выполняет реальных платежей.
    """

    def __init__(self):
        """Инициализация mock-сервиса"""
        logger.info("🎭 MockPaymentService initialized (DEMO MODE)")
        # Храним "платежи" в памяти для имитации
        self._payments = {}

    def create_payment(
        self,
        amount: Decimal,
        description: str,
        client_email: str,
        return_url: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Имитирует создание платежа

        Args:
            amount: Сумма платежа в рублях
            description: Описание платежа
            client_email: Email клиента
            return_url: URL для возврата
            metadata: Метаданные

        Returns:
            Dict с информацией о "платеже"
        """
        # Генерируем уникальный ID платежа
        payment_id = f"mock_{uuid.uuid4().hex[:24]}"

        # Создаём mock URL для оплаты (используем готовый return_url без добавления параметров)
        confirmation_url = return_url

        # Сохраняем "платёж"
        self._payments[payment_id] = {
            "id": payment_id,
            "amount": amount,
            "description": description,
            "client_email": client_email,
            "status": "pending",
            "paid": False,
            "created_at": datetime.now(),
            "metadata": metadata or {},
            "test": True  # Всегда тестовый режим
        }

        logger.info(
            f"🎭 MOCK: Payment created - ID: {payment_id}, "
            f"Amount: {amount} RUB, Email: {client_email}"
        )

        return {
            "payment_id": payment_id,
            "confirmation_url": confirmation_url,
            "status": "pending",
            "test": True
        }

    def check_payment_status(self, payment_id: str) -> Dict:
        """
        Имитирует проверку статуса платежа

        В mock-режиме автоматически переводит платёж в статус "succeeded"
        для упрощения демонстрации.

        Args:
            payment_id: ID платежа

        Returns:
            Dict со статусом платежа
        """
        payment = self._payments.get(payment_id)

        if not payment:
            # Если платёж не найден, создаём минимальный объект
            logger.warning(f"🎭 MOCK: Payment {payment_id} not found, creating mock data")
            payment = {
                "id": payment_id,
                "status": "succeeded",
                "paid": True,
                "amount": Decimal("1000.00"),
                "created_at": datetime.now(),
                "metadata": {}
            }
            self._payments[payment_id] = payment

        # Автоматически "подтверждаем" платёж для демо
        if payment["status"] == "pending":
            payment["status"] = "succeeded"
            payment["paid"] = True
            logger.info(f"🎭 MOCK: Auto-confirming payment {payment_id}")

        return {
            "status": payment["status"],
            "paid": payment["paid"],
            "amount": payment["amount"],
            "created_at": payment["created_at"],
            "metadata": payment["metadata"]
        }

    def process_webhook(self, webhook_data: Dict) -> Dict:
        """
        Имитирует обработку webhook от платёжной системы

        Args:
            webhook_data: Данные webhook

        Returns:
            Dict с обработанными данными
        """
        payment_object = webhook_data.get('object', {})
        payment_id = payment_object.get('id', f"mock_{uuid.uuid4().hex[:24]}")

        logger.info(f"🎭 MOCK: Processing webhook for payment {payment_id}")

        # Обновляем статус если платёж существует
        if payment_id in self._payments:
            self._payments[payment_id]["status"] = payment_object.get('status', 'succeeded')
            self._payments[payment_id]["paid"] = True

        return {
            "payment_id": payment_id,
            "status": payment_object.get('status', 'succeeded'),
            "paid": True,
            "amount": Decimal(payment_object.get('amount', {}).get('value', '1000.00')),
            "metadata": payment_object.get('metadata', {}),
            "event_type": webhook_data.get('event', 'payment.succeeded')
        }

    def cancel_payment(self, payment_id: str) -> bool:
        """
        Имитирует отмену платежа

        Args:
            payment_id: ID платежа

        Returns:
            bool: Всегда True для демо
        """
        if payment_id in self._payments:
            self._payments[payment_id]["status"] = "canceled"
            self._payments[payment_id]["paid"] = False

        logger.info(f"🎭 MOCK: Payment {payment_id} cancelled")
        return True

    def create_refund(self, payment_id: str, amount: Decimal, reason: str = "") -> Dict:
        """
        Имитирует создание возврата средств

        Args:
            payment_id: ID платежа
            amount: Сумма возврата
            reason: Причина возврата

        Returns:
            Dict с информацией о возврате
        """
        refund_id = f"mock_refund_{uuid.uuid4().hex[:20]}"

        logger.info(
            f"🎭 MOCK: Refund created - ID: {refund_id}, "
            f"Payment: {payment_id}, Amount: {amount} RUB"
        )

        return {
            "refund_id": refund_id,
            "status": "succeeded",
            "amount": amount
        }


# Singleton instance
_mock_service = None


def get_mock_payment_service() -> MockPaymentService:
    """
    Возвращает singleton instance MockPaymentService
    """
    global _mock_service
    if _mock_service is None:
        _mock_service = MockPaymentService()
    return _mock_service
