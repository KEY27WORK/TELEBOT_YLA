# База с уже установленными браузерами и системными зависимостями Playwright
# (Python 3.11, Ubuntu Jammy, Chromium/Firefox/WebKit в комплекте)
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Удобные env-ки для Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Рабочая директория внутри контейнера
WORKDIR /app

# Системные пакеты: xvfb для headful-дебага, шрифты (латиница/кириллица/emoji)
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      xvfb \
      fonts-dejavu-core \
      fonts-dejavu-extra \
      fonts-noto \
      fonts-noto-color-emoji \
      ca-certificates \
      && rm -rf /var/lib/apt/lists/*

# (Опционально) Установка зависимостей: если есть requirements.txt – установить.
# Файл можно держать в корне репозитория рядом с Dockerfile.
COPY requirements.txt /app/requirements.txt
RUN bash -lc 'test -f requirements.txt && pip install --no-cache-dir -r requirements.txt || true'

# Кладём исходники
# Если в репо есть не только src/, добавь .dockerignore, чтобы не тащить лишнее.
COPY src/ /app/src/

# Удобный PYTHONPATH, чтобы запускать "python -m app.bot.main"
ENV PYTHONPATH=/app/src

# На проде запускаем headless (всё управляется конфигом 60_playwright.yaml)
CMD ["python", "-m", "app.bot.main"]