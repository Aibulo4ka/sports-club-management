"""
Тесты для паттернов проектирования в модуле pricing
Тестируемые паттерны:
- Strategy Pattern (DiscountStrategy и его реализации)
- Factory Pattern (get_best_discount_strategy)
"""

import pytest
from decimal import Decimal

from apps.memberships.pricing import (
    DiscountStrategy,
    NoDiscountStrategy,
    StudentDiscountStrategy,
    LongTermDiscountStrategy,
    CombinedDiscountStrategy,
    PriceCalculator,
    get_best_discount_strategy
)


@pytest.mark.patterns
class TestStrategyPattern:
    """Тесты для паттерна Strategy - различные стратегии скидок"""

    def test_no_discount_strategy(self):
        """Тест стратегии без скидки"""
        strategy = NoDiscountStrategy()

        discount = strategy.calculate_discount(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=False
        )

        assert discount == Decimal('0.00')
        assert strategy.get_description() == "Без скидки"

    def test_student_discount_strategy_for_student(self):
        """Тест студенческой скидки для студента"""
        strategy = StudentDiscountStrategy(discount_percentage=Decimal('15.0'))

        discount = strategy.calculate_discount(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=True
        )

        # 15% от 5000 = 750
        assert discount == Decimal('750.00')
        assert "15%" in strategy.get_description()

    def test_student_discount_strategy_for_non_student(self):
        """Тест студенческой скидки для не-студента"""
        strategy = StudentDiscountStrategy(discount_percentage=Decimal('15.0'))

        discount = strategy.calculate_discount(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=False
        )

        # Не студент - нет скидки
        assert discount == Decimal('0.00')

    def test_student_discount_custom_percentage(self):
        """Тест студенческой скидки с кастомным процентом"""
        strategy = StudentDiscountStrategy(discount_percentage=Decimal('20.0'))

        discount = strategy.calculate_discount(
            base_price=Decimal('10000.00'),
            duration_days=30,
            is_student=True
        )

        # 20% от 10000 = 2000
        assert discount == Decimal('2000.00')

    def test_long_term_discount_90_days(self):
        """Тест скидки за длительный период - 90 дней (10%)"""
        strategy = LongTermDiscountStrategy()

        discount = strategy.calculate_discount(
            base_price=Decimal('5000.00'),
            duration_days=90,
            is_student=False
        )

        # 10% от 5000 = 500
        assert discount == Decimal('500.00')

    def test_long_term_discount_180_days(self):
        """Тест скидки за длительный период - 180 дней (15%)"""
        strategy = LongTermDiscountStrategy()

        discount = strategy.calculate_discount(
            base_price=Decimal('5000.00'),
            duration_days=180,
            is_student=False
        )

        # 15% от 5000 = 750
        assert discount == Decimal('750.00')

    def test_long_term_discount_365_days(self):
        """Тест скидки за длительный период - 365 дней (20%)"""
        strategy = LongTermDiscountStrategy()

        discount = strategy.calculate_discount(
            base_price=Decimal('5000.00'),
            duration_days=365,
            is_student=False
        )

        # 20% от 5000 = 1000
        assert discount == Decimal('1000.00')

    def test_long_term_discount_no_discount(self):
        """Тест скидки за длительный период - меньше 90 дней"""
        strategy = LongTermDiscountStrategy()

        discount = strategy.calculate_discount(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=False
        )

        # Меньше 90 дней - нет скидки
        assert discount == Decimal('0.00')

    def test_combined_discount_strategy_max(self):
        """Тест комбинированной стратегии - выбирает максимальную скидку"""
        student_strategy = StudentDiscountStrategy(discount_percentage=Decimal('15.0'))
        long_term_strategy = LongTermDiscountStrategy()

        combined = CombinedDiscountStrategy([student_strategy, long_term_strategy])

        # Студент с абонементом на 365 дней
        # Студенческая: 15% от 10000 = 1500
        # Долгосрочная: 20% от 10000 = 2000
        # Должна выбрать максимум: 2000
        discount = combined.calculate_discount(
            base_price=Decimal('10000.00'),
            duration_days=365,
            is_student=True
        )

        assert discount == Decimal('2000.00')

    def test_combined_discount_empty_strategies(self):
        """Тест комбинированной стратегии без стратегий"""
        combined = CombinedDiscountStrategy([])

        discount = combined.calculate_discount(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=False
        )

        assert discount == Decimal('0.00')

    def test_strategy_interface(self):
        """Тест что все стратегии реализуют интерфейс DiscountStrategy"""
        strategies = [
            NoDiscountStrategy(),
            StudentDiscountStrategy(),
            LongTermDiscountStrategy(),
            CombinedDiscountStrategy([])
        ]

        for strategy in strategies:
            assert isinstance(strategy, DiscountStrategy)
            assert hasattr(strategy, 'calculate_discount')
            assert hasattr(strategy, 'get_description')


