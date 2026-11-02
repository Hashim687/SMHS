FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -r -u 1001 smhs
COPY . .
RUN chown -R smhs /app
USER smhs
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py createcachetable && python manage.py seed && gunicorn smhs.wsgi:application -b 0.0.0.0:8000 -w 3 --access-logfile - --timeout 30"]
