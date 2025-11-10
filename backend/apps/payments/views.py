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
                client = user.profile.client
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
            client = request.user.profile.client
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
            client = request.user.profile.client
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

        Проверяет статус в YooKassa (позже)
        """
        payment = self.get_object()

        # Проверяем доступ
        if hasattr(request.user, 'profile'):
            try:
                client = request.user.profile.client
                if payment.client != client and request.user.profile.role != 'ADMIN':
                    return Response(
                        {'error': 'Доступ запрещён'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Client.DoesNotExist:
                pass

        # TODO: Здесь будет проверка статуса в YooKassa API
        # Пока просто возвращаем текущий статус

        serializer = PaymentSerializer(payment)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[])
    def webhook(self, request):
        """
        Webhook endpoint для YooKassa
        POST /api/payments/webhook/

        YooKassa отправляет сюда уведомления об изменении статуса платежа
        """
        # TODO: Реализовать обработку webhook от YooKassa
        # 1. Проверить подпись запроса
        # 2. Извлечь данные о платеже
        # 3. Обновить статус в базе
        # 4. Активировать абонемент если оплата успешна
        # 5. Отправить уведомление клиенту через Observer pattern

        return Response(
            {'message': 'Webhook endpoint (будет реализован позже)'},
            status=status.HTTP_200_OK
        )
