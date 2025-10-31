from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'amount', 'status', 'payment_method', 'created_at', 'completed_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('client__profile__user__username', 'transaction_id')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'completed_at')
