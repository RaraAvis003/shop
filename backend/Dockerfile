FROM python:3.11-slim

# Установка системных зависимостей (добавляем netcat для проверки БД)
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Копирование и настройка entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Создание директорий для логов и медиа
RUN mkdir -p logs media staticfiles

# Открытие порта
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]