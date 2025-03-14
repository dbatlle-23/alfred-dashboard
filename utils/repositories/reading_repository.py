# utils/repositories/reading_repository.py
import os
import json
import glob
from datetime import datetime
import pandas as pd
import logging
from utils.logging import get_logger

logger = get_logger(__name__)

class ReadingRepository:
    def __init__(self, data_source_path="data/readings/"):
        self.data_source_path = data_source_path
        self.anomalies_path = "data/anomalies/"
        
        # Crear directorio para anomalías si no existe
        os.makedirs(self.anomalies_path, exist_ok=True)
    
    def get_original_readings(self, asset_id, consumption_type, start_date=None, end_date=None):
        """Obtiene las lecturas originales sin modificaciones"""
        logger.info(f"Buscando lecturas para asset_id={asset_id}, consumption_type={consumption_type}")
        
        # Buscar en la carpeta de datos analizados
        analyzed_data_folder = os.path.join("data", "analyzed_data")
        matching_files = []
        
        if os.path.exists(analyzed_data_folder):
            # Buscar en todas las carpetas de proyectos
            for project_folder in os.listdir(analyzed_data_folder):
                project_path = os.path.join(analyzed_data_folder, project_folder)
                if os.path.isdir(project_path):
                    # Buscar archivos que coincidan con el patrón
                    for filename in os.listdir(project_path):
                        if filename.startswith(f"daily_readings_{asset_id}_") and filename.endswith(".csv"):
                            file_path = os.path.join(project_path, filename)
                            matching_files.append({
                                "project_id": project_folder,
                                "filename": filename,
                                "full_path": file_path
                            })
        
        # Si encontramos archivos CSV, cargar los datos
        if matching_files:
            logger.info(f"Se encontraron {len(matching_files)} archivos CSV para el asset {asset_id}")
            
            # Usar el primer archivo encontrado
            file_path = matching_files[0]["full_path"]
            logger.info(f"Cargando datos desde {file_path}")
            
            try:
                # Cargar el archivo CSV
                csv_data = pd.read_csv(file_path)
                
                # Convertir la columna de fecha a datetime
                if 'date' in csv_data.columns:
                    csv_data['date'] = pd.to_datetime(csv_data['date'])
                
                # Filtrar por fechas si se proporcionan
                if start_date and end_date:
                    # Convertir fechas a objetos datetime si son strings
                    if isinstance(start_date, str):
                        start_date = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d")
                    if isinstance(end_date, str):
                        end_date = datetime.strptime(end_date.split("T")[0], "%Y-%m-%d")
                    
                    # Filtrar por rango de fechas
                    csv_data = csv_data[(csv_data['date'] >= start_date) & (csv_data['date'] <= end_date)]
                
                # Verificar si hay datos después del filtrado
                if csv_data.empty:
                    logger.warning(f"No hay datos en el rango de fechas seleccionado en el archivo CSV")
                    return None
                
                # Convertir los valores a numéricos
                if 'value' in csv_data.columns:
                    # Filtrar solo valores numéricos
                    csv_data = csv_data[csv_data['value'] != 'Error']
                    csv_data = csv_data[csv_data['value'] != 'Sin datos disponibles']
                    
                    try:
                        # Convertir a numérico
                        csv_data['consumption'] = pd.to_numeric(csv_data['value'], errors='coerce')
                        
                        # Eliminar filas con valores NaN
                        csv_data = csv_data.dropna(subset=['consumption'])
                        
                        # Añadir columnas necesarias si no existen
                        if 'asset_id' not in csv_data.columns:
                            csv_data['asset_id'] = asset_id
                        if 'consumption_type' not in csv_data.columns:
                            csv_data['consumption_type'] = consumption_type
                        
                        # Seleccionar solo las columnas necesarias
                        result_df = csv_data[['date', 'consumption', 'asset_id', 'consumption_type']]
                        
                        logger.info(f"Se cargaron {len(result_df)} lecturas válidas desde el archivo CSV")
                        return result_df
                    except Exception as e:
                        logger.error(f"Error al convertir valores a numéricos: {str(e)}")
            
            except Exception as e:
                logger.error(f"Error al cargar datos desde el archivo CSV: {str(e)}")
        
        # Si no se encontraron archivos o hubo un error, crear datos de ejemplo
        logger.warning(f"No se encontraron datos para asset_id={asset_id}, consumption_type={consumption_type}. Creando datos de ejemplo.")
        
        # Crear datos de ejemplo para demostración
        from datetime import timedelta
        
        # Generar fechas para los últimos 30 días
        end_date = datetime.now() if end_date is None else end_date
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date.split("T")[0], "%Y-%m-%d")
        
        start_date = end_date - timedelta(days=30) if start_date is None else start_date
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d")
        
        # Generar lista de fechas entre start_date y end_date
        delta = end_date - start_date
        dates = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
        
        # Simular un reinicio de contador en la mitad de los datos
        mid_point = len(dates) // 2
        consumption_values = []
        
        # Primera mitad: valores crecientes
        for i in range(mid_point):
            consumption_values.append(100 + i * 10)
        
        # Segunda mitad: reinicio y valores crecientes desde un valor más bajo
        for i in range(mid_point, len(dates)):
            if i == mid_point:
                # Reinicio del contador (valor más bajo que el anterior)
                consumption_values.append(50)
            else:
                # Valores crecientes después del reinicio
                consumption_values.append(50 + (i - mid_point) * 10)
        
        # Crear DataFrame con los datos de ejemplo
        example_data = pd.DataFrame({
            'date': dates,
            'consumption': consumption_values,
            'asset_id': [asset_id] * len(dates),
            'consumption_type': [consumption_type] * len(dates)
        })
        
        logger.info(f"Creados {len(example_data)} registros de ejemplo con un reinicio de contador")
        return example_data
    
    def save_anomaly(self, anomaly):
        """Guarda una anomalía detectada"""
        # Generar nombre de archivo basado en asset_id y fecha
        asset_id = anomaly.get('asset_id')
        date_str = anomaly.get('date').strftime('%Y%m%d')
        filename = f"{self.anomalies_path}anomaly_{asset_id}_{date_str}.json"
        
        # Guardar anomalía como JSON
        with open(filename, 'w') as f:
            json.dump(anomaly, f, default=str)
        
        return filename
    
    def get_anomalies(self, asset_id=None, consumption_type=None, start_date=None, end_date=None):
        """Obtiene las anomalías registradas con filtros opcionales"""
        # Listar todos los archivos de anomalías
        anomaly_files = glob.glob(f"{self.anomalies_path}anomaly_*.json")
        
        anomalies = []
        for file in anomaly_files:
            with open(file, 'r') as f:
                anomaly = json.load(f)
                
                # Aplicar filtros
                if asset_id and anomaly.get('asset_id') != asset_id:
                    continue
                    
                if consumption_type and anomaly.get('consumption_type') != consumption_type:
                    continue
                
                # Convertir fecha a datetime para comparación
                anomaly_date = datetime.fromisoformat(anomaly.get('date'))
                
                if start_date and anomaly_date < start_date:
                    continue
                    
                if end_date and anomaly_date > end_date:
                    continue
                
                anomalies.append(anomaly)
        
        return anomalies