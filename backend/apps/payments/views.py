"""
Views (ViewSets) для платежей
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction

from .models import Payment, PaymentStatus
from .serializers import (
    PaymentSerializer,
    PaymentListSerializer,
    PaymentCreateSerializer,
    PaymentUpdateSerializer
)
from apps.accounts.models import Client


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления платежами

    Endpoints:
    - GET /api/payments/ - список всех платежей (для админа)
    - GET /api/payments/my/ - мои платежи (для клиента)
    - GET /api/payments/{id}/ - детали платежа
    - POST /api/payments/ - создать платеж
    """
    queryset = Payment.objects.select_related(
        'client__profile__user',
        'membership__membership_type'
    ).all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """
        Выбираем сериализатор в зависимости от действия
        """
        if self.action == 'list':
            return PaymentListSerializer
        elif self.action == 'create':
            return PaymentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PaymentUpdateSerializer
        return PaymentSerializer

    def get_queryset(self):
        """
        Фильтруем queryset в зависимости от роли пользователя
        Клиенты видят только свои платежи
        """
        user = self.request.user

        # Если пользователь - клиент, показываем только его платежи
        if hasattr(user, 'profile') and user.profile.role == 'CLIENT':
            try:
                client = user.profile.client_info
                return self.queryset.filter(client=client)
            except Client.DoesNotExist:
                return self.queryset.none()

        # Для админов и тренеров - все платежи
        return self.queryset

    @action(detail=False, methods=['get'])
    def my(self, request):
        """
        Получить мои платежи (для текущего клиента)
        GET /api/payments/my/

        Query params:
        - status: фильтр по статусу (PENDING, COMPLETED, FAILED, REFUNDED)
        """
        if not hasattr(request.user, 'profile'):
            return Response(
                {'error': 'Пользователь не имеет профиля'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = request.user.profile.client_info
        except Client.DoesNotExist:
            return Response(
                {'error': 'Клиент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Фильтруем по статусу если указан в query params
        payments = self.queryset.filter(client=client)
        payment_status = request.query_params.get('status')
        if payment_status:
            payments = payments.filter(status=payment_status)

        # Сортировка: последние первыми
        payments = payments.order_by('-created_at')

        serializer = PaymentListSerializer(payments, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Создать новый платеж
        POST /api/payments/

        Body:
        {
            "membership_type_id": 1,
            "payment_method": "YOOKASSA"  // опционально
        }

        Создаёт платеж и неактивный абонемент.
        Позже здесь будет интеграция с YooKassa для получения payment_url
        """
        # Получаем клиента из профиля текущего пользователя
        if not hasattr(request.user, 'profile'):
            return Response(
                {'error': 'Пользователь не имеет профиля'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = request.user.profile.client_info
        except Client.DoesNotExist:
            return Response(
                {'error': 'Клиент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Создаём платеж через сериализатор (клиент передаётся через контекст)
        serializer = PaymentCreateSerializer(
            data=request.data,
            context={'client': client, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()

        # TODO: Здесь будет интеграция с YooKassa API
        # 1. Создать платёж в YooKassa
        # 2. Получить payment_url
        # 3. Сохранить transaction_id и payment_url
        # 4. Вернуть URL для редиректа клиента

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        """
        Проверить статус платежа
        GET /api/payments/{id}/status_check/

        Проверяет статус в YooKassa и обновляет в БД
        """
        payment = self.get_object()

        # Проверяем доступ
        if hasattr(request.user, 'profile'):
            try:
                client = request.user.profile.client_info_info
                if payment.client != client and request.user.profile.role != 'ADMIN':
                    return Response(
                        {'error': 'Доступ запрещён'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Client.DoesNotExist:
                pass

        # Проверяем статус в платёжной системе (YooKassa или mock)
        if payment.payment_method == 'YOOKASSA' and payment.transaction_id:
            try:
                from .payment_service_factory import get_payment_service

                payment_service = get_payment_service()
                yookassa_status = payment_service.check_payment_status(payment.transaction_id)

                # Обновляем статус если изменился
                if yookassa_status['status'] == 'succeeded' and yookassa_status['paid']:
                    if payment.status != PaymentStatus.COMPLETED:
                        payment.status = PaymentStatus.COMPLETED
                        payment.completed_at = timezone.now()

                        # Активируем абонемент
                        if payment.membership:
                            from apps.memberships.models import MembershipStatus
                            payment.membership.status = MembershipStatus.ACTIVE
                            payment.membership.save()

                        payment.save()

                elif yookassa_status['status'] == 'canceled':
                    payment.status = PaymentStatus.FAILED
                    payment.save()

            except Exception as e:
                return Response(
                    {'error': f'Ошибка проверки статуса: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        serializer = PaymentSerializer(payment)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[])
    def webhook(self, request):
        """
        Webhook endpoint для YooKassa
        POST /api/payments/webhook/

        YooKassa отправляет сюда уведомления об изменении статуса платежа

        События:
        - payment.waiting_for_capture - ожидает подтверждения
        - payment.succeeded - успешно оплачен
        - payment.canceled - отменён
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            from .payment_service_factory import get_payment_service
            from apps.memberships.models import MembershipStatus

            # Обрабатываем webhook (YooKassa или mock)
            payment_service = get_payment_service()
            webhook_data = payment_service.process_webhook(request.data)

            logger.info(f"Webhook received: {webhook_data}")

            # Извлекаем metadata с нашим payment_id
            metadata = webhook_data.get('metadata', {})
            internal_payment_id = metadata.get('payment_id')

            if not internal_payment_id:
                logger.error("Webhook не содержит payment_id в metadata")
                return Response(
                    {'error': 'payment_id не найден в metadata'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Находим платёж в нашей БД
            try:
                payment = Payment.objects.select_related('membership', 'client__profile__user').get(
                    id=internal_payment_id
                )
            except Payment.DoesNotExist:
                logger.error(f"Payment {internal_payment_id} не найден в БД")
                return Response(
                    {'error': 'Платёж не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Обновляем статус в зависимости от события
            yookassa_status = webhook_data['status']
            is_paid = webhook_data.get('paid', False)

            with transaction.atomic():
                if yookassa_status == 'succeeded' and is_paid:
                    # Платёж успешно завершён
                    payment.status = PaymentStatus.COMPLETED
                    payment.completed_at = timezone.now()
                    payment.notes += f"\n[Webhook] Оплачено {timezone.now()}"

                    # Активируем абонемент
                    if payment.membership:
                        payment.membership.status = MembershipStatus.ACTIVE
                        payment.membership.save()
                        logger.info(f"Membership {payment.membership.id} activated")

                    # Отправляем email уведомление об успешной оплате
                    try:
                        from apps.core.email_utils import send_payment_success_email
                        send_payment_success_email(payment)
                        logger.info(f"Payment success email sent to {payment.client.profile.user.email}")
                    except Exception as email_error:
                        logger.error(f"Failed to send payment email: {str(email_error)}")

                elif yookassa_status == 'canceled':
                    # Платёж отменён
                    payment.status = PaymentStatus.FAILED
                    payment.notes += f"\n[Webhook] Отменён {timezone.now()}"

                    # Отменяем абонемент
                    if payment.membership:
                        payment.membership.status = MembershipStatus.SUSPENDED
                        payment.membership.save()

                payment.save()

            logger.info(f"Payment {payment.id} updated: status={payment.status}")

            return Response({'status': 'success'}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
