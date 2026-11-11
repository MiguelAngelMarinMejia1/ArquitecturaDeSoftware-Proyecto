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

# Gather CSS, JS and site photos into /app/staticfiles; WhiteNoise serves them.
# Translations (.mo) are committed in locale/, so no compile step is needed.
RUN python manage.py collectstatic --noinput \
    && mkdir -p /app/data /app/media

EXPOSE 8000

# On start: create/update tables, load the sample rooms, then serve with
# gunicorn (production WSGI server). 3 workers: Django calls the Flask
# services synchronously, so one slow call must not block every visitor.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py loaddata seed && exec gunicorn hotelMDJ.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout 60 --access-logfile - --error-logfile -"]
