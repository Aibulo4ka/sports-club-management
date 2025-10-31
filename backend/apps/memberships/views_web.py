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
            client = request.user.profile.client

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
        client = request.user.profile.client
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
        client = request.user.profile.client
    except (AttributeError, Client.DoesNotExist):
        messages.error(request, 'Вы не являетесь клиентом клуба')
        return redirect('memberships_web:catalog')

    if request.method == 'POST':
        # Get start date from form (default to today)
        start_date_str = request.POST.get('start_date')

        try:
            if start_date_str:
                from datetime import datetime
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            else:
                start_date = timezone.now().date()

            # Validate start date is not in the past
            if start_date < timezone.now().date():
                messages.error(request, 'Дата начала не может быть в прошлом')
                return redirect('memberships_web:purchase', membership_type_id=membership_type_id)

            # Calculate end date
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

            messages.success(
                request,
                f'Поздравляем! Вы успешно приобрели абонемент "{membership_type.name}". '
                f'Он действителен с {start_date.strftime("%d.m.%Y")} по {end_date.strftime("%d.%m.%Y")}.'
            )

            return redirect('memberships_web:my_memberships')

        except Exception as e:
            messages.error(request, f'Ошибка при покупке абонемента: {str(e)}')
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
