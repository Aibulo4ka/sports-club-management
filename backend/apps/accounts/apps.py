from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Аккаунты и пользователи'

    def ready(self):
        """Импортируем signals при запуске приложения"""
        import apps.accounts.signals
