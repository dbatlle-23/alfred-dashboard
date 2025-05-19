import os
import pandas as pd
import glob
import re
from typing import Dict, List, Optional, Tuple, Union
import logging
import numpy as np
from datetime import datetime, timedelta
import time
from functools import lru_cache

# Configurar logging
logger = logging.getLogger(__name__)

# Variable global para almacenar el estado de debug
_DEBUG_MODE = None
_DEBUG_CHECKED = False

# Global cache dictionary and timestamp for in-memory caching
_CSV_DATA_CACHE = {}
_CACHE_TIMESTAMP = {}
_CACHE_EXPIRY = 60 * 5  # Cache expiry in seconds (5 minutes)

# Función para verificar si estamos en modo debug
def is_debug_mode():
    """Verifica si la aplicación está en modo debug"""
    global _DEBUG_MODE, _DEBUG_CHECKED
    
    debug_env = os.environ.get("DASH_DEBUG", "false").lower()
    is_debug = debug_env == 'true'
    
    # Solo imprimir el mensaje la primera vez o si el valor cambia
    if _DEBUG_MODE != is_debug or not _DEBUG_CHECKED:
        print(f"[INFO] is_debug_mode - DASH_DEBUG={debug_env}, is_debug={is_debug}")
        _DEBUG_MODE = is_debug
        _DEBUG_CHECKED = True
        
    return is_debug

# Función para log condicional
def debug_log(message, level="info"):
    """
    Registra un mensaje de log solo si estamos en modo debug
    
    Args:
        message: Mensaje a registrar
        level: Nivel de log (info, warning, error)
    """
    if not is_debug_mode():
        return
    
    if level == "info":
        logger.info(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)
    else:
        logger.info(message)

# Mapeo de tags a tipos de consumo
TAGS_TO_CONSUMPTION_TYPE = {
    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_COLD_WATER": "Agua fría sanitaria",
    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL": "Energía general",
    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER": "Agua caliente sanitaria",
    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL": "Agua general",
    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_IN": "Flujo entrante de personas",
    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_OUT": "Flujo saliente de personas",
    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_COOLING": "Energía térmica frío",
    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT": "Energía térmica calor"
}

