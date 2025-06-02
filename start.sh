#!/bin/bash

# Script de inicio para Railway
echo "=== Alfred Dashboard - Railway Startup Script ==="

# Verificar variables de entorno críticas
echo "Verificando variables de entorno..."

# Establecer puerto por defecto si no está definido
if [ -z "$PORT" ]; then
    export PORT=8050
    echo "PORT no definido, usando puerto por defecto: $PORT"
else
    echo "Puerto asignado por Railway: $PORT"
fi

# Verificar que el puerto sea válido
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "ERROR: Puerto inválido '$PORT', usando 8050"
    export PORT=8050
fi

echo "Iniciando servidor en puerto $PORT..."
echo "Comando: gunicorn app:server --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --max-requests 1000 --preload"

# Ejecutar Gunicorn
exec gunicorn app:server \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --workers 1 \
    --max-requests 1000 \
    --preload \
    --access-logfile - \
    --error-logfile - 