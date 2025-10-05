    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=general_limit:10m rate=50r/s;
    
    # Client max body size (для загрузки изображений)
    client_max_body_size 10M;
    
    # API requests
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Django admin
    location /admin/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Static files (Django)
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files (uploaded content)
    location /media/ {
        alias /app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Next.js
    location / {
        limit_req zone=general_limit burst=100 nodelay;
        proxy_pass http://nextjs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (для Next.js dev)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 17.3 Dockerfile для Django

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установить зависимости системы
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Установить Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать код
COPY . .

# Создать директории
RUN mkdir -p /app/staticfiles /app/media

# Собрать статику
RUN python manage.py collectstatic --noinput

# Создать непривилегированного пользователя
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### 17.4 Dockerfile для Next.js

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Установить зависимости
COPY package.json package-lock.json ./
RUN npm ci

# Скопировать код и собрать
COPY . .
RUN npm run build

# Production image
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
```

### 17.5 .env файл (пример)

```bash
# Database
DB_PASSWORD=strong_password_here

# Django
DJANGO_SECRET_KEY=your-secret-key-here-min-50-chars
DEBUG=False
ALLOWED_HOSTS=shop.example.com,www.shop.example.com

# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin_password

# ЮKassa
YUKASSA_SHOP_ID=123456
YUKASSA_SECRET_KEY=live_your_secret_key

# Email (Yandex SMTP пример)
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@shop.example.com
EMAIL_HOST_PASSWORD=email_password_here

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### 17.6 GitHub Actions CI/CD (пример)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to VPS
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/shop
            git pull origin main
            docker-compose down
            docker-compose up -d --build
            docker-compose exec -T django python manage.py migrate
            docker-compose exec -T django python manage.py collectstatic --noinput
```

### 17.7 Backup скрипт

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/$DATE"

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker-compose exec -T db pg_dump -U user shopdb | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup MinIO
docker run --rm \
  --network shop_default \
  -v $BACKUP_DIR:/backup \
  minio/mc:latest \
  mirror minio/products /backup/minio

# Удалить бэкапы старше 30 дней
find /backups -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

Добавить в crontab:
```bash
0 2 * * * /opt/shop/backup.sh >> /var/log/shop_backup.log 2>&1
```

---

## 18. SEO ОПТИМИЗАЦИЯ

### 18.1 Next.js Metadata

```typescript
// app/layout.tsx
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: {
    default: 'Мастерская ножей - Авторские ножи и топоры ручной работы',
    template: '%s | Мастерская ножей'
  },
  description: 'Изготовление авторских ножей и топоров на заказ. Высокое качество, гарантия 12 месяцев. Доставка по всей России.',
  keywords: ['ножи на заказ', 'авторские ножи', 'топоры ручной работы', 'охотничьи ножи'],
  openGraph: {
    type: 'website',
    locale: 'ru_RU',
    url: 'https://shop.example.com',
    siteName: 'Мастерская ножей',
    images: [
      {
        url: 'https://shop.example.com/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'Мастерская ножей'
      }
    ]
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
}
```

```typescript
// app/product/[slug]/page.tsx
export async function generateMetadata({ params }): Promise<Metadata> {
  const product = await fetchProduct(params.slug)
  
  return {
    title: product.name,
    description: product.description.slice(0, 160),
    openGraph: {
      title: product.name,
      description: product.description,
      images: [
        {
          url: product.images[0].url,
          width: 800,
          height: 600,
          alt: product.name
        }
      ],
    },
    // Structured Data
    other: {
      'product:price:amount': product.price.toString(),
      'product:price:currency': 'RUB',
    }
  }
}
```

### 18.2 Structured Data (Schema.org)

```typescript
// components/ProductStructuredData.tsx
export default function ProductStructuredData({ product }) {
  const structuredData = {
    "@context": "https://schema.org/",
    "@type": "Product",
    "name": product.name,
    "image": product.images.map(img => img.url),
    "description": product.description,
    "sku": product.id,
    "brand": {
      "@type": "Brand",
      "name": "Мастерская ножей"
    },
    "offers": {
      "@type": "Offer",
      "url": `https://shop.example.com/product/${product.slug}`,
      "priceCurrency": "RUB",
      "price": product.price,
      "availability": product.stock_status === 'in_stock' 
        ? "https://schema.org/InStock" 
        : "https://schema.org/PreOrder",
      "seller": {
        "@type": "Organization",
        "name": "Мастерская ножей"
      }
    },
    "aggregateRating": {
      "@type": "AggregateRating",
      "ratingValue": product.average_rating,
      "reviewCount": product.review_count
    }
  }
  
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  )
}
```

### 18.3 Sitemap.xml

```typescript
// app/sitemap.ts
import { MetadataRoute } from 'next'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const products = await fetchAllProducts()
  
  const productUrls = products.map(product => ({
    url: `https://shop.example.com/product/${product.slug}`,
    lastModified: product.updated_at,
    changeFrequency: 'weekly' as const,
    priority: 0.8,
  }))
  
  return [
    {
      url: 'https://shop.example.com',
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: 'https://shop.example.com/catalog',
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.9,
    },
    ...productUrls,
  ]
}
```

### 18.4 robots.txt

```typescript
// app/robots.ts
import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin/', '/api/', '/account/'],
      },
    ],
    sitemap: 'https://shop.example.com/sitemap.xml',
  }
}
```

---

## 19. БЕЗОПАСНОСТЬ

### 19.1 Django Security Settings

```python
# settings.py

# HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Other
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# CORS (если Next.js на отдельном домене)
CORS_ALLOWED_ORIGINS = [
    "https://shop.example.com",
]

# CSRF
CSRF_TRUSTED_ORIGINS = [
    "https://shop.example.com",
]

# Rate limiting (django-ratelimit)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
```

### 19.2 Валидация на backend

```python
# orders/validators.py
from django.core.exceptions import ValidationError

def validate_phone_number(value):
    """Валидация российского номера телефона"""
    import re
    pattern = r'^(\+7|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}# ТЕХНИЧЕСКОЕ ЗАДАНИЕ
## Интернет-магазин ножей и топоров

---

## 1. ОБЩАЯ ИНФОРМАЦИЯ ПРОЕКТА

### 1.1 Описание проекта
Интернет-магазин авторских ножей и топоров ручной работы с возможностью покупки товаров "в наличии" и оформления заказов "под заказ".

### 1.2 Масштаб проекта
- **Количество товаров**: до 100 единиц
- **Ожидаемая нагрузка**: 10-100 заказов в день
- **Команда разработки**: 1 разработчик (solo dev)
- **Сроки**: MVP как можно раньше, но не критично

### 1.3 Инфраструктура
- **VPS характеристики**: 2 CPU, 4-8 GB RAM
- **Операционная система**: Linux (Ubuntu 22.04 LTS рекомендуется)
- **Контейнеризация**: Docker + Docker Compose

---

## 2. ТЕХНОЛОГИЧЕСКИЙ СТЕК

### 2.1 Backend
```yaml
Фреймворк: Django 5.0
API: Django REST Framework (DRF)
База данных: PostgreSQL 15
Кэш/Очереди: Redis 7
Хранилище файлов: MinIO (S3-совместимое)
Async задачи: Celery + Redis
Web сервер: Gunicorn
Reverse proxy: Nginx
Платежи: ЮKassa API
```

### 2.2 Frontend
```yaml
Фреймворк: Next.js 14 (App Router)
Язык: TypeScript (опционально, можно JavaScript)
Стилизация: Tailwind CSS
UI компоненты: shadcn/ui
Иконки: lucide-react
Слайдеры: Swiper.js
```

### 2.3 DevOps
```yaml
Контейнеризация: Docker, Docker Compose
CI/CD: GitHub Actions или GitLab CI
SSL: Let's Encrypt (автоматическое обновление)
Мониторинг: Django Debug Toolbar (dev), логи (prod)
Резервное копирование: PostgreSQL dump + MinIO sync
```

---

## 3. СТРУКТУРА САЙТА

### 3.1 Список страниц

#### Обязательные страницы (MVP):
1. **Главная** (`/`)
   - Hero-слайдер (fullscreen)
   - Секция "Новинки" (4-6 карточек)
   - Секция "Популярные категории" (плитка 3-4 шт)
   - Преимущества магазина (3 блока)
   - Footer

2. **Каталог** (`/catalog`)
   - Фильтры (sidebar)
   - Сортировка (dropdown)
   - Grid товаров (3-4 колонки desktop, 1-2 mobile)
   - Пагинация

3. **Карточка товара** (`/product/[slug]`)
   - Галерея фото (lightbox при клике)
   - Название, цена, статус наличия
   - Кнопка "Купить" / "Заказать"
   - Таблица характеристик
   - Описание (rich text)
   - Отзывы
   - "Похожие товары" (слайдер 4-6 шт)

4. **Корзина** (`/cart`)
   - Список товаров с миниатюрами
   - Разделение: "В наличии" и "Под заказ"
   - Итоговая сумма
   - Кнопка "Оформить заказ"

5. **Оформление заказа** (`/checkout`)
   - Форма контактов (имя, email, телефон)
   - Адрес доставки
   - Способ доставки (список)
   - Способ оплаты (карта, СБП через ЮKassa)
   - Подтверждение заказа

6. **Личный кабинет** (`/account`)
   - Профиль пользователя
   - Список заказов (статусы, детали)
   - История покупок
   - Возможность повторить заказ

7. **Избранное** (`/wishlist`)
   - Grid товаров из избранного
   - Кнопка "Добавить в корзину"
   - Кнопка "Удалить из избранного"

8. **Акции и распродажи** (`/promotions`)
   - Список активных акций
   - Баннеры акций
   - Товары, участвующие в акции

9. **Статические страницы**:
   - О компании (`/about`)
   - Доставка и оплата (`/delivery`)
   - Гарантии (`/warranty`)
   - Контакты (`/contacts`)
   - Политика конфиденциальности (`/privacy`)
   - Пользовательское соглашение (`/terms`)

#### Опциональные (на будущее):
- Сравнение товаров
- Блог (будет на YouTube, на сайте только ссылки)
- Программа лояльности

---

## 4. ДЕТАЛЬНОЕ ОПИСАНИЕ ГЛАВНОЙ СТРАНИЦЫ

### 4.1 Header (sticky)
```
┌────────────────────────────────────────────────────────────┐
│ [Логотип] | Каталог | О нас | Акции | Контакты | YouTube  │
│                                          [🔍] [❤️(3)] [🛒(2)]│
└────────────────────────────────────────────────────────────┘
```

**Элементы**:
- Логотип (слева, кликабелен → главная)
- Навигационное меню
- Поиск (иконка, раскрывается в input)
- Избранное (иконка сердца + счетчик)
- Корзина (иконка + счетчик)

**Технические требования**:
- Sticky позиция при скролле
- Мобильная версия: бургер-меню
- Z-index: 50 (над контентом)

---

### 4.2 Hero-слайдер (fullscreen)

**Дизайн концепция**:
```
┌────────────────────────────────────────────────────────────┐
│                                                             │
│  [◄]            Полноэкранное фото товара            [►]   │
│                  (с затемнением 30%)                        │
│                                                             │
│  ┌─────────────────────────┐                               │
│  │ Охотничий нож "Медведь" │     ← Карточка с инфо        │
│  │ Сталь: AUS-8            │       (левый нижний угол)     │
│  │ Длина: 240 мм           │                               │
│  │ ₽ 12 990                │                               │
│  │ [Смотреть товар →]      │                               │
│  └─────────────────────────┘                               │
│                                                             │
│           ━━━━  ━━━━  ━━━━  ━━━━  ← Линейные индикаторы  │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- **Изображения**: Полноэкранные (1920x1080 минимум), WebP формат
- **Количество слайдов**: 3-5 товаров
- **Автопрокрутка**: каждые 5 секунд, останавливается при взаимодействии
- **Навигация**: 
  - Стрелки по бокам (полупрозрачные кнопки)
  - Линейные индикаторы внизу (не точки!)
- **Карточка товара**:
  - Фон: `bg-white/95 backdrop-blur-sm`
  - Padding: 32px
  - Закругленные углы: 8px
  - Тень: `shadow-2xl`
  - Содержимое:
    - Название (h2, 3xl, bold)
    - Подзаголовок (опционально)
    - 2-3 ключевые характеристики
    - Цена (3xl, bold)
    - Кнопка CTA (красная, `bg-red-600`)

**Альтернативное расположение карточки**:
- Вариант 1: Левый нижний угол (основной)
- Вариант 2: Правый нижний угол
- Вариант 3: По центру (полупрозрачный фон)

**Код индикаторов** (линии, не точки):
```jsx
<div className="flex gap-3">
  {slides.map((_, index) => (
    <div
      className={`h-1 rounded-full transition-all ${
        index === currentSlide
          ? 'w-16 bg-white'
          : 'w-8 bg-white/50'
      }`}
    />
  ))}
