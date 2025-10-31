from django.contrib import admin
from .models import MembershipType, Membership


@admin.register(MembershipType)
class MembershipTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'visits_limit', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('client', 'membership_type', 'start_date', 'end_date', 'status', 'visits_remaining')
    list_filter = ('status', 'membership_type')
    search_fields = ('client__profile__user__username', 'client__profile__user__email')
    date_hierarchy = 'purchased_at'
