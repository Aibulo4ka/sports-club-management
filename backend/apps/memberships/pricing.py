"""
Discount pricing strategies using Strategy Pattern
This module implements different discount strategies for membership pricing
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional


class DiscountStrategy(ABC):
    """
    Abstract base class for discount strategies (Strategy Pattern)
    """

    @abstractmethod
    def calculate_discount(self, base_price: Decimal, duration_days: int,
                          is_student: bool = False) -> Decimal:
        """
        Calculate discount amount based on strategy

        Args:
            base_price: Original membership price
            duration_days: Duration of membership in days
            is_student: Whether the client is a student

        Returns:
            Discount amount (not percentage)
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of this discount strategy"""
        pass


class NoDiscountStrategy(DiscountStrategy):
    """
    Strategy with no discount applied
    """

    def calculate_discount(self, base_price: Decimal, duration_days: int,
                          is_student: bool = False) -> Decimal:
        return Decimal('0.00')

    def get_description(self) -> str:
        return "Без скидки"


class StudentDiscountStrategy(DiscountStrategy):
    """
    Strategy that applies discount for students
    Default: 15% discount for students
    """

    def __init__(self, discount_percentage: Decimal = Decimal('15.0')):
        self.discount_percentage = discount_percentage

    def calculate_discount(self, base_price: Decimal, duration_days: int,
                          is_student: bool = False) -> Decimal:
        if not is_student:
            return Decimal('0.00')

        discount_amount = base_price * (self.discount_percentage / Decimal('100'))
        return discount_amount.quantize(Decimal('0.01'))

    def get_description(self) -> str:
        return f"Студенческая скидка {self.discount_percentage}%"


class LongTermDiscountStrategy(DiscountStrategy):
    """
    Strategy that applies discount based on membership duration
    - 90+ days (3+ months): 10% discount
    - 180+ days (6+ months): 15% discount
    - 365+ days (1+ year): 20% discount
    """

    def __init__(self):
        self.tiers = [
            (365, Decimal('20.0')),  # 1 year: 20%
            (180, Decimal('15.0')),  # 6 months: 15%
            (90, Decimal('10.0')),   # 3 months: 10%
        ]

    def calculate_discount(self, base_price: Decimal, duration_days: int,
                          is_student: bool = False) -> Decimal:
        discount_percentage = Decimal('0.00')

        # Find applicable discount tier
        for days_threshold, percentage in self.tiers:
            if duration_days >= days_threshold:
                discount_percentage = percentage
                break

        if discount_percentage == Decimal('0.00'):
            return Decimal('0.00')

        discount_amount = base_price * (discount_percentage / Decimal('100'))
        return discount_amount.quantize(Decimal('0.01'))

    def get_description(self) -> str:
        return "Скидка за длительный период (до 20%)"


class CombinedDiscountStrategy(DiscountStrategy):
    """
    Strategy that combines multiple discount strategies
    Takes the maximum discount from all strategies
    """

    def __init__(self, strategies: list[DiscountStrategy]):
        self.strategies = strategies

    def calculate_discount(self, base_price: Decimal, duration_days: int,
                          is_student: bool = False) -> Decimal:
        if not self.strategies:
            return Decimal('0.00')

        # Calculate all possible discounts and take the maximum
        discounts = [
            strategy.calculate_discount(base_price, duration_days, is_student)
            for strategy in self.strategies
        ]

        return max(discounts)

    def get_description(self) -> str:
        strategy_descriptions = [s.get_description() for s in self.strategies]
        return f"Комбинированная ({', '.join(strategy_descriptions)})"


class PriceCalculator:
    """
    Context class for applying discount strategies
    Calculates final price using the selected strategy
    """

    def __init__(self, strategy: Optional[DiscountStrategy] = None):
        self._strategy = strategy or NoDiscountStrategy()

    def set_strategy(self, strategy: DiscountStrategy):
        """Change the discount strategy at runtime"""
        self._strategy = strategy

    def calculate_final_price(self, base_price: Decimal, duration_days: int,
                             is_student: bool = False) -> dict:
        """
        Calculate final price with discount applied

        Returns:
            dict with base_price, discount_amount, final_price, discount_description
        """
        discount_amount = self._strategy.calculate_discount(
            base_price, duration_days, is_student
        )

        final_price = base_price - discount_amount

        # Ensure final price is not negative
        if final_price < Decimal('0.00'):
            final_price = Decimal('0.00')

        return {
            'base_price': base_price,
            'discount_amount': discount_amount,
            'discount_percentage': self._calculate_percentage(base_price, discount_amount),
            'final_price': final_price.quantize(Decimal('0.01')),
            'discount_description': self._strategy.get_description()
        }

    @staticmethod
    def _calculate_percentage(base_price: Decimal, discount_amount: Decimal) -> Decimal:
        """Calculate discount percentage from amounts"""
        if base_price == Decimal('0.00'):
            return Decimal('0.00')

        percentage = (discount_amount / base_price) * Decimal('100')
        return percentage.quantize(Decimal('0.01'))


def get_best_discount_strategy(is_student: bool, duration_days: int) -> DiscountStrategy:
    """
    Factory function to get the best discount strategy for a client

    Args:
        is_student: Whether the client is a student
        duration_days: Duration of the membership

    Returns:
        The most beneficial discount strategy
    """
    strategies = []

    if is_student:
        strategies.append(StudentDiscountStrategy())

    if duration_days >= 90:
        strategies.append(LongTermDiscountStrategy())

    if not strategies:
        return NoDiscountStrategy()

    if len(strategies) == 1:
        return strategies[0]

    # Return combined strategy that picks the best discount
    return CombinedDiscountStrategy(strategies)
