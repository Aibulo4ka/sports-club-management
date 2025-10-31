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
    """Abstract strategy for calculating discounts"""

    @abstractmethod
    def calculate_discount(self, base_price: Decimal, user: User) -> Decimal:
        """
        Calculate discount amount for given price and user
        Returns: discount amount (not percentage)
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get description of this discount"""
        pass


# Конкретные стратегии
class StudentDiscount(DiscountStrategy):
    """20% discount for students"""

    def calculate_discount(self, base_price: Decimal, user: User) -> Decimal:
        # Проверяем, является ли пользователь студентом
        if hasattr(user, 'profile') and hasattr(user.profile, 'client_info'):
            if user.profile.client_info.is_student:
                return base_price * Decimal('0.20')  # 20% скидка
        return Decimal('0')

    def get_description(self) -> str:
        return "Студенческая скидка 20%"


class GroupDiscount(DiscountStrategy):
    """15% discount for group members (3+ people)"""

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
    """10% discount for clients registered > 1 year"""

    def calculate_discount(self, base_price: Decimal, user: User) -> Decimal:
        # Скидка за лояльность
        membership_duration = timezone.now() - user.date_joined
        if membership_duration > timedelta(days=365):
            return base_price * Decimal('0.10')  # 10% скидка
        return Decimal('0')

    def get_description(self) -> str:
        return "Скидка за лояльность 10% (более года с нами)"


class NoDiscount(DiscountStrategy):
    """No discount"""

    def calculate_discount(self, base_price: Decimal, user: User) -> Decimal:
        return Decimal('0')

    def get_description(self) -> str:
        return "Без скидки"


# Контекст
class PriceCalculator:
    """
    Context class for calculating prices with discounts
    """

    def __init__(self):
        self._strategy: Optional[DiscountStrategy] = None

    def set_strategy(self, strategy: DiscountStrategy) -> None:
        """Set discount strategy"""
        self._strategy = strategy

    def calculate_final_price(self, base_price: Decimal, user: User) -> tuple[Decimal, Decimal, str]:
        """
        Calculate final price after applying discount
        Returns: (final_price, discount_amount, discount_description)
        """
        if not self._strategy:
            self._strategy = NoDiscount()

        discount = self._strategy.calculate_discount(base_price, user)
        final_price = base_price - discount
        description = self._strategy.get_description()

        return final_price, discount, description

    def get_best_discount(self, base_price: Decimal, user: User) -> tuple[Decimal, Decimal, str]:
        """
        Find and apply the best discount for the user
        Returns: (final_price, discount_amount, discount_description)
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
