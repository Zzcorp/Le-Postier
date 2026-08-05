FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=le_postier.settings

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# The repo is developed on Windows: normalize line endings on the entrypoint
# so /bin/sh never sees a stray \r, then make it executable.
RUN sed -i 's/\r$//' deploy/entrypoint.sh && chmod +x deploy/entrypoint.sh

# Non-root runtime user. /data/media is the MEDIA_ROOT bind-mount target,
# /app/staticfiles receives collectstatic output at container start.
RUN useradd --create-home appuser && \
    mkdir -p /app/staticfiles /data/media && \
    chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000

# No migrate/collectstatic at build time — the entrypoint runs them at
# container start, when the database and the .env are actually available.
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