</div>
```

**Источник товаров для слайдера**:
- Django: поле `Product.is_featured = True`
- Выбираются случайно или по порядку
- API endpoint: `/api/products/featured/`

---

### 4.3 Секция "Новинки"

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│                        Новинки                              │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  [Фото]  │  │  [Фото]  │  │  [Фото]  │  │  [Фото]  │  │
│  │  300x300 │  │  300x300 │  │  300x300 │  │  300x300 │  │
│  │          │  │          │  │          │  │          │  │
│  │ Название │  │ Название │  │ Название │  │ Название │  │
│  │ ₽ 7 990  │  │ ₽ 5 490  │  │ ₽ 12 990 │  │ ₽ 8 990  │  │
│  │ [🛒]     │  │ [🛒]     │  │ [🛒]     │  │ [🛒]     │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
│  ┌──────────┐  ┌──────────┐                                │
│  │  ...     │  │  ...     │                                │
│  └──────────┘  └──────────┘                                │
│                                                             │
│              [Смотреть весь каталог →]                     │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- **Количество товаров**: 4-6 штук
- **Источник**: `Product.is_new = True`, отсортированные по дате создания
- **Grid**: 
  - Desktop: 4 колонки
  - Tablet: 2 колонки
  - Mobile: 1 колонка
- **Gap**: 24px между карточками
- **Кнопка внизу**: Ссылка на каталог с иконкой стрелки вправо

---

### 4.4 Секция "Популярные категории"

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│              Популярные категории                           │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ │
│  │    [Иконка]     │  │    [Иконка]     │  │  [Иконка]  │ │
│  │      🔪         │  │      🪓         │  │    ⚔️      │ │
│  │                 │  │                 │  │            │ │
│  │     Ножи        │  │     Топоры      │  │   Мачете   │ │
│  │   42 товара     │  │   18 товаров    │  │ 8 товаров  │ │
│  └─────────────────┘  └─────────────────┘  └────────────┘ │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- **Количество категорий**: 3-4 штуки
- **Источник**: Основные категории из базы (без подкатегорий)
- **Дизайн блока**:
  - Фон: белый (`bg-white`)
  - Padding: 32px
  - Закругленные углы: 8px
  - Тень: `shadow-sm`, при hover: `shadow-md`
  - Иконка: 64px, по центру
  - Название: 20px, semibold
  - Счетчик: 14px, серый
- **Hover эффект**: название меняет цвет на красный
- **Клик**: переход в каталог с фильтром по категории

---

### 4.5 Секция "Преимущества"

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│                  Почему выбирают нас                        │
│                                                             │
│     [📦]              [✓]              [🛡️]                │
│  Доставка          Гарантия         Качество               │
│  по всей РФ        12 месяцев       Ручная работа          │
│  Быстрая и         Полная           Каждое изделие         │
│  надежная          гарантия         создается мастерами    │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- **Количество блоков**: 3 штуки
- **Иконки**: из библиотеки lucide-react (Truck, Shield, Award)
- **Размер иконок**: 64px в круге с фоном `bg-red-100`
- **Текст**: 
  - Заголовок: 20px, semibold
  - Описание: 16px, серый
- **Выравнивание**: по центру

---

### 4.6 Footer

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│  [Логотип]                                                  │
│                                                             │
│  О компании     Покупателям      Контакты                  │
│  - О нас        - Доставка       📧 info@shop.ru           │
│  - Гарантии     - Оплата         📱 +7 (999) 123-45-67     │
│                 - Возврат        📍 Москва, ул. ...        │
│                                                             │
│  Мы в соцсетях: [YouTube] [VK] [Telegram]                  │
│                                                             │
│  © 2025 Мастерская ножей | Политика конфиденциальности    │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- **Фон**: темный (`bg-gray-900`)
- **Текст**: белый/серый
- **Ссылки**: с hover эффектом
- **Responsive**: на мобильных колонки друг под другом

---

## 5. КАТАЛОГ ТОВАРОВ

### 5.1 Структура страницы

```
┌─────────────┬──────────────────────────────────────────────┐
│             │  [Сортировка ▼]  [Grid/List]  🔍 Поиск      │
│  Фильтры    ├──────────────────────────────────────────────┤
│  (Sidebar)  │  Показано 24 из 87 товаров                   │
│             ├──────────────────────────────────────────────┤
│ Категории   │  ┌────┬────┬────┬────┐                      │
│ ☐ Ножи      │  │img │img │img │img │                      │
│   ☐ Охот.   │  │    │    │    │    │                      │
│   ☐ Тур.    │  └────┴────┴────┴────┘                      │
│ ☐ Топоры    │  ┌────┬────┬────┬────┐                      │
│             │  │img │img │img │img │                      │
│ Цена        │  │    │    │    │    │                      │
│ [════•════] │  └────┴────┴────┴────┘                      │
│ 1000  50000 │                                              │
│             │  [Загрузить еще ▼]                           │
│ Длина клинка│                                              │
│ [════•════] │                                              │
│ 80    250мм │                                              │
│             │                                              │
│ Материал    │                                              │
│ ☐ VG-10     │                                              │
│ ☐ AUS-8     │                                              │
│ ☐ D2        │                                              │
│             │                                              │
│ [Сбросить]  │                                              │
└─────────────┴──────────────────────────────────────────────┘
```

### 5.2 Фильтры (детально)

**Обязательные фильтры**:
1. **Категории** (чекбоксы, древовидная структура)
2. **Цена** (range slider, мин/макс инпуты)
3. **Длина клинка** (range slider, мм)
4. **Общая длина** (range slider, мм)
5. **Вес** (range slider, граммы)
6. **Материал клинка** (чекбоксы)
7. **Материал рукояти** (чекбоксы)
8. **Твердость HRC** (range slider)
9. **Назначение** (чекбоксы: туризм, охота, EDC, коллекция)
10. **Статус** (радио: все / в наличии / под заказ)

**Технические требования**:
- Range sliders: использовать компонент из shadcn/ui
- Debounce для слайдеров: 300ms
- URL-параметры для всех фильтров (для SEO и шарабельности)
- Пример URL: `/catalog?category=knives&price_min=5000&price_max=15000&blade_material=vg10`
- Кнопка "Сбросить фильтры" внизу sidebar
- Счетчик активных фильтров в header

**Мобильная версия**:
- Фильтры в Bottom Sheet (Material UI)
- Кнопка "Фильтры" с бейджем количества активных фильтров
- Кнопки "Применить" и "Сбросить" внизу Bottom Sheet

### 5.3 Сортировка

**Опции**:
- По популярности (по умолчанию)
- По цене: дешевле → дороже
- По цене: дороже → дешевле
- По новизне (сначала новые)
- По названию (А-Я)

**Технические требования**:
- Dropdown компонент
- Сохранение в URL: `?sort=price_asc`
- Иконка направления сортировки

### 5.4 Grid товаров

**Требования**:
- Desktop: 4 колонки
- Tablet: 3 колонки
- Mobile: 2 колонки (или 1 в list mode)
- Gap: 24px
- Skeleton loaders при загрузке (shadcn/ui Skeleton)

### 5.5 Пагинация

**Варианты**:
1. **Классическая** (страницы 1, 2, 3...)
2. **Infinite scroll** (рекомендуется для UX)
3. **"Загрузить еще"** (кнопка)

**Рекомендация**: Infinite scroll с индикатором загрузки

---

## 6. КАРТОЧКА ТОВАРА

### 6.1 Layout

```
┌────────────────────────────────────────────────────────────┐
│  Главная > Каталог > Ножи > Охотничий нож "Медведь"       │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  Охотничий нож "Медведь"             │
│  │                 │  ⭐⭐⭐⭐⭐ 4.8 (12 отзывов)            │
│  │   Основное      │                                        │
│  │   фото          │  Артикул: NK-001                       │
│  │   800x600       │  ✓ В наличии                           │
│  │                 │                                        │
│  ├─────────────────┤  ₽ 12 990                              │
│  │ [▢][▢][▢][▢]   │                                        │
│  └─────────────────┘  [Добавить в корзину]  [❤️ В избранное]│
│      Thumbnails       [Купить в 1 клик]                     │
│                                                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                             │
│  Характеристики:                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Длина клинка      │ 150 мм                          │  │
│  │ Общая длина       │ 280 мм                          │  │
│  │ Вес               │ 320 г                           │  │
│  │ Материал клинка   │ AUS-8                           │  │
│  │ Твердость         │ 58-60 HRC                       │  │
│  │ Материал рукояти  │ Карельская береза               │  │
│  │ Назначение        │ Охота, туризм                   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                             │
│  [Табы: Описание | Отзывы (12) | Доставка]                │
│                                                             │
│  [Активная вкладка с контентом]                            │
│                                                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                             │
│  Похожие товары                                            │
│  [Слайдер с 4-6 товарами]                                  │
└────────────────────────────────────────────────────────────┘
```

### 6.2 Галерея изображений

**Требования**:
- **Основное фото**: 800x600px (aspect ratio 4:3)
- **Thumbnails**: 100x75px, до 8 штук
- **Lightbox**: При клике на основное фото открывается полноэкранная галерея
- **Навигация**: 
  - Клик по thumbnail → меняет основное фото
  - Стрелки влево/вправо
  - Свайп на мобильных
- **Zoom**: При hover на desktop (опционально)

**Библиотека**: `yet-another-react-lightbox`

### 6.3 Блок информации

**Элементы**:
1. **Название** (h1, 2.5rem, bold)
2. **Рейтинг** (звезды + средний балл + количество отзывов)
3. **Артикул** (серый, мелкий текст)
4. **Статус наличия**:
   - ✓ В наличии (зеленый)
   - ⏱ Под заказ (синий, + срок изготовления)
   - ✗ Нет в наличии (серый)
5. **Цена** (3rem, bold, красный если скидка)
   - Если скидка: зачеркнутая старая цена
   - Процент скидки в бейдже
6. **Кнопки**:
   - "Добавить в корзину" (большая, красная)
   - "Купить в 1 клик" (второстепенная, белая с обводкой)
   - "В избранное" (иконка сердца)

### 6.4 Таблица характеристик

**Формат**: Две колонки (название характеристики | значение)

**Обязательные характеристики**:
- Длина клинка (мм)
- Общая длина (мм)
- Вес (г)
- Толщина клинка (мм)
- Материал клинка
- Твердость (HRC)
- Материал рукояти
- Назначение
- Тип заточки
- Наличие ножен (да/нет, материал)

**Дополнительные** (из JSONB поля `specifications`):
- Форма клинка
- Тип замка (для складных)
- Производитель
- Страна
- и т.д.

### 6.5 Табы с контентом

**Вкладка "Описание"**:
- Rich text (HTML)
- Поддержка форматирования: bold, italic, списки, заголовки
- Изображения (опционально)
- Видео YouTube (embed, опционально)

**Вкладка "Отзывы"**:
- См. раздел 7 "Система отзывов"

**Вкладка "Доставка"**:
- Информация о способах доставки
- Сроки
- Стоимость
- Условия возврата

### 6.6 Похожие товары

**Логика подбора**:
1. Та же категория
2. Близкий ценовой диапазон (±30%)
3. Исключить текущий товар
4. Лимит: 6 штук

**UI**: Swiper слайдер с карточками товаров

---

## 7. СИСТЕМА ОТЗЫВОВ

### 7.1 Модель данных (Django)

```python
class Review(models.Model):
    product = ForeignKey(Product)
    user = ForeignKey(User)
    
    # Оценка
    rating = IntegerField(1-5)
    
    # Контент
    title = CharField(max_length=200)
    text = TextField()
    pros = TextField(blank=True)  # Достоинства
    cons = TextField(blank=True)  # Недостатки
    
    # Модерация
    is_approved = BooleanField(default=False)
    
    # Метаданные
    is_verified_buyer = BooleanField(default=False)  # Проверенная покупка
    helpful_count = IntegerField(default=0)  # Сколько отметили "Полезно"
    
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['product', 'user']  # 1 отзыв на товар от пользователя

class ReviewImage(models.Model):
    review = ForeignKey(Review)
    image = ImageField(upload_to='reviews/')
    order = IntegerField(default=0)

class ReviewHelpful(models.Model):
    review = ForeignKey(Review)
    user = ForeignKey(User)
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['review', 'user']
```

### 7.2 UI отзывов

**Блок с общей информацией**:
```
┌────────────────────┬──────────────────────────────────────┐
│                    │                                      │
│       4.8          │  5 ★  ████████████████████  (8)     │
│   ⭐⭐⭐⭐⭐        │  4 ★  ██████████░░░░░░░░░  (3)     │
│                    │  3 ★  ██░░░░░░░░░░░░░░░░  (1)     │
│   12 отзывов       │  2 ★  ░░░░░░░░░░░░░░░░░░  (0)     │
│                    │  1 ★  ░░░░░░░░░░░░░░░░░░  (0)     │
└────────────────────┴──────────────────────────────────────┘

[Написать отзыв]
```

**Карточка отзыва**:
```
┌────────────────────────────────────────────────────────────┐
│  Иван П.  ✓ Проверенная покупка      ⭐⭐⭐⭐⭐  15.01.2025│
├────────────────────────────────────────────────────────────┤
│  Отличный нож для охоты                                    │
│                                                             │
│  Купил этот нож месяц назад, использовал в походе.        │
│  Очень доволен качеством изготовления и балансом...       │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ ✅ Достоинства   │  │ ❌ Недостатки    │               │
│  │ • Острая заточка │  │ • Тяжеловат      │               │
│  │ • Удобная рукоять│  │                  │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
│  [📷] [📷] [📷]  ← Фото от покупателя                     │
│                                                             │
│  👍 Полезно (5)  |  Ответить                              │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- Сортировка: по дате (новые первые) / по полезности / по рейтингу
- Фильтр по звездам (5★, 4★, 3★ и ниже)
- Возможность прикрепить до 5 фото
- Модерация через Django Admin (is_approved)
- Бейдж "Проверенная покупка" если user купил этот товар
- Кнопка "Полезно" (можно нажать 1 раз, учет в ReviewHelpful)

### 7.3 Форма добавления отзыва

**Поля**:
- Оценка (5 звезд, обязательно)
- Заголовок (max 200 символов, обязательно)
- Текст отзыва (max 2000 символов, обязательно)
- Достоинства (опционально)
- Недостатки (опционально)
- Фото (до 5 штук, опционально)

**Валидация**:
- Нельзя оставить отзыв, если не авторизован
- Один пользователь = один отзыв на товар
- Минимальная длина текста: 50 символов

**UI**:
- Модальное окно или отдельная страница
- Превью загруженных фото
- Счетчик символов
- Кнопка "Отправить на модерацию"

---

## 8. КОРЗИНА И ОФОРМЛЕНИЕ ЗАКАЗА

### 8.1 Корзина (страница)

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│  Корзина (3 товара)                        [Очистить корзину]│
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ═══════════════ В НАЛИЧИИ (2 товара) ════════════════════ │
│                                                             │
│  [img] Нож "Медведь"              [- 1 +]    ₽ 12 990  [✕]│
│        Сталь: AUS-8                                         │
│        Резерв до: 15:42:30                                  │
│                                                             │
│  [img] Топор "Викинг"             [- 1 +]    ₽ 8 500   [✕]│
│        Вес: 1200г                                           │
│                                                             │
│  ═══════════════ ПОД ЗАКАЗ (1 товар) ══════════════════════│
│                                                             │
│  [img] Мачете "Джунгли"           [- 1 +]    ₽ 15 000  [✕]│
│        Срок изготовления: 14-21 день                        │
│        Предоплата: ₽ 5 000 (33%)                            │
│                                                             │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Промокод: [___________] [Применить]                       │
│                                                             │
│  Итого (В наличии):              ₽ 21 490                  │
│  Итого (Под заказ):              ₽ 15 000                  │
│  Предоплата (Под заказ):         ₽ 5 000                   │
│  ─────────────────────────────────────────                 │
│  К оплате сейчас:                ₽ 26 490                  │
│                                                             │
│                              [Оформить заказ →]            │
└────────────────────────────────────────────────────────────┘
```

**Функционал**:
1. **Разделение товаров**:
   - Блок "В наличии" (сразу оплата и доставка)
   - Блок "Под заказ" (указан срок, требуется предоплата)

2. **Управление количеством**:
   - Кнопки +/- для изменения
   - Input с числом (можно ввести вручную)
   - Проверка наличия (для "В наличии")

3. **Резервирование**:
   - Таймер обратного отсчета (24-72 часа, настраивается)
   - При истечении → товар удаляется из корзины
   - Уведомление за 1 час до окончания

4. **Промокод**:
   - Поле ввода + кнопка "Применить"
   - Валидация на backend
   - Отображение скидки в итоговой сумме

5. **Итоговый расчет**:
   - Отдельные суммы для "В наличии" и "Под заказ"
   - Для "Под заказ" показывается предоплата (настраивается в админке, например 30-50%)
   - Финальная сумма к оплате

### 8.2 Хранение корзины

**Варианты**:
1. **Для авторизованных**: в базе данных (модель Cart, CartItem)
2. **Для гостей**: в localStorage (до 7 дней)

**Модель Django**:
```python
class Cart(models.Model):
    user = ForeignKey(User, null=True, blank=True)
    session_key = CharField(max_length=40, null=True)  # Для гостей
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = ForeignKey(Cart)
    product = ForeignKey(Product)
    quantity = IntegerField(default=1)
    
    # Резервирование (только для "В наличии")
    reserved_until = DateTimeField(null=True, blank=True)
    
    added_at = DateTimeField(auto_now_add=True)
```

**API endpoints**:
- `POST /api/cart/add/` - добавить товар
- `PATCH /api/cart/item/{id}/` - изменить количество
- `DELETE /api/cart/item/{id}/` - удалить товар
- `POST /api/cart/apply-promo/` - применить промокод
- `GET /api/cart/` - получить корзину

### 8.3 Оформление заказа (Checkout)

**Шаги** (Multi-step form или все на одной странице):

**Шаг 1: Контактные данные**
```
┌────────────────────────────────────────────────────────────┐
│  1. Контактные данные                                       │
├────────────────────────────────────────────────────────────┤
│  Имя: [_____________________]                              │
│  Телефон: [_____________________]                          │
│  Email: [_____________________]                            │
│                                                             │
│  ☐ Зарегистрироваться (создать аккаунт после заказа)      │
└────────────────────────────────────────────────────────────┘
```

**Шаг 2: Доставка**
```
┌────────────────────────────────────────────────────────────┐
│  2. Доставка                                                │
├────────────────────────────────────────────────────────────┤
│  Способ доставки:                                          │
│  ○ Курьером по Москве (₽ 500, 1-2 дня)                    │
│  ○ СДЭК до пункта выдачи (₽ 350, 3-5 дней)                │
│  ○ Почта России (₽ 400, 7-14 дней)                        │
│  ○ Самовывоз (бесплатно, адрес: ул. Примерная, 1)         │
│                                                             │
│  Адрес доставки:                                           │
│  Индекс: [______]                                          │
│  Город: [_____________________]                            │
│  Улица: [_____________________]                            │
│  Дом: [___] Корпус: [___] Кв: [___]                       │
│                                                             │
│  Комментарий: [________________________________]           │
└────────────────────────────────────────────────────────────┘
```

**Шаг 3: Оплата**
```
┌────────────────────────────────────────────────────────────┐
│  3. Оплата                                                  │
├────────────────────────────────────────────────────────────┤
│  Способ оплаты:                                            │
│  ○ Онлайн (картой, СБП) через ЮKassa                      │
│  ○ При получении (наличными или картой курьеру)           │
│                                                             │
│  ☐ Согласен с условиями пользовательского соглашения      │
│  ☐ Согласен на обработку персональных данных              │
└────────────────────────────────────────────────────────────┘
```

**Шаг 4: Подтверждение**
```
┌────────────────────────────────────────────────────────────┐
│  4. Подтверждение заказа                                    │
├────────────────────────────────────────────────────────────┤
│  Ваш заказ:                                                │
│  • Нож "Медведь" x1            ₽ 12 990                    │
│  • Топор "Викинг" x1           ₽ 8 500                     │
│                                                             │
│  Доставка: Курьер по Москве    ₽ 500                       │
│  Скидка (промокод NEW10):      -₽ 2 149                    │
│  ─────────────────────────────────────                     │
│  Итого:                        ₽ 19 841                    │
│                                                             │
│  Получатель: Иван Иванов                                   │
│  Телефон: +7 (999) 123-45-67                               │
│  Адрес: 101000, Москва, ул. Примерная, д.1, кв.10         │
│                                                             │
│              [← Назад]  [Оформить заказ →]                 │
└────────────────────────────────────────────────────────────┘
```

**После оформления**:
1. Если оплата онлайн → редирект на ЮKassa
2. После оплаты → страница "Спасибо за заказ"
3. Email с подтверждением и номером заказа
4. SMS с номером заказа (опционально)

### 8.4 Страница "Спасибо за заказ"

```
┌────────────────────────────────────────────────────────────┐
│                                                             │
│                    ✓ Заказ оформлен!                       │
│                                                             │
│  Номер вашего заказа: #12345                               │
│  Статус: Оплачен                                           │
│                                                             │
│  Письмо с деталями отправлено на: ivan@example.com        │
│                                                             │
│  Вы можете отслеживать статус заказа в личном кабинете.   │
│                                                             │
│         [Перейти в личный кабинет]  [На главную]          │
└────────────────────────────────────────────────────────────┘
```

---

## 9. ЛИЧНЫЙ КАБИНЕТ

### 9.1 Структура

```
┌─────────────┬──────────────────────────────────────────────┐
│             │                                              │
│  Меню:      │           Личный кабинет                    │
│             │           Иван Иванов                        │
│  • Профиль  │           ivan@example.com                   │
│  • Заказы   ├──────────────────────────────────────────────┤
│  • Избранное│                                              │
│  • Выход    │  [Активная страница]                        │
│             │                                              │
└─────────────┴──────────────────────────────────────────────┘
```

### 9.2 Страница "Мои заказы"

```
┌────────────────────────────────────────────────────────────┐
│  Мои заказы (12)                [Фильтр по статусу ▼]      │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Заказ #12345                   15.01.2025   ✓ Оплачен│ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ [img] Нож "Медведь" x1                   ₽ 12 990    │ │
│  │ [img] Топор "Викинг" x1                  ₽ 8 500     │ │
│  │                                                       │ │
│  │ Итого: ₽ 21 490                                      │ │
│  │                                                       │ │
│  │ Статус: В обработке                                  │ │
│  │ Трек-номер: 1234567890                               │ │
│  │                                                       │ │
│  │     [Подробнее]  [Повторить заказ]  [Отменить]      │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Заказ #12344                   10.01.2025 ⏱ Под заказ│ │
│  │ ...                                                   │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

