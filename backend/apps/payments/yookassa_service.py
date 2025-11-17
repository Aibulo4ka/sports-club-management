"""
Сервис для работы с ЮKassa API
Документация: https://yookassa.ru/developers/api
"""

import logging
import uuid
from decimal import Decimal
from typing import Dict, Optional
from yookassa import Configuration, Payment as YooPayment
from django.conf import settings

logger = logging.getLogger(__name__)


class YooKassaService:
    """
    Сервис для работы с ЮKassa API

    Основные методы:
    - create_payment(): создать платеж и получить URL для оплаты
    - check_payment_status(): проверить статус платежа
    - process_webhook(): обработать уведомление от ЮKassa
    """

    def __init__(self):
        """
        Инициализация конфигурации ЮKassa
        """
        # Настройка аутентификации
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

        logger.info(f"YooKassa configured with shop_id: {settings.YOOKASSA_SHOP_ID[:5]}***")

    def create_payment(
        self,
        amount: Decimal,
        description: str,
        client_email: str,
        return_url: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Создаёт платёж в ЮKassa и возвращает URL для оплаты

        Args:
            amount: Сумма платежа в рублях
            description: Описание платежа
            client_email: Email клиента для отправки чека
            return_url: URL для возврата после оплаты
            metadata: Дополнительные данные (например, payment_id из нашей БД)

        Returns:
            Dict с полями:
            - payment_id: ID платежа в ЮKassa
            - confirmation_url: URL для редиректа клиента
            - status: Статус платежа

        Raises:
            Exception: При ошибке создания платежа
        """
        try:
            # Генерируем уникальный idempotence_key для защиты от дублирования
            idempotence_key = str(uuid.uuid4())

            # Создаём платёж
            payment = YooPayment.create({
                "amount": {
                    "value": str(amount),  # ЮKassa требует строку
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url
                },
                "capture": True,  # Автоматическое списание после подтверждения
                "description": description,
                "receipt": {
                    "customer": {
                        "email": client_email
                    },
                    "items": [
                        {
                            "description": description,
                            "quantity": "1.00",
                            "amount": {
                                "value": str(amount),
                                "currency": "RUB"
                            },
                            "vat_code": 1  # НДС не облагается
                        }
                    ]
                },
                "metadata": metadata or {}
            }, idempotence_key)

            logger.info(f"Payment created in YooKassa: {payment.id}, status: {payment.status}")

            return {
                "payment_id": payment.id,
                "confirmation_url": payment.confirmation.confirmation_url,
                "status": payment.status,
                "test": payment.test  # True для тестовых платежей
            }

        except Exception as e:
            logger.error(f"Error creating payment in YooKassa: {str(e)}")
            raise Exception(f"Ошибка создания платежа: {str(e)}")

    def check_payment_status(self, payment_id: str) -> Dict:
        """
        Проверяет статус платежа в ЮKassa

        Args:
            payment_id: ID платежа в ЮKassa

        Returns:
            Dict с полями:
            - status: Статус платежа (pending, waiting_for_capture, succeeded, canceled)
            - paid: Оплачен ли платёж
            - amount: Сумма платежа
            - metadata: Метаданные

        Raises:
            Exception: При ошибке проверки статуса
        """
        try:
            payment = YooPayment.find_one(payment_id)

            logger.info(f"Payment {payment_id} status: {payment.status}")

            return {
                "status": payment.status,
                "paid": payment.paid,
                "amount": Decimal(payment.amount.value),
                "created_at": payment.created_at,
                "metadata": payment.metadata
            }

        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}")
            raise Exception(f"Ошибка проверки статуса платежа: {str(e)}")

    def process_webhook(self, webhook_data: Dict) -> Dict:
        """
        Обрабатывает webhook уведомление от ЮKassa

        Webhook отправляется когда статус платежа изменяется:
        - payment.waiting_for_capture - ожидает подтверждения
        - payment.succeeded - успешно оплачен
        - payment.canceled - отменён

        Args:
            webhook_data: JSON данные от ЮKassa

        Returns:
            Dict с информацией о платеже:
            - payment_id: ID платежа в ЮKassa
            - status: Новый статус
            - metadata: Метаданные (наш внутренний payment_id)
        """
        try:
            event_type = webhook_data.get('event')
            payment_object = webhook_data.get('object')

            if not payment_object:
                raise ValueError("Webhook не содержит объект payment")

            payment_id = payment_object.get('id')
            status = payment_object.get('status')
            paid = payment_object.get('paid', False)
            metadata = payment_object.get('metadata', {})
            amount = payment_object.get('amount', {}).get('value')

            logger.info(
                f"Webhook received: event={event_type}, "
                f"payment_id={payment_id}, status={status}, paid={paid}"
            )

            return {
                "payment_id": payment_id,
                "status": status,
                "paid": paid,
                "amount": Decimal(amount) if amount else None,
                "metadata": metadata,
                "event_type": event_type
            }

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            raise Exception(f"Ошибка обработки webhook: {str(e)}")

    def cancel_payment(self, payment_id: str) -> bool:
        """
        Отменяет платёж в ЮKassa

        Args:
            payment_id: ID платежа в ЮKassa

        Returns:
            bool: True если успешно отменён
        """
        try:
            idempotence_key = str(uuid.uuid4())

            # Отменяем платёж
            YooPayment.cancel(payment_id, idempotence_key)

            logger.info(f"Payment {payment_id} cancelled")
            return True

        except Exception as e:
            logger.error(f"Error cancelling payment: {str(e)}")
            return False

    def create_refund(self, payment_id: str, amount: Decimal, reason: str = "") -> Dict:
        """
        Создаёт возврат средств

        Args:
            payment_id: ID платежа в ЮKassa
            amount: Сумма возврата
            reason: Причина возврата

        Returns:
            Dict с информацией о возврате
        """
        try:
            from yookassa import Refund

            idempotence_key = str(uuid.uuid4())

            refund = Refund.create({
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "payment_id": payment_id,
                "description": reason or "Возврат средств"
            }, idempotence_key)

            logger.info(f"Refund created: {refund.id} for payment {payment_id}")

            return {
                "refund_id": refund.id,
                "status": refund.status,
                "amount": Decimal(refund.amount.value)
            }

        except Exception as e:
            logger.error(f"Error creating refund: {str(e)}")
            raise Exception(f"Ошибка создания возврата: {str(e)}")


# Singleton instance
_yookassa_service = None


def get_yookassa_service() -> YooKassaService:
    """
    Возвращает singleton instance YooKassaService
    """
    global _yookassa_service
    if _yookassa_service is None:
        _yookassa_service = YooKassaService()
    return _yookassa_service
