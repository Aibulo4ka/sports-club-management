"""
Management command для создания тестового клиента с абонементом
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.accounts.models import Profile, Client, UserRole
from apps.memberships.models import MembershipType, Membership, MembershipStatus
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Создаёт тестового клиента с активным абонементом'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='testclient',
            help='Имя пользователя (по умолчанию: testclient)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='testclient@sportclub.com',
            help='Email (по умолчанию: testclient@sportclub.com)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='test123',
            help='Пароль (по умолчанию: test123)'
        )
        parser.add_argument(
            '--phone',
            type=str,
            default='+79991234567',
            help='Телефон (по умолчанию: +79991234567)'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        phone = options['phone']

        # Проверяем, существует ли пользователь
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'⚠️  Пользователь {username} уже существует!')
            )
            user = User.objects.get(username=username)
        else:
            # Создаём пользователя
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name='Тест',
                last_name='Клиентов'
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Создан пользователь: {username}')
            )

        # Создаём или получаем профиль
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'role': UserRole.CLIENT,
                'phone': phone
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Создан профиль с ролью CLIENT')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'ℹ️  Профиль уже существует')
            )

        # Проверяем, что создался Client (благодаря signal)
        try:
            client = profile.client_info
            self.stdout.write(
                self.style.SUCCESS(f'✅ Client запись существует')
            )
        except Client.DoesNotExist:
            # Если по какой-то причине не создался, создаём вручную
            client = Client.objects.create(profile=profile)
            self.stdout.write(
                self.style.WARNING(f'⚠️  Client создан вручную (signal не сработал)')
            )

        # Получаем первый активный тип абонемента
        membership_type = MembershipType.objects.filter(is_active=True).first()

        if not membership_type:
            self.stdout.write(
                self.style.ERROR('❌ Нет активных типов абонементов! Запустите create_test_data.')
            )
            return

        # Проверяем, есть ли уже активный абонемент
        existing_membership = Membership.objects.filter(
            client=client,
            status=MembershipStatus.ACTIVE
        ).first()

        if existing_membership:
            self.stdout.write(
                self.style.WARNING(f'ℹ️  У клиента уже есть активный абонемент: {existing_membership.membership_type.name}')
            )
            self.stdout.write(
                self.style.WARNING(f'    Посещений осталось: {existing_membership.visits_remaining if existing_membership.visits_remaining else "Безлимит"}')
            )
        else:
            # Создаём активный абонемент на 30 дней
            membership = Membership.objects.create(
                client=client,
                membership_type=membership_type,
                status=MembershipStatus.ACTIVE,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=30),
                visits_remaining=membership_type.visits_limit
            )

            self.stdout.write(
                self.style.SUCCESS(f'✅ Создан абонемент: {membership_type.name}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'   Действует: {membership.start_date} - {membership.end_date}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'   Посещений: {membership.visits_remaining if membership.visits_remaining else "Безлимит"}')
            )

        # Итоговая информация
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('🎉 ГОТОВО! Тестовый клиент создан'))
        self.stdout.write('='*50)
        self.stdout.write(f'📧 Email:    {email}')
        self.stdout.write(f'👤 Логин:    {username}')
        self.stdout.write(f'🔑 Пароль:   {password}')
        self.stdout.write(f'📱 Телефон:  {phone}')
        self.stdout.write('='*50)
        self.stdout.write('\n💡 Теперь можно:')
        self.stdout.write('   1. Войти на сайт: http://localhost:8000/login/')
        self.stdout.write('   2. Перейти к расписанию: http://localhost:8000/classes/schedule/')
        self.stdout.write('   3. Забронировать занятие')
        self.stdout.write('='*50 + '\n')