**Статусы заказов**:
- 🕐 Ожидает оплаты (pending)
- ✓ Оплачен (paid)
- 📦 В обработке (processing)
- 🚚 Отправлен (shipped)
- ✅ Доставлен (delivered)
- ⏱ Под заказ (made_to_order)
- ❌ Отменен (cancelled)

**Функционал**:
- Фильтр по статусу
- Поиск по номеру заказа
- Детальная страница заказа
- Кнопка "Повторить заказ" (добавляет товары в корзину)
- Возможность отменить заказ (если статус pending/processing)

### 9.3 Детальная страница заказа

```
┌────────────────────────────────────────────────────────────┐
│  ← Назад к заказам                                         │
├────────────────────────────────────────────────────────────┤
│  Заказ #12345 от 15.01.2025                               │
│  Статус: 📦 В обработке                                    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Товары:                                                   │
│  • Нож "Медведь" x1              ₽ 12 990                  │
│  • Топор "Викинг" x1             ₽ 8 500                   │
│                                                             │
│  Доставка: Курьер по Москве      ₽ 500                     │
│  Скидка:                         -₽ 2 149                  │
│  ───────────────────────────────────────                   │
│  Итого:                          ₽ 19 841                  │
│                                                             │
│  Способ оплаты: Онлайн (карта)                            │
│  ID платежа: 2d8f7g9h-1a2b-3c4d-5e6f-7g8h9i0j1k2l         │
│                                                             │
│  Доставка:                                                 │
│  Адрес: 101000, Москва, ул. Примерная, д.1, кв.10         │
│  Получатель: Иван Иванов                                   │
│  Телефон: +7 (999) 123-45-67                               │
│  Трек-номер: 1234567890 [Отследить →]                     │
│                                                             │
│  История статусов:                                         │
│  • 15.01.2025 14:30 - Заказ создан                        │
│  • 15.01.2025 14:32 - Оплата получена                     │
│  • 15.01.2025 15:00 - Передан в обработку                 │
│  • 16.01.2025 10:00 - Отправлен (трек: 1234567890)        │
│                                                             │
│              [Скачать чек]  [Связаться с поддержкой]      │
└────────────────────────────────────────────────────────────┘
```

### 9.4 Страница "Профиль"

```
┌────────────────────────────────────────────────────────────┐
│  Профиль                                                    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Личные данные:                                            │
│  Имя: [Иван Иванов________________]                        │
│  Email: [ivan@example.com__________] ✓ Подтвержден        │
│  Телефон: [+7 (999) 123-45-67______]                      │
│                                                             │
│                               [Сохранить изменения]        │
│                                                             │
│  Смена пароля:                                             │
│  Текущий пароль: [_______________]                         │
│  Новый пароль: [_______________]                           │
│  Повтор пароля: [_______________]                          │
│                                                             │
│                               [Изменить пароль]            │
│                                                             │
│  Адреса доставки:                                          │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 📍 Москва, ул. Примерная, д.1, кв.10              │   │
│  │    [Редактировать] [Удалить]                       │   │
│  └────────────────────────────────────────────────────┘   │
│  [+ Добавить новый адрес]                                 │
└────────────────────────────────────────────────────────────┘
```

---

## 10. СТРАНИЦА АКЦИЙ И РАСПРОДАЖ

### 10.1 Layout

```
┌────────────────────────────────────────────────────────────┐
│  Акции и распродажи                                        │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                                                       │ │
│  │        [Баннер акции 1200x400]                       │ │
│  │        РАСПРОДАЖА ЗИМНЕЙ КОЛЛЕКЦИИ                   │ │
│  │        Скидки до 30%                                  │ │
│  │        До 31 января                                   │ │
│  │                                                       │ │
│  │        [Смотреть товары →]                           │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 🎁 НОВОГОДНЯЯ АКЦИЯ            До: 31.12.2025 23:59 │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ Скидка 15% на все топоры по промокоду: NEWYEAR      │ │
│  │                                                       │ │
│  │ Товары в акции:                                      │ │
│  │ [card] [card] [card] [card]                          │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 📦 БЕСПЛАТНАЯ ДОСТАВКА         До: 15.01.2025        │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ При заказе от 15 000 ₽                               │ │
│  │ [Смотреть каталог →]                                 │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### 10.2 Модель Django (promotions)

```python
class Promotion(models.Model):
    DISCOUNT_TYPE = [
        ('percentage', 'Процент'),
        ('fixed', 'Фиксированная сумма'),
        ('free_shipping', 'Бесплатная доставка'),
    ]
    
    title = CharField('Название', max_length=200)
    slug = SlugField(unique=True)
    description = TextField('Описание')
    
    # Скидка
    discount_type = CharField(choices=DISCOUNT_TYPE)
    discount_value = DecimalField(max_digits=10, decimal_places=2)
    
    # Условия
    min_order_amount = DecimalField('Минимальная сумма заказа', null=True, blank=True)
    promo_code = CharField('Промокод', max_length=50, blank=True)
    
    # Период
    start_date = DateTimeField('Начало')
    end_date = DateTimeField('Окончание')
    
    # Товары (или все, если не указано)
    products = ManyToManyField(Product, blank=True)
    categories = ManyToManyField(Category, blank=True)
    
    # Визуальное
    banner_image = ImageField('Баннер', upload_to='promotions/')
    is_featured = BooleanField('На главной', default=False)
    is_active = BooleanField('Активна', default=True)
    
    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
```

### 10.3 Функционал

- **Автоматическое применение**: если товар участвует в акции, показывается старая и новая цена
- **Промокоды**: вводятся в корзине, валидируются на backend
- **Таймер**: обратный отсчет до окончания акции
- **Фильтр**: показывать только активные / все акции
- **SEO**: отдельные страницы для крупных акций (slug)

---

## 11. ИЗБРАННОЕ (WISHLIST)

### 11.1 Модель Django

```python
class WishlistItem(models.Model):
    user = ForeignKey(User, on_delete=CASCADE)
    product = ForeignKey(Product, on_delete=CASCADE)
    added_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'product']
```

### 11.2 UI

**Кнопка в карточке товара**:
- Иконка сердца (пустое / заполненное)
- Клик → добавить/удалить из избранного
- Анимация при добавлении (scale + fill)

**Страница избранного**:
```
┌────────────────────────────────────────────────────────────┐
│  Избранное (5)                       [Очистить избранное]  │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  [Фото]  │  │  [Фото]  │  │  [Фото]  │  │  [Фото]  │  │
│  │  + в наличии │  + под заказ│  + нет    │  │          │  │
│  │  ₽ 12 990│  │  ₽ 8 500 │  │  ₽ 15 000│  │          │  │
│  │  [🛒] [✕]│  │  [🛒] [✕]│  │  [✉️] [✕]│  │          │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└────────────────────────────────────────────────────────────┘
```

**Функционал**:
- Grid как в каталоге
- Быстрое добавление в корзину
- Кнопка "Удалить" (✕)
- Если товара нет в наличии → кнопка "Уведомить о поступлении" (✉️)

---

## 12. ПОИСК

### 12.1 UI поиска

**В Header**:
- Иконка 🔍
- При клике → раскрывается input
- Начинать поиск при вводе 3+ символов
- Debounce 300ms

**Поисковая выдача** (dropdown под input):
```
┌────────────────────────────────────────────────────────┐
│  Найдено 5 товаров по запросу "охотничий"             │
├────────────────────────────────────────────────────────┤
│  [img] Нож "Охотничий"           ₽ 12 990  ✓ В наличии│
│  [img] Топор "Охотник"           ₽ 8 500   ⏱ Под заказ│
│  [img] Мачете "Джунгли"          ₽ 15 000  ✓ В наличии│
│                                                         │
│              [Показать все результаты →]               │
└────────────────────────────────────────────────────────┘
```

**Страница результатов поиска** (`/search?q=охотничий`):
- Заголовок: "Результаты поиска: охотничий (5 товаров)"
- Grid товаров как в каталоге
- Подсветка совпадений в названии
- Возможность применить фильтры
- Если ничего не найдено → "Попробуйте изменить запрос" + ссылка на каталог

### 12.2 Backend поиска (PostgreSQL Full-Text Search)

**Для MVP** (до 100 товаров):
```python
# products/views.py
from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery
from django.db.models import Q

def search_products(query):
    if len(query) < 3:
        return Product.objects.none()
    
    # Полнотекстовый поиск
    search_vector = SearchVector('name', weight='A', config='russian') + \
                    SearchVector('description', weight='B', config='russian')
    search_query = SearchQuery(query, config='russian')
    
    results = Product.objects.annotate(
        search=search_vector,
        rank=SearchRank(search_vector, search_query)
    ).filter(search=search_query).order_by('-rank', '-created_at')
    
    return results[:20]  # Топ 20 результатов
```

**Для масштаба** (>1000 товаров):
- Elasticsearch + django-elasticsearch-dsl
- Индексация: название, описание, характеристики
- Автодополнение (autocomplete)
- Поиск с опечатками (fuzzy search)

---

## 13. ИНТЕГРАЦИЯ ЮKASSA

### 13.1 Модель платежа

```python
class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('waiting_for_capture', 'Ожидает подтверждения'),
        ('succeeded', 'Успешно'),
        ('canceled', 'Отменен'),
        ('refunded', 'Возвращен'),
    ]
    
    order = ForeignKey(Order, on_delete=PROTECT)
    
    # ID от ЮKassa
    payment_id = CharField(max_length=100, unique=True)
    
    # Сумма
    amount = DecimalField(max_digits=10, decimal_places=2)
    currency = CharField(max_length=3, default='RUB')
    
    # Статус
    status = CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    
    # Данные от ЮKassa (JSON)
    metadata = JSONField(default=dict, blank=True)
    
    # Идемпотентность
    idempotency_key = UUIDField(unique=True, default=uuid.uuid4)
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'Платеж {self.payment_id} - {self.amount} ₽'
```

### 13.2 Процесс оплаты

**Шаг 1: Создание платежа**
```python
# orders/views.py
from yookassa import Payment as YooKassaPayment, Configuration

# Настройка ЮKassa
Configuration.account_id = settings.YUKASSA_SHOP_ID
Configuration.secret_key = settings.YUKASSA_SECRET_KEY

