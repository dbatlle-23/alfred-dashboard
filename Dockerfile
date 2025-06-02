FROM python:3.9-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    pkg-config \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Actualizar pip
RUN pip install --upgrade pip

# Copiar requirements.txt primero para aprovechar la caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear directorio de configuración
RUN mkdir -p config logs

# Crear usuario no-root
RUN adduser --disabled-password --gecos '' --shell /bin/bash user \
    && chown -R user:user /app
USER user

# Exponer el puerto (Railway asigna automáticamente)
EXPOSE 8050

# Comando para ejecutar la aplicación con Gunicorn
# Railway inyecta PORT automáticamente
CMD ["sh", "-c", "gunicorn app:server --bind 0.0.0.0:${PORT:-8050} --timeout 120 --workers 1 --max-requests 1000 --preload"]
