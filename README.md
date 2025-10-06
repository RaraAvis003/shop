# Интернет-магазин ножей и топоров

Fullstack проект на Django + Next.js для продажи авторских ножей и топоров ручной работы.

## Текущий статус: Этап 1 - Backend MVP ✅

### Реализовано:
- Модели: Category, Product, ProductImage
- Django Admin с кастомизацией
- REST API для товаров и категорий
- Фильтрация, поиск, сортировка
- Docker Compose инфраструктура
- PostgreSQL + Redis + Celery

## Быстрый старт
```bash
# 1. Запуск проекта
docker-compose up -d --build

# 2. Создание суперпользователя
docker-compose exec backend python manage.py createsuperuser

# 3. Открыть админку
# http://localhost:8000/admin/