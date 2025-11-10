"""
Web views for memberships app (Django templates)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from .models import MembershipType, Membership, MembershipStatus
from .pricing import PriceCalculator, get_best_discount_strategy
from apps.accounts.models import Client


def catalog_view(request):
    """
    Display catalog of membership types with prices
    Shows discounts if user is authenticated
    """
    # Get all active membership types
    membership_types = MembershipType.objects.filter(is_active=True).order_by('price')

    # If user is authenticated and is a client, calculate prices with discounts
    if request.user.is_authenticated:
        try:
            client = request.user.profile.client_info

            # Add calculated price with discount to each membership type
            for membership_type in membership_types:
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

                # Attach calculated price to the membership type object
                membership_type.calculated_price = price_info

        except (AttributeError, Client.DoesNotExist):
            # User is not a client (maybe staff/admin)
            pass

    return render(request, 'memberships/catalog.html', {
        'membership_types': membership_types
    })


@login_required
def my_memberships_view(request):
    """
    Display user's memberships (active and inactive)
    """
    try:
        client = request.user.profile.client_info
    except (AttributeError, Client.DoesNotExist):
        messages.error(request, 'Вы не являетесь клиентом клуба')
        return redirect('accounts_web:home')

    today = timezone.now().date()

    # Get active memberships
    active_memberships = Membership.objects.filter(
        client=client,
        status=MembershipStatus.ACTIVE,
        end_date__gte=today
    ).select_related('membership_type').order_by('-start_date')

    # Add days_remaining to each active membership
    for membership in active_memberships:
        delta = membership.end_date - today
        membership.days_remaining = delta.days

    # Get inactive memberships (expired or suspended)
    inactive_memberships = Membership.objects.filter(
        client=client
    ).exclude(
        status=MembershipStatus.ACTIVE,
        end_date__gte=today
    ).select_related('membership_type').order_by('-purchased_at')

    return render(request, 'memberships/my_memberships.html', {
        'active_memberships': active_memberships,
        'inactive_memberships': inactive_memberships
    })


@login_required
def purchase_view(request, membership_type_id):
    """
    Display purchase page and handle membership purchase
    """
    membership_type = get_object_or_404(MembershipType, id=membership_type_id, is_active=True)

    try:
        client = request.user.profile.client_info
    except (AttributeError, Client.DoesNotExist):
        messages.error(request, 'Вы не являетесь клиентом клуба')
        return redirect('memberships_web:catalog')

    if request.method == 'POST':
        # Создаём платёж через Payment API
        try:
            from apps.payments.models import Payment, PaymentMethod
            from apps.payments.serializers import PaymentCreateSerializer

            # Подготавливаем данные для создания платежа
            payment_data = {
                'membership_type_id': membership_type.id,
                'payment_method': PaymentMethod.YOOKASSA
            }

            # Создаём платёж через сериализатор
            serializer = PaymentCreateSerializer(
                data=payment_data,
                context={'client': client, 'request': request}
            )

            if serializer.is_valid():
                payment = serializer.save()

                # TODO: После интеграции с YooKassa здесь будет редирект на payment_url
                # Пока просто перенаправляем на страницу истории платежей
                messages.info(
                    request,
                    f'Платёж создан! Сумма к оплате: {payment.amount} руб. '
                    f'После оплаты ваш абонемент будет активирован автоматически.'
                )
                return redirect('payments_web:my_payments')
            else:
                messages.error(request, f'Ошибка при создании платежа: {serializer.errors}')
                return redirect('memberships_web:purchase', membership_type_id=membership_type_id)

        except Exception as e:
            messages.error(request, f'Ошибка при создании платежа: {str(e)}')
            return redirect('memberships_web:purchase', membership_type_id=membership_type_id)

    # GET request - display purchase page
    # Calculate price with discount
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

    return render(request, 'memberships/purchase.html', {
        'membership_type': membership_type,
        'client': client,
        'price_info': price_info,
        'today': timezone.now().date()
    })
