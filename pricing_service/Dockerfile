# Image for the pricing microservice (Flask).
# Independent from the Django image: own dependencies, built and scaled apart.
# Build it alone with: docker build -t hotelmdj-pricing ./pricing_service
# (docker compose builds it for you.)

FROM python:3.11-slim

# No .pyc files; print logs immediately.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first to take advantage of Docker's layer cache.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# gunicorn is a production server for Python apps.
#   --bind 0.0.0.0:5000  listen on every interface so Nginx can reach it
#   --workers 2          two processes serve requests in parallel
#   app:app              "the app object inside app.py"
# Without Docker, run: python app.py
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
