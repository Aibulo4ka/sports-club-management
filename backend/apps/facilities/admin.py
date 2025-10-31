from django.contrib import admin
from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'floor', 'is_active')
    list_filter = ('is_active', 'floor')
    search_fields = ('name',)
