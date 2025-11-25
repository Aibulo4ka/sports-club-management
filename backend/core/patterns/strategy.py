"""
Strategy Pattern - DiscountStrategy
Based on Lr3/Strategy.py

Используется для расчета скидок на абонементы.
Позволяет динамически выбирать алгоритм расчета скидки.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone


# Интерфейс стратегии
class DiscountStrategy(ABC):
    """Абстрактная стратегия для расчета скидок"""

    @abstractmethod
    def calculate_discount(self, base_price: Decimal, user: User) -> Decimal:
        """
        Рассчитать сумму скидки для заданной цены и пользователя
        Возвращает: сумму скидки (не процент)
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Получить описание этой скидки"""
        pass


# Конкретные стратегии
class StudentDiscount(DiscountStrategy):
    """Скидка 20% для студентов"""

    def calculate_discount(self, base_price: Decimal, user: User) -> Decimal:
        # Проверяем, является ли пользователь студентом
        if hasattr(user, 'profile') and hasattr(user.profile, 'client_info'):
            if user.profile.client_info.is_student:
                return base_price * Decimal('0.20')  # 20% скидка
        return Decimal('0')

    def get_description(self) -> str:
        return "Студенческая скидка 20%"


class GroupDiscount(DiscountStrategy):
    """Скидка 15% для групповых занятий (от 3 человек)"""

    def calculate_discount(self, base_price: Decimal, user: User) -> Decimal:
        # Скидка для групповых занятий
        if hasattr(user, 'profile') and hasattr(user.profile, 'client_info'):
            group_size = user.profile.client_info.group_members.count()
            if group_size >= 3:
                return base_price * Decimal('0.15')  # 15% скидка
        return Decimal('0')

    def get_description(self) -> str:
        return "Групповая скидка 15% (от 3 человек)"


class LoyaltyDiscount(DiscountStrategy):
    """Скидка 10% для клиентов, зарегистрированных более года"""

    def calculate_discount(self, base_price: Decimal, user: User) -> Decimal:
        # Скидка за лояльность
        membership_duration = timezone.now() - user.date_joined
        if membership_duration > timedelta(days=365):
            return base_price * Decimal('0.10')  # 10% скидка
        return Decimal('0')

    def get_description(self) -> str:
        return "Скидка за лояльность 10% (более года с нами)"


class NoDiscount(DiscountStrategy):
    """Без скидки"""

    def calculate_discount(self, base_price: Decimal, user: User) -> Decimal:
        return Decimal('0')

    def get_description(self) -> str:
        return "Без скидки"


# Контекст
class PriceCalculator:
    """
    Класс-контекст для расчета цен со скидками
    """

    def __init__(self):
        self._strategy: Optional[DiscountStrategy] = None

    def set_strategy(self, strategy: DiscountStrategy) -> None:
        """Установить стратегию скидки"""
        self._strategy = strategy

    def calculate_final_price(self, base_price: Decimal, user: User) -> tuple[Decimal, Decimal, str]:
        """
        Рассчитать финальную цену после применения скидки
        Возвращает: (финальная_цена, сумма_скидки, описание_скидки)
        """
        if not self._strategy:
            self._strategy = NoDiscount()

        discount = self._strategy.calculate_discount(base_price, user)
        final_price = base_price - discount
        description = self._strategy.get_description()

        return final_price, discount, description

    def get_best_discount(self, base_price: Decimal, user: User) -> tuple[Decimal, Decimal, str]:
        """
        Найти и применить лучшую скидку для пользователя
        Возвращает: (финальная_цена, сумма_скидки, описание_скидки)
        """
        strategies = [
            StudentDiscount(),
            GroupDiscount(),
            LoyaltyDiscount()
        ]

        best_discount = Decimal('0')
        best_strategy = NoDiscount()

        for strategy in strategies:
            discount = strategy.calculate_discount(base_price, user)
            if discount > best_discount:
                best_discount = discount
                best_strategy = strategy

        self.set_strategy(best_strategy)
        return self.calculate_final_price(base_price, user)
