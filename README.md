# Hop & Barley — учебный магазин Django / DRF

Каталог, фильтры, поиск, пагинация, рейтинг и популярность; session-корзина;
оформление заказов; личный кабинет; отзывы после покупки; JWT API;
учебная оплата и оплата при получении; аналитика администратора.

## Запуск через Docker / PostgreSQL

Нужны Docker Desktop и Git. Для существующего проекта сохраните его `.env`.
При первом запуске скопируйте `.env.example` в `.env` и замените секретный ключ
и пароль базы. `.env` не добавляется в Git.

```powershell
docker compose up -d db
docker compose build web
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py createsuperuser
docker compose up -d web
```

Команду `createsuperuser` выполняйте только для создания нового администратора.
Исходные имена сервиса `db` и тома `pg_data` сохранены: обновляйте существующую
папку проекта, чтобы Compose использовал прежний том. Не выполняйте `down -v`.
Перед миграцией существующей базы сделайте её резервную копию.

- Магазин: http://127.0.0.1:8000/
- Кабинет: http://127.0.0.1:8000/users/account/
- Админка: http://127.0.0.1:8000/admin/
- Аналитика: http://127.0.0.1:8000/admin/orders/order/analytics/
- Swagger: http://127.0.0.1:8000/api/docs/

Локальный Python: рекомендуется 3.13. Установите `requirements.txt`, затем
выполните `python manage.py migrate` и `python manage.py runserver`.
В `.env` для PostgreSQL вне Docker укажите `POSTGRES_HOST=127.0.0.1`.
При отсутствии `POSTGRES_DB` настройки development используют SQLite.

## Оплата и статусы

Это учебный магазин. Карта и кошелёк работают только в демонстрационном режиме:
платёжный провайдер не подключён, реквизиты не запрашиваются, деньги не списываются.
`PAYMENT_DEMO_ENABLED=true` включает этот режим; в production-настройках он отключён.

После оформления заказ имеет статус `pending`, остатки зарезервированы,
создан неоплаченный `Payment`. Сумма рассчитывается по актуальным ценам в базе.
Учебная оплата доступна только владельцу заказа и меняет его статус на `paid`.
Повторное подтверждение не создаёт второй платёж и не списывает остатки снова.

Для оплаты при получении (`cod`) сотрудник:

1. В Orders выбирает действие «Отправить выбранные заказы».
2. После получения наличных в Payments выбирает «Подтвердить получение наличных».
3. В Orders отмечает заказ доставленным.

У сотрудника должны быть соответствующие права изменения Order и Payment.
Клиент не может подтвердить получение наличных самостоятельно.
Неоплаченный заказ в ожидании можно отменить в кабинете или API: остатки вернутся
ровно один раз. Оплаченные и отправленные заказы этим способом не отменяются;
реальные возвраты денег не входят в учебную реализацию.
Удаление товара, уже попавшего в заказ, запрещено; вместо удаления снимите `is_active`.
Старые заказы сохраняются; способ оплаты для исторических заказов без Payment
автоматически не выдумывается.

## Аналитика

В Orders есть ссылка «Аналитика продаж». Доступ требует `view_order` (или права
изменения заказа), а не только флага `is_staff`.
Отчёт показывает количество заказов и распределение по статусам, сумму оплаченных
неотменённых заказов и топ-10 товаров по оплаченному количеству.
Период фильтруется по дате создания заказа, включая обе границы.
Учебные платежи включены в показатели и явно обозначены на странице.

## Email

Подтверждение заказа отправляется после успешной фиксации транзакции.
Ошибка почтового сервера записывается в журнал и не откатывает заказ.
По умолчанию письма выводятся в консоль, реальная почта не отправляется.
Для SMTP задайте `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` и
переменные `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` из `.env.example`.
В Django настройки собраны через `MAILERS`. Тесты используют почту в памяти.

## API

| Маршрут | Методы / назначение |
|---|---|
| `/api/products/`, `/api/products/<id>/` | GET: каталог и товар |
| `/api/categories/` | GET: категории |
| `/api/products/<id>/reviews/` | GET / POST: отзывы |
| `/api/cart/` | GET / POST: session-корзина |
| `/api/cart/<product_id>/` | PATCH / DELETE: количество и удаление |
| `/api/orders/` | GET / POST: свои заказы и создание |
| `/api/orders/<id>/` | GET / DELETE: просмотр / отмена неоплаченного |
| `/api/orders/<id>/demo-pay/` | POST: учебная оплата своего заказа |
| `/api/users/register/` | POST: email, password |
| `/api/users/login/` | POST: username (email), password → access / refresh |
| `/api/users/token/refresh/` | POST: refresh → access |
| `/api/schema/`, `/api/docs/` | OpenAPI / Swagger |

Авторизация: `Authorization: Bearer <access>`. Access — 30 минут, refresh — 7 дней.
Для session-корзины сохраняйте cookies; JWT сам по себе не переносит корзину
между браузерами. Для session-авторизации POST/PATCH/DELETE требуют CSRF.
Товары поддерживают `search`, `category` (slug), `category__name`, `category__slug`,
`min_price`, `max_price`, `ordering=price|-price|created_at|avg_rating`.

Создание заказа:

```json
{
  "shipping_address": "Tallinn, Test street",
  "payment_method": "cod",
  "items": [{"product_id": 1, "quantity": 2}]
}
```

Способы: `cod`, `debit`, `wallet`. Без явного способа используется `cod`.
Цена, сумма, пользователь и статус устанавливаются сервером.

## Проверки

```powershell
python -m pytest -q
python manage.py check --settings=config.settings.test
python manage.py makemigrations --check --dry-run --settings=config.settings.test
ruff check .
ruff format --check .
python manage.py spectacular --file schema.yaml --validate --fail-on-warn --settings=config.settings.test
mypy .
```

По умолчанию pytest использует изолированную SQLite. Рабочая база не затрагивается.
Три проверки одновременных запросов требуют PostgreSQL и на SQLite пропускаются.
В CI запускается PostgreSQL 16, миграции, весь pytest, Ruff и проверка OpenAPI.
Пользователь тестовой PostgreSQL должен иметь право создавать тестовую базу.
`python -m pytest --ds=config.settings.test_postgres -q` использует переменные
PostgreSQL из окружения и отдельную базу с префиксом `test_`.

Полный mypy запускается отдельной обязательной CI-задачей. При подготовке этой версии
локально пройдены все 51 тест на PostgreSQL 16, включая три проверки одновременных
запросов; mypy, Ruff, проверки Django и валидация OpenAPI также прошли.
Запуск CI именно на GitHub нужно подтвердить после отправки ветки.

Исходный HTML-шаблон содержит дополнительные маркетинговые ссылки-заглушки;
разделы сообщества и материалов не являются реализованными функциями магазина.
GraphQL не добавлен: в доступном описании ТЗ он отмечен как бонус.
