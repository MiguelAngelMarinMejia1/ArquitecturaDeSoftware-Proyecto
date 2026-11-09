# Image for the catalog microservice (Flask).
# Build it alone with: docker build -t hotelmdj-catalog ./catalog_service

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

# Without Docker, run: python app.py
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "app:app"]