@pytest.mark.patterns
class TestPriceCalculatorContext:
    """Тесты для контекста PriceCalculator (часть паттерна Strategy)"""

    def test_calculator_with_no_discount(self):
        """Тест калькулятора без скидки"""
        calculator = PriceCalculator(NoDiscountStrategy())

        result = calculator.calculate_final_price(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=False
        )

        assert result['base_price'] == Decimal('5000.00')
        assert result['discount_amount'] == Decimal('0.00')
        assert result['final_price'] == Decimal('5000.00')
        assert result['discount_percentage'] == Decimal('0.00')

    def test_calculator_with_student_discount(self):
        """Тест калькулятора со студенческой скидкой"""
        calculator = PriceCalculator(StudentDiscountStrategy())

        result = calculator.calculate_final_price(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=True
        )

        assert result['base_price'] == Decimal('5000.00')
        assert result['discount_amount'] == Decimal('750.00')  # 15% от 5000
        assert result['final_price'] == Decimal('4250.00')
        assert result['discount_percentage'] == Decimal('15.00')

    def test_calculator_change_strategy_at_runtime(self):
        """Тест смены стратегии во время выполнения"""
        calculator = PriceCalculator(NoDiscountStrategy())

        # Сначала без скидки
        result1 = calculator.calculate_final_price(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=False
        )
        assert result1['discount_amount'] == Decimal('0.00')

        # Меняем стратегию
        calculator.set_strategy(StudentDiscountStrategy())

        # Теперь со студенческой скидкой
        result2 = calculator.calculate_final_price(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=True
        )
        assert result2['discount_amount'] == Decimal('750.00')

    def test_calculator_default_strategy(self):
        """Тест калькулятора с дефолтной стратегией"""
        calculator = PriceCalculator()  # Без аргумента

        result = calculator.calculate_final_price(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=False
        )

        # По умолчанию должна быть NoDiscountStrategy
        assert result['discount_amount'] == Decimal('0.00')

    def test_calculator_negative_price_protection(self):
        """Тест защиты от отрицательной цены"""
        # Создаём стратегию с 200% скидкой (нереально, но для теста)
        class OverDiscountStrategy(DiscountStrategy):
            def calculate_discount(self, base_price, duration_days, is_student=False):
                return base_price * Decimal('2.0')  # 200% скидка

            def get_description(self):
                return "Over discount"

        calculator = PriceCalculator(OverDiscountStrategy())

        result = calculator.calculate_final_price(
            base_price=Decimal('1000.00'),
            duration_days=30,
            is_student=False
        )

        # Финальная цена не должна быть отрицательной
        assert result['final_price'] == Decimal('0.00')


