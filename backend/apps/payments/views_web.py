"""
Веб-представления для приложения платежей (Django шаблоны)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Payment, PaymentStatus
from apps.accounts.models import Client


@login_required
def my_payments_view(request):
    """
    Отображает историю платежей пользователя
    """
    try:
        client = request.user.profile.client_info
    except (AttributeError, Client.DoesNotExist):
        messages.error(request, 'Вы не являетесь клиентом клуба')
        return redirect('accounts_web:home')

    # Получаем все платежи клиента
    payments = Payment.objects.filter(
        client=client
    ).select_related(
        'membership__membership_type'
    ).order_by('-created_at')

    # Фильтрация по статусу (опционально)
    status_filter = request.GET.get('status')
    if status_filter and status_filter in dict(PaymentStatus.choices):
        payments = payments.filter(status=status_filter)

    # Разделяем на завершенные и незавершенные
    completed_payments = payments.filter(status=PaymentStatus.COMPLETED)
    pending_payments = payments.filter(status=PaymentStatus.PENDING)
    failed_payments = payments.filter(status__in=[PaymentStatus.FAILED, PaymentStatus.REFUNDED])

    return render(request, 'payments/my_payments.html', {
        'completed_payments': completed_payments,
        'pending_payments': pending_payments,
        'failed_payments': failed_payments,
        'all_payments': payments,
        'status_filter': status_filter,
        'payment_statuses': PaymentStatus.choices
    })


@login_required
def payment_success_view(request, payment_id):
    """
    Страница успешной оплаты
    Отображается после успешного завершения платежа через YooKassa
    """
    payment = get_object_or_404(Payment, id=payment_id)

    # Проверяем, что платеж принадлежит текущему пользователю
    try:
        client = request.user.profile.client_info
        if payment.client != client:
            messages.error(request, 'Доступ запрещён')
            return redirect('payments_web:my_payments')
    except (AttributeError, Client.DoesNotExist):
        messages.error(request, 'Вы не являетесь клиентом клуба')
        return redirect('accounts_web:home')

    # Проверяем статус платежа
    if payment.status != PaymentStatus.COMPLETED:
        messages.warning(
            request,
            'Этот платеж ещё не завершён. Проверьте статус позже.'
        )

    return render(request, 'payments/payment_success.html', {
        'payment': payment,
        'membership': payment.membership
    })


@login_required
def payment_failed_view(request, payment_id):
    """
    Страница неудачной оплаты
    Отображается если платеж не прошёл или был отклонён
    """
    payment = get_object_or_404(Payment, id=payment_id)

    # Проверяем, что платеж принадлежит текущему пользователю
    try:
        client = request.user.profile.client_info
        if payment.client != client:
            messages.error(request, 'Доступ запрещён')
            return redirect('payments_web:my_payments')
    except (AttributeError, Client.DoesNotExist):
        messages.error(request, 'Вы не являетесь клиентом клуба')
        return redirect('accounts_web:home')

    return render(request, 'payments/payment_failed.html', {
        'payment': payment,
        'membership': payment.membership
    })
