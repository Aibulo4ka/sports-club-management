from django.contrib import admin
from .models import Booking, Visit


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('client', 'class_instance', 'booking_date', 'status')
    list_filter = ('status', 'booking_date')
    search_fields = ('client__profile__user__username',)
    date_hierarchy = 'booking_date'


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('booking', 'checked_in_at', 'checked_by')
    search_fields = ('booking__client__profile__user__username',)
    date_hierarchy = 'checked_in_at'