def create_payment(order):
    idempotency_key = str(uuid.uuid4())
    
    payment = YooKassaPayment.create({
        "amount": {
            "value": str(order.total_amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"https://shop.example.com/order/{order.id}/success"
        },
        "capture": True,
        "description": f"Заказ #{order.id}",
        "metadata": {
            "order_id": order.id
        }
    }, idempotency_key)
    
    # Сохранить в базу
    Payment.objects.create(
        order=order,
        payment_id=payment.id,
        amount=order.total_amount,
        status='pending',
        metadata=payment,
        idempotency_key=idempotency_key
    )
    
    return payment.confirmation.confirmation_url  # URL для редиректа
```

**Шаг 2: Обработка вебхука**
```python
# orders/webhooks.py
import hmac
import hashlib
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def yukassa_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # 1. Проверить IP (whitelist ЮKassa)
    allowed_ips = ['185.71.76.0/27', '185.71.77.0/27', '77.75.153.0/25', '77.75.156.11', '77.75.156.35', '77.75.154.128/25']
    client_ip = request.META.get('REMOTE_ADDR')
    # TODO: проверить IP в whitelist
    
    # 2. Проверить подпись
    body = request.body.decode('utf-8')
    data = json.loads(body)
    
    # 3. Обработать событие
    event_type = data.get('event')
    payment_data = data.get('object')
    
    if event_type == 'payment.succeeded':
        handle_payment_succeeded(payment_data)
    elif event_type == 'payment.canceled':
        handle_payment_canceled(payment_data)
    elif event_type == 'refund.succeeded':
        handle_refund_succeeded(payment_data)
    
    return JsonResponse({'status': 'ok'})

def handle_payment_succeeded(payment_data):
    payment_id = payment_data['id']
    
    try:
        payment = Payment.objects.get(payment_id=payment_id)
        payment.status = 'succeeded'
        payment.metadata = payment_data
        payment.save()
        
        # Обновить статус заказа
        order = payment.order
        order.status = 'paid'
        order.save()
        
        # Отправить email
        send_order_confirmation_email.delay(order.id)
        
        # Если "В наличии" → зарезервировать товар
        reserve_stock(order)
        
    except Payment.DoesNotExist:
        # Логировать ошибку
        pass
```

### 13.3 Возвраты

```python
from yookassa import Refund

def create_refund(payment, amount, reason=''):
    idempotency_key = str(uuid.uuid4())
    
    refund = Refund.create({
        "payment_id": payment.payment_id,
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "description": reason
    }, idempotency_key)
    
    # Обновить статус платежа
    payment.status = 'refunded'
    payment.save()
    
    # Обновить заказ
    payment.order.status = 'cancelled'
    payment.order.save()
    
    # Вернуть товар в наличие
    release_stock(payment.order)
```

---

## 14. EMAIL УВЕДОМЛЕНИЯ

### 14.1 Типы писем

1. **Регистрация**: Подтверждение email
2. **Восстановление пароля**
3. **Новый заказ**: Подтверждение с деталями
4. **Оплата получена**: Чек и следующие шаги
5. **Заказ отправлен**: Трек-номер
6. **Заказ доставлен**: Просьба оставить отзыв
7. **Заказ отменен**: Информация о возврате
8. **Товар в наличии**: Уведомление из wishlist
9. **Модерация отзыва**: Отзыв опубликован

### 14.2 Настройка Django

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yandex.ru'  # Или другой SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'noreply@shop.example.com'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD')
DEFAULT_FROM_EMAIL = 'Мастерская ножей <noreply@shop.example.com>'
```

### 14.3 Celery задачи

```python
# orders/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string

@shared_task
def send_order_confirmation_email(order_id):
    order = Order.objects.get(id=order_id)
    
    subject = f'Заказ #{order.id} подтвержден'
    html_message = render_to_string('emails/order_confirmation.html', {
        'order': order,
        'items': order.items.all()
    })
    
    send_mail(
        subject=subject,
        message='',  # Plain text version
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        html_message=html_message,
        fail_silently=False
    )

@shared_task
def send_order_shipped_email(order_id, tracking_number):
    order = Order.objects.get(id=order_id)
    
    subject = f'Заказ #{order.id} отправлен'
    html_message = render_to_string('emails/order_shipped.html', {
        'order': order,
        'tracking_number': tracking_number
    })
    
    send_mail(
        subject=subject,
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        html_message=html_message,
        fail_silently=False
    )
```

### 14.4 Шаблоны писем

**Структура**:
```
templates/emails/
├── base.html              # Базовый шаблон (header, footer)
├── order_confirmation.html
├── order_shipped.html
├── order_delivered.html
├── password_reset.html
└── product_available.html
```

**Пример** (order_confirmation.html):
```html
{% extends 'emails/base.html' %}

{% block content %}
<h1>Спасибо за заказ!</h1>

<p>Здравствуйте, {{ order.name }}!</p>

<p>Ваш заказ #{{ order.id }} успешно оформлен и оплачен.</p>

<h2>Детали заказа:</h2>

<table>
  <tr>
    <th>Товар</th>
    <th>Количество</th>
    <th>Цена</th>
  </tr>
  {% for item in items %}
  <tr>
    <td>{{ item.product.name }}</td>
    <td>{{ item.quantity }}</td>
    <td>{{ item.price }} ₽</td>
  </tr>
  {% endfor %}
</table>

<p><strong>Итого: {{ order.total_amount }} ₽</strong></p>

<p>Адрес доставки: {{ order.delivery_address }}</p>

<p>Вы можете отследить статус заказа в <a href="https://shop.example.com/account/orders">личном кабинете</a>.</p>
{% endblock %}
```

---

## 15. АДМИНКА DJANGO

### 15.1 Кастомизация Admin

```python
# admin.py
from django.contrib import admin
from django.utils.html import format_html

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'thumbnail_preview', 'name', 'category', 'price', 
        'stock_status_badge', 'is_featured', 'views_count', 'created_at'
    ]
    list_filter = ['stock_status', 'category', 'is_featured', 'is_new', 'created_at']
    search_fields = ['name', 'description', 'blade_material']
    prepopulated_fields = {'slug': ('name',)}
    
    readonly_fields = ['views_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'slug', 'category', 'description', 'price', 'stock_status')
        }),
        ('Характеристики', {
            'fields': (
                'blade_length', 'total_length', 'weight', 
                'blade_material', 'handle_material', 'hardness', 'specifications'
            )
        }),
        ('SEO и отображение', {
            'fields': ('is_featured', 'is_new', 'views_count')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ProductImageInline]
    
    def thumbnail_preview(self, obj):
        first_image = obj.images.first()
        if first_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                first_image.image.url
            )
        return '-'
    thumbnail_preview.short_description = 'Фото'
    
    def stock_status_badge(self, obj):
        colors = {
            'in_stock': 'green',
            'made_to_order': 'blue',
            'out_of_stock': 'gray'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px;">{}</span>',
            colors.get(obj.stock_status, 'gray'),
            obj.get_stock_status_display()
        )
    stock_status_badge.short_description = 'Статус'
    
    actions = ['mark_as_featured', 'mark_as_in_stock']
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} товаров добавлено в слайдер')
    mark_as_featured.short_description = 'Добавить в слайдер на главной'
    
    def mark_as_in_stock(self, request, queryset):
        updated = queryset.update(stock_status='in_stock')
        self.message_user(request, f'{updated} товаров отмечено как "В наличии"')
    mark_as_in_stock.short_description = 'Отметить "В наличии"'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'email', 'phone', 'total_amount', 
        'status_badge', 'payment_status', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'delivery_method']
    search_fields = ['id', 'email', 'phone', 'name']
    readonly_fields = ['created_at', 'updated_at', 'payment_link']
    
    fieldsets = (
        ('Клиент', {
            'fields': ('user', 'name', 'email', 'phone')
        }),
        ('Доставка', {
            'fields': ('delivery_address', 'delivery_method', 'delivery_cost')
        }),
        ('Оплата', {
            'fields': ('total_amount', 'status', 'payment_id', 'payment_link')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    inlines = [OrderItemInline]
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'processing': 'blue',
            'shipped': 'purple',
            'delivered': 'darkgreen',
            'cancelled': 'red'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def payment_status(self, obj):
        try:
            payment = obj.payment_set.first()
            return payment.status if payment else '-'
        except:
            return '-'
    payment_status.short_description = 'Платеж'
    
    def payment_link(self, obj):
        try:
            payment = obj.payment_set.first()
            if payment:
                return format_html(
                    '<a href="https://yookassa.ru/payments/{}" target="_blank">Посмотреть в ЮKassa</a>',
                    payment.payment_id
                )
        except:
            pass
        return '-'
    payment_link.short_description = 'Ссылка на платеж'
    
    actions = ['mark_as_shipped', 'export_to_excel']
    
    def mark_as_shipped(self, request, queryset):
        for order in queryset:
            order.status = 'shipped'
            order.save()
            # Отправить email с трек-номером
            send_order_shipped_email.delay(order.id, 'TRACK123')
        
        self.message_user(request, f'{queryset.count()} заказов отмечено как "Отправлено"')
    mark_as_shipped.short_description = 'Отметить как отправленные'
```

### 15.2 Dashboard (опционально)

Для расширенной статистики можно использовать:
- **django-admin-tools**: кастомные dashboard виджеты
- **django-grappelli**: улучшенный UI админки
- **django-suit**: современная тема для admin

**Виджеты для dashboard**:
- График продаж за последние 30 дней
- Топ-10 популярных товаров
- Последние заказы (статусы)
- Сумма продаж за день/неделю/месяц
- Товары с низким остатком

---

## 16. API ENDPOINTS (DRF)

### 16.1 Список основных endpoints

```python
# urls.py
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/auth/', include('rest_framework.urls')),
    path('api/webhooks/yukassa/', yukassa_webhook, name='yukassa_webhook'),
]
```

### 16.2 Основные ViewSets

```python
# products/views.py
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'category': ['exact'],
        'price': ['gte', 'lte'],
        'blade_length': ['gte', 'lte'],
        'stock_status': ['exact'],
    }
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'views_count']
    ordering = ['-created_at']
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Увеличить счетчик просмотров
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Товары для слайдера на главной"""
        products = self.queryset.filter(is_featured=True)[:5]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def new(self, request):
        """Новинки"""
        products = self.queryset.filter(is_new=True)[:6]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """Похожие товары"""
        product = self.get_object()
        similar = Product.objects.filter(
            category=product.category
        ).exclude(id=product.id).order_by('?')[:6]
        serializer = self.get_serializer(similar, many=True)
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=self.request.user)
        else:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            cart, _ = Cart.objects.get_or_create(session_key=session_key)
        return CartItem.objects.filter(cart=cart)
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        """Добавить товар в корзину"""
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        product = Product.objects.get(id=product_id)
        
        # Получить или создать корзину
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            cart, _ = Cart.objects.get_or_create(session_key=session_key)
        
        # Добавить товар
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        # Если "В наличии" → зарезервировать
        if product.stock_status == 'in_stock':
            reserve_until = timezone.now() + timedelta(hours=24)
            cart_item.reserved_until = reserve_until
            cart_item.save()
        
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data)
```

### 16.3 Пагинация

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 24,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}
```

---

## 17. ИНФРАСТРУКТУРА И DEPLOYMENT

### 17.1 Docker Compose (Production)

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - django
      - nextjs
    restart: unless-stopped

  django:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/shopdb
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - YUKASSA_SHOP_ID=${YUKASSA_SHOP_ID}
      - YUKASSA_SECRET_KEY=${YUKASSA_SECRET_KEY}
      - SECRET_KEY=${DJANGO_SECRET_KEY}
      - DEBUG=False
      - ALLOWED_HOSTS=shop.example.com
    depends_on:
      - db
      - redis
      - minio
    restart: unless-stopped

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A config worker -l info
    volumes:
      - media_volume:/app/media
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/shopdb
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A config beat -l info
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/shopdb
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  nextjs:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - NEXT_PUBLIC_API_URL=https://shop.example.com/api
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=shopdb
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY}
    restart: unless-stopped

volumes:
  postgres_data:
  minio_data:
  static_volume:
  media_volume:
```

### 17.2 Nginx конфигурация

```nginx
# nginx/conf.d/default.conf
upstream django {
    server django:8000;
}

upstream nextjs {
    server nextjs:3000;
}

server {
    listen 80;
    server_name shop.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name shop.example.com;
    
    ssl_certificate /etc/letsencrypt/live/shop.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/shop.example.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max
    if not re.match(pattern, value):
        raise ValidationError('Неверный формат номера телефона')

def validate_order_amount(order):
    """Проверка суммы заказа"""
    calculated_total = sum(item.price * item.quantity for item in order.items.all())
    if abs(calculated_total - order.total_amount) > 0.01:
        raise ValidationError('Сумма заказа не соответствует товарам')
```

### 19.3 SQL Injection защита

Django ORM автоматически защищает от SQL injection, но если используете raw SQL:

```python
# ❌ ПЛОХО
Product.objects.raw(f"SELECT * FROM products WHERE name = '{user_input}'")

# ✅ ХОРОШО
Product.objects.raw("SELECT * FROM products WHERE name = %s", [user_input])
```

### 19.4 XSS защита

```python
# Django templates автоматически экранируют HTML
{{ product.name }}  # Безопасно

# Если нужен raw HTML (например, для описания товара)
{{ product.description|safe }}  # Только для доверенного контента!

# Лучше использовать bleach для очистки HTML
import bleach

allowed_tags = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li']
clean_html = bleach.clean(user_input, tags=allowed_tags, strip=True)
```

### 19.5 Защита от CSRF в API

```python
# DRF с SessionAuthentication автоматически проверяет CSRF

# Для exemption (например, вебхуки)
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def yukassa_webhook(request):
    # Проверяем IP и подпись вместо CSRF
    pass
```

---

## 20. ТЕСТИРОВАНИЕ

### 20.1 Unit тесты Django

```python
# products/tests.py
from django.test import TestCase
from decimal import Decimal
from .models import Product, Category

class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Ножи', slug='knives')
        self.product = Product.objects.create(
            name='Тестовый нож',
            slug='test-knife',
            category=self.category,
            price=Decimal('10000.00'),
            stock_status='in_stock',
            blade_length=Decimal('120.0')
        )
    
    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Тестовый нож')
        self.assertEqual(self.product.price, Decimal('10000.00'))
    
    def test_product_slug_auto_generation(self):
        product = Product.objects.create(
            name='Новый нож',
            category=self.category,
            price=Decimal('5000.00')
        )
        self.assertEqual(product.slug, 'novyj-nozh')
    
    def test_product_str_method(self):
        self.assertEqual(str(self.product), 'Тестовый нож')


class ProductAPITest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Ножи', slug='knives')
        self.product = Product.objects.create(
            name='API Test Knife',
            slug='api-test-knife',
            category=self.category,
            price=Decimal('10000.00')
        )
    
    def test_product_list_endpoint(self):
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['results']), 1)
    
    def test_product_detail_endpoint(self):
        response = self.client.get(f'/api/products/{self.product.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'API Test Knife')
    
    def test_product_filter_by_price(self):
        response = self.client.get('/api/products/?price__gte=5000&price__lte=15000')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['results']), 1)
```

### 20.2 Integration тесты (заказы)

```python
# orders/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from .models import Order, OrderItem
from products.models import Product, Category

User = get_user_model()

class OrderFlowTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Ножи', slug='knives')
        self.product = Product.objects.create(
            name='Test Knife',
            slug='test-knife',
            category=self.category,
            price=Decimal('10000.00'),
            stock_status='in_stock'
        )
    
    def test_create_order(self):
        self.client.login(username='testuser', password='testpass123')
        
        order_data = {
            'email': 'test@example.com',
            'phone': '+79991234567',
            'name': 'Test User',
            'delivery_address': 'Москва, ул. Тестовая, 1',
            'delivery_method': 'courier',
            'items': [
                {'product_id': self.product.id, 'quantity': 1}
            ]
        }
        
        response = self.client.post('/api/orders/', order_data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        order = Order.objects.get(id=response.json()['id'])
        self.assertEqual(order.total_amount, Decimal('10000.00'))
        self.assertEqual(order.items.count(), 1)
```

### 20.3 E2E тесты (Playwright)

```typescript
// tests/e2e/checkout.spec.ts
import { test, expect } from '@playwright/test'

test('complete checkout flow', async ({ page }) => {
  // 1. Перейти на главную
  await page.goto('https://shop.example.com')
  
  // 2. Открыть каталог
  await page.click('text=Каталог')
  
  // 3. Добавить товар в корзину
  await page.click('.product-card:first-child button[aria-label="Добавить в корзину"]')
  
  // 4. Перейти в корзину
  await page.click('[aria-label="Корзина"]')
  await expect(page).toHaveURL(/\/cart/)
  
  // 5. Оформить заказ
  await page.click('text=Оформить заказ')
  
  // 6. Заполнить форму
  await page.fill('input[name="name"]', 'Test User')
  await page.fill('input[name="email"]', 'test@example.com')
  await page.fill('input[name="phone"]', '+79991234567')
  await page.fill('textarea[name="address"]', 'Москва, ул. Тестовая, 1')
  
  // 7. Выбрать доставку
  await page.click('text=Курьером по Москве')
  
  // 8. Подтвердить заказ
  await page.click('text=Оформить заказ')
  
  // 9. Проверить успешное создание
  await expect(page).toHaveURL(/\/order\/\d+\/success/)
  await expect(page.locator('text=Заказ оформлен')).toBeVisible()
})
```

---

## 21. ПРОИЗВОДИТЕЛЬНОСТЬ

### 21.1 Оптимизация Django запросов

```python
# ❌ ПЛОХО (N+1 problem)
products = Product.objects.all()
for product in products:
    print(product.category.name)  # Каждый раз запрос к БД

# ✅ ХОРОШО
products = Product.objects.select_related('category').all()
for product in products:
    print(product.category.name)  # Один JOIN запрос

# Для Many-to-Many
products = Product.objects.prefetch_related('images', 'reviews').all()
```

### 21.2 Кэширование в Django

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'shop',
        'TIMEOUT': 300,
    }
}

# views.py
from django.views.decorators.cache import cache_page
from django.core.cache import cache

@cache_page(60 * 15)  # 15 минут
def product_list(request):
    products = Product.objects.all()
    return render(request, 'products/list.html', {'products': products})

# Или программно
def get_featured_products():
    cache_key = 'featured_products'
    products = cache.get(cache_key)
    
    if products is None:
        products = list(Product.objects.filter(is_featured=True)[:5])
        cache.set(cache_key, products, 60 * 60)  # 1 час
    
    return products
```

### 21.3 Database индексы

```python
# products/models.py
class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(unique=True, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    stock_status = models.CharField(max_length=20, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['category', 'stock_status']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['price', 'stock_status']),
        ]
```

### 21.4 Next.js оптимизация

```typescript
// next.config.js
module.exports = {
  images: {
    domains: ['shop.example.com'],
    formats: ['image/webp', 'image/avif'],
  },
  // Сжатие
  compress: true,
  // Static optimization
  output: 'standalone',
  // Experimental features
  experimental: {
    optimizeCss: true,
  },
}

// Использование Image optimization
import Image from 'next/image'

<Image
  src={product.image}
  width={400}
  height={300}
  alt={product.name}
  loading="lazy"
  placeholder="blur"
  blurDataURL={product.thumbnailBase64}
/>
```

---

## 22. МОНИТОРИНГ И ЛОГИРОВАНИЕ

### 22.1 Structured logging

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/shop/django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'orders': {
            'handlers': ['file'],
            'level': 'INFO',
        },
        'payments': {
            'handlers': ['file'],
            'level': 'WARNING',
        },
    },
}
```

### 22.2 Мониторинг ошибок

```python
# settings.py (если используете Sentry)
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="https://your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True,
    environment="production",
)
```

### 22.3 Метрики приложения

```python
# Простой custom middleware для метрик
import time
from django.utils.deprecation import MiddlewareMixin

class MetricsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            # Логировать или отправлять в систему мониторинга
            logger.info(f"{request.method} {request.path} {response.status_code} {duration:.2f}s")
        return response
```

---

## 23. ЧЕКЛИСТ ЗАПУСКА

### 23.1 Перед деплоем

**Backend**:
- [ ] `DEBUG = False` в production
- [ ] `ALLOWED_HOSTS` настроен правильно
- [ ] `SECRET_KEY` уникальный и в секретах
- [ ] Все миграции применены
- [ ] Статика собрана (`collectstatic`)
- [ ] Superuser создан
- [ ] Тестовые данные удалены

