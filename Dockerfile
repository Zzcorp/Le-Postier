FROM python:3.11-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=le_postier.settings_production \
    PORT=10000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Ensure the module structure is correct
RUN python -c "import os; print('Project structure:'); \
    for root, dirs, files in os.walk('/app'): \
        level = root.replace('/app', '').count(os.sep); \
        indent = ' ' * 2 * level; \
        print(f'{indent}{os.path.basename(root)}/'); \
        subindent = ' ' * 2 * (level + 1); \
        for file in files[:5]: print(f'{subindent}{file}')"

# Create necessary directories
RUN mkdir -p staticfiles media

# Try to collect static files (allow failure for now)
RUN python manage.py collectstatic --noinput || echo "Collectstatic failed, continuing..."

# Create user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 10000

# Start command
CMD ["sh", "-c", "python manage.py migrate --noinput || true && gunicorn le_postier.wsgi:application --bind 0.0.0.0:$PORT --workers 2"]