@pytest.mark.patterns
class TestFactoryPattern:
    """Тесты для паттерна Factory - get_best_discount_strategy"""

    def test_factory_regular_client_short_term(self):
        """Тест фабрики для обычного клиента с коротким абонементом"""
        strategy = get_best_discount_strategy(
            is_student=False,
            duration_days=30
        )

        # Должна вернуть NoDiscountStrategy
        assert isinstance(strategy, NoDiscountStrategy)

    def test_factory_student_short_term(self):
        """Тест фабрики для студента с коротким абонементом"""
        strategy = get_best_discount_strategy(
            is_student=True,
            duration_days=30
        )

        # Должна вернуть StudentDiscountStrategy
        assert isinstance(strategy, StudentDiscountStrategy)

    def test_factory_regular_client_long_term(self):
        """Тест фабрики для обычного клиента с долгим абонементом"""
        strategy = get_best_discount_strategy(
            is_student=False,
            duration_days=180
        )

        # Должна вернуть LongTermDiscountStrategy
        assert isinstance(strategy, LongTermDiscountStrategy)

    def test_factory_student_long_term(self):
        """Тест фабрики для студента с долгим абонементом"""
        strategy = get_best_discount_strategy(
            is_student=True,
            duration_days=365
        )

        # Должна вернуть CombinedDiscountStrategy (студент + долгосрочная)
        assert isinstance(strategy, CombinedDiscountStrategy)

        # Проверяем что внутри две стратегии
        assert len(strategy.strategies) == 2

    def test_factory_edge_case_90_days(self):
        """Тест граничного случая - ровно 90 дней"""
        strategy = get_best_discount_strategy(
            is_student=False,
            duration_days=90
        )

        # На 90 дней должна быть долгосрочная скидка
        assert isinstance(strategy, LongTermDiscountStrategy)

    def test_factory_edge_case_89_days(self):
        """Тест граничного случая - 89 дней (меньше 90)"""
        strategy = get_best_discount_strategy(
            is_student=False,
            duration_days=89
        )

        # Меньше 90 дней - нет скидки
        assert isinstance(strategy, NoDiscountStrategy)

    def test_factory_returns_best_strategy(self):
        """Тест что фабрика возвращает лучшую стратегию"""
        # Проверяем что для студента с долгим абонементом
        # фабрика вернёт комбинированную стратегию
        strategy = get_best_discount_strategy(
            is_student=True,
            duration_days=365
        )

        calculator = PriceCalculator(strategy)
        result = calculator.calculate_final_price(
            base_price=Decimal('10000.00'),
            duration_days=365,
            is_student=True
        )

        # Комбинированная стратегия должна выбрать максимум
        # Студент: 15% = 1500
        # Годовая: 20% = 2000
        # Максимум: 2000
        assert result['discount_amount'] == Decimal('2000.00')


@pytest.mark.patterns
class TestIntegrationStrategyAndFactory:
    """Интеграционные тесты Strategy + Factory паттернов"""

    def test_full_pricing_workflow_student(self):
        """Тест полного процесса расчёта цены для студента"""
        # 1. Фабрика создаёт стратегию
        strategy = get_best_discount_strategy(
            is_student=True,
            duration_days=30
        )

        # 2. Калькулятор применяет стратегию
        calculator = PriceCalculator(strategy)

        # 3. Рассчитываем финальную цену
        result = calculator.calculate_final_price(
            base_price=Decimal('5000.00'),
            duration_days=30,
            is_student=True
        )

        # Проверяем результат
        assert result['base_price'] == Decimal('5000.00')
        assert result['discount_amount'] == Decimal('750.00')
        assert result['final_price'] == Decimal('4250.00')
        assert "Студенческая" in result['discount_description']

    def test_full_pricing_workflow_long_term(self):
        """Тест полного процесса для долгосрочного абонемента"""
        strategy = get_best_discount_strategy(
            is_student=False,
            duration_days=365
        )

        calculator = PriceCalculator(strategy)
        result = calculator.calculate_final_price(
            base_price=Decimal('20000.00'),
            duration_days=365,
            is_student=False
        )

        # 20% скидка на годовой абонемент
        assert result['discount_amount'] == Decimal('4000.00')
        assert result['final_price'] == Decimal('16000.00')

    def test_multiple_clients_different_strategies(self):
        """Тест что разные клиенты получают разные стратегии"""
        # Обычный клиент
        strategy1 = get_best_discount_strategy(is_student=False, duration_days=30)
        calc1 = PriceCalculator(strategy1)
        result1 = calc1.calculate_final_price(Decimal('5000.00'), 30, False)

        # Студент
        strategy2 = get_best_discount_strategy(is_student=True, duration_days=30)
        calc2 = PriceCalculator(strategy2)
        result2 = calc2.calculate_final_price(Decimal('5000.00'), 30, True)

        # Долгосрочный клиент
        strategy3 = get_best_discount_strategy(is_student=False, duration_days=365)
        calc3 = PriceCalculator(strategy3)
        result3 = calc3.calculate_final_price(Decimal('5000.00'), 365, False)

        # Все должны получить разные скидки
        assert result1['discount_amount'] == Decimal('0.00')  # Нет скидки
        assert result2['discount_amount'] == Decimal('750.00')  # 15% студент
        assert result3['discount_amount'] == Decimal('1000.00')  # 20% годовая