**Frontend**:
- [ ] `NEXT_PUBLIC_API_URL` указывает на prod API
- [ ] Build проходит без ошибок
- [ ] Все env переменные настроены

**Инфраструктура**:
- [ ] SSL сертификат установлен
- [ ] Nginx конфигурация проверена
- [ ] Docker containers запускаются
- [ ] Backup скрипт настроен
- [ ] Логи ротируются

**Безопасность**:
- [ ] Firewall настроен (только 80, 443 открыты)
- [ ] SSH вход только по ключу
- [ ] Пароли сложные и уникальные
- [ ] Rate limiting работает
- [ ] HTTPS редирект включен

**Интеграции**:
- [ ] ЮKassa credentials в production mode
- [ ] Email SMTP работает
- [ ] Вебхуки ЮKassa зарегистрированы
- [ ] MinIO доступен и настроен

### 23.2 После деплоя

- [ ] Создать тестовый заказ
- [ ] Проверить оплату (тестовый платеж)
- [ ] Проверить email уведомления
- [ ] Проверить вебхуки ЮKassa
- [ ] Добавить несколько товаров через админку
- [ ] Проверить поиск
- [ ] Проверить фильтры в каталоге
- [ ] Проверить мобильную версию
- [ ] Проверить скорость загрузки (PageSpeed Insights)
- [ ] Настроить Google Analytics / Яндекс.Метрику

---

## 24. ДАЛЬНЕЙШЕЕ РАЗВИТИЕ

### Фаза 2 (после MVP):
- Telegram-бот для уведомлений
- Система отзывов с фото
- Программа лояльности
- Сравнение товаров
- Рекомендации на основе истории
- Фильтр по наличию на складе в реальном времени

### Фаза 3 (масштабирование):
- Elasticsearch для поиска
- CDN для статики (CloudFlare)
- Микросервисная архитектура (если нужно)
- Интеграция с 1C (если потребуется)
- Мобильное приложение (React Native)
- Multi-language support

---

## 25. КОНТАКТЫ И ПОДДЕРЖКА

### Документация:
- Django: https://docs.djangoproject.com/
- DRF: https://www.django-rest-framework.org/
- Next.js: https://nextjs.org/docs
- ЮKassa: https://yookassa.ru/developers
- PostgreSQL: https://www.postgresql.org/docs/
- Redis: https://redis.io/documentation
- MinIO: https://min.io/docs/

### Полезные ресурсы:
- Django REST Framework tutorial: https://www.django-rest-framework.org/tutorial/quickstart/
- Next.js e-commerce example: https://github.com/vercel/commerce
- Docker Compose для Django: https://docs.docker.com/samples/django/
- ЮKassa SDK Python: https://github.com/yoomoney/yookassa-sdk-python

---

## 26. ПРИЛОЖЕНИЯ

### Приложение A: Структура проекта

```
shop/
├── backend/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── celery.py
│   ├── products/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── admin.py
│   │   ├── filters.py
│   │   └── urls.py
│   ├── orders/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── tasks.py
│   │   ├── webhooks.py
│   │   └── urls.py
│   ├── reviews/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── promotions/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── wishlist/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   └── views.py
│   ├── templates/
│   │   └── emails/
│   │       ├── base.html
│   │       ├── order_confirmation.html
│   │       └── order_shipped.html
│   ├── static/
│   ├── media/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── manage.py
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── catalog/
│   │   │   └── page.tsx
│   │   ├── product/
│   │   │   └── [slug]/
│   │   │       └── page.tsx
│   │   ├── cart/
│   │   │   └── page.tsx
│   │   ├── checkout/
│   │   │   └── page.tsx
│   │   ├── account/
│   │   │   ├── page.tsx
│   │   │   └── orders/
│   │   │       └── page.tsx
│   │   ├── wishlist/
│   │   │   └── page.tsx
│   │   └── promotions/
│   │       └── page.tsx
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── HeroSlider.tsx
│   │   ├── ProductCard.tsx
│   │   ├── ProductReviews.tsx
│   │   ├── WishlistButton.tsx
│   │   └── ui/
│   │       └── (shadcn components)
│   ├── lib/
│   │   ├── api.ts
│   │   └── utils.ts
│   ├── public/
│   │   ├── images/
│   │   └── icons/
│   ├── styles/
│   │   └── globals.css
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
│       └── default.conf
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
└── README.md
```

### Приложение B: requirements.txt

```txt
# Django
Django==5.0.1
djangorestframework==3.14.0
django-filter==23.5
django-cors-headers==4.3.1
django-environ==0.11.2

# Database
psycopg2-binary==2.9.9
dj-database-url==2.1.0

# Cache & Celery
redis==5.0.1
celery==5.3.6
django-redis==5.4.0

# File Storage
django-storages==1.14.2
boto3==1.34.23

# Images
Pillow==10.2.0
django-imagekit==5.0.0

# Authentication & Security
djangorestframework-simplejwt==5.3.1
django-ratelimit==4.1.0

# Payments
yookassa==3.0.0

# Utils
python-slugify==8.0.1
python-decouple==3.8

# Monitoring & Logging
python-json-logger==2.0.7
sentry-sdk==1.40.0

# Testing
pytest==7.4.4
pytest-django==4.7.0
factory-boy==3.3.0

# Server
gunicorn==21.2.0
```

### Приложение C: package.json (Frontend)

```json
{
  "name": "shop-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "playwright test"
  },
  "dependencies": {
    "next": "14.1.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "typescript": "5.3.3",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-dropdown-menu": "^2.0.6",
    "@radix-ui/react-slider": "^1.1.2",
    "@radix-ui/react-tabs": "^1.0.4",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "lucide-react": "^0.309.0",
    "swiper": "^11.0.5",
    "tailwind-merge": "^2.2.0",
    "tailwindcss-animate": "^1.0.7",
    "yet-another-react-lightbox": "^3.15.6",
    "zustand": "^4.4.7"
  },
  "devDependencies": {
    "@types/node": "20.11.0",
    "@types/react": "18.2.48",
    "@types/react-dom": "18.2.18",
    "@playwright/test": "^1.41.0",
    "autoprefixer": "10.4.17",
    "eslint": "8.56.0",
    "eslint-config-next": "14.1.0",
    "postcss": "8.4.33",
    "tailwindcss": "3.4.1"
  }
}
```

### Приложение D: Примеры API запросов

**Получить список товаров:**
```bash
GET /api/products/
GET /api/products/?category=knives&price__gte=5000&price__lte=15000
GET /api/products/?search=охотничий
GET /api/products/?ordering=-created_at
```

**Получить товар:**
```bash
GET /api/products/123/
GET /api/products/hunting-knife-bear/  # по slug
```

**Добавить в корзину:**
```bash
POST /api/cart/add/
Content-Type: application/json

{
  "product_id": 123,
  "quantity": 1
}
```

**Создать заказ:**
```bash
POST /api/orders/
Content-Type: application/json

{
  "email": "customer@example.com",
  "phone": "+79991234567",
  "name": "Иван Иванов",
  "delivery_address": "Москва, ул. Тестовая, 1",
  "delivery_method": "courier",
  "items": [
    {
      "product_id": 123,
      "quantity": 1
    }
  ]
}
```

**Добавить отзыв:**
```bash
POST /api/reviews/
Content-Type: application/json
Authorization: Bearer <token>

{
  "product": 123,
  "rating": 5,
  "title": "Отличный нож",
  "text": "Купил месяц назад, очень доволен качеством...",
  "pros": "Острая заточка, удобная рукоять",
  "cons": "Немного тяжеловат"
}
```

**Добавить в избранное:**
```bash
POST /api/wishlist/
Content-Type: application/json
Authorization: Bearer <token>

{
  "product_id": 123
}
```

### Приложение E: Полезные команды

**Django:**
```bash
# Создать миграции
python manage.py makemigrations

# Применить миграции
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser

# Собрать статику
python manage.py collectstatic --noinput

# Запустить dev сервер
python manage.py runserver

# Открыть Django shell
python manage.py shell

# Создать фикстуры (тестовые данные)
python manage.py dumpdata products --indent 2 > fixtures/products.json
python manage.py loaddata fixtures/products.json
```

**Docker:**
```bash
# Собрать и запустить контейнеры
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f django
docker-compose logs -f celery_worker

# Выполнить команду в контейнере
docker-compose exec django python manage.py migrate
docker-compose exec django python manage.py createsuperuser

# Остановить контейнеры
docker-compose down

# Остановить и удалить volumes
docker-compose down -v

# Пересобрать один сервис
docker-compose up -d --build django
```

**PostgreSQL:**
```bash
# Подключиться к БД
docker-compose exec db psql -U user -d shopdb

# Бэкап
docker-compose exec db pg_dump -U user shopdb > backup.sql

# Восстановление
docker-compose exec -T db psql -U user shopdb < backup.sql
```

**Celery:**
```bash
# Запустить worker
celery -A config worker -l info

# Запустить beat (планировщик)
celery -A config beat -l info

# Посмотреть активные задачи
celery -A config inspect active

# Очистить очередь
celery -A config purge
```

**Next.js:**
```bash
# Dev сервер
npm run dev

# Production build
npm run build

# Запустить production сервер
npm run start

# Линтинг
npm run lint

# E2E тесты
npm run test
```

### Приложение F: Чеклист разработки по фазам

**Фаза 1: Базовая структура (1-2 недели)**
- [ ] Настроить Django проект
- [ ] Создать модели: Product, Category, ProductImage
- [ ] Настроить Django Admin
- [ ] Создать API endpoints для товаров
- [ ] Настроить Next.js проект
- [ ] Создать базовый layout (Header, Footer)
- [ ] Сделать главную страницу (без слайдера)
- [ ] Сделать страницу каталога (без фильтров)
- [ ] Сделать карточку товара

**Фаза 2: Функционал покупки (1-2 недели)**
- [ ] Создать модели: Cart, CartItem
- [ ] Реализовать корзину (API + UI)
- [ ] Создать модели: Order, OrderItem
- [ ] Реализовать оформление заказа
- [ ] Интегрировать ЮKassa
- [ ] Настроить вебхуки
- [ ] Настроить email уведомления
- [ ] Создать личный кабинет (заказы)

**Фаза 3: Дополнительный функционал (1 неделя)**
- [ ] Добавить фильтры в каталог
- [ ] Добавить поиск
- [ ] Реализовать избранное
- [ ] Добавить hero-слайдер на главную
- [ ] Создать систему отзывов
- [ ] Создать страницу акций
- [ ] Добавить статические страницы

**Фаза 4: Deployment и оптимизация (1 неделя)**
- [ ] Настроить Docker Compose
- [ ] Настроить Nginx
- [ ] Получить SSL сертификат
- [ ] Настроить минимальный мониторинг
- [ ] Настроить бэкапы
- [ ] Провести нагрузочное тестирование
- [ ] Оптимизировать медленные запросы
- [ ] Добавить кэширование

**Итого MVP: 4-6 недель**

### Приложение G: Troubleshooting

**Проблема: Товары не отображаются в каталоге**
- Проверить, что товары созданы в админке
- Проверить API endpoint: `/api/products/`
- Проверить CORS настройки
- Открыть DevTools → Network и посмотреть ошибки

**Проблема: Не приходят email**
- Проверить SMTP настройки в `.env`
- Проверить логи Celery: `docker-compose logs celery_worker`
- Проверить, что Celery worker запущен
- Попробовать отправить тестовое письмо из Django shell

**Проблема: Изображения не загружаются**
- Проверить, что MinIO запущен: `docker-compose ps minio`
- Проверить настройки в `settings.py`: `DEFAULT_FILE_STORAGE`
- Проверить права доступа к директории media
- Проверить Nginx конфигурацию для `/media/`

**Проблема: Вебхуки ЮKassa не работают**
- Проверить, что URL вебхука правильный (https!)
- Проверить логи: `docker-compose logs django | grep webhook`
- Проверить IP whitelist ЮKassa
- Использовать ngrok для локального тестирования

**Проблема: Медленная загрузка каталога**
- Проверить количество SQL запросов (Django Debug Toolbar)
- Добавить `select_related()` и `prefetch_related()`
- Добавить database индексы
- Включить кэширование

**Проблема: Docker контейнеры не запускаются**
- Проверить логи: `docker-compose logs`
- Проверить, что порты не заняты: `netstat -tulpn`
- Проверить `.env` файл
- Проверить права доступа к volumes
- Попробовать пересобрать: `docker-compose up -d --build --force-recreate`

---

## ЗАКЛЮЧЕНИЕ

Данное техническое задание содержит полную информацию для разработки интернет-магазина ножей и топоров с нуля.

### Ключевые особенности проекта:
✅ **Простота**: Монолитная архитектура, понятная для solo-разработчика
✅ **Масштабируемость**: Возможность роста до 1000+ товаров без рефакторинга
✅ **Безопасность**: Все критичные аспекты учтены (HTTPS, CSRF, XSS, Rate limiting)
✅ **Production-ready**: Docker, CI/CD, мониторинг, бэкапы

### Рекомендуемый порядок реализации:
1. **Настроить инфраструктуру** (Docker, PostgreSQL, Redis)
2. **Создать базовые модели** (Product, Category)
3. **Реализовать каталог** (API + UI)
4. **Добавить корзину и заказы**
5. **Интегрировать платежи** (ЮKassa)
6. **Добавить дополнительный функционал** (отзывы, избранное, акции)
7. **Оптимизировать и задеплоить**

### Оценка времени (solo dev):
- **MVP**: 4-6 недель
- **Полный функционал**: 8-10 недель
- **С тестами и документацией**: 10-12 недель

### Важные напоминания:
⚠️ Всегда используйте `.env` для секретов
⚠️ Регулярно делайте бэкапы базы данных
⚠️ Тестируйте платежи в sandbox-режиме
⚠️ Мониторьте логи после деплоя
⚠️ Используйте Git для версионирования

**Удачи в разработке! 🚀**

---

*Документ создан: 2025-01-04*
*Версия: 1.0*
*Для вопросов и уточнений начните новый чат с этим ТЗ*# ТЕХНИЧЕСКОЕ ЗАДАНИЕ
## Интернет-магазин ножей и топоров

---

## 1. ОБЩАЯ ИНФОРМАЦИЯ ПРОЕКТА

### 1.1 Описание проекта
Интернет-магазин авторских ножей и топоров ручной работы с возможностью покупки товаров "в наличии" и оформления заказов "под заказ".

### 1.2 Масштаб проекта
- **Количество товаров**: до 100 единиц
- **Ожидаемая нагрузка**: 10-100 заказов в день
- **Команда разработки**: 1 разработчик (solo dev)
- **Сроки**: MVP как можно раньше, но не критично

### 1.3 Инфраструктура
- **VPS характеристики**: 2 CPU, 4-8 GB RAM
- **Операционная система**: Linux (Ubuntu 22.04 LTS рекомендуется)
- **Контейнеризация**: Docker + Docker Compose

---

## 2. ТЕХНОЛОГИЧЕСКИЙ СТЕК

### 2.1 Backend
```yaml
Фреймворк: Django 5.0
API: Django REST Framework (DRF)
База данных: PostgreSQL 15
Кэш/Очереди: Redis 7
Хранилище файлов: MinIO (S3-совместимое)
Async задачи: Celery + Redis
Web сервер: Gunicorn
Reverse proxy: Nginx
Платежи: ЮKassa API
```

### 2.2 Frontend
```yaml
Фреймворк: Next.js 14 (App Router)
Язык: TypeScript (опционально, можно JavaScript)
Стилизация: Tailwind CSS
UI компоненты: shadcn/ui
Иконки: lucide-react
Слайдеры: Swiper.js
```

### 2.3 DevOps
```yaml
Контейнеризация: Docker, Docker Compose
CI/CD: GitHub Actions или GitLab CI
SSL: Let's Encrypt (автоматическое обновление)
Мониторинг: Django Debug Toolbar (dev), логи (prod)
Резервное копирование: PostgreSQL dump + MinIO sync
```

---

## 3. СТРУКТУРА САЙТА

### 3.1 Список страниц

#### Обязательные страницы (MVP):
1. **Главная** (`/`)
   - Hero-слайдер (fullscreen)
   - Секция "Новинки" (4-6 карточек)
   - Секция "Популярные категории" (плитка 3-4 шт)
   - Преимущества магазина (3 блока)
   - Footer

2. **Каталог** (`/catalog`)
   - Фильтры (sidebar)
   - Сортировка (dropdown)
   - Grid товаров (3-4 колонки desktop, 1-2 mobile)
   - Пагинация

