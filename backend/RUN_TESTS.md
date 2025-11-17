# 🧪 Запуск тестов

## Быстрый старт

### Docker (рекомендуется)

```bash
# Запустить все тесты
docker-compose exec backend pytest -v

# С покрытием кода
docker-compose exec backend pytest --cov=apps --cov-report=html

# Только unit-тесты
docker-compose exec backend pytest -m unit

# Конкретный файл
docker-compose exec backend pytest apps/accounts/tests/test_models.py -v
```

### Локально

```bash
cd backend

# Активировать venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Запустить тесты
pytest -v

# С покрытием
pytest --cov=apps --cov-report=html --cov-report=term-missing

# Только unit-тесты
pytest -m unit

# Только integration тесты
pytest -m integration
```

---

## Структура тестов

```
backend/
├── conftest.py                 # Общие фикстуры
├── pytest.ini                  # Конфигурация pytest
├── .coveragerc                 # Конфигурация coverage
└── apps/
    ├── accounts/tests/
    │   └── test_models.py      # ✅ 15+ тестов
    ├── memberships/tests/
    │   └── test_models.py      # ✅ 12+ тестов
    ├── bookings/tests/
    │   └── test_models.py      # ✅ 14+ тестов
    └── payments/tests/
        └── test_models.py      # ✅ 15+ тестов
```

**Итого:** 56+ unit-тестов для моделей

---

## Маркеры (markers)

Тесты помечены специальными маркерами для удобной фильтрации:

- `@pytest.mark.unit` - Unit-тесты
- `@pytest.mark.integration` - Integration тесты
- `@pytest.mark.patterns` - Тесты паттернов проектирования
- `@pytest.mark.slow` - Медленные тесты
- `@pytest.mark.yookassa` - Тесты требующие ЮKassa API

### Примеры использования

```bash
# Только unit-тесты
pytest -m unit

# Только integration тесты
pytest -m integration

# Всё кроме медленных
pytest -m "not slow"

# Unit и patterns
pytest -m "unit or patterns"
```

---

## Просмотр покрытия

После запуска с `--cov-report=html`:

```bash
# Откроется HTML отчёт
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

Или просмотр в терминале:

```bash
pytest --cov=apps --cov-report=term-missing
```

---

## Полезные опции pytest

```bash
# Подробный вывод
pytest -v

# Очень подробный
pytest -vv

# Остановиться на первой ошибке
pytest -x

# Показать локальные переменные при ошибке
pytest -l

# Запустить последние упавшие тесты
pytest --lf

# Запустить только новые/изменённые
pytest --nf

# Параллельный запуск (требует pytest-xdist)
pytest -n 4  # 4 процесса

# Без захвата вывода (для print/pdb)
pytest -s
```

---

## Пример вывода

```
======================== test session starts =========================
platform linux -- Python 3.11.0, pytest-7.4.3, pluggy-1.3.0
django: settings: config.settings.dev
rootdir: /app/backend
configfile: pytest.ini
testpaths: apps
plugins: django-4.7.0, cov-4.1.0
collected 56 items

apps/accounts/tests/test_models.py::TestProfileModel::test_create_profile PASSED [  1%]
apps/accounts/tests/test_models.py::TestProfileModel::test_profile_default_role PASSED [  3%]
...
apps/payments/tests/test_models.py::TestPaymentModel::test_cash_payment PASSED [100%]

========================= 56 passed in 2.34s ==========================

---------- coverage: platform linux, python 3.11.0-final-0 -----------
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
apps/accounts/models.py                    45      3    93%   67-69
apps/memberships/models.py                 32      1    97%   48
apps/bookings/models.py                    38      2    95%   52-53
apps/payments/models.py                    28      0   100%
---------------------------------------------------------------------
TOTAL                                     143      6    96%
```

---

## Troubleshooting

### pytest не найден

```bash
pip install pytest pytest-django pytest-cov
```

### Ошибка "No module named apps"

Убедитесь что запускаете pytest из директории `backend/`:

```bash
cd backend
pytest
```

### Ошибка доступа к БД

Проверьте что БД запущена:

```bash
# Docker
docker-compose ps db

# Локально
sudo systemctl status postgresql
```

### Тесты падают с ошибкой импорта

Проверьте `DJANGO_SETTINGS_MODULE` в `pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.dev
```

---

## CI/CD Integration

Для GitHub Actions:

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=apps --cov-report=xml
      - uses: codecov/codecov-action@v2
```

---

## Написание новых тестов

### Шаблон теста модели

```python
import pytest

@pytest.mark.unit
class TestMyModel:
    def test_create_instance(self, my_fixture):
        """Тест создания экземпляра"""
        instance = my_fixture
        assert instance.field == 'value'

    def test_str_representation(self, my_fixture):
        """Тест __str__"""
        assert str(my_fixture) == 'Expected string'
```

### Использование фикстур

Все фикстуры определены в `conftest.py`:

```python
def test_something(test_client, test_membership):
    # test_client и test_membership автоматически созданы
    assert test_client is not None
    assert test_membership is not None
```

---

**Дата:** 2025-11-17
**Версия:** 1.0
