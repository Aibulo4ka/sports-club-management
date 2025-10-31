"""
Admin configuration for accounts app
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile, Client, Trainer


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role')

    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '-'
    get_role.short_description = 'Роль'


# Unregister the default User admin
admin.site.unregister(User)
# Register with custom admin
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'date_of_birth', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'get_phone', 'is_student', 'get_email')
    list_filter = ('is_student',)
    search_fields = ('profile__user__username', 'profile__user__email', 'profile__phone')
    filter_horizontal = ('group_members',)

    def get_full_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username
    get_full_name.short_description = 'ФИО'

    def get_phone(self, obj):
        return obj.profile.phone
    get_phone.short_description = 'Телефон'

    def get_email(self, obj):
        return obj.profile.user.email
    get_email.short_description = 'Email'


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'specialization', 'experience_years', 'is_active')
    list_filter = ('is_active', 'specialization')
    search_fields = ('profile__user__username', 'profile__user__email', 'specialization')
    readonly_fields = ('profile',)

    def get_full_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username
    get_full_name.short_description = 'ФИО'
