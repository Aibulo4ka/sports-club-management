# Примеры использования Payment API

Практические примеры работы с платёжной системой для фронтенд-разработчиков.

## 📋 Содержание

1. [Создание платежа](#создание-платежа)
2. [Получение списка платежей](#получение-списка-платежей)
3. [Проверка статуса](#проверка-статуса)
4. [Обработка success/fail страниц](#обработка-successfail-страниц)

---

## 1. Создание платежа

### JavaScript (Fetch API)

```javascript
// Создание платежа за абонемент
async function purchaseMembership(membershipTypeId) {
  try {
    const response = await fetch('/api/payments/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`  // JWT токен
      },
      body: JSON.stringify({
        membership_type_id: membershipTypeId,
        payment_method: 'YOOKASSA'
      })
    });

    const data = await response.json();

    if (response.ok) {
      // Редирект на страницу оплаты ЮKassa
      window.location.href = data.payment_url;
    } else {
      console.error('Ошибка создания платежа:', data);
      alert(`Ошибка: ${data.error || 'Неизвестная ошибка'}`);
    }
  } catch (error) {
    console.error('Network error:', error);
  }
}

// Использование
purchaseMembership(1);  // ID типа абонемента
```

### React Example

```jsx
import { useState } from 'react';
import axios from 'axios';

function MembershipPurchase({ membershipType }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handlePurchase = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(
        '/api/payments/',
        {
          membership_type_id: membershipType.id,
          payment_method: 'YOOKASSA'
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );

      // Редирект на ЮKassa
      window.location.href = response.data.payment_url;

    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка создания платежа');
      setLoading(false);
    }
  };

  return (
    <div className="membership-card">
      <h3>{membershipType.name}</h3>
      <p className="price">{membershipType.price} ₽</p>
      <p>{membershipType.description}</p>

      <button
        onClick={handlePurchase}
        disabled={loading}
        className="btn btn-primary"
      >
        {loading ? 'Обработка...' : 'Купить абонемент'}
      </button>

      {error && <div className="alert alert-danger">{error}</div>}
    </div>
  );
}
```

### Vue Example

```vue
<template>
  <div class="membership-purchase">
    <button
      @click="purchase"
      :disabled="loading"
      class="btn-purchase"
    >
      {{ loading ? 'Загрузка...' : 'Оплатить' }}
    </button>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script>
export default {
  props: {
    membershipTypeId: Number
  },
  data() {
    return {
      loading: false,
      error: null
    };
  },
  methods: {
    async purchase() {
      this.loading = true;
      this.error = null;

      try {
        const response = await this.$http.post('/api/payments/', {
          membership_type_id: this.membershipTypeId,
          payment_method: 'YOOKASSA'
        });

        // Редирект на оплату
        window.location.href = response.data.payment_url;

      } catch (err) {
        this.error = err.response?.data?.error || 'Ошибка оплаты';
        this.loading = false;
      }
    }
  }
};
</script>
```

---

## 2. Получение списка платежей

### JavaScript

```javascript
// Получить все платежи текущего пользователя
async function getMyPayments(status = null) {
  try {
    const url = new URL('/api/payments/my/', window.location.origin);
    if (status) {
      url.searchParams.append('status', status);
    }

    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    const payments = await response.json();
    return payments;

  } catch (error) {
    console.error('Error fetching payments:', error);
    return [];
  }
}

// Примеры использования
const allPayments = await getMyPayments();
const completedPayments = await getMyPayments('COMPLETED');
const pendingPayments = await getMyPayments('PENDING');
```

### React Example - Payment History

```jsx
import { useEffect, useState } from 'react';
import axios from 'axios';

