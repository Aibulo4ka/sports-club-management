#!/bin/bash
# Скрипт для запуска тестов

echo "🧪 Запуск тестов..."

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создайте его: python -m venv venv"
    exit 1
fi

# Активация venv
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# Установка зависимостей если нужно
if ! python -m pytest --version &> /dev/null; then
    echo "📦 Установка pytest и зависимостей..."
    pip install -q pytest pytest-django pytest-cov
fi

# Запуск тестов
if [ "$1" == "unit" ]; then
    echo "Running unit tests only..."
    python -m pytest -m unit -v
elif [ "$1" == "coverage" ]; then
    echo "Running tests with coverage..."
    python -m pytest --cov=apps --cov-report=html --cov-report=term-missing
elif [ "$1" == "fast" ]; then
    echo "Running fast tests (no coverage)..."
    python -m pytest -v --tb=short
else
    echo "Running all tests..."
    python -m pytest -v
fi

echo "✅ Тесты завершены!"
