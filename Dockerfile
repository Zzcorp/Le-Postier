FROM python:3.11-slim
WORKDIR /app
RUN pip install django==4.2.7 gunicorn==21.2.0
COPY simple_app.py .
EXPOSE 10000
CMD ["gunicorn", "simple_app:application", "--bind", "0.0.0.0:10000", "--workers", "1"]