def extract_asset_and_tag(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae el ID del asset y el tag del nombre del archivo.
    
    Formatos soportados (en orden de prioridad):
    1. daily_readings_<asset_id>_<consumption_type>.csv (Formato principal según PROJECT_CONTEXT.md)
    2. daily_readings_<asset_id>__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_<tag>.csv
    3. daily_readings_<asset_id>__<tag>.csv
    4. daily_readings_<asset_id>__<tag>_<year>.csv
    
    Args:
        filename: Nombre del archivo
        
    Returns:
        Tupla con (asset_id, tag) o (None, None) si no se puede extraer
    """
    try:
        # Obtener solo el nombre del archivo sin la ruta
        base_filename = os.path.basename(filename)
        debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Procesando archivo: {base_filename}")
        
        # Verificar si es un formato conocido
        if 'daily_readings_' not in base_filename:
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Formato de archivo no reconocido: {base_filename}")
            return None, None
        
        # Remover el prefijo 'daily_readings_'
        filename_without_prefix = base_filename.replace('daily_readings_', '')
        
        # CASO 1: Verificar si el archivo usa el formato del PROJECT_CONTEXT.md: 
        # daily_readings_<asset_id>_<consumption_type>.csv
        if '_' in filename_without_prefix and not filename_without_prefix.startswith('_'):
            # Este es el formato principal según la documentación
            parts = filename_without_prefix.split('_')
            asset_id = parts[0]
            
            # Extraer el tipo de consumo (todo lo que viene después del primer guión bajo)
            consumption_type_part = '_'.join(parts[1:]).replace('.csv', '')
            
            # Intentar encontrar el tag correspondiente al tipo de consumo
            tag = None
            
            # Buscar coincidencias exactas primero
            for known_tag, _ in TAGS_TO_CONSUMPTION_TYPE.items():
                if consumption_type_part in known_tag:
                    tag = known_tag
                    break
            
            # Si no se encuentra, buscar por la última parte (short name)
            if not tag:
                # Buscar en los tags conocidos para encontrar coincidencias parciales
                for known_tag in TAGS_TO_CONSUMPTION_TYPE.keys():
                    short_name = known_tag.split('_')[-1].lower()
                    consumption_type_lower = consumption_type_part.lower()
                    
                    if short_name in consumption_type_lower or consumption_type_lower in short_name:
                        tag = known_tag
                        break
            
            # Si aún no se encuentra, intentar con formato de prefijo TRANSVERSAL
            if not tag and 'TRANSVERSAL' in consumption_type_part:
                # Normalizar el formato para que tenga un guión bajo al inicio
                tag = '_' + consumption_type_part
            
            # Si sigue sin encontrarse, buscar palabras clave
            if not tag:
                # Buscar coincidencias parciales por palabra clave
                for known_tag in TAGS_TO_CONSUMPTION_TYPE.keys():
                    for keyword in ["WATER", "ENERGY", "FLOW", "DOMESTIC", "THERMAL"]:
                        if keyword in consumption_type_part and keyword in known_tag:
                            tag = known_tag
                            break
                    if tag:
                        break
            
            # Si no se ha encontrado ninguna coincidencia, usar el tag original
            if not tag:
                tag = consumption_type_part
            
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Formato PROJECT_CONTEXT: Asset ID: {asset_id}, Tag: {tag}")
            
            # Verificar si el tag está en el mapeo TAGS_TO_CONSUMPTION_TYPE
            consumption_type = TAGS_TO_CONSUMPTION_TYPE.get(tag, "Desconocido")
            debug_log(f"[DEBUG CRÍTICO] extract_asset_and_tag - Tag '{tag}' mapeado a tipo de consumo: '{consumption_type}'")
            
            if consumption_type == "Desconocido":
                debug_log(f"[DEBUG CRÍTICO] extract_asset_and_tag - ¡ALERTA! Tag '{tag}' no encontrado en TAGS_TO_CONSUMPTION_TYPE")
                # Listar todas las claves disponibles en el mapeo para depuración
                available_tags = list(TAGS_TO_CONSUMPTION_TYPE.keys())
                debug_log(f"[DEBUG CRÍTICO] extract_asset_and_tag - Tags disponibles en mapeo: {available_tags}")
            
            return asset_id, tag
        
        # CASO 2: Formato con doble guión bajo y tag transversal
        # daily_readings_<asset_id>__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_<tag>.csv
        elif '__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_' in base_filename:
            # Formato: daily_readings_ASSETID__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_tag_name.csv
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Detectado formato con __TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_")
            
            # Extraer el asset_id (parte entre daily_readings_ y __)
            asset_id_part = base_filename.split('__')[0]
            asset_id = asset_id_part.replace('daily_readings_', '')
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Asset ID extraído: {asset_id}")
            
            # Extraer el tag completo pero normalizado con un solo guión bajo al inicio
            tag_part = base_filename.split('__')[1]
            # Eliminar la extensión .csv si está presente
            if tag_part.endswith('.csv'):
                tag_part = tag_part[:-4]
            # Normalizar el tag para que tenga un solo guión bajo al inicio
            tag = '_' + tag_part
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Tag extraído y normalizado: {tag}")
            
            # DEBUG: Verificar si el tag está en el mapeo TAGS_TO_CONSUMPTION_TYPE
            consumption_type = TAGS_TO_CONSUMPTION_TYPE.get(tag, "Desconocido")
            debug_log(f"[DEBUG CRÍTICO] extract_asset_and_tag - Tag '{tag}' mapeado a tipo de consumo: '{consumption_type}'")
            
            if consumption_type == "Desconocido":
                debug_log(f"[DEBUG CRÍTICO] extract_asset_and_tag - ¡ALERTA! Tag '{tag}' no encontrado en TAGS_TO_CONSUMPTION_TYPE")
                # Listar todas las claves disponibles en el mapeo para depuración
                available_tags = list(TAGS_TO_CONSUMPTION_TYPE.keys())
                debug_log(f"[DEBUG CRÍTICO] extract_asset_and_tag - Tags disponibles en mapeo: {available_tags}")
            
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Archivo: {base_filename} -> Asset ID: {asset_id}, Tag: {tag}")
            return asset_id, tag
        
        # CASO 3: Formato con doble guión bajo pero sin tag transversal
        # daily_readings_<asset_id>__<tag>.csv
        elif '__' in base_filename:
            parts = base_filename.split('__')
            asset_id = parts[0].replace('daily_readings_', '')
            tag_part = parts[1]
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Formato con doble guión bajo: partes={parts}")
            
            # Eliminar la extensión .csv
            if tag_part.endswith('.csv'):
                tag_part = tag_part[:-4]
            
            # CASO 4: Verificar si tiene año al final
            # daily_readings_<asset_id>__<tag>_<year>.csv
            if '_' in tag_part and tag_part.split('_')[-1].isdigit():
                # Quitar el año del final
                tag_parts = tag_part.split('_')
                tag = '_'.join(tag_parts[:-1])
                debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Detectado año al final: {tag_parts[-1]}, tag sin año: {tag}")
            else:
                tag = tag_part
            
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Asset ID: {asset_id}, Tag: {tag}")
            
            # Verificar si el tag está en el mapeo TAGS_TO_CONSUMPTION_TYPE
            # Primero intentamos con el tag tal cual
            consumption_type = TAGS_TO_CONSUMPTION_TYPE.get(tag, None)
            
            # Si no se encuentra, intentamos con un guión bajo al inicio
            if consumption_type is None and not tag.startswith('_'):
                prefixed_tag = '_' + tag
                consumption_type = TAGS_TO_CONSUMPTION_TYPE.get(prefixed_tag, None)
                if consumption_type is not None:
                    tag = prefixed_tag
                    debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Tag normalizado con guión bajo inicial: {tag}")
            
            # Si aún no se encuentra, usamos la lógica de coincidencia parcial
            if consumption_type is None:
                # Buscar coincidencias parciales
                for known_tag, known_type in TAGS_TO_CONSUMPTION_TYPE.items():
                    # Extraer últimas partes de ambos tags para comparación
                    known_parts = known_tag.split('_')
                    tag_parts = tag.split('_')
                    
                    if tag_parts[-1].lower() == known_parts[-1].lower():
                        tag = known_tag
                        consumption_type = known_type
                        debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Coincidencia parcial encontrada, usando tag: {tag}")
                        break
            
            # Si no se encontró ninguna coincidencia, asignamos "Desconocido"
            if consumption_type is None:
                consumption_type = "Desconocido"
                debug_log(f"[DEBUG CRÍTICO] extract_asset_and_tag - ¡ALERTA! Tag '{tag}' no encontrado en TAGS_TO_CONSUMPTION_TYPE")
                # Listar todas las claves disponibles en el mapeo para depuración
                available_tags = list(TAGS_TO_CONSUMPTION_TYPE.keys())
                debug_log(f"[DEBUG CRÍTICO] extract_asset_and_tag - Tags disponibles en mapeo: {available_tags}")
            
            return asset_id, tag
        
        # Si llegamos aquí, intentar un último esfuerzo con la lógica original
        # Eliminar 'daily_readings_' del inicio
        parts = filename_without_prefix.split('_')
        debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Último intento, partes: {parts}")
        
        if len(parts) >= 1:
            asset_id = parts[0]
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Asset ID extraído: {asset_id}")
            
            if len(parts) >= 2:
                # Intentar construir un tag que tenga sentido
                tag = '_'.join(parts[1:]).replace('.csv', '')
                debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Tag extraído: {tag}")
                return asset_id, tag
            else:
                debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - No se pudo extraer un tag, usando 'unknown'")
                return asset_id, 'unknown'
        
        # Si no podemos identificar ningún formato
        debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - No se pudo identificar ningún formato conocido: {base_filename}")
        return None, None
        
    except Exception as e:
        debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - No se pudo extraer assetId y tag de {filename}: {str(e)}")
        print(f"No se pudo extraer assetId y tag de {filename}: {str(e)}")
        return None, None

def load_csv_data(file_path: str) -> Optional[pd.DataFrame]:
    """
    Carga datos desde un archivo CSV.
    
    Args:
        file_path: Ruta al archivo CSV
        
    Returns:
        DataFrame con los datos o None si hay error
    """
    try:
        debug_log(f"[DEBUG DETALLADO] load_csv_data - Intentando cargar archivo: {file_path}")
        
        # Intentar cargar el archivo con diferentes configuraciones
        try:
            df = pd.read_csv(file_path)
            debug_log(f"[DEBUG DETALLADO] load_csv_data - Archivo cargado correctamente: {file_path}")
            # Imprimir las primeras filas para depuración
            debug_log(f"[DEBUG DETALLADO] load_csv_data - Primeras filas del archivo: {df.head().to_dict() if not df.empty else 'DataFrame vacío'}")
            # Imprimir detalles de las columnas
            debug_log(f"[DEBUG DETALLADO] load_csv_data - Columnas del archivo: {df.columns.tolist()}")
            debug_log(f"[DEBUG DETALLADO] load_csv_data - Tipos de datos de las columnas: {df.dtypes.to_dict()}")
        except pd.errors.EmptyDataError:
            debug_log(f"[DEBUG DETALLADO] load_csv_data - Error al cargar el archivo {file_path}: No columns to parse from file")
            print(f"Error al cargar el archivo {file_path}: No columns to parse from file")
            return None
        except pd.errors.ParserError:
            # Intentar con diferentes delimitadores
            debug_log(f"[DEBUG DETALLADO] load_csv_data - Error de parser, intentando con delimitador ';': {file_path}")
            try:
                df = pd.read_csv(file_path, sep=';')
                debug_log(f"[DEBUG DETALLADO] load_csv_data - Archivo cargado correctamente con delimitador ';': {file_path}")
                # Imprimir las primeras filas para depuración con este delimitador
                debug_log(f"[DEBUG DETALLADO] load_csv_data - Primeras filas del archivo con delimitador ';': {df.head().to_dict() if not df.empty else 'DataFrame vacío'}")
            except:
                debug_log(f"[DEBUG DETALLADO] load_csv_data - Error al cargar el archivo {file_path}: No se pudo determinar el delimitador")
                print(f"Error al cargar el archivo {file_path}: No se pudo determinar el delimitador")
                return None
        
        # Verificar que el DataFrame tenga las columnas requeridas
        required_columns = ['date', 'value']
        if not all(col in df.columns for col in required_columns):
            debug_log(f"[DEBUG DETALLADO] load_csv_data - El archivo {file_path} no tiene las columnas requeridas: {required_columns}. Columnas encontradas: {list(df.columns)}")
            print(f"El archivo {file_path} no tiene las columnas requeridas: {required_columns}")
            return None
            
        # Extraer asset_id y tag del nombre del archivo
        asset_id, tag = extract_asset_and_tag(file_path)
        debug_log(f"[DEBUG DETALLADO] load_csv_data - Asset ID y tag extraídos: {asset_id}, {tag}")
        
        # Si no se pudo extraer el asset_id o tag, retornar None
        if asset_id is None or tag is None:
            debug_log(f"[DEBUG DETALLADO] load_csv_data - No se pudo extraer asset_id o tag del archivo: {file_path}")
            return None
            
        # Añadir columnas de asset_id y tag
        df['asset_id'] = asset_id
        df['tag'] = tag
        
        # Convertir la columna de fecha a datetime
        try:
            # Guardar un registro de los valores de fecha antes de convertir
            debug_log(f"[DEBUG DETALLADO] load_csv_data - Valores de fecha originales: {df['date'].head(5).tolist()}")
            
            # Intentar inferir el formato de fecha
            date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']
            date_conversion_success = False
            
            for date_format in date_formats:
                try:
                    df['date'] = pd.to_datetime(df['date'], format=date_format, errors='raise')
                    date_conversion_success = True
                    debug_log(f"[DEBUG DETALLADO] load_csv_data - Fechas convertidas correctamente con formato: {date_format}")
                    break
                except:
                    continue
            
            # Si no funcionó ningún formato específico, intentar con inferencia automática
            if not date_conversion_success:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                
            # Verificar si hubo valores NaT después de la conversión
            nat_count = df['date'].isna().sum()
            if nat_count > 0:
                debug_log(f"[DEBUG DETALLADO] load_csv_data - Se encontraron {nat_count} valores NaT después de convertir a datetime")
                print(f"[ADVERTENCIA] Se encontraron {nat_count} valores de fecha no válidos en el archivo {file_path}")
                
                # Eliminar filas con valores NaT en la columna date para evitar problemas posteriores
                df = df.dropna(subset=['date'])
                debug_log(f"[DEBUG DETALLADO] load_csv_data - Se eliminaron filas con fechas NaT, quedan {len(df)} filas")
            
            # Verificar y mostrar el rango de fechas
            if not df.empty and not df['date'].isna().all():
                min_date = df['date'].min()
                max_date = df['date'].max()
                debug_log(f"[DEBUG DETALLADO] load_csv_data - Rango de fechas: {min_date} a {max_date}")
            else:
                debug_log(f"[DEBUG DETALLADO] load_csv_data - Todas las fechas son NaT después de la conversión o DataFrame vacío")
                if df.empty:
                    print(f"[ERROR] No hay datos válidos después de eliminar fechas inválidas en el archivo {file_path}")
                    return None
                else:
                    print(f"[ERROR] Todas las fechas son inválidas en el archivo {file_path}")
                    return None
        except Exception as e:
            debug_log(f"[DEBUG DETALLADO] load_csv_data - Error al convertir la columna de fecha: {str(e)}")
            print(f"[ERROR] Error al convertir la columna de fecha en el archivo {file_path}: {str(e)}")
            # Si hay un error crítico con la columna de fecha, devolver None ya que esta columna es esencial
            return None
        
        # Manejar valores de error en la columna 'value'
        # Primero, identificar filas con valores no numéricos
        # Convertir la columna 'value' a string para manejar diferentes tipos de datos
        df['value'] = df['value'].astype(str)
        
        # Identificar valores que contienen 'Error', 'error', 'Sin datos', etc.
        error_mask = df['value'].str.contains('Error|error|Sin datos|sin datos|N/A|n/a', case=False, na=False)
        
        # Identificar valores que no se pueden convertir a números
        numeric_mask = pd.to_numeric(df['value'], errors='coerce').notna()
        non_numeric_mask = ~numeric_mask
        
        # Combinar ambas máscaras
        problem_mask = error_mask | non_numeric_mask
        error_count = problem_mask.sum()
        
        debug_log(f"[DEBUG DETALLADO] load_csv_data - Se encontraron {error_count} valores problemáticos en la columna 'value' del archivo {file_path}")
        
        if error_count > 0:
            debug_log(f"[DEBUG DETALLADO] load_csv_data - Se encontraron {error_count} valores problemáticos en la columna 'value' del archivo {file_path}")
            print(f"Se encontraron {error_count} valores problemáticos en la columna 'value' del archivo {file_path}")
            
            # Convertir valores problemáticos a NaN
            df.loc[problem_mask, 'value'] = np.nan
            
            # Intentar interpolar valores faltantes (solo si hay suficientes datos válidos)
            valid_data_ratio = df['value'].notna().sum() / len(df)
            debug_log(f"[DEBUG DETALLADO] load_csv_data - Ratio de datos válidos: {valid_data_ratio:.2f}")
            
            if valid_data_ratio > 0.5:  # Si más del 50% de los datos son válidos
                # Convertir a numérico antes de interpolar
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                # Interpolar valores faltantes
                df['value'] = df['value'].interpolate(method='linear')
                debug_log(f"[DEBUG DETALLADO] load_csv_data - Se interpolaron valores faltantes en la columna 'value'")
            else:
                # Si no hay suficientes datos para interpolar, reemplazar NaN con 0
                df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
                debug_log(f"[DEBUG DETALLADO] load_csv_data - Se reemplazaron valores NaN con 0 en la columna 'value'")
        else:
            # Si no hay valores problemáticos, asegurarse de que la columna sea numérica
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        # Añadir columna de timestamp (útil para algunas visualizaciones)
        df['timestamp'] = df['date'].astype(int) // 10**9
        
        # Mapear el tipo de consumo basado en el tag
        consumption_type = TAGS_TO_CONSUMPTION_TYPE.get(tag, "Desconocido")
        df['consumption_type'] = consumption_type
        debug_log(f"[DEBUG DETALLADO] load_csv_data - Tipo de consumo mapeado: {consumption_type} para tag: {tag}")
        
        # Logs adicionales para debugging
        debug_log(f"[DEBUG CRÍTICO] load_csv_data - Asignando tipo de consumo para el archivo: {file_path}")
        debug_log(f"[DEBUG CRÍTICO] load_csv_data - Tag extraído: '{tag}'")
        debug_log(f"[DEBUG CRÍTICO] load_csv_data - Tipo de consumo asignado: '{consumption_type}'")
        
        if consumption_type == "Desconocido":
            debug_log(f"[DEBUG CRÍTICO] load_csv_data - ¡ALERTA! El tag '{tag}' no corresponde a ningún tipo de consumo conocido")
            debug_log(f"[DEBUG CRÍTICO] load_csv_data - Verificando si el tag está presente en otra forma en el mapeo:")
            
            # Intentar encontrar coincidencias parciales
            partial_matches = []
            for known_tag, known_type in TAGS_TO_CONSUMPTION_TYPE.items():
                if tag in known_tag or known_tag in tag:
                    partial_matches.append((known_tag, known_type))
            
            if partial_matches:
                debug_log(f"[DEBUG CRÍTICO] load_csv_data - Coincidencias parciales encontradas: {partial_matches}")
            else:
                debug_log(f"[DEBUG CRÍTICO] load_csv_data - No se encontraron coincidencias parciales")
            
            # Ver si el tag sin guión bajo inicial está en el mapeo
            if tag.startswith('_') and tag[1:] in TAGS_TO_CONSUMPTION_TYPE:
                debug_log(f"[DEBUG CRÍTICO] load_csv_data - El tag sin guión bajo inicial '{tag[1:]}' está en el mapeo")
            
            # Ver si el tag con guión bajo inicial está en el mapeo
            if not tag.startswith('_') and f"_{tag}" in TAGS_TO_CONSUMPTION_TYPE:
                debug_log(f"[DEBUG CRÍTICO] load_csv_data - El tag con guión bajo inicial '_{tag}' está en el mapeo")
        
        # Extraer el project_id del path (asumiendo estructura de carpetas)
        path_parts = file_path.split(os.sep)
        for part in path_parts:
            if len(part) == 36 and '-' in part:  # Formato UUID
                df['project_id'] = part
                debug_log(f"[DEBUG DETALLADO] load_csv_data - Project ID extraído del path: {part}")
                break
        else:
            df['project_id'] = 'unknown'
            debug_log(f"[DEBUG DETALLADO] load_csv_data - No se pudo extraer project_id del path: {file_path}")
        
        # Renombrar 'value' a 'consumption' para mayor claridad
        df['consumption'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
        
        # Añadir columna de mes para facilitar agrupaciones
        df['month'] = df['date'].dt.to_period('M')
        
        # Añadir columna para indicar si el valor es estimado (por ahora, todos son False)
        df['is_estimated'] = False
        
        debug_log(f"[DEBUG DETALLADO] load_csv_data - Archivo procesado correctamente: {file_path}, {len(df)} filas")
        return df
    except Exception as e:
        debug_log(f"[DEBUG DETALLADO] load_csv_data - Error al cargar el archivo {file_path}: {str(e)}")
        print(f"Error al cargar el archivo {file_path}: {str(e)}")
        return None

# Create a helper function for caching with a custom key
def get_cache_key(base_path, consumption_tags, project_id):
    """
    Generate a cache key based on function parameters.
    
    Args:
        base_path: Base path for CSV files
        consumption_tags: List of consumption tags to filter by
        project_id: Project ID to filter by
        
    Returns:
        String cache key
    """
    # Sort consumption tags to ensure consistent keys
    tag_str = ",".join(sorted(consumption_tags)) if consumption_tags else "None"
    proj_str = project_id if project_id else "None"
    return f"{base_path}|{tag_str}|{proj_str}"
    
def load_all_csv_data(base_path: str = "data/analyzed_data", minimal: bool = False, consumption_tags: Optional[List[str]] = None, project_id: Optional[str] = None, jwt_token: Optional[str] = None) -> pd.DataFrame:
    """
    Carga todos los archivos CSV de consumo en un único DataFrame.
    
    Args:
        base_path: Ruta base donde buscar los archivos CSV
        minimal: Si es True, solo carga información mínima para obtener la estructura (proyectos/assets)
        consumption_tags: Lista de tags de consumo para filtrar los archivos a cargar (opcional)
        project_id: ID del proyecto para filtrar los archivos a cargar (opcional)
        jwt_token: Token JWT para autenticación con la API (opcional)
        
    Returns:
        DataFrame combinado con todos los datos
    """
    # Skip caching for minimal=True since it's used for structure only
    if not minimal:
        # Generate a cache key based on the function parameters
        cache_key = get_cache_key(base_path, consumption_tags, project_id)
        
        # Check if we have a valid cache entry
        current_time = time.time()
        if cache_key in _CSV_DATA_CACHE and cache_key in _CACHE_TIMESTAMP:
            # Check if the cache is still valid (not expired)
            if current_time - _CACHE_TIMESTAMP[cache_key] < _CACHE_EXPIRY:
                debug_log(f"[INFO] load_all_csv_data - Using cached data for key: {cache_key}")
                print(f"[INFO METRICS] load_all_csv_data - Using cached data (saved {_CACHE_EXPIRY} seconds ago)")
                return _CSV_DATA_CACHE[cache_key].copy()
            else:
                debug_log(f"[INFO] load_all_csv_data - Cache expired for key: {cache_key}")
                print(f"[INFO METRICS] load_all_csv_data - Cache expired, reloading data")
    
    # Log detallado para verificar el valor exacto de project_id
    debug_log(f"[DEBUG CRÍTICO] load_all_csv_data - Valor exacto de project_id recibido: '{project_id}', tipo: {type(project_id)}")
    
    all_data = []
    
    # Si hay tags de consumo, registrarlos para depuración
    if consumption_tags:
        debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Filtrando archivos por tags de consumo: {consumption_tags}")
    
    # REMOVED API CALL: No longer fetch project assets from API
    # Instead, we'll rely solely on local filesystem operations
    
    # Buscar todos los directorios de proyecto
    project_dirs = [d for d in glob.glob(os.path.join(base_path, "*")) if os.path.isdir(d)]
    debug_log(f"[DEBUG CRÍTICO] load_all_csv_data - Directorios de proyecto encontrados: {project_dirs}")
    
    # Log the number of directories found instead of detailed logging for each
    print(f"[INFO METRICS] load_all_csv_data - Encontrados {len(project_dirs)} directorios de proyecto")
    
    # Filtrar directorios de proyecto si se especificó un project_id
    if project_id and project_id != "all":
        # Log para verificar la condición de filtrado
        print(f"[INFO METRICS] load_all_csv_data - Filtrando por proyecto {project_id}")
        
        # Aplicar el filtro
        filtered_dirs = [d for d in project_dirs if os.path.basename(d) == project_id]
        
        project_dirs = filtered_dirs
        print(f"[INFO METRICS] load_all_csv_data - Después del filtro quedan {len(project_dirs)} directorios")
    
    # Si no hay directorios de proyecto, buscar archivos CSV directamente en base_path
    if not project_dirs:
        print(f"[INFO METRICS] load_all_csv_data - No se encontraron directorios de proyecto, buscando archivos CSV en {base_path}")
        csv_files = glob.glob(os.path.join(base_path, "daily_readings_*.csv"))
        print(f"[INFO METRICS] load_all_csv_data - Encontrados {len(csv_files)} archivos CSV en {base_path}")
        
        # Process each CSV file found in the base path
        for file_path in csv_files:
            # Extraer asset_id y tag para filtrar
            asset_id, tag = extract_asset_and_tag(file_path)
            
            # No filtering by project assets from API - use file structure instead
            
            # Verificar si el archivo corresponde a los tags de consumo seleccionados
            if consumption_tags and not minimal:
                if not tag_matches_selection(tag, consumption_tags):
                    debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Omitiendo archivo {file_path} porque no corresponde a los tags seleccionados")
                    continue
                else:
                    debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Procesando archivo {file_path} que coincide con los tags seleccionados")
            
            # Si es modo minimal, solo cargar las primeras filas para obtener la estructura
            if minimal:
                try:
                    df = pd.read_csv(file_path, nrows=5)  # Cargar solo 5 filas
                    if df is not None and not df.empty:
                        all_data.append(df)
                except Exception as e:
                    debug_log(f"Error al cargar datos mínimos de {file_path}: {str(e)}")
            else:
                df = load_csv_data(file_path)
                if df is not None:
                    all_data.append(df)
    else:
        # Buscar archivos CSV en cada directorio de proyecto
        for project_dir in project_dirs:
            current_project_id = os.path.basename(project_dir)
            print(f"[INFO METRICS] load_all_csv_data - Buscando archivos CSV en directorio: {current_project_id}")
            
            # Si estamos filtrando por un proyecto específico y este no coincide, omitirlo
            if project_id and project_id != "all" and current_project_id != project_id:
                debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Omitiendo directorio {project_dir} porque no coincide con el proyecto seleccionado {project_id}")
                continue
                
            csv_files = glob.glob(os.path.join(project_dir, "daily_readings_*.csv"))
            print(f"[INFO METRICS] load_all_csv_data - Encontrados {len(csv_files)} archivos CSV en {project_dir}")
            
            # Si es modo minimal, solo cargar un archivo por proyecto
            if minimal and csv_files:
                try:
                    df = pd.read_csv(csv_files[0], nrows=5)  # Cargar solo 5 filas del primer archivo
                    if df is not None and not df.empty:
                        # Asegurarse de que tenga la columna project_id
                        if 'project_id' not in df.columns:
                            df['project_id'] = current_project_id
                        all_data.append(df)
                except Exception as e:
                    debug_log(f"Error al cargar datos mínimos de {csv_files[0]}: {str(e)}")
            else:
                for file_path in csv_files:
                    # Extraer asset_id y tag para filtrar
                    asset_id, tag = extract_asset_and_tag(file_path)
                    
                    # No filtering by project assets from API - use file structure instead
                    
                    # Verificar si el archivo corresponde a los tags de consumo seleccionados
                    if consumption_tags:
                        if not tag_matches_selection(tag, consumption_tags):
                            debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Omitiendo archivo {file_path} porque no corresponde a los tags seleccionados")
                            continue
                        else:
                            debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Procesando archivo {file_path} que coincide con los tags seleccionados")
                    
                    df = load_csv_data(file_path)
                    if df is not None:
                        # Ensure the DataFrame has project_id
                        if 'project_id' not in df.columns:
                            df['project_id'] = current_project_id
                        all_data.append(df)
    
    # Combinar todos los DataFrames
    if all_data:
        print(f"[INFO METRICS] load_all_csv_data - Combinando {len(all_data)} DataFrames")
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"[INFO METRICS] load_all_csv_data - DataFrame combinado tiene {len(combined_df)} filas")
        
        # Store the result in cache if not in minimal mode
        if not minimal:
            cache_key = get_cache_key(base_path, consumption_tags, project_id)
            _CSV_DATA_CACHE[cache_key] = combined_df.copy()
            _CACHE_TIMESTAMP[cache_key] = time.time()
            debug_log(f"[INFO] load_all_csv_data - Data cached with key: {cache_key}")
            print(f"[INFO METRICS] load_all_csv_data - Data cached successfully ({len(combined_df)} rows)")
            
        return combined_df
    else:
        debug_log("[DEBUG DETALLADO] load_all_csv_data - No se encontraron datos válidos en los archivos CSV")
        return pd.DataFrame()

def get_projects_with_data(df: Optional[pd.DataFrame]) -> List[Dict]:
    """
    Obtiene la lista de proyectos que tienen datos.
    
    Args:
        df: DataFrame con los datos combinados o None para escanear directorios
        
    Returns:
        Lista de diccionarios con información de los proyectos
    """
    if df is None:
        # Si no se proporciona DataFrame, escanear directorios directamente
        base_path = "data/analyzed_data"
        project_dirs = [d for d in glob.glob(os.path.join(base_path, "*")) if os.path.isdir(d)]
        
        if not project_dirs:
            # Si no hay directorios de proyecto, verificar si hay archivos CSV en la raíz
            csv_files = glob.glob(os.path.join(base_path, "daily_readings_*.csv"))
            if csv_files:
                return [{'id': 'default', 'nombre': "Proyecto default"}]
            return []
        
        # Extraer los IDs de proyecto de los nombres de directorio
        projects = []
        for project_dir in project_dirs:
            project_id = os.path.basename(project_dir)
            # Verificar si hay archivos CSV en este directorio
            csv_files = glob.glob(os.path.join(project_dir, "daily_readings_*.csv"))
            if csv_files:
                projects.append({'id': project_id, 'nombre': f"Proyecto {project_id}"})
        
        return projects
    
    if df.empty:
        return []
    
    projects = df['project_id'].unique()
    return [{'id': project, 'nombre': f"Proyecto {project}"} for project in projects]

def get_project_for_asset(asset_id: str) -> Optional[str]:
    """
    Busca a qué proyecto pertenece un asset específico examinando los archivos CSV existentes.
    
    Args:
        asset_id (str): ID del asset a buscar
        
    Returns:
        str: ID del proyecto al que pertenece el asset, o None si no se encuentra
    """
    debug_log(f"[DEBUG] get_project_for_asset - Buscando proyecto para el asset {asset_id}")
    base_path = "data/analyzed_data"
    
    # Verificar que el directorio base existe
    if not os.path.exists(base_path):
        debug_log(f"[DEBUG] get_project_for_asset - Directorio base {base_path} no existe")
        return None
    
    # Buscar en cada directorio de proyecto
    project_dirs = [d for d in glob.glob(os.path.join(base_path, "*")) if os.path.isdir(d)]
    debug_log(f"[DEBUG] get_project_for_asset - Encontrados {len(project_dirs)} directorios de proyecto")
    
    for project_dir in project_dirs:
        project_id = os.path.basename(project_dir)
        
        # Saltar el directorio "general" si existe
        if project_id == "general":
            continue
            
        # Buscar archivos que contengan el asset_id
        asset_files = glob.glob(os.path.join(project_dir, f"daily_readings_{asset_id}__*.csv"))
        
        if asset_files:
            debug_log(f"[DEBUG] get_project_for_asset - Encontrados {len(asset_files)} archivos para el asset {asset_id} en el proyecto {project_id}")
            return project_id
    
    # Si llegamos aquí, no encontramos el asset en ningún proyecto
    debug_log(f"[DEBUG] get_project_for_asset - No se encontró ningún proyecto para el asset {asset_id}")
    return None

def get_asset_metadata(asset_id: str, project_id: Optional[str] = None, jwt_token: Optional[str] = None) -> Dict[str, str]:
    """
    Obtiene los metadatos de un asset específico (bloque, escalera, apartamento).
    
    Args:
        asset_id (str): ID del asset
        project_id (str, optional): ID del proyecto al que pertenece el asset
        jwt_token (str, optional): Token JWT para autenticación API
        
    Returns:
        Dict[str, str]: Diccionario con los metadatos del asset (block_number, staircase, apartment)
    """
    debug_log(f"[DEBUG] get_asset_metadata - Buscando metadatos para el asset {asset_id}")
    
    # Valores predeterminados
    metadata = {
        'block_number': 'N/A',
        'staircase': 'N/A',
        'apartment': 'N/A'
    }
    
    # Intentar obtener los metadatos desde la API
    try:
        from utils.api import get_assets, get_project_assets
        
        assets = []
        if project_id and project_id != "all":
            assets = get_project_assets(project_id, jwt_token=jwt_token)
        else:
            assets = get_assets(jwt_token=jwt_token)
        
        # Buscar el asset en la lista
        asset_info = next((a for a in assets if a.get('id') == asset_id), None)
        
        if asset_info:
            debug_log(f"[DEBUG] get_asset_metadata - Encontrado asset {asset_id} en la API")
            metadata = {
                'block_number': asset_info.get('block_number', 'N/A'),
                'staircase': asset_info.get('staircase', 'N/A'),
                'apartment': asset_info.get('apartment', 'N/A')
            }
            return metadata
    except Exception as e:
        debug_log(f"[ERROR] get_asset_metadata - Error al obtener metadatos desde la API: {str(e)}")
    
    # Si no se pudo obtener desde la API, intentar buscar en los datos locales
    if not project_id:
        project_id = get_project_for_asset(asset_id)
    
    if project_id:
        # Buscar en los archivos de configuración o metadatos locales
        try:
            # Aquí podría buscar en archivos JSON de configuración o metadatos
            # Por ahora, simplemente devolvemos los valores predeterminados
            pass
        except Exception as e:
            debug_log(f"[ERROR] get_asset_metadata - Error al buscar metadatos locales: {str(e)}")
    
    return metadata

def get_assets_with_data(df: pd.DataFrame, project_id: Optional[str] = None) -> List[Dict]:
    """
    Obtiene la lista de assets que tienen datos, opcionalmente filtrados por proyecto.
    
    Args:
        df: DataFrame con los datos combinados
        project_id: ID del proyecto para filtrar (opcional)
        
    Returns:
        Lista de diccionarios con información de los assets
    """
    if df.empty:
        return []
    
    if project_id and project_id != "all":
        filtered_df = df[df['project_id'] == project_id]
    else:
        filtered_df = df
    
    assets = filtered_df['asset_id'].unique()
    return [{'id': asset, 'nombre': f"Asset {asset}"} for asset in assets]

def get_consumption_types(df: pd.DataFrame) -> List[str]:
    """
    Obtiene la lista de tipos de consumo disponibles en los datos.
    
    Args:
        df: DataFrame con los datos combinados
        
    Returns:
        Lista de tipos de consumo
    """
    if df.empty:
        return list(TAGS_TO_CONSUMPTION_TYPE.values())
    
    return df['consumption_type'].unique().tolist()

def filter_data(df: pd.DataFrame, 
                client_id: Optional[str] = None,
                project_id: Optional[str] = None, 
                asset_id: Optional[str] = None, 
                consumption_type: Optional[Union[str, List[str]]] = None,
                consumption_tags: Optional[List[str]] = None,
                start_date: Optional[str] = None,
                end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Filter DataFrame based on specified criteria.
    
    Args:
        df: DataFrame to filter
        client_id: Client ID to filter by
        project_id: Project ID to filter by
        asset_id: Asset ID to filter by
        consumption_type: Consumption type to filter by (deprecated - use consumption_tags)
        consumption_tags: List of consumption tags to filter by
        start_date: Start date for filtering (inclusive)
        end_date: End date for filtering (inclusive)
        
    Returns:
        Filtered DataFrame
    """
    if df.empty:
        return df
    
    # Create a copy to avoid modifying the original
    filtered_df = df.copy()
    
    # Track the original row count
    start_count = len(filtered_df)
    
    # Ensure required columns exist
    for col in ['client_id', 'project_id', 'asset_id', 'date']:
        if col not in filtered_df.columns:
            if col == 'client_id' and client_id:
                filtered_df['client_id'] = client_id
            elif col == 'project_id' and project_id:
                filtered_df['project_id'] = project_id
            elif col == 'asset_id':
                filtered_df['asset_id'] = 'unknown'
            elif col == 'date':
                # Try to create date from timestamp if available
                if 'timestamp' in filtered_df.columns:
                    try:
                        filtered_df['date'] = pd.to_datetime(filtered_df['timestamp'], unit='s')
                    except:
                        # If conversion fails, create a default date
                        filtered_df['date'] = pd.Timestamp.now()
                else:
                    filtered_df['date'] = pd.Timestamp.now()
    
    # Apply client filter if specified
    if client_id:
        filtered_df = filtered_df[filtered_df['client_id'] == client_id]
    
    # Apply project filter if specified and not "all"
    if project_id and project_id != "all":
        filtered_df = filtered_df[filtered_df['project_id'] == project_id]
    
    # Apply asset filter if specified and not "all"
    if asset_id and asset_id != "all":
        filtered_df = filtered_df[filtered_df['asset_id'] == asset_id]
    
    # Legacy consumption_type parameter support
    if consumption_type and not consumption_tags:
        if isinstance(consumption_type, str):
            consumption_tags = [consumption_type]
        else:
            consumption_tags = consumption_type
    
    # Apply consumption tags filter
    if consumption_tags:
        # Create masks for both consumption_type and tag columns
        type_mask = pd.Series(False, index=filtered_df.index)
        
        # Check consumption_type column
        if 'consumption_type' in filtered_df.columns:
            for tag in consumption_tags:
                type_mask |= filtered_df['consumption_type'] == tag
        
        # Check tag column
        if 'tag' in filtered_df.columns and not type_mask.any():
            for tag in consumption_tags:
                type_mask |= filtered_df['tag'] == tag
        
        # Apply the filter if there are matches
        if type_mask.any():
            filtered_df = filtered_df[type_mask]
    
    # Convert date strings to datetime if needed
    if start_date or end_date:
        # Ensure date column is datetime
        if not pd.api.types.is_datetime64_any_dtype(filtered_df['date']):
            filtered_df['date'] = pd.to_datetime(filtered_df['date'], errors='coerce')
            # Drop rows with invalid dates
            filtered_df = filtered_df.dropna(subset=['date'])
    
    # Apply date filters
    if start_date:
        start_date = pd.to_datetime(start_date)
        filtered_df = filtered_df[filtered_df['date'] >= start_date]
    
    if end_date:
        end_date = pd.to_datetime(end_date)
        filtered_df = filtered_df[filtered_df['date'] <= end_date]
    
    # Log the result
    end_count = len(filtered_df)
    print(f"[INFO] filter_data - Filtered from {start_count} to {end_count} rows")
    
    return filtered_df

def aggregate_data_by_project(df: pd.DataFrame, consumption_type: Optional[str] = None) -> pd.DataFrame:
    """
    Agrega los datos por proyecto.
    
    Args:
        df: DataFrame con los datos combinados
        consumption_type: Tipo de consumo para filtrar (opcional)
        
    Returns:
        DataFrame agregado por proyecto
    """
    if df.empty:
        return df
    
    # Filtrar por tipo de consumo si se especifica
    if consumption_type and consumption_type != "all":
        filtered_df = df[df['consumption_type'] == consumption_type]
    else:
        filtered_df = df
    
    # Verificar que exista la columna consumption
    if 'consumption' not in filtered_df.columns:
        # Intentar usar 'value' si 'consumption' no está disponible
        if 'value' in filtered_df.columns:
            filtered_df['consumption'] = filtered_df['value']
        else:
            debug_log("No se encontró la columna 'consumption' ni 'value' para la agregación")
            return pd.DataFrame()
    
    # Agrupar por proyecto y fecha, sumando los valores
    aggregated = filtered_df.groupby(['project_id', 'date'])['consumption'].sum().reset_index()
    
    return aggregated

def aggregate_data_by_asset(df: pd.DataFrame, consumption_type: Optional[str] = None) -> pd.DataFrame:
    """
    Agrega los datos por asset.
    
    Args:
        df: DataFrame con los datos combinados
        consumption_type: Tipo de consumo para filtrar (opcional)
        
    Returns:
        DataFrame agregado por asset
    """
    if df.empty:
        return df
    
    # Filtrar por tipo de consumo si se especifica
    if consumption_type and consumption_type != "all":
        filtered_df = df[df['consumption_type'] == consumption_type]
    else:
        filtered_df = df
    
    # Verificar que exista la columna consumption
    if 'consumption' not in filtered_df.columns:
        # Intentar usar 'value' si 'consumption' no está disponible
        if 'value' in filtered_df.columns:
            filtered_df['consumption'] = filtered_df['value']
        else:
            debug_log("No se encontró la columna 'consumption' ni 'value' para la agregación")
            return pd.DataFrame()
    
    # Agrupar por asset y fecha, sumando los valores
    aggregated = filtered_df.groupby(['asset_id', 'date'])['consumption'].sum().reset_index()
    
    return aggregated

def aggregate_data_by_consumption_type(df: pd.DataFrame, project_id: Optional[str] = None) -> pd.DataFrame:
    """
    Agrega los datos por tipo de consumo.
    
    Args:
        df: DataFrame con los datos combinados
        project_id: ID del proyecto para filtrar (opcional)
        
    Returns:
        DataFrame agregado por tipo de consumo
    """
    if df.empty:
        return df
    
    # Filtrar por proyecto si se especifica
    if project_id and project_id != "all":
        filtered_df = df[df['project_id'] == project_id]
    else:
        filtered_df = df
    
    # Verificar que exista la columna consumption
    if 'consumption' not in filtered_df.columns:
        # Intentar usar 'value' si 'consumption' no está disponible
        if 'value' in filtered_df.columns:
            filtered_df['consumption'] = filtered_df['value']
        else:
            debug_log("No se encontró la columna 'consumption' ni 'value' para la agregación")
            return pd.DataFrame()
    
    # Agrupar por tipo de consumo, sumando los valores totales
    aggregated = filtered_df.groupby('consumption_type')['consumption'].sum()
    
    return aggregated

def aggregate_data_by_month_and_asset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega los datos por mes y asset, mostrando la última lectura de cada mes.
    
    Args:
        df: DataFrame con los datos filtrados
        
    Returns:
        DataFrame agregado con las lecturas finales por mes y asset
    """
    if df.empty:
        debug_log("[DEBUG DETALLADO] aggregate_data_by_month_and_asset - DataFrame vacío, no hay datos para agregar")
        return pd.DataFrame()
    
    debug_log(f"[DEBUG DETALLADO] aggregate_data_by_month_and_asset - Agregando datos por mes y asset, DataFrame original tiene {len(df)} filas")
    
    # Asegurarse de que la fecha esté en formato datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Crear una columna de año-mes para agrupar
    df['year_month'] = df['date'].dt.strftime('%Y-%m')
    
    # Ordenar por fecha para asegurar que tomamos la última lectura de cada mes
    df = df.sort_values('date')
    
    # Agrupar por asset_id, año-mes y obtener la última lectura de cada mes
    grouped = df.groupby(['asset_id', 'year_month']).last().reset_index()
    
    # Ordenar por asset_id y año-mes
    grouped = grouped.sort_values(['asset_id', 'year_month'])
    
    debug_log(f"[DEBUG DETALLADO] aggregate_data_by_month_and_asset - DataFrame agregado tiene {len(grouped)} filas")
    
    return grouped

# Función auxiliar para verificar si un tag coincide con los tags seleccionados
def tag_matches_selection(tag, selected_tags):
    if not selected_tags:
        debug_log(f"[DEBUG DETALLADO] tag_matches_selection - No hay tags seleccionados, aceptando todos")
        return True
    
    debug_log(f"[DEBUG DETALLADO] tag_matches_selection - Comparando tag '{tag}' con tags seleccionados: {selected_tags}")
    
    # Verificar coincidencia directa
    if tag in selected_tags:
        debug_log(f"[DEBUG DETALLADO] tag_matches_selection - Coincidencia directa encontrada para '{tag}'")
        return True
    
    # Normalizar el tag del archivo para comparación
    normalized_file_tag = tag
    if tag.startswith('__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_'):
        normalized_file_tag = '_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_' + tag.split('__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_')[1]
    elif tag.startswith('_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_'):
        normalized_file_tag = tag
    
    debug_log(f"[DEBUG DETALLADO] tag_matches_selection - Tag normalizado del archivo: '{normalized_file_tag}'")
    
    # Verificar coincidencia con formato __TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_
    for selected_tag in selected_tags:
        # Normalizar el tag seleccionado para comparación
        normalized_selected_tag = selected_tag
        if selected_tag.startswith('__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_'):
            normalized_selected_tag = '_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_' + selected_tag.split('__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_')[1]
        elif selected_tag.startswith('_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_'):
            normalized_selected_tag = selected_tag
        
        debug_log(f"[DEBUG DETALLADO] tag_matches_selection - Tag normalizado seleccionado: '{normalized_selected_tag}'")
        
        # Comparar los tags normalizados
        if normalized_file_tag == normalized_selected_tag:
            debug_log(f"[DEBUG DETALLADO] tag_matches_selection - Coincidencia encontrada después de normalizar: '{normalized_file_tag}' == '{normalized_selected_tag}'")
            return True
            
        # Si el tag seleccionado tiene el formato completo pero el tag del archivo no
        if normalized_selected_tag.startswith('_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_'):
            # Extraer la parte final del tag (después de _TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_)
            clean_selected_tag = normalized_selected_tag.replace('_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_', '')
            
            # Si el tag del archivo no tiene el prefijo, comparar directamente
            if not normalized_file_tag.startswith('_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_'):
                if normalized_file_tag.lower() == clean_selected_tag.lower():
                    debug_log(f"[DEBUG DETALLADO] tag_matches_selection - Coincidencia encontrada comparando tag sin prefijo: '{normalized_file_tag}' == '{clean_selected_tag}'")
                    return True
            else:
                # Si ambos tienen el prefijo, extraer la parte final del tag del archivo
                clean_file_tag = normalized_file_tag.replace('_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_', '')
                if clean_file_tag.lower() == clean_selected_tag.lower():
                    debug_log(f"[DEBUG DETALLADO] tag_matches_selection - Coincidencia encontrada después de limpiar: '{clean_file_tag}' == '{clean_selected_tag}'")
                    return True
    
    debug_log(f"[DEBUG DETALLADO] tag_matches_selection - No se encontró coincidencia para el tag '{tag}'")
    return False

def generate_monthly_readings_by_consumption_type(df: pd.DataFrame, consumption_tags: List[str], start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
    """
    Genera tablas de lecturas mensuales por tipo de consumo.
    
    Args:
        df: DataFrame con los datos filtrados
        consumption_tags: Lista de tags de consumo
        start_date: Fecha de inicio
        end_date: Fecha de fin
        
    Returns:
        Dict[str, pd.DataFrame]: Diccionario con tablas de lecturas mensuales por tipo de consumo
    """
    # Logs de depuración
    debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Iniciando generación de tablas")
    debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - DataFrame shape: {df.shape}")
    debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Columnas: {df.columns.tolist()}")
    debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Tags: {consumption_tags}")
    debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Rango de fechas: {start_date} a {end_date}")
    
    # Verificar si hay datos de consumo en el DataFrame
    if 'consumption' not in df.columns:
        debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - ERROR: No hay columna 'consumption' en el DataFrame")
        return {}
    
    # Asegurar que la columna date es datetime
    if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # Crear un diccionario para almacenar las tablas por tipo de consumo
    tables_by_consumption_type = {}
    
    # Generar una lista de meses entre start_date y end_date
    months = []
    current_date = start_date.replace(day=1)
    while current_date <= end_date:
        months.append(current_date)
        # Avanzar al siguiente mes
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Meses a procesar: {[m.strftime('%b %Y') for m in months]}")
    
    # Procesar cada tag de consumo
    for tag in consumption_tags:
        # Filtrar datos por tag
        tag_df = df[df['tag'] == tag].copy()
        
        debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Tag: {tag}, Filas: {len(tag_df)}")
        
        if tag_df.empty:
            debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - No hay datos para el tag {tag}")
            continue
        
        # Obtener el nombre legible del tipo de consumo
        consumption_type = TAGS_TO_CONSUMPTION_TYPE.get(tag, tag)
        
        # Crear un DataFrame para la tabla de este tipo de consumo
        assets = tag_df['asset_id'].unique()
        debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Assets para {tag}: {len(assets)}")
        
        # Crear un DataFrame vacío con los assets como índice
        table_df = pd.DataFrame(index=assets)
        
        # Añadir una columna para el nombre del asset
        asset_names = {}
        for asset_id in assets:
            # Buscar el nombre del asset en el DataFrame
            asset_rows = tag_df[tag_df['asset_id'] == asset_id]
            if not asset_rows.empty and 'asset_name' in asset_rows.columns:
                asset_names[asset_id] = asset_rows['asset_name'].iloc[0]
            else:
                asset_names[asset_id] = asset_id
        
        table_df['Asset'] = [asset_names.get(asset_id, asset_id) for asset_id in assets]
        
        # Para cada mes, calcular el consumo como la diferencia entre la lectura final e inicial
        for month_start in months:
            # Calcular el final del mes
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - pd.Timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - pd.Timedelta(days=1)
            
            # Formatear el nombre de la columna como "MMM YYYY" (ej: "Ene 2024")
            month_name = month_start.strftime("%b %Y")
            
            debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Procesando mes: {month_name}")
            
            # Inicializar la columna con valores NaN
            # Usamos un objeto para almacenar los valores, que luego convertiremos a la columna final
            # Esto evita problemas de tipo de datos
            month_values = {}
            
            # Para cada asset, calcular el consumo del mes
            for asset_id in assets:
                # Filtrar por asset y rango de fechas del mes
                asset_month_data = tag_df[
                    (tag_df['asset_id'] == asset_id) & 
                    (tag_df['date'] >= month_start) & 
                    (tag_df['date'] <= month_end)
                ]
                
                if not asset_month_data.empty and len(asset_month_data) >= 2:
                    # Ordenar por fecha
                    asset_month_data = asset_month_data.sort_values('date')
                    
                    # Obtener la primera y última lectura del mes
                    first_reading = asset_month_data.iloc[0]['consumption']
                    last_reading = asset_month_data.iloc[-1]['consumption']
                    
                    # Calcular el consumo como la diferencia entre la última y la primera lectura
                    try:
                        # Convertir a números si son strings
                        if isinstance(first_reading, str):
                            first_reading = float(first_reading)
                        if isinstance(last_reading, str):
                            last_reading = float(last_reading)
                            
                        # Calcular la diferencia
                        consumption_value = last_reading - first_reading
                        
                        # Si el valor es negativo (posible error o reinicio del contador), usar el último valor
                        if consumption_value < 0:
                            debug_log(f"[WARNING] generate_monthly_readings_by_consumption_type - Consumo negativo para asset {asset_id}, mes {month_name}: {consumption_value}. Usando último valor: {last_reading}")
                            consumption_value = last_reading
                    except (ValueError, TypeError) as e:
                        debug_log(f"[ERROR] generate_monthly_readings_by_consumption_type - Error al calcular consumo para asset {asset_id}, mes {month_name}: {str(e)}")
                        consumption_value = np.nan
                    
                    month_values[asset_id] = consumption_value
                    debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Asset {asset_id}, Mes {month_name}, Consumo calculado: {consumption_value}")
                elif not asset_month_data.empty and len(asset_month_data) == 1:
                    # Si solo hay una lectura en el mes, usar ese valor (no podemos calcular diferencia)
                    consumption_value = asset_month_data.iloc[0]['consumption']
                    month_values[asset_id] = consumption_value
                    debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Asset {asset_id}, Mes {month_name}, Solo una lectura disponible: {consumption_value}")
                else:
                    # Si no hay datos, almacenar NaN
                    month_values[asset_id] = np.nan
                    debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Asset {asset_id}, Mes {month_name}, Sin datos")
            
            # Añadir la columna al DataFrame
            table_df[month_name] = pd.Series(month_values)
            
            # Verificar los valores de la columna
            debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Columna {month_name}, Valores: {table_df[month_name].tolist()}")
        
        # Guardar la tabla en el diccionario
        tables_by_consumption_type[consumption_type] = table_df
        debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Tabla para {consumption_type} creada con {len(table_df)} filas y {len(table_df.columns)} columnas")
    
    return tables_by_consumption_type 

def load_asset_detail_data(project_id, asset_id, consumption_tags, month, jwt_token=None):
    """
    Carga los datos detallados de un asset específico para un mes determinado.
    
    Args:
        project_id (str): ID del proyecto
        asset_id (str): ID del asset
        consumption_tags (list): Lista de tags de consumo
        month (str): Mes en formato 'YYYY-MM'
        jwt_token (str, optional): Token JWT para autenticación
        
    Returns:
        pd.DataFrame: DataFrame con los datos detallados o None si no hay datos
    """
    try:
        # Convertir el mes a fecha de inicio y fin
        year, month_num = map(int, month.split('-'))
        start_date = datetime(year, month_num, 1)
        
        # Calcular el último día del mes
        if month_num == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month_num + 1, 1) - timedelta(days=1)
        
        debug_log(f"[DEBUG] load_asset_detail_data - Cargando datos para asset {asset_id} en el mes {month}")
        debug_log(f"[DEBUG] load_asset_detail_data - Rango de fechas: {start_date} a {end_date}")
        
        # Cargar todos los datos del CSV
        all_data = load_all_csv_data(
            project_id=project_id,
            consumption_tags=consumption_tags,
            jwt_token=jwt_token
        )
        
        # Filtrar por asset_id y rango de fechas
        if all_data is not None and not all_data.empty:
            debug_log(f"[DEBUG] load_asset_detail_data - Datos cargados: {len(all_data)} filas")
            
            # Asegurar que la columna date es datetime
            all_data['date'] = pd.to_datetime(all_data['date'])
            
            # Filtrar por asset_id y rango de fechas
            filtered_data = all_data[
                (all_data['asset_id'] == asset_id) &
                (all_data['date'] >= start_date) &
                (all_data['date'] <= end_date)
            ]
            
            debug_log(f"[DEBUG] load_asset_detail_data - Datos filtrados: {len(filtered_data)} filas")
            
            # Ordenar por fecha
            if not filtered_data.empty:
                filtered_data = filtered_data.sort_values('date')
                
                # Convertir columnas de tipo Period a string para evitar problemas de serialización
                for col in filtered_data.columns:
                    if pd.api.types.is_period_dtype(filtered_data[col]):
                        filtered_data[col] = filtered_data[col].astype(str)
            
            return filtered_data
        
        debug_log(f"[DEBUG] load_asset_detail_data - No se encontraron datos para el asset {asset_id}")
        return None
    except Exception as e:
        debug_log(f"[ERROR] load_asset_detail_data - Error cargando datos: {str(e)}")
        import traceback
        debug_log(f"[ERROR] load_asset_detail_data - Traceback: {traceback.format_exc()}")
        return None

# Add a new function to manually clear the cache when needed
def clear_data_cache():
    """
    Clear the CSV data cache.
    """
    global _CSV_DATA_CACHE, _CACHE_TIMESTAMP
    _CSV_DATA_CACHE = {}
    _CACHE_TIMESTAMP = {}
    print("[INFO METRICS] clear_data_cache - Data cache cleared")
    return True

def clear_all_caches():
    """Clear all data caches in the system."""
    # Clear the CSV data cache
    clear_data_cache()
    
    # Clear the processed data cache
    try:
        from utils.metrics.data_processing import clear_processed_data_cache
        clear_processed_data_cache()
    except ImportError:
        print("[WARN] clear_all_caches - Could not import clear_processed_data_cache function")
    
    # Clear any visualization caches
    try:
        import plotly.io as pio
        pio.templates.default = "plotly"  # Reset default template
    except ImportError:
        print("[WARN] clear_all_caches - Could not reset plotly templates")
    
    print("[INFO] clear_all_caches - All caches cleared successfully")
    return True 