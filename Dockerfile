# Free-hosting image (Render etc.): builds the React site, then serves it and the API from Django.
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -r -u 1001 smhs
COPY backend/ .
COPY --from=web /web/dist ./frontend_dist
RUN chown -R smhs /app
USER smhs
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py createcachetable && (python manage.py shell -c \"import sys; from clinic.models import Department; sys.exit(0 if Department.objects.exists() else 1)\" || python manage.py seed) && gunicorn smhs.wsgi:application -b 0.0.0.0:${PORT:-10000} -w 2 --access-logfile - --timeout 60"]
