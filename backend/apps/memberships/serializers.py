"""
Serializers for memberships app
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import MembershipType, Membership, MembershipStatus
from .pricing import PriceCalculator, get_best_discount_strategy


class MembershipTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for MembershipType model
    """

    class Meta:
        model = MembershipType
        fields = [
            'id', 'name', 'description', 'price', 'duration_days',
            'visits_limit', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MembershipTypeWithPriceSerializer(serializers.ModelSerializer):
    """
    Serializer for MembershipType with calculated price for specific client
    Includes discount calculation based on client's student status
    """
    calculated_price = serializers.SerializerMethodField()

    class Meta:
        model = MembershipType
        fields = [
            'id', 'name', 'description', 'price', 'duration_days',
            'visits_limit', 'is_active', 'calculated_price'
        ]
        read_only_fields = ['id', 'calculated_price']

    def get_calculated_price(self, obj):
        """
        Calculate price with discount applied
        Expects 'client' in context
        """
        client = self.context.get('client')

        if not client:
            return {
                'base_price': str(obj.price),
                'final_price': str(obj.price),
                'discount_amount': '0.00',
                'discount_percentage': '0.00',
                'discount_description': 'Без скидки'
            }

        # Get best discount strategy for this client
        strategy = get_best_discount_strategy(
            is_student=client.is_student,
            duration_days=obj.duration_days
        )

        # Calculate final price
        calculator = PriceCalculator(strategy)
        price_info = calculator.calculate_final_price(
            base_price=obj.price,
            duration_days=obj.duration_days,
            is_student=client.is_student
        )

        # Convert Decimal to string for JSON serialization
        return {
            'base_price': str(price_info['base_price']),
            'final_price': str(price_info['final_price']),
            'discount_amount': str(price_info['discount_amount']),
            'discount_percentage': str(price_info['discount_percentage']),
            'discount_description': price_info['discount_description']
        }


class MembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for Membership model - for list/retrieve
    """
    membership_type_details = MembershipTypeSerializer(source='membership_type', read_only=True)
    client_name = serializers.CharField(source='client.profile.user.get_full_name', read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            'id', 'client', 'client_name', 'membership_type', 'membership_type_details',
            'start_date', 'end_date', 'status', 'visits_remaining',
            'purchased_at', 'is_expired', 'days_remaining'
        ]
        read_only_fields = ['id', 'purchased_at', 'client_name', 'membership_type_details',
                           'is_expired', 'days_remaining']

    def get_is_expired(self, obj):
        """Check if membership is expired"""
        return obj.end_date < timezone.now().date()

    def get_days_remaining(self, obj):
        """Calculate days remaining until expiration"""
        today = timezone.now().date()
        if obj.end_date < today:
            return 0
        delta = obj.end_date - today
        return delta.days


class MembershipCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new membership
    Automatically calculates start_date, end_date, and applies discount
    """
    client_id = serializers.IntegerField()
    membership_type_id = serializers.IntegerField()
    start_date = serializers.DateField(required=False)

    def validate_client_id(self, value):
        """Validate that client exists"""
        from apps.accounts.models import Client

        try:
            Client.objects.get(id=value)
        except Client.DoesNotExist:
            raise serializers.ValidationError("Клиент с таким ID не найден")

        return value

    def validate_membership_type_id(self, value):
        """Validate that membership type exists and is active"""
        try:
            membership_type = MembershipType.objects.get(id=value)
            if not membership_type.is_active:
                raise serializers.ValidationError("Этот тип абонемента неактивен")
        except MembershipType.DoesNotExist:
            raise serializers.ValidationError("Тип абонемента с таким ID не найден")

        return value

    def create(self, validated_data):
        """Create membership with automatic date calculation"""
        from apps.accounts.models import Client

        client = Client.objects.get(id=validated_data['client_id'])
        membership_type = MembershipType.objects.get(id=validated_data['membership_type_id'])

        # Set start date (default to today if not provided)
        start_date = validated_data.get('start_date', timezone.now().date())

        # Calculate end date based on duration
        end_date = start_date + timedelta(days=membership_type.duration_days)

        # Create membership
        membership = Membership.objects.create(
            client=client,
            membership_type=membership_type,
            start_date=start_date,
            end_date=end_date,
            status=MembershipStatus.ACTIVE,
            visits_remaining=membership_type.visits_limit
        )

        return membership

    def to_representation(self, instance):
        """Use MembershipSerializer for output"""
        return MembershipSerializer(instance).data


class MembershipUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating membership
    Only status and visits_remaining can be updated
    """

    class Meta:
        model = Membership
        fields = ['status', 'visits_remaining']

    def validate_visits_remaining(self, value):
        """Ensure visits_remaining is not negative"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Количество посещений не может быть отрицательным")
        return value


class PriceCalculationSerializer(serializers.Serializer):
    """
    Serializer for calculating membership price with discount
    Used as a utility endpoint to preview pricing
    """
    membership_type_id = serializers.IntegerField()
    client_id = serializers.IntegerField()

    def validate(self, attrs):
        """Validate that both membership type and client exist"""
        from apps.accounts.models import Client

        try:
            MembershipType.objects.get(id=attrs['membership_type_id'])
        except MembershipType.DoesNotExist:
            raise serializers.ValidationError("Тип абонемента не найден")

        try:
            Client.objects.get(id=attrs['client_id'])
        except Client.DoesNotExist:
            raise serializers.ValidationError("Клиент не найден")

        return attrs

    def calculate(self):
        """Calculate and return pricing information"""
        from apps.accounts.models import Client

        client = Client.objects.get(id=self.validated_data['client_id'])
        membership_type = MembershipType.objects.get(id=self.validated_data['membership_type_id'])

        # Get best discount strategy
        strategy = get_best_discount_strategy(
            is_student=client.is_student,
            duration_days=membership_type.duration_days
        )

        # Calculate price
        calculator = PriceCalculator(strategy)
        price_info = calculator.calculate_final_price(
            base_price=membership_type.price,
            duration_days=membership_type.duration_days,
            is_student=client.is_student
        )

        return {
            'membership_type': MembershipTypeSerializer(membership_type).data,
            'client': {
                'id': client.id,
                'name': client.profile.user.get_full_name(),
                'is_student': client.is_student
            },
            'pricing': {
                'base_price': str(price_info['base_price']),
                'discount_amount': str(price_info['discount_amount']),
                'discount_percentage': str(price_info['discount_percentage']),
                'final_price': str(price_info['final_price']),
                'discount_description': price_info['discount_description']
            }
        }
