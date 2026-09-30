# Imagen del microservicio de cotizacion (Flask).
#
# Es independiente de la imagen de Django: tiene sus propias dependencias y se
# puede construir, desplegar y escalar por separado.
#
# Construir solo esta imagen:   docker build -t hotelmdj-pricing ./pricing_service
# Normalmente no hace falta: docker compose la construye por ti.

# 1. Imagen base: Python 3.11 en su version "slim" (liviana).
FROM python:3.11-slim

# 2. Ajustes de Python para contenedores (sin .pyc y logs sin buffer).
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Carpeta de trabajo dentro del contenedor.
WORKDIR /app

# 4. Instalar dependencias primero para aprovechar la cache de Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el codigo del microservicio.
COPY . .

# 6. Puerto en el que escucha Flask dentro de la red de Docker.
EXPOSE 5000

# 7. Arrancar con gunicorn, un servidor de produccion para apps Python.
#    - --bind 0.0.0.0:5000  escucha en todas las interfaces, para que Nginx llegue
#    - --workers 2          dos procesos atienden peticiones en paralelo
#    - app:app              "del archivo app.py, usa el objeto app"
#    En tu PC (sin Docker) puedes usar simplemente: python app.py
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