3. **Карточка товара** (`/product/[slug]`)
   - Галерея фото (lightbox при клике)
   - Название, цена, статус наличия
   - Кнопка "Купить" / "Заказать"
   - Таблица характеристик
   - Описание (rich text)
   - Отзывы
   - "Похожие товары" (слайдер 4-6 шт)

4. **Корзина** (`/cart`)
   - Список товаров с миниатюрами
   - Разделение: "В наличии" и "Под заказ"
   - Итоговая сумма
   - Кнопка "Оформить заказ"

5. **Оформление заказа** (`/checkout`)
   - Форма контактов (имя, email, телефон)
   - Адрес доставки
   - Способ доставки (список)
   - Способ оплаты (карта, СБП через ЮKassa)
   - Подтверждение заказа

6. **Личный кабинет** (`/account`)
   - Профиль пользователя
   - Список заказов (статусы, детали)
   - История покупок
   - Возможность повторить заказ

7. **Избранное** (`/wishlist`)
   - Grid товаров из избранного
   - Кнопка "Добавить в корзину"
   - Кнопка "Удалить из избранного"

8. **Акции и распродажи** (`/promotions`)
   - Список активных акций
   - Баннеры акций
   - Товары, участвующие в акции

9. **Статические страницы**:
   - О компании (`/about`)
   - Доставка и оплата (`/delivery`)
   - Гарантии (`/warranty`)
   - Контакты (`/contacts`)
   - Политика конфиденциальности (`/privacy`)
   - Пользовательское соглашение (`/terms`)

#### Опциональные (на будущее):
- Сравнение товаров
- Блог (будет на YouTube, на сайте только ссылки)
- Программа лояльности

---

## 4. ДЕТАЛЬНОЕ ОПИСАНИЕ ГЛАВНОЙ СТРАНИЦЫ

### 4.1 Header (sticky)
```
┌────────────────────────────────────────────────────────────┐
│ [Логотип] | Каталог | О нас | Акции | Контакты | YouTube  │
│                                          [🔍] [❤️(3)] [🛒(2)]│
└────────────────────────────────────────────────────────────┘
```

**Элементы**:
- Логотип (слева, кликабелен → главная)
- Навигационное меню
- Поиск (иконка, раскрывается в input)
- Избранное (иконка сердца + счетчик)
- Корзина (иконка + счетчик)

**Технические требования**:
- Sticky позиция при скролле
- Мобильная версия: бургер-меню
- Z-index: 50 (над контентом)

---

### 4.2 Hero-слайдер (fullscreen)

**Дизайн концепция**:
```
┌────────────────────────────────────────────────────────────┐
│                                                             │
│  [◄]            Полноэкранное фото товара            [►]   │
│                  (с затемнением 30%)                        │
│                                                             │
│  ┌─────────────────────────┐                               │
│  │ Охотничий нож "Медведь" │     ← Карточка с инфо        │
│  │ Сталь: AUS-8            │       (левый нижний угол)     │
│  │ Длина: 240 мм           │                               │
│  │ ₽ 12 990                │                               │
│  │ [Смотреть товар →]      │                               │
│  └─────────────────────────┘                               │
│                                                             │
│           ━━━━  ━━━━  ━━━━  ━━━━  ← Линейные индикаторы  │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- **Изображения**: Полноэкранные (1920x1080 минимум), WebP формат
- **Количество слайдов**: 3-5 товаров
- **Автопрокрутка**: каждые 5 секунд, останавливается при взаимодействии
- **Навигация**: 
  - Стрелки по бокам (полупрозрачные кнопки)
  - Линейные индикаторы внизу (не точки!)
- **Карточка товара**:
  - Фон: `bg-white/95 backdrop-blur-sm`
  - Padding: 32px
  - Закругленные углы: 8px
  - Тень: `shadow-2xl`
  - Содержимое:
    - Название (h2, 3xl, bold)
    - Подзаголовок (опционально)
    - 2-3 ключевые характеристики
    - Цена (3xl, bold)
    - Кнопка CTA (красная, `bg-red-600`)

**Альтернативное расположение карточки**:
- Вариант 1: Левый нижний угол (основной)
- Вариант 2: Правый нижний угол
- Вариант 3: По центру (полупрозрачный фон)

**Код индикаторов** (линии, не точки):
```jsx
<div className="flex gap-3">
  {slides.map((_, index) => (
    <div
      className={`h-1 rounded-full transition-all ${
        index === currentSlide
          ? 'w-16 bg-white'
          : 'w-8 bg-white/50'
      }`}
    />
  ))}
</div>
```

**Источник товаров для слайдера**:
- Django: поле `Product.is_featured = True`
- Выбираются случайно или по порядку
- API endpoint: `/api/products/featured/`

---

### 4.3 Секция "Новинки"

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│                        Новинки                              │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  [Фото]  │  │  [Фото]  │  │  [Фото]  │  │  [Фото]  │  │
│  │  300x300 │  │  300x300 │  │  300x300 │  │  300x300 │  │
│  │          │  │          │  │          │  │          │  │
│  │ Название │  │ Название │  │ Название │  │ Название │  │
│  │ ₽ 7 990  │  │ ₽ 5 490  │  │ ₽ 12 990 │  │ ₽ 8 990  │  │
│  │ [🛒]     │  │ [🛒]     │  │ [🛒]     │  │ [🛒]     │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
│  ┌──────────┐  ┌──────────┐                                │
│  │  ...     │  │  ...     │                                │
│  └──────────┘  └──────────┘                                │
│                                                             │
│              [Смотреть весь каталог →]                     │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- **Количество товаров**: 4-6 штук
- **Источник**: `Product.is_new = True`, отсортированные по дате создания
- **Grid**: 
  - Desktop: 4 колонки
  - Tablet: 2 колонки
  - Mobile: 1 колонка
- **Gap**: 24px между карточками
- **Кнопка внизу**: Ссылка на каталог с иконкой стрелки вправо

---

### 4.4 Секция "Популярные категории"

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│              Популярные категории                           │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ │
│  │    [Иконка]     │  │    [Иконка]     │  │  [Иконка]  │ │
│  │      🔪         │  │      🪓         │  │    ⚔️      │ │
│  │                 │  │                 │  │            │ │
│  │     Ножи        │  │     Топоры      │  │   Мачете   │ │
│  │   42 товара     │  │   18 товаров    │  │ 8 товаров  │ │
│  └─────────────────┘  └─────────────────┘  └────────────┘ │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- **Количество категорий**: 3-4 штуки
- **Источник**: Основные категории из базы (без подкатегорий)
- **Дизайн блока**:
  - Фон: белый (`bg-white`)
  - Padding: 32px
  - Закругленные углы: 8px
  - Тень: `shadow-sm`, при hover: `shadow-md`
  - Иконка: 64px, по центру
  - Название: 20px, semibold
  - Счетчик: 14px, серый
- **Hover эффект**: название меняет цвет на красный
- **Клик**: переход в каталог с фильтром по категории

---

### 4.5 Секция "Преимущества"

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│                  Почему выбирают нас                        │
│                                                             │
│     [📦]              [✓]              [🛡️]                │
│  Доставка          Гарантия         Качество               │
│  по всей РФ        12 месяцев       Ручная работа          │
│  Быстрая и         Полная           Каждое изделие         │
│  надежная          гарантия         создается мастерами    │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- **Количество блоков**: 3 штуки
- **Иконки**: из библиотеки lucide-react (Truck, Shield, Award)
- **Размер иконок**: 64px в круге с фоном `bg-red-100`
- **Текст**: 
  - Заголовок: 20px, semibold
  - Описание: 16px, серый
- **Выравнивание**: по центру

---

### 4.6 Footer

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│  [Логотип]                                                  │
│                                                             │
│  О компании     Покупателям      Контакты                  │
│  - О нас        - Доставка       📧 info@shop.ru           │
│  - Гарантии     - Оплата         📱 +7 (999) 123-45-67     │
│                 - Возврат        📍 Москва, ул. ...        │
│                                                             │
│  Мы в соцсетях: [YouTube] [VK] [Telegram]                  │
│                                                             │
│  © 2025 Мастерская ножей | Политика конфиденциальности    │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- **Фон**: темный (`bg-gray-900`)
- **Текст**: белый/серый
- **Ссылки**: с hover эффектом
- **Responsive**: на мобильных колонки друг под другом

---

## 5. КАТАЛОГ ТОВАРОВ

### 5.1 Структура страницы

```
┌─────────────┬──────────────────────────────────────────────┐
│             │  [Сортировка ▼]  [Grid/List]  🔍 Поиск      │
│  Фильтры    ├──────────────────────────────────────────────┤
│  (Sidebar)  │  Показано 24 из 87 товаров                   │
│             ├──────────────────────────────────────────────┤
│ Категории   │  ┌────┬────┬────┬────┐                      │
│ ☐ Ножи      │  │img │img │img │img │                      │
│   ☐ Охот.   │  │    │    │    │    │                      │
│   ☐ Тур.    │  └────┴────┴────┴────┘                      │
│ ☐ Топоры    │  ┌────┬────┬────┬────┐                      │
│             │  │img │img │img │img │                      │
│ Цена        │  │    │    │    │    │                      │
│ [════•════] │  └────┴────┴────┴────┘                      │
│ 1000  50000 │                                              │
│             │  [Загрузить еще ▼]                           │
│ Длина клинка│                                              │
│ [════•════] │                                              │
│ 80    250мм │                                              │
│             │                                              │
│ Материал    │                                              │
│ ☐ VG-10     │                                              │
│ ☐ AUS-8     │                                              │
│ ☐ D2        │                                              │
│             │                                              │
│ [Сбросить]  │                                              │
└─────────────┴──────────────────────────────────────────────┘
```

### 5.2 Фильтры (детально)

**Обязательные фильтры**:
1. **Категории** (чекбоксы, древовидная структура)
2. **Цена** (range slider, мин/макс инпуты)
3. **Длина клинка** (range slider, мм)
4. **Общая длина** (range slider, мм)
5. **Вес** (range slider, граммы)
6. **Материал клинка** (чекбоксы)
7. **Материал рукояти** (чекбоксы)
8. **Твердость HRC** (range slider)
9. **Назначение** (чекбоксы: туризм, охота, EDC, коллекция)
10. **Статус** (радио: все / в наличии / под заказ)

**Технические требования**:
- Range sliders: использовать компонент из shadcn/ui
- Debounce для слайдеров: 300ms
- URL-параметры для всех фильтров (для SEO и шарабельности)
- Пример URL: `/catalog?category=knives&price_min=5000&price_max=15000&blade_material=vg10`
- Кнопка "Сбросить фильтры" внизу sidebar
- Счетчик активных фильтров в header

**Мобильная версия**:
- Фильтры в Bottom Sheet (Material UI)
- Кнопка "Фильтры" с бейджем количества активных фильтров
- Кнопки "Применить" и "Сбросить" внизу Bottom Sheet

### 5.3 Сортировка

**Опции**:
- По популярности (по умолчанию)
- По цене: дешевле → дороже
- По цене: дороже → дешевле
- По новизне (сначала новые)
- По названию (А-Я)

**Технические требования**:
- Dropdown компонент
- Сохранение в URL: `?sort=price_asc`
- Иконка направления сортировки

### 5.4 Grid товаров

**Требования**:
- Desktop: 4 колонки
- Tablet: 3 колонки
- Mobile: 2 колонки (или 1 в list mode)
- Gap: 24px
- Skeleton loaders при загрузке (shadcn/ui Skeleton)

### 5.5 Пагинация

**Варианты**:
1. **Классическая** (страницы 1, 2, 3...)
2. **Infinite scroll** (рекомендуется для UX)
3. **"Загрузить еще"** (кнопка)

**Рекомендация**: Infinite scroll с индикатором загрузки

---

## 6. КАРТОЧКА ТОВАРА

### 6.1 Layout

```
┌────────────────────────────────────────────────────────────┐
│  Главная > Каталог > Ножи > Охотничий нож "Медведь"       │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  Охотничий нож "Медведь"             │
│  │                 │  ⭐⭐⭐⭐⭐ 4.8 (12 отзывов)            │
│  │   Основное      │                                        │
│  │   фото          │  Артикул: NK-001                       │
│  │   800x600       │  ✓ В наличии                           │
│  │                 │                                        │
│  ├─────────────────┤  ₽ 12 990                              │
│  │ [▢][▢][▢][▢]   │                                        │
│  └─────────────────┘  [Добавить в корзину]  [❤️ В избранное]│
│      Thumbnails       [Купить в 1 клик]                     │
│                                                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                             │
│  Характеристики:                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Длина клинка      │ 150 мм                          │  │
│  │ Общая длина       │ 280 мм                          │  │
│  │ Вес               │ 320 г                           │  │
│  │ Материал клинка   │ AUS-8                           │  │
│  │ Твердость         │ 58-60 HRC                       │  │
│  │ Материал рукояти  │ Карельская береза               │  │
│  │ Назначение        │ Охота, туризм                   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                             │
│  [Табы: Описание | Отзывы (12) | Доставка]                │
│                                                             │
│  [Активная вкладка с контентом]                            │
│                                                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                             │
│  Похожие товары                                            │
│  [Слайдер с 4-6 товарами]                                  │
└────────────────────────────────────────────────────────────┘
```

### 6.2 Галерея изображений

**Требования**:
- **Основное фото**: 800x600px (aspect ratio 4:3)
- **Thumbnails**: 100x75px, до 8 штук
- **Lightbox**: При клике на основное фото открывается полноэкранная галерея
- **Навигация**: 
  - Клик по thumbnail → меняет основное фото
  - Стрелки влево/вправо
  - Свайп на мобильных
- **Zoom**: При hover на desktop (опционально)

**Библиотека**: `yet-another-react-lightbox`

### 6.3 Блок информации

**Элементы**:
1. **Название** (h1, 2.5rem, bold)
2. **Рейтинг** (звезды + средний балл + количество отзывов)
3. **Артикул** (серый, мелкий текст)
4. **Статус наличия**:
   - ✓ В наличии (зеленый)
   - ⏱ Под заказ (синий, + срок изготовления)
   - ✗ Нет в наличии (серый)
5. **Цена** (3rem, bold, красный если скидка)
   - Если скидка: зачеркнутая старая цена
   - Процент скидки в бейдже
6. **Кнопки**:
   - "Добавить в корзину" (большая, красная)
   - "Купить в 1 клик" (второстепенная, белая с обводкой)
   - "В избранное" (иконка сердца)

### 6.4 Таблица характеристик

**Формат**: Две колонки (название характеристики | значение)

**Обязательные характеристики**:
- Длина клинка (мм)
- Общая длина (мм)
- Вес (г)
- Толщина клинка (мм)
- Материал клинка
- Твердость (HRC)
- Материал рукояти
- Назначение
- Тип заточки
- Наличие ножен (да/нет, материал)

**Дополнительные** (из JSONB поля `specifications`):
- Форма клинка
- Тип замка (для складных)
- Производитель
- Страна
- и т.д.

### 6.5 Табы с контентом

**Вкладка "Описание"**:
- Rich text (HTML)
- Поддержка форматирования: bold, italic, списки, заголовки
- Изображения (опционально)
- Видео YouTube (embed, опционально)

**Вкладка "Отзывы"**:
- См. раздел 7 "Система отзывов"

**Вкладка "Доставка"**:
- Информация о способах доставки
- Сроки
- Стоимость
- Условия возврата

### 6.6 Похожие товары

**Логика подбора**:
1. Та же категория
2. Близкий ценовой диапазон (±30%)
3. Исключить текущий товар
4. Лимит: 6 штук

**UI**: Swiper слайдер с карточками товаров

---

## 7. СИСТЕМА ОТЗЫВОВ

### 7.1 Модель данных (Django)

```python
class Review(models.Model):
    product = ForeignKey(Product)
    user = ForeignKey(User)
    
    # Оценка
    rating = IntegerField(1-5)
    
    # Контент
    title = CharField(max_length=200)
    text = TextField()
    pros = TextField(blank=True)  # Достоинства
    cons = TextField(blank=True)  # Недостатки
    
    # Модерация
    is_approved = BooleanField(default=False)
    
    # Метаданные
    is_verified_buyer = BooleanField(default=False)  # Проверенная покупка
    helpful_count = IntegerField(default=0)  # Сколько отметили "Полезно"
    
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['product', 'user']  # 1 отзыв на товар от пользователя

class ReviewImage(models.Model):
    review = ForeignKey(Review)
    image = ImageField(upload_to='reviews/')
    order = IntegerField(default=0)

