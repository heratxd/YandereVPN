FROM python:3.10-slim

# Настройки часового пояса и окружения Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow

WORKDIR /app

# Установка системных зависимостей для сборки некоторых библиотек и Certbot
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    certbot \
    && rm -rf /var/lib/apt/lists/*

# Копирование требований и их установка
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода бота
COPY . .

# Команда для запуска бота
CMD ["python", "main.py"]
