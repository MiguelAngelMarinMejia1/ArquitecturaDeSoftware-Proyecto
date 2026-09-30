# Imagen del monolito Django (Hotel MDJ).
#
# Construir solo esta imagen:   docker build -t hotelmdj-django .
# Normalmente no hace falta: docker compose la construye por ti.

# 1. Imagen base: Python 3.11 en su version "slim" (liviana).
FROM python:3.11-slim

# 2. Ajustes de Python para contenedores:
#    - no crear archivos .pyc
#    - imprimir los logs al instante (sin buffer) para verlos en "docker compose logs"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Carpeta de trabajo dentro del contenedor. Todo lo siguiente pasa aqui.
WORKDIR /app

# 4. Instalar dependencias ANTES de copiar el codigo.
#    Docker guarda cada paso en cache: si solo cambias codigo y no
#    requirements.txt, este paso no se repite y la construccion es mas rapida.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el codigo del proyecto (lo que excluye .dockerignore no se copia).
COPY . .

# 6. Carpeta donde vivira el archivo SQLite. docker-compose.yml monta aqui un
#    volumen para que los datos no se pierdan al recrear el contenedor.
RUN mkdir -p /app/data

# 7. Puerto en el que escucha Django dentro de la red de Docker.
EXPOSE 8000

# 8. Comando al arrancar el contenedor:
#    - migrate:          crea/actualiza las tablas en SQLite
#    - loaddata seed:    carga los tipos de habitacion y habitaciones de ejemplo
#    - runserver 0.0.0.0 escucha en todas las interfaces (no solo localhost),
#      necesario para que Nginx pueda llegar a Django desde otro contenedor.
#    runserver es el servidor de desarrollo: suficiente para el taller, no para produccion.
CMD ["sh", "-c", "python manage.py migrate && python manage.py loaddata seed && python manage.py runserver 0.0.0.0:8000"]
