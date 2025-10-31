from django.contrib import admin
from .models import ClassType, Class


@admin.register(ClassType)
class ClassTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_minutes', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('class_type', 'trainer', 'room', 'datetime', 'max_capacity', 'status')
    list_filter = ('status', 'class_type', 'trainer')
    search_fields = ('class_type__name', 'trainer__profile__user__username')
    date_hierarchy = 'datetime'
