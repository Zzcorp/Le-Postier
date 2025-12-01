FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=le_postier.settings \
    PORT=10000

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Debug: Check structure
RUN echo "=== Project Structure ===" && \
    ls -la && \
    echo "=== Settings Check ===" && \
    python -c "from django.conf import settings; print('DEBUG:', settings.DEBUG); print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)"

RUN mkdir -p staticfiles media
RUN python manage.py collectstatic --noinput || true

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:10000/ || exit 1

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 10000

CMD ["sh", "-c", "echo 'Starting Django app...' && python manage.py migrate --noinput || true && gunicorn le_postier.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --access-logfile - --error-logfile -"]