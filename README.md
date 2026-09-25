# Hop & Barley — Django/DRF shop

Учебный интернет-магазин: Django web UI (sessions), DRF REST API (JWT), PostgreSQL/Docker,
каталог/поиск/фильтры, корзина в сессии, checkout, заказы, отзывы после покупки,
личный кабинет, Swagger/OpenAPI и базовые pytest-тесты.

## Docker
1. Создайте `.env`:
   POSTGRES_DB=hop
   POSTGRES_USER=hop
   POSTGRES_PASSWORD=hop
   POSTGRES_HOST=db
   DJANGO_SECRET_KEY=dev-secret
2. `docker compose up -d --build`
3. `docker compose exec web python manage.py makemigrations`
4. `docker compose exec web python manage.py migrate`
5. `docker compose exec web python manage.py createsuperuser`

Web: http://127.0.0.1:8000/
Swagger: http://127.0.0.1:8000/api/docs/

## JWT
POST `/api/users/login/` -> access/refresh.
POST `/api/users/token/refresh/` -> refreshed access token.
Use `Authorization: Bearer <access>`.

## Tests / lint
`pytest`
`flake8 .`
