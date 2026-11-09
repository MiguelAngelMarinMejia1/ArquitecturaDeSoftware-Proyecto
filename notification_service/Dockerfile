# Image for the notification microservice (Flask).
# Build it alone with: docker build -t hotelmdj-notifications ./notification_service

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Its own SQLite file lives here (a named volume in docker-compose.yml).
RUN mkdir -p /app/data

EXPOSE 5003

CMD ["gunicorn", "--bind", "0.0.0.0:5003", "--workers", "2", "app:app"]
