# Image for the Django monolith (Hotel MDJ).
# Build it alone with: docker build -t hotelmdj-django .
# (docker compose builds it for you.)

FROM python:3.11-slim

# No .pyc files; print logs immediately so "docker compose logs" shows them.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies before copying the code, so Docker can reuse this
# cached layer when only the code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project (except what .dockerignore excludes).
COPY . .

# Folder for the SQLite file; docker-compose.yml mounts a volume here.
RUN mkdir -p /app/data

EXPOSE 8000

# On start: create/update tables, load the sample rooms, run the server.
# 0.0.0.0 lets Nginx reach Django from another container.
# runserver is a development server: fine for this workshop, not for production.
CMD ["sh", "-c", "python manage.py migrate && python manage.py loaddata seed && python manage.py runserver 0.0.0.0:8000"]
