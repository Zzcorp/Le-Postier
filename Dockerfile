FROM python:3.11.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=le_postier.settings \
    PORT=10000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p staticfiles media && \
    python manage.py collectstatic --noinput || true && \
    python manage.py migrate --run-syncdb || true

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 10000

CMD ["gunicorn", "le_postier.wsgi:application", "--bind", "0.0.0.0:10000", "--workers", "2", "--timeout", "120"]