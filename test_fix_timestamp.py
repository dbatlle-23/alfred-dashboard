#!/usr/bin/env python3
"""
Script para probar la corrección de timestamp en get_daily_readings_for_tag_monthly
"""

import os
import sys
from datetime import datetime
import pandas as pd
from utils.api import get_daily_readings_for_tag_monthly, ensure_project_folder_exists
from utils.logging import get_logger

# Configurar logger
logger = get_logger(__name__)

def main():
    print("Iniciando prueba de get_daily_readings_for_tag_monthly...")
    
    # Parámetros para la prueba
    asset_id = "DQ5NGTRVKEW57"
    tag = {
        "device_id": "some_device_id",  # Sustituir con valores reales si se conocen
        "sensor_id": "some_sensor_id",   # Sustituir con valores reales si se conocen
        "gateway_id": "some_gateway_id", # Sustituir con valores reales si se conocen
        "tag_name": "TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER"
    }
    
    # Usar el mes actual
    current_date = datetime.now()
    month = f"{current_date.year}-{current_date.month:02d}"
    
    # Asegurar que existe la carpeta del proyecto
    project_id = "general"
    project_folder = ensure_project_folder_exists(project_id)
    
    print(f"Llamando a get_daily_readings_for_tag_monthly para asset_id={asset_id}, month={month}")
    
    # Llamar a la función con la corrección aplicada
    result = get_daily_readings_for_tag_monthly(asset_id, tag, month, project_folder)
    
    # Verificar el resultado
    if result is not None and not result.empty:
        print(f"Se obtuvieron {len(result)} registros")
        print("\nPrimeros 5 registros:")
        print(result.head())
    else:
        print("No se obtuvieron datos")
    
    # Verificar si se creó o actualizó el archivo
    file_name = f"daily_readings_{asset_id}__{tag['tag_name']}.csv"
    file_path = os.path.join(project_folder, file_name)
    
    if os.path.exists(file_path):
        print(f"\nEl archivo {file_path} existe")
        try:
            file_data = pd.read_csv(file_path)
            print(f"El archivo tiene {len(file_data)} registros")
            print("\nPrimeros 5 registros del archivo:")
            print(file_data.head())
        except Exception as e:
            print(f"Error al leer el archivo: {str(e)}")
    else:
        print(f"\nEl archivo {file_path} no existe")

if __name__ == "__main__":
    main() 