function PaymentHistory() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchPayments();
  }, [filter]);

  const fetchPayments = async () => {
    try {
      const params = filter !== 'all' ? { status: filter } : {};
      const response = await axios.get('/api/payments/my/', { params });
      setPayments(response.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Загрузка...</div>;

  return (
    <div className="payment-history">
      <h2>История платежей</h2>

      {/* Фильтр */}
      <div className="filters">
        <button onClick={() => setFilter('all')}>Все</button>
        <button onClick={() => setFilter('COMPLETED')}>Оплачено</button>
        <button onClick={() => setFilter('PENDING')}>Ожидает оплаты</button>
        <button onClick={() => setFilter('FAILED')}>Ошибки</button>
      </div>

      {/* Список платежей */}
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Сумма</th>
            <th>Статус</th>
            <th>Дата</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {payments.map(payment => (
            <tr key={payment.id}>
              <td>{payment.id}</td>
              <td>{payment.amount} ₽</td>
              <td>
                <span className={`badge badge-${getStatusColor(payment.status)}`}>
                  {payment.status_display}
                </span>
              </td>
              <td>{new Date(payment.created_at).toLocaleDateString()}</td>
              <td>
                {payment.status === 'PENDING' && (
                  <a href={payment.payment_url} className="btn btn-sm">
                    Оплатить
                  </a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function getStatusColor(status) {
  const colors = {
    COMPLETED: 'success',
    PENDING: 'warning',
    FAILED: 'danger'
  };
  return colors[status] || 'secondary';
}
```

---

## 3. Проверка статуса

### JavaScript

```javascript
// Проверить статус конкретного платежа
async function checkPaymentStatus(paymentId) {
  try {
    const response = await fetch(`/api/payments/${paymentId}/status_check/`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });

    const payment = await response.json();
    return payment;

  } catch (error) {
    console.error('Error checking status:', error);
    return null;
  }
}

// Использование
const payment = await checkPaymentStatus(42);
if (payment.status === 'COMPLETED') {
  console.log('Платёж завершён!');
}
```

### Polling (автоматическая проверка статуса)

```javascript
// Проверять статус каждые 5 секунд
function pollPaymentStatus(paymentId, callback, maxAttempts = 60) {
  let attempts = 0;

  const interval = setInterval(async () => {
    attempts++;

    const payment = await checkPaymentStatus(paymentId);

    if (payment.status === 'COMPLETED') {
      clearInterval(interval);
      callback('success', payment);
    } else if (payment.status === 'FAILED' || attempts >= maxAttempts) {
      clearInterval(interval);
      callback('failed', payment);
    }
  }, 5000);  // каждые 5 секунд

  return interval;
}

// Использование
pollPaymentStatus(42, (status, payment) => {
  if (status === 'success') {
    alert('Платёж успешно завершён!');
    window.location.href = '/memberships';
  } else {
    alert('Ошибка оплаты');
  }
});
```

---

## 4. Обработка success/fail страниц

### Success Page (Vue)

```vue
<template>
  <div class="payment-success">
    <div v-if="loading" class="spinner">Проверка платежа...</div>

    <div v-else-if="payment && payment.status === 'COMPLETED'" class="success">
      <h1>✅ Оплата успешна!</h1>
      <p>Ваш абонемент активирован</p>

      <div class="payment-details">
        <p><strong>Сумма:</strong> {{ payment.amount }} ₽</p>
        <p><strong>Дата:</strong> {{ formatDate(payment.completed_at) }}</p>
      </div>

      <router-link to="/memberships" class="btn btn-primary">
        Перейти к абонементам
      </router-link>
    </div>

    <div v-else class="pending">
      <h1>⏳ Обработка платежа...</h1>
      <p>Платёж обрабатывается, пожалуйста подождите</p>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      loading: true,
      payment: null,
      paymentId: null
    };
  },
  async mounted() {
    // Получаем payment_id из URL
    this.paymentId = this.$route.query.payment_id;

    if (!this.paymentId) {
      this.$router.push('/');
      return;
    }

    // Проверяем статус
    await this.checkStatus();

    // Если ещё PENDING - продолжаем проверять
    if (this.payment && this.payment.status === 'PENDING') {
      this.startPolling();
    }
  },
  methods: {
    async checkStatus() {
      try {
        const response = await this.$http.get(
          `/api/payments/${this.paymentId}/status_check/`
        );
        this.payment = response.data;
      } catch (error) {
        console.error('Error:', error);
      } finally {
        this.loading = false;
      }
    },
    startPolling() {
      const interval = setInterval(async () => {
        await this.checkStatus();

        if (this.payment.status !== 'PENDING') {
          clearInterval(interval);
        }
      }, 3000);  // каждые 3 секунды
    },
    formatDate(date) {
      return new Date(date).toLocaleString('ru-RU');
    }
  }
};
</script>
```

### Fail/Cancel Page (React)

```jsx
import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

function PaymentFail() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [payment, setPayment] = useState(null);

  useEffect(() => {
    const paymentId = searchParams.get('payment_id');
    if (paymentId) {
      fetchPayment(paymentId);
    }
  }, []);

  const fetchPayment = async (id) => {
    try {
      const response = await axios.get(`/api/payments/${id}/`);
      setPayment(response.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const retryPayment = () => {
    if (payment?.payment_url) {
      window.location.href = payment.payment_url;
    }
  };

  return (
    <div className="payment-fail">
      <h1>❌ Оплата не завершена</h1>
      <p>К сожалению, платёж не был завершён</p>

      {payment && (
        <div className="payment-info">
          <p>Сумма: {payment.amount} ₽</p>
          <p>Статус: {payment.status_display}</p>
        </div>
      )}

      <div className="actions">
        <button onClick={retryPayment} className="btn btn-primary">
          Попробовать снова
        </button>
        <button onClick={() => navigate('/')} className="btn btn-secondary">
          На главную
        </button>
      </div>
    </div>
  );
}

export default PaymentFail;
```

---

## 🔐 Авторизация

Все API endpoints требуют JWT авторизации:

```javascript
// Получение токена при логине
const loginResponse = await fetch('/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'user', password: 'pass' })
});

const { access, refresh } = await loginResponse.json();
localStorage.setItem('access_token', access);
localStorage.setItem('refresh_token', refresh);

// Использование токена
const headers = {
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`
};
```

---

## 📱 Примеры для мобильных приложений

### React Native

```javascript
import axios from 'axios';
import { Linking } from 'react-native';

async function purchaseMembership(membershipTypeId) {
  try {
    const response = await axios.post('/api/payments/', {
      membership_type_id: membershipTypeId,
      payment_method: 'YOOKASSA'
    });

    // Открываем URL оплаты в браузере
    await Linking.openURL(response.data.payment_url);

    // Устанавливаем deep link для возврата в приложение
    // В настройках ЮKassa укажите: myapp://payment-success

  } catch (error) {
    console.error('Payment error:', error);
  }
}
```

---

## 🛠️ Утилиты

### Форматирование суммы

```javascript
function formatPrice(amount) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB'
  }).format(amount);
}

// Использование
formatPrice(4500);  // "4 500,00 ₽"
```

### Форматирование даты

```javascript
function formatDate(dateString) {
  return new Intl.DateTimeFormat('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(dateString));
}

// Использование
formatDate('2025-11-17T12:00:00Z');  // "17 ноября 2025 г., 15:00"
```

---

**Документация обновлена:** 2025-11-17