class ReviewHelpful(models.Model):
    review = ForeignKey(Review)
    user = ForeignKey(User)
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['review', 'user']
```

### 7.2 UI отзывов

**Блок с общей информацией**:
```
┌────────────────────┬──────────────────────────────────────┐
│                    │                                      │
│       4.8          │  5 ★  ████████████████████  (8)     │
│   ⭐⭐⭐⭐⭐        │  4 ★  ██████████░░░░░░░░░  (3)     │
│                    │  3 ★  ██░░░░░░░░░░░░░░░░  (1)     │
│   12 отзывов       │  2 ★  ░░░░░░░░░░░░░░░░░░  (0)     │
│                    │  1 ★  ░░░░░░░░░░░░░░░░░░  (0)     │
└────────────────────┴──────────────────────────────────────┘

[Написать отзыв]
```

**Карточка отзыва**:
```
┌────────────────────────────────────────────────────────────┐
│  Иван П.  ✓ Проверенная покупка      ⭐⭐⭐⭐⭐  15.01.2025│
├────────────────────────────────────────────────────────────┤
│  Отличный нож для охоты                                    │
│                                                             │
│  Купил этот нож месяц назад, использовал в походе.        │
│  Очень доволен качеством изготовления и балансом...       │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ ✅ Достоинства   │  │ ❌ Недостатки    │               │
│  │ • Острая заточка │  │ • Тяжеловат      │               │
│  │ • Удобная рукоять│  │                  │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
│  [📷] [📷] [📷]  ← Фото от покупателя                     │
│                                                             │
│  👍 Полезно (5)  |  Ответить                              │
└────────────────────────────────────────────────────────────┘
```

**Требования**:
- Сортировка: по дате (новые первые) / по полезности / по рейтингу
- Фильтр по звездам (5★, 4★, 3★ и ниже)
- Возможность прикрепить до 5 фото
- Модерация через Django Admin (is_approved)
- Бейдж "Проверенная покупка" если user купил этот товар
- Кнопка "Полезно" (можно нажать 1 раз, учет в ReviewHelpful)

### 7.3 Форма добавления отзыва

**Поля**:
- Оценка (5 звезд, обязательно)
- Заголовок (max 200 символов, обязательно)
- Текст отзыва (max 2000 символов, обязательно)
- Достоинства (опционально)
- Недостатки (опционально)
- Фото (до 5 штук, опционально)

**Валидация**:
- Нельзя оставить отзыв, если не авторизован
- Один пользователь = один отзыв на товар
- Минимальная длина текста: 50 символов

**UI**:
- Модальное окно или отдельная страница
- Превью загруженных фото
- Счетчик символов
- Кнопка "Отправить на модерацию"

---

## 8. КОРЗИНА И ОФОРМЛЕНИЕ ЗАКАЗА

### 8.1 Корзина (страница)

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│  Корзина (3 товара)                        [Очистить корзину]│
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ═══════════════ В НАЛИЧИИ (2 товара) ════════════════════ │
│                                                             │
│  [img] Нож "Медведь"              [- 1 +]    ₽ 12 990  [✕]│
│        Сталь: AUS-8                                         │
│        Резерв до: 15:42:30                                  │
│                                                             │
│  [img] Топор "Викинг"             [- 1 +]    ₽ 8 500   [✕]│
│        Вес: 1200г                                           │
│                                                             │
│  ═══════════════ ПОД ЗАКАЗ (1 товар) ══════════════════════│
│                                                             │
│  [img] Мачете "Джунгли"           [- 1 +]    ₽ 15 000  [✕]│
│        Срок изготовления: 14-21 день                        │
│        Предоплата: ₽ 5 000 (33%)                            │
│                                                             │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Промокод: [___________] [Применить]                       │
│                                                             │
│  Итого (В наличии):              ₽ 21 490                  │
│  Итого (Под заказ):              ₽ 15 000                  │
│  Предоплата (Под заказ):         ₽ 5 000                   │
│  ─────────────────────────────────────────                 │
│  К оплате сейчас:                ₽ 26 490                  │
│                                                             │
│                              [Оформить заказ →]            │
└────────────────────────────────────────────────────────────┘
```

**Функционал**:
1. **Разделение товаров**:
   - Блок "В наличии" (сразу оплата и доставка)
   - Блок "Под заказ" (указан срок, требуется предоплата)

2. **Управление количеством**:
   - Кнопки +/- для изменения
   - Input с числом (можно ввести вручную)
   - Проверка наличия (для "В наличии")

3. **Резервирование**:
   - Таймер обратного отсчета (24-72 часа, настраивается)
   - При истечении → товар удаляется из корзины
   - Уведомление за 1 час до окончания

4. **Промокод**:
   - Поле ввода + кнопка "Применить"
   - Валидация на backend
   - Отображение скидки в итоговой сумме

5. **Итоговый расчет**:
   - Отдельные суммы для "В наличии" и "Под заказ"
   - Для "Под заказ" показывается предоплата (настраивается в админке, например 30-50%)
   - Финальная сумма к оплате

### 8.2 Хранение корзины

**Варианты**:
1. **Для авторизованных**: в базе данных (модель Cart, CartItem)
2. **Для гостей**: в localStorage (до 7 дней)

**Модель Django**:
```python
class Cart(models.Model):
    user = ForeignKey(User, null=True, blank=True)
    session_key = CharField(max_length=40, null=True)  # Для гостей
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = ForeignKey(Cart)
    product = ForeignKey(Product)
    quantity = IntegerField(default=1)
    
    # Резервирование (только для "В наличии")
    reserved_until = DateTimeField(null=True, blank=True)
    
    added_at = DateTimeField(auto_now_add=True)
```

**API endpoints**:
- `POST /api/cart/add/` - добавить товар
- `PATCH /api/cart/item/{id}/` - изменить количество
- `DELETE /api/cart/item/{id}/` - удалить товар
- `POST /api/cart/apply-promo/` - применить промокод
- `GET /api/cart/` - получить корзину

### 8.3 Оформление заказа (Checkout)

**Шаги** (Multi-step form или все на одной странице):

**Шаг 1: Контактные данные**
```
┌────────────────────────────────────────────────────────────┐
│  1. Контактные данные                                       │
├────────────────────────────────────────────────────────────┤
│  Имя: [_____________________]                              │
│  Телефон: [_____________________]                          │
│  Email: [_____________________]                            │
│                                                             │
│  ☐ Зарегистрироваться (создать аккаунт после заказа)      │
└────────────────────────────────────────────────────────────┘
```

**Шаг 2: Доставка**
```
┌────────────────────────────────────────────────────────────┐
│  2. Доставка                                                │
├────────────────────────────────────────────────────────────┤
│  Способ доставки:                                          │
│  ○ Курьером по Москве (₽ 500, 1-2 дня)                    │
│  ○ СДЭК до пункта выдачи (₽ 350, 3-5 дней)                │
│  ○ Почта России (₽ 400, 7-14 дней)                        │
│  ○ Самовывоз (бесплатно, адрес: ул. Примерная, 1)         │
│                                                             │
│  Адрес доставки:                                           │
│  Индекс: [______]                                          │
│  Город: [_____________________]                            │
│  Улица: [_____________________]                            │
│  Дом: [___] Корпус: [___] Кв: [___]                       │
│                                                             │
│  Комментарий: [________________________________]           │
└────────────────────────────────────────────────────────────┘
```

**Шаг 3: Оплата**
```
┌────────────────────────────────────────────────────────────┐
│  3. Оплата                                                  │
├────────────────────────────────────────────────────────────┤
│  Способ оплаты:                                            │
│  ○ Онлайн (картой, СБП) через ЮKassa                      │
│  ○ При получении (наличными или картой курьеру)           │
│                                                             │
│  ☐ Согласен с условиями пользовательского соглашения      │
│  ☐ Согласен на обработку персональных данных              │
└────────────────────────────────────────────────────────────┘
```

**Шаг 4: Подтверждение**
```
┌────────────────────────────────────────────────────────────┐
│  4. Подтверждение заказа                                    │
├────────────────────────────────────────────────────────────┤
│  Ваш заказ:                                                │
│  • Нож "Медведь" x1            ₽ 12 990                    │
│  • Топор "Викинг" x1           ₽ 8 500                     │
│                                                             │
│  Доставка: Курьер по Москве    ₽ 500                       │
│  Скидка (промокод NEW10):      -₽ 2 149                    │
│  ─────────────────────────────────────                     │
│  Итого:                        ₽ 19 841                    │
│                                                             │
│  Получатель: Иван Иванов                                   │
│  Телефон: +7 (999) 123-45-67                               │
│  Адрес: 101000, Москва, ул. Примерная, д.1, кв.10         │
│                                                             │
│              [← Назад]  [Оформить заказ →]                 │
└────────────────────────────────────────────────────────────┘
```

**После оформления**:
1. Если оплата онлайн → редирект на ЮKassa
2. После оплаты → страница "Спасибо за заказ"
3. Email с подтверждением и номером заказа
4. SMS с номером заказа (опционально)

### 8.4 Страница "Спасибо за заказ"

```
┌────────────────────────────────────────────────────────────┐
│                                                             │
│                    ✓ Заказ оформлен!                       │
│                                                             │
│  Номер вашего заказа: #12345                               │
│  Статус: Оплачен                                           │
│                                                             │
│  Письмо с деталями отправлено на: ivan@example.com        │
│                                                             │
│  Вы можете отслеживать статус заказа в личном кабинете.   │
│                                                             │
│         [Перейти в личный кабинет]  [На главную]          │
└────────────────────────────────────────────────────────────┘
```

---

## 9. ЛИЧНЫЙ КАБИНЕТ

### 9.1 Структура

```
┌─────────────┬──────────────────────────────────────────────┐
│             │                                              │
│  Меню:      │           Личный кабинет                    │
│             │           Иван Иванов                        │
│  • Профиль  │           ivan@example.com                   │
│  • Заказы   ├──────────────────────────────────────────────┤
│  • Избранное│                                              │
│  • Выход    │  [Активная страница]                        │
│             │                                              │
└─────────────┴──────────────────────────────────────────────┘
```

### 9.2 Страница "Мои заказы"

```
┌────────────────────────────────────────────────────────────┐
│  Мои заказы (12)                [Фильтр по статусу ▼]      │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Заказ #12345                   15.01.2025   ✓ Оплачен│ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ [img] Нож "Медведь" x1                   ₽ 12 990    │ │
│  │ [img] Топор "Викинг" x1                  ₽ 8 500     │ │
│  │                                                       │ │
│  │ Итого: ₽ 21 490                                      │ │
│  │                                                       │ │
│  │ Статус: В обработке                                  │ │
│  │ Трек-номер: 1234567890                               │ │
│  │                                                       │ │
│  │     [Подробнее]  [Повторить заказ]  [Отменить]      │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Заказ #12344                   10.01.2025 ⏱ Под заказ│ │
│  │ ...                                                   │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

**Статусы заказов**:
- 🕐 Ожидает оплаты (pending)
- ✓ Оплачен (paid)
- 📦 В обработке (processing)
- 🚚 Отправлен (shipped)
- ✅ Доставлен (delivered)
- ⏱ Под заказ (made_to_order)
- ❌ Отменен (cancelled)

**Функционал**:
- Фильтр по статусу
- Поиск по номеру заказа
- Детальная страница заказа
- Кнопка "Повторить заказ" (добавляет товары в корзину)
- Возможность отменить заказ (если статус pending/processing)

### 9.3 Детальная страница заказа

```
┌────────────────────────────────────────────────────────────┐
│  ← Назад к заказам                                         │
├────────────────────────────────────────────────────────────┤
│  Заказ #12345 от 15.01.2025                               │
│  Статус: 📦 В обработке                                    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Товары:                                                   │
│  • Нож "Медведь" x1              ₽ 12 990                  │
│  • Топор "Викинг" x1             ₽ 8 500                   │
│                                                             │
│  Доставка: Курьер по Москве      ₽ 500                     │
│  Скидка:                         -₽ 2 149                  │
│  ───────────────────────────────────────                   │
│  Итого:                          ₽ 19 841                  │
│                                                             │
│  Способ оплаты: Онлайн (карта)                            │
│  ID платежа: 2d8f7g9h-1a2b-3c4d-5e6f-7g8h9i0j1k2l         │
│                                                             │
│  Доставка:                                                 │
│  Адрес: 101000, Москва, ул. Примерная, д.1, кв.10         │
│  Получатель: Иван Иванов                                   │
│  Телефон: +7 (999) 123-45-67                               │
│  Трек-номер: 1234567890 [Отследить →]                     │
│                                                             │
│  История статусов:                                         │
│  • 15.01.2025 14:30 - Заказ создан                        │
│  • 15.01.2025 14:32 - Оплата получена                     │
│  • 15.01.2025 15:00 - Передан в обработку                 │
│  • 16.01.2025 10:00 - Отправлен (трек: 1234567890)        │
│                                                             │
│              [Скачать чек]  [Связаться с поддержкой]      │
└────────────────────────────────────────────────────────────┘
```

### 9.4 Страница "Профиль"

```
┌────────────────────────────────────────────────────────────┐
│  Профиль                                                    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Личные данные:                                            │
│  Имя: [Иван Иванов________________]                        │
│  Email: [ivan@example.com__________] ✓ Подтвержден        │
│  Телефон: [+7 (999) 123-45-67______]                      │
│                                                             │
│                               [Сохранить изменения]        │
│                                                             │
│  Смена пароля:                                             │
│  Текущий пароль: [_______________]                         │
│  Новый пароль: [_______________]                           │
│  Повтор пароля: [_______________]                          │
│                                                             │
│                               [Изменить пароль]            │
│                                                             │
│  Адреса доставки:                                          │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 📍 Москва, ул. Примерная, д.1, кв.10              │   │
│  │    [Редактировать] [Удалить]                       │   │
│  └────────────────────────────────────────────────────┘   │
│  [+ Добавить новый адрес]                                 │
└────────────────────────────────────────────────────────────┘
```

---

## 10. СТРАНИЦА АКЦИЙ И РАСПРОДАЖ

### 10.1 Layout

```
┌────────────────────────────────────────────────────────────┐
│  Акции и распродажи                                        │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                                                       │ │
│  │        [Баннер акции 1200x400]                       │ │
│  │        РАСПРОДАЖА ЗИМНЕЙ КОЛЛЕКЦИИ                   │ │
│  │        Скидки до 30%                                  │ │
│  │        До 31 января                                   │ │
│  │                                                       │ │
│  │        [Смотреть товары →]                           │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 🎁 НОВОГОДНЯЯ АКЦИЯ            До: 31.12.2025 23:59 │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ Скидка 15% на все топоры по промокоду: NEWYEAR      │ │
│  │                                                       │ │
│  │ Товары в акции:                                      │ │
│  │ [card] [card] [card] [card]                          │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 📦 БЕСПЛАТНАЯ ДОСТАВКА         До: 15.01.2025        │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ При заказе от 15 000 ₽                               │ │
│  │ [Смотреть каталог →]                                 │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### 10.2 Модель Django (promotions)

```python
class Promotion(models.Model):
    DISCOUNT_TYPE = [
        ('percentage', 'Процент'),
        ('fixed', 'Фиксированная сумма'),
        ('free_shipping', 'Бесплатная доставка'),
    ]
    
    title = CharField('Название', max_length=200)
    slug = SlugField(unique=True)
    description = TextField('Описание')
    
    # Скидка
    discount_type = CharField(choices=DISCOUNT_TYPE)
    discount_value = DecimalField(max_digits=10, decimal_places=2)
    
    # Условия
    min_order_amount = DecimalField('Минимальная сумма заказа', null=True, blank=True)
    promo_code = CharField('Промокод', max_length=50, blank=True)
    
    # Период
    start_date = DateTimeField('Начало')
    end_date = DateTimeField('Окончание')
    
    # Товары (или все, если не указано)
    products = ManyToManyField(Product, blank=True)
    categories = ManyToManyField(Category, blank=True)
    
    # Визуальное
    banner_image = ImageField('Баннер', upload_to='promotions/')
    is_featured = BooleanField('На главной', default=False)
    is_active = BooleanField('Активна', default=True)
    
    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
```

### 10.3 Функционал

- **Автоматическое применение**: если товар участвует в акции, показывается старая и новая цена
- **Промокоды**: вводятся в корзине, валидируются на backend
- **Таймер**: обратный отсчет до окончания акции
- **Фильтр**: показывать только активные / все акции
- **SEO**: отдельные страницы для крупных акций (slug)

---

## 11. ИЗБРАННОЕ (WISHLIST)

### 11.1 Модель Django

```python
class WishlistItem(models.Model):
    user = ForeignKey(User, on_delete=CASCADE)
    product = ForeignKey(Product, on_delete=CASCADE)
    added_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'product']
```

### 11.2 UI

