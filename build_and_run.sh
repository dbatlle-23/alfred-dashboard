#!/bin/bash

# Construir la imagen Docker
echo "Construyendo la imagen Docker..."
docker-compose build

# Ejecutar el contenedor
echo "Iniciando el contenedor..."
docker-compose up -d

echo "Alfred Dashboard está ejecutándose en http://localhost:8050"
