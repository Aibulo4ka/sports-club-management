"""
Сериализаторы для приложения платежей
"""

from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal

from .models import Payment, PaymentStatus, PaymentMethod


class PaymentListSerializer(serializers.ModelSerializer):
    """
    Упрощенный сериализатор для списка платежей
    Показывает основную информацию без вложенных деталей
    """
    client_name = serializers.CharField(source='client.profile.user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'client', 'client_name', 'amount', 'status', 'status_display',
            'payment_method', 'method_display', 'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'client_name', 'status_display', 'method_display',
                           'created_at', 'completed_at']


class PaymentSerializer(serializers.ModelSerializer):
    """
    Полный сериализатор для детальной информации о платеже
    Включает вложенную информацию о клиенте и абонементе
    """
    client_name = serializers.CharField(source='client.profile.user.get_full_name', read_only=True)
    client_email = serializers.EmailField(source='client.profile.user.email', read_only=True)
    client_phone = serializers.CharField(source='client.profile.phone', read_only=True)

    membership_type_name = serializers.CharField(
        source='membership.membership_type.name',
        read_only=True,
        allow_null=True
    )

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'client', 'client_name', 'client_email', 'client_phone',
            'membership', 'membership_type_name', 'amount',
            'status', 'status_display', 'payment_method', 'method_display',
            'transaction_id', 'payment_url', 'created_at', 'completed_at', 'notes'
        ]
        read_only_fields = [
            'id', 'client_name', 'client_email', 'client_phone',
            'membership_type_name', 'status_display', 'method_display',
            'created_at', 'completed_at'
        ]


class PaymentCreateSerializer(serializers.Serializer):
    """
    Сериализатор для создания нового платежа
    Используется для инициации процесса оплаты (позже интегрируем с YooKassa)
    """
    membership_type_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices,
        default=PaymentMethod.YOOKASSA
    )

    def validate_membership_type_id(self, value):
        """Проверяет, что тип абонемента существует и активен"""
        from apps.memberships.models import MembershipType

        try:
            membership_type = MembershipType.objects.get(id=value)
            if not membership_type.is_active:
                raise serializers.ValidationError("Этот тип абонемента неактивен")
        except MembershipType.DoesNotExist:
            raise serializers.ValidationError("Тип абонемента с таким ID не найден")

        return value

    def validate(self, attrs):
        """Дополнительная валидация"""
        # Получаем клиента из контекста (должно быть установлено во view)
        client = self.context.get('client')
        if not client:
            raise serializers.ValidationError("Клиент не указан в контексте")

        return attrs

    def create(self, validated_data):
        """
        Создает запись платежа
        Позже здесь будет интеграция с YooKassa API
        """
        from apps.memberships.models import MembershipType, Membership
        from apps.memberships.pricing import PriceCalculator, get_best_discount_strategy
        from datetime import timedelta

        client = self.context['client']
        membership_type = MembershipType.objects.get(id=validated_data['membership_type_id'])

        # Рассчитываем цену со скидкой используя паттерн Strategy
        strategy = get_best_discount_strategy(
            is_student=client.is_student,
            duration_days=membership_type.duration_days
        )
        calculator = PriceCalculator(strategy)
        price_info = calculator.calculate_final_price(
            base_price=membership_type.price,
            duration_days=membership_type.duration_days,
            is_student=client.is_student
        )

        final_price = price_info['final_price']

        # Создаем абонемент (неактивный до завершения оплаты)
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=membership_type.duration_days)

        from apps.memberships.models import MembershipStatus
        membership = Membership.objects.create(
            client=client,
            membership_type=membership_type,
            start_date=start_date,
            end_date=end_date,
            status=MembershipStatus.SUSPENDED,  # Активируется после оплаты
            visits_remaining=membership_type.visits_limit
        )

        # Создаем платеж
        payment = Payment.objects.create(
            client=client,
            membership=membership,
            amount=final_price,
            status=PaymentStatus.PENDING,
            payment_method=validated_data['payment_method'],
            notes=f"Скидка применена: {price_info['discount_description']}"
        )

        # TODO: Здесь будет интеграция с YooKassa API для получения payment_url
        # Пока только создаем запись платежа

        return payment

    def to_representation(self, instance):
        """Использует PaymentSerializer для вывода"""
        return PaymentSerializer(instance).data


class PaymentUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления статуса платежа
    Используется внутренне (например, webhook обработчиком)
    """

    class Meta:
        model = Payment
        fields = ['status', 'transaction_id', 'completed_at', 'notes']

    def update(self, instance, validated_data):
        """
        Обновляет платеж и обрабатывает побочные эффекты
        """
        old_status = instance.status
        new_status = validated_data.get('status', old_status)

        # Обновляем платеж
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Если платеж завершен, устанавливаем completed_at и активируем абонемент
        if new_status == PaymentStatus.COMPLETED and old_status != PaymentStatus.COMPLETED:
            instance.completed_at = timezone.now()

            # Активируем абонемент
            if instance.membership:
                from apps.memberships.models import MembershipStatus
                instance.membership.status = MembershipStatus.ACTIVE
                instance.membership.save()

        instance.save()
        return instance