**Кнопка в карточке товара**:
- Иконка сердца (пустое / заполненное)
- Клик → добавить/удалить из избранного
- Анимация при добавлении (scale + fill)

**Страница избранного**:
```
┌────────────────────────────────────────────────────────────┐
│  Избранное (5)                       [Очистить избранное]  │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  [Фото]  │  │  [Фото]  │  │  [Фото]  │  │  [Фото]  │  │
│  │  + в наличии │  + под заказ│  + нет    │  │          │  │
│  │  ₽ 12 990│  │  ₽ 8 500 │  │  ₽ 15 000│  │          │  │
│  │  [🛒] [✕]│  │  [🛒] [✕]│  │  [✉️] [✕]│  │          │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└────────────────────────────────────────────────────────────┘
```

**Функционал**:
- Grid как в каталоге
- Быстрое добавление в корзину
- Кнопка "Удалить" (✕)
- Если товара нет в наличии → кнопка "Уведомить о поступлении" (✉️)

---

## 12. ПОИСК

### 12.1 UI поиска

**В Header**:
- Иконка 🔍
- При клике → раскрывается input
- Начинать поиск при вводе 3+ символов
- Debounce 300ms

**Поисковая выдача** (dropdown под input):
```
┌────────────────────────────────────────────────────────┐
│  Найдено 5 товаров по запросу "охотничий"             │
├────────────────────────────────────────────────────────┤
│  [img] Нож "Охотничий"           ₽ 12 990  ✓ В наличии│
│  [img] Топор "Охотник"           ₽ 8 500   ⏱ Под заказ│
│  [img] Мачете "Джунгли"          ₽ 15 000  ✓ В наличии│
│                                                         │
│              [Показать все результаты →]               │
└────────────────────────────────────────────────────────┘
```

**Страница результатов поиска** (`/search?q=охотничий`):
- Заголовок: "Результаты поиска: охотничий (5 товаров)"
- Grid товаров как в каталоге
- Подсветка совпадений в названии
- Возможность применить фильтры
- Если ничего не найдено → "Попробуйте изменить запрос" + ссылка на каталог

### 12.2 Backend поиска (PostgreSQL Full-Text Search)

**Для MVP** (до 100 товаров):
```python
# products/views.py
from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery
from django.db.models import Q

def search_products(query):
    if len(query) < 3:
        return Product.objects.none()
    
    # Полнотекстовый поиск
    search_vector = SearchVector('name', weight='A', config='russian') + \
                    SearchVector('description', weight='B', config='russian')
    search_query = SearchQuery(query, config='russian')
    
    results = Product.objects.annotate(
        search=search_vector,
        rank=SearchRank(search_vector, search_query)
    ).filter(search=search_query).order_by('-rank', '-created_at')
    
    return results[:20]  # Топ 20 результатов
```

**Для масштаба** (>1000 товаров):
- Elasticsearch + django-elasticsearch-dsl
- Индексация: название, описание, характеристики
- Автодополнение (autocomplete)
- Поиск с опечатками (fuzzy search)

---

## 13. ИНТЕГРАЦИЯ ЮKASSA

### 13.1 Модель платежа

```python
class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('waiting_for_capture', 'Ожидает подтверждения'),
        ('succeeded', 'Успешно'),
        ('canceled', 'Отменен'),
        ('refunded', 'Возвращен'),
    ]
    
    order = ForeignKey(Order, on_delete=PROTECT)
    
    # ID от ЮKassa
    payment_id = CharField(max_length=100, unique=True)
    
    # Сумма
    amount = DecimalField(max_digits=10, decimal_places=2)
    currency = CharField(max_length=3, default='RUB')
    
    # Статус
    status = CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    
    # Данные от ЮKassa (JSON)
    metadata = JSONField(default=dict, blank=True)
    
    # Идемпотентность
    idempotency_key = UUIDField(unique=True, default=uuid.uuid4)
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'Платеж {self.payment_id} - {self.amount} ₽'
```

### 13.2 Процесс оплаты

**Шаг 1: Создание платежа**
```python
# orders/views.py
from yookassa import Payment as YooKassaPayment, Configuration

# Настройка ЮKassa
Configuration.account_id = settings.YUKASSA_SHOP_ID
Configuration.secret_key = settings.YUKASSA_SECRET_KEY

def create_payment(order):
    idempotency_key = str(uuid.uuid4())
    
    payment = YooKassaPayment.create({
        "amount": {
            "value": str(order.total_amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"https://shop.example.com/order/{order.id}/success"
        },
        "capture": True,
        "description": f"Заказ #{order.id}",
        "metadata": {
            "order_id": order.id
        }
    }, idempotency_key)
    
    # Сохранить в базу
    Payment.objects.create(
        order=order,
        payment_id=payment.id,
        amount=order.total_amount,
        status='pending',
        metadata=payment,
        idempotency_key=idempotency_key
    )
    
    return payment.confirmation.confirmation_url  # URL для редиректа
```

**Шаг 2: Обработка вебхука**
```python
# orders/webhooks.py
import hmac
import hashlib
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def yukassa_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # 1. Проверить IP (whitelist ЮKassa)
    allowed_ips = ['185.71.76.0/27', '185.71.77.0/27', '77.75.153.0/25', '77.75.156.11', '77.75.156.35', '77.75.154.128/25']
    client_ip = request.META.get('REMOTE_ADDR')
    # TODO: проверить IP в whitelist
    
    # 2. Проверить подпись
    body = request.body.decode('utf-8')
    data = json.loads(body)
    
    # 3. Обработать событие
    event_type = data.get('event')
    payment_data = data.get('object')
    
    if event_type == 'payment.succeeded':
        handle_payment_succeeded(payment_data)
    elif event_type == 'payment.canceled':
        handle_payment_canceled(payment_data)
    elif event_type == 'refund.succeeded':
        handle_refund_succeeded(payment_data)
    
    return JsonResponse({'status': 'ok'})

def handle_payment_succeeded(payment_data):
    payment_id = payment_data['id']
    
    try:
        payment = Payment.objects.get(payment_id=payment_id)
        payment.status = 'succeeded'
        payment.metadata = payment_data
        payment.save()
        
        # Обновить статус заказа
        order = payment.order
        order.status = 'paid'
        order.save()
        
        # Отправить email
        send_order_confirmation_email.delay(order.id)
        
        # Если "В наличии" → зарезервировать товар
        reserve_stock(order)
        
    except Payment.DoesNotExist:
        # Логировать ошибку
        pass
```

### 13.3 Возвраты

```python
from yookassa import Refund

def create_refund(payment, amount, reason=''):
    idempotency_key = str(uuid.uuid4())
    
    refund = Refund.create({
        "payment_id": payment.payment_id,
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "description": reason
    }, idempotency_key)
    
    # Обновить статус платежа
    payment.status = 'refunded'
    payment.save()
    
    # Обновить заказ
    payment.order.status = 'cancelled'
    payment.order.save()
    
    # Вернуть товар в наличие
    release_stock(payment.order)
```

---

## 14. EMAIL УВЕДОМЛЕНИЯ

### 14.1 Типы писем

1. **Регистрация**: Подтверждение email
2. **Восстановление пароля**
3. **Новый заказ**: Подтверждение с деталями
4. **Оплата получена**: Чек и следующие шаги
5. **Заказ отправлен**: Трек-номер
6. **Заказ доставлен**: Просьба оставить отзыв
7. **Заказ отменен**: Информация о возврате
8. **Товар в наличии**: Уведомление из wishlist
9. **Модерация отзыва**: Отзыв опубликован

### 14.2 Настройка Django

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yandex.ru'  # Или другой SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'noreply@shop.example.com'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD')
DEFAULT_FROM_EMAIL = 'Мастерская ножей <noreply@shop.example.com>'
```

### 14.3 Celery задачи

```python
# orders/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string

@shared_task
def send_order_confirmation_email(order_id):
    order = Order.objects.get(id=order_id)
    
    subject = f'Заказ #{order.id} подтвержден'
    html_message = render_to_string('emails/order_confirmation.html', {
        'order': order,
        'items': order.items.all()
    })
    
    send_mail(
        subject=subject,
        message='',  # Plain text version
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        html_message=html_message,
        fail_silently=False
    )

@shared_task
def send_order_shipped_email(order_id, tracking_number):
    order = Order.objects.get(id=order_id)
    
    subject = f'Заказ #{order.id} отправлен'
    html_message = render_to_string('emails/order_shipped.html', {
        'order': order,
        'tracking_number': tracking_number
    })
    
    send_mail(
        subject=subject,
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        html_message=html_message,
        fail_silently=False
    )
```

### 14.4 Шаблоны писем

**Структура**:
```
templates/emails/
├── base.html              # Базовый шаблон (header, footer)
├── order_confirmation.html
├── order_shipped.html
├── order_delivered.html
├── password_reset.html
└── product_available.html
```

**Пример** (order_confirmation.html):
```html
{% extends 'emails/base.html' %}

{% block content %}
<h1>Спасибо за заказ!</h1>

<p>Здравствуйте, {{ order.name }}!</p>

<p>Ваш заказ #{{ order.id }} успешно оформлен и оплачен.</p>

<h2>Детали заказа:</h2>

<table>
  <tr>
    <th>Товар</th>
    <th>Количество</th>
    <th>Цена</th>
  </tr>
  {% for item in items %}
  <tr>
    <td>{{ item.product.name }}</td>
    <td>{{ item.quantity }}</td>
    <td>{{ item.price }} ₽</td>
  </tr>
  {% endfor %}
</table>

<p><strong>Итого: {{ order.total_amount }} ₽</strong></p>

<p>Адрес доставки: {{ order.delivery_address }}</p>

<p>Вы можете отследить статус заказа в <a href="https://shop.example.com/account/orders">личном кабинете</a>.</p>
{% endblock %}
```

---

## 15. АДМИНКА DJANGO

### 15.1 Кастомизация Admin

```python
# admin.py
from django.contrib import admin
from django.utils.html import format_html

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'thumbnail_preview', 'name', 'category', 'price', 
        'stock_status_badge', 'is_featured', 'views_count', 'created_at'
    ]
    list_filter = ['stock_status', 'category', 'is_featured', 'is_new', 'created_at']
    search_fields = ['name', 'description', 'blade_material']
    prepopulated_fields = {'slug': ('name',)}
    
    readonly_fields = ['views_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'slug', 'category', 'description', 'price', 'stock_status')
        }),
        ('Характеристики', {
            'fields': (
                'blade_length', 'total_length', 'weight', 
                'blade_material', 'handle_material', 'hardness', 'specifications'
            )
        }),
        ('SEO и отображение', {
            'fields': ('is_featured', 'is_new', 'views_count')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ProductImageInline]
    
    def thumbnail_preview(self, obj):
        first_image = obj.images.first()
        if first_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                first_image.image.url
            )
        return '-'
    thumbnail_preview.short_description = 'Фото'
    
    def stock_status_badge(self, obj):
        colors = {
            'in_stock': 'green',
            'made_to_order': 'blue',
            'out_of_stock': 'gray'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px;">{}</span>',
            colors.get(obj.stock_status, 'gray'),
            obj.get_stock_status_display()
        )
    stock_status_badge.short_description = 'Статус'
    
    actions = ['mark_as_featured', 'mark_as_in_stock']
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} товаров добавлено в слайдер')
    mark_as_featured.short_description = 'Добавить в слайдер на главной'
    
    def mark_as_in_stock(self, request, queryset):
        updated = queryset.update(stock_status='in_stock')
        self.message_user(request, f'{updated} товаров отмечено как "В наличии"')
    mark_as_in_stock.short_description = 'Отметить "В наличии"'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'email', 'phone', 'total_amount', 
        'status_badge', 'payment_status', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'delivery_method']
    search_fields = ['id', 'email', 'phone', 'name']
    readonly_fields = ['created_at', 'updated_at', 'payment_link']
    
    fieldsets = (
        ('Клиент', {
            'fields': ('user', 'name', 'email', 'phone')
        }),
        ('Доставка', {
            'fields': ('delivery_address', 'delivery_method', 'delivery_cost')
        }),
        ('Оплата', {
            'fields': ('total_amount', 'status', 'payment_id', 'payment_link')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    inlines = [OrderItemInline]
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'processing': 'blue',
            'shipped': 'purple',
            'delivered': 'darkgreen',
            'cancelled': 'red'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def payment_status(self, obj):
        try:
            payment = obj.payment_set.first()
            return payment.status if payment else '-'
        except:
            return '-'
    payment_status.short_description = 'Платеж'
    
    def payment_link(self, obj):
        try:
            payment = obj.payment_set.first()
            if payment:
                return format_html(
                    '<a href="https://yookassa.ru/payments/{}" target="_blank">Посмотреть в ЮKassa</a>',
                    payment.payment_id
                )
        except:
            pass
        return '-'
    payment_link.short_description = 'Ссылка на платеж'
    
    actions = ['mark_as_shipped', 'export_to_excel']
    
    def mark_as_shipped(self, request, queryset):
        for order in queryset:
            order.status = 'shipped'
            order.save()
            # Отправить email с трек-номером
            send_order_shipped_email.delay(order.id, 'TRACK123')
        
        self.message_user(request, f'{queryset.count()} заказов отмечено как "Отправлено"')
    mark_as_shipped.short_description = 'Отметить как отправленные'
```

### 15.2 Dashboard (опционально)

Для расширенной статистики можно использовать:
- **django-admin-tools**: кастомные dashboard виджеты
- **django-grappelli**: улучшенный UI админки
- **django-suit**: современная тема для admin

**Виджеты для dashboard**:
- График продаж за последние 30 дней
- Топ-10 популярных товаров
- Последние заказы (статусы)
- Сумма продаж за день/неделю/месяц
- Товары с низким остатком

---

## 16. API ENDPOINTS (DRF)

### 16.1 Список основных endpoints

```python
# urls.py
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/auth/', include('rest_framework.urls')),
    path('api/webhooks/yukassa/', yukassa_webhook, name='yukassa_webhook'),
]
```

### 16.2 Основные ViewSets

```python
# products/views.py
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'category': ['exact'],
        'price': ['gte', 'lte'],
        'blade_length': ['gte', 'lte'],
        'stock_status': ['exact'],
    }
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'views_count']
    ordering = ['-created_at']
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Увеличить счетчик просмотров
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Товары для слайдера на главной"""
        products = self.queryset.filter(is_featured=True)[:5]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def new(self, request):
        """Новинки"""
        products = self.queryset.filter(is_new=True)[:6]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """Похожие товары"""
        product = self.get_object()
        similar = Product.objects.filter(
            category=product.category
        ).exclude(id=product.id).order_by('?')[:6]
        serializer = self.get_serializer(similar, many=True)
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=self.request.user)
        else:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            cart, _ = Cart.objects.get_or_create(session_key=session_key)
        return CartItem.objects.filter(cart=cart)
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        """Добавить товар в корзину"""
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        product = Product.objects.get(id=product_id)
        
        # Получить или создать корзину
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            cart, _ = Cart.objects.get_or_create(session_key=session_key)
        
        # Добавить товар
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        # Если "В наличии" → зарезервировать
        if product.stock_status == 'in_stock':
            reserve_until = timezone.now() + timedelta(hours=24)
            cart_item.reserved_until = reserve_until
            cart_item.save()
        
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data)
```

### 16.3 Пагинация

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 24,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}
```

---

## 17. ИНФРАСТРУКТУРА И DEPLOYMENT

### 17.1 Docker Compose (Production)

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - django
      - nextjs
    restart: unless-stopped

  django:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/shopdb
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - YUKASSA_SHOP_ID=${YUKASSA_SHOP_ID}
      - YUKASSA_SECRET_KEY=${YUKASSA_SECRET_KEY}
      - SECRET_KEY=${DJANGO_SECRET_KEY}
      - DEBUG=False
      - ALLOWED_HOSTS=shop.example.com
    depends_on:
      - db
      - redis
      - minio
    restart: unless-stopped

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A config worker -l info
    volumes:
      - media_volume:/app/media
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/shopdb
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A config beat -l info
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/shopdb
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  nextjs:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - NEXT_PUBLIC_API_URL=https://shop.example.com/api
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=shopdb
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY}
    restart: unless-stopped

volumes:
  postgres_data:
  minio_data:
  static_volume:
  media_volume:
```

### 17.2 Nginx конфигурация

```nginx
# nginx/conf.d/default.conf
upstream django {
    server django:8000;
}

upstream nextjs {
    server nextjs:3000;
}

server {
    listen 80;
    server_name shop.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name shop.example.com;
    
    ssl_certificate /etc/letsencrypt/live/shop.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/shop.example.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max