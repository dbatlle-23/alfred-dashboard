import os
import pandas as pd
import glob
import re
from typing import Dict, List, Optional, Tuple, Union
import logging
import numpy as np
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

# Variable global para almacenar el estado de debug
_DEBUG_MODE = None
_DEBUG_CHECKED = False

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

def extract_asset_and_tag(filename: str) -> Tuple[str, str]:
    """
    Extrae el ID del asset y el tag del nombre del archivo.
    
    Formatos soportados:
    - daily_readings_ASSETID_tag_name.csv
    - daily_readings_ASSETID__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_tag_name.csv
    - daily_readings_ASSETID_tag_name_YYYY.csv
    
    Args:
        filename: Nombre del archivo
        
    Returns:
        Tupla con (asset_id, tag)
    """
    try:
        # Obtener solo el nombre del archivo sin la ruta
        base_filename = os.path.basename(filename)
        debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Procesando archivo: {base_filename}")
        
        # Verificar si es un formato conocido
        if 'daily_readings_' not in base_filename:
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Formato de archivo no reconocido: {base_filename}")
            return None, None
        
        # Verificar si el archivo contiene el formato TRANSVERSAL
        if '__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_' in base_filename:
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
            
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Archivo: {base_filename} -> Asset ID: {asset_id}, Tag: {tag}")
            return asset_id, tag
            
        # Para otros formatos, usar la lógica original
        # Eliminar 'daily_readings_' del inicio
        parts = base_filename.replace('daily_readings_', '').split('_')
        debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Partes del nombre después de eliminar 'daily_readings_': {parts}")
        
        # Extraer el asset_id (primera parte después de daily_readings_)
        asset_id = parts[0]
        debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Asset ID extraído: {asset_id}")
        
        # Determinar el tag basado en el formato del archivo
        if len(parts) >= 3 and parts[-1].endswith('.csv'):
            # Formato: daily_readings_ASSETID_tag_name.csv
            # Unir todas las partes excepto el asset_id y la extensión
            tag = '_'.join(parts[1:]).replace('.csv', '')
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Tag extraído del formato estándar: {tag}")
        elif len(parts) >= 3 and parts[-1].isdigit():
            # Formato: daily_readings_ASSETID_tag_name_YYYY.csv
            # Unir todas las partes excepto el asset_id y el año
            tag = '_'.join(parts[1:-1])
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Tag extraído del formato con año: {tag}")
        else:
            # Si no podemos determinar el formato, usamos un valor por defecto
            tag = 'unknown'
            debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - No se pudo determinar el formato del archivo: {base_filename}")
        
        # Añadir log para depuración
        debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - Archivo: {base_filename} -> Asset ID: {asset_id}, Tag: {tag}")
            
        return asset_id, tag
    except Exception as e:
        debug_log(f"[DEBUG DETALLADO] extract_asset_and_tag - No se pudo extraer assetId y tag de {filename}: {str(e)}")
        print(f"No se pudo extraer assetId y tag de {filename}")
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
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Añadir columna de timestamp (útil para algunas visualizaciones)
        df['timestamp'] = df['date'].astype(int) // 10**9
        
        # Mapear el tipo de consumo basado en el tag
        consumption_type = TAGS_TO_CONSUMPTION_TYPE.get(tag, "Desconocido")
        df['consumption_type'] = consumption_type
        debug_log(f"[DEBUG DETALLADO] load_csv_data - Tipo de consumo mapeado: {consumption_type} para tag: {tag}")
        
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
        df['consumption'] = df['value']
        
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
    # Log detallado para verificar el valor exacto de project_id
    debug_log(f"[DEBUG CRÍTICO] load_all_csv_data - Valor exacto de project_id recibido: '{project_id}', tipo: {type(project_id)}")
    
    all_data = []
    
    # Si hay tags de consumo, registrarlos para depuración
    if consumption_tags:
        debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Filtrando archivos por tags de consumo: {consumption_tags}")
    
    # Si hay project_id, obtener los assets del proyecto desde la API
    project_assets = []
    if project_id and project_id != "all":
        try:
            from utils.api import get_project_assets
            debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Obteniendo assets para el proyecto {project_id} desde la API")
            project_assets = get_project_assets(project_id, jwt_token)
            if project_assets:
                project_asset_ids = [asset.get('id') for asset in project_assets]
                debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Se obtuvieron {len(project_asset_ids)} assets para el proyecto {project_id}: {project_asset_ids}")
            else:
                debug_log(f"[DEBUG DETALLADO] load_all_csv_data - No se encontraron assets para el proyecto {project_id} en la API")
        except Exception as e:
            debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Error al obtener assets del proyecto {project_id}: {str(e)}")
    
    # Buscar todos los directorios de proyecto
    project_dirs = [d for d in glob.glob(os.path.join(base_path, "*")) if os.path.isdir(d)]
    debug_log(f"[DEBUG CRÍTICO] load_all_csv_data - Directorios de proyecto encontrados: {project_dirs}")
    debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Encontrados {len(project_dirs)} directorios de proyecto")
    
    # Filtrar directorios de proyecto si se especificó un project_id
    if project_id and project_id != "all":
        # Log para verificar la condición de filtrado
        debug_log(f"[DEBUG CRÍTICO] load_all_csv_data - Aplicando filtro de project_id: '{project_id}'")
        
        # Mostrar los nombres de los directorios para comparar con project_id
        dir_basenames = [os.path.basename(d) for d in project_dirs]
        debug_log(f"[DEBUG CRÍTICO] load_all_csv_data - Nombres de directorios para comparar: {dir_basenames}")
        
        # Aplicar el filtro
        filtered_dirs = [d for d in project_dirs if os.path.basename(d) == project_id]
        debug_log(f"[DEBUG CRÍTICO] load_all_csv_data - Directorios después del filtro: {filtered_dirs}")
        
        project_dirs = filtered_dirs
        debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Filtrando por proyecto {project_id}, quedan {len(project_dirs)} directorios")
    
    # Si no hay directorios de proyecto, buscar archivos CSV directamente en base_path
    if not project_dirs:
        debug_log(f"[DEBUG DETALLADO] load_all_csv_data - No se encontraron directorios de proyecto, buscando archivos CSV en {base_path}")
        csv_files = glob.glob(os.path.join(base_path, "daily_readings_*.csv"))
        debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Encontrados {len(csv_files)} archivos CSV en {base_path}")
        for file_path in csv_files:
            # Extraer asset_id y tag para filtrar
            asset_id, tag = extract_asset_and_tag(file_path)
            
            # Filtrar por assets del proyecto si están disponibles
            if project_assets and asset_id not in [a.get('id') for a in project_assets]:
                debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Omitiendo archivo {file_path} porque el asset {asset_id} no pertenece al proyecto {project_id}")
                continue
            
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
            debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Buscando archivos CSV en directorio de proyecto: {project_dir} (ID: {current_project_id})")
            
            # Si estamos filtrando por un proyecto específico y este no coincide, omitirlo
            if project_id and project_id != "all" and current_project_id != project_id:
                debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Omitiendo directorio {project_dir} porque no coincide con el proyecto seleccionado {project_id}")
                continue
                
            csv_files = glob.glob(os.path.join(project_dir, "daily_readings_*.csv"))
            debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Encontrados {len(csv_files)} archivos CSV en {project_dir}")
            
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
                    
                    # Filtrar por assets del proyecto si están disponibles
                    if project_assets and asset_id not in [a.get('id') for a in project_assets]:
                        debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Omitiendo archivo {file_path} porque el asset {asset_id} no pertenece al proyecto {project_id}")
                        continue
                    
                    # Verificar si el archivo corresponde a los tags de consumo seleccionados
                    if consumption_tags:
                        if not tag_matches_selection(tag, consumption_tags):
                            debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Omitiendo archivo {file_path} porque no corresponde a los tags seleccionados")
                            continue
                        else:
                            debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Procesando archivo {file_path} que coincide con los tags seleccionados")
                    
                    df = load_csv_data(file_path)
                    if df is not None:
                        all_data.append(df)
    
    # Combinar todos los DataFrames
    if all_data:
        debug_log(f"[DEBUG DETALLADO] load_all_csv_data - Combinando {len(all_data)} DataFrames")
        combined_df = pd.concat(all_data, ignore_index=True)
        debug_log(f"[DEBUG DETALLADO] load_all_csv_data - DataFrame combinado tiene {len(combined_df)} filas")
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
    Filtra los datos según los criterios especificados.
    
    Args:
        df: DataFrame con los datos combinados
        client_id: ID del cliente para filtrar (opcional)
        project_id: ID del proyecto para filtrar (opcional)
        asset_id: ID del asset para filtrar (opcional)
        consumption_type: Tipo de consumo para filtrar (opcional, deprecated). Puede ser un string o una lista de strings.
        consumption_tags: Lista de tags de consumo para filtrar (opcional)
        start_date: Fecha de inicio para filtrar (opcional)
        end_date: Fecha de fin para filtrar (opcional)
        
    Returns:
        DataFrame filtrado
    """
    if df.empty:
        debug_log("[DEBUG DETALLADO] filter_data - DataFrame vacío, no hay datos para filtrar")
        return df
    
    debug_log(f"[DEBUG DETALLADO] filter_data - Iniciando filtrado con parámetros: client_id={client_id}, project_id={project_id}, asset_id={asset_id}, consumption_type={consumption_type}, consumption_tags={consumption_tags}, start_date={start_date}, end_date={end_date}")
    debug_log(f"[DEBUG DETALLADO] filter_data - DataFrame original tiene {len(df)} filas")
    
    filtered_df = df.copy()
    
    # Filtrar por client_id
    if client_id and client_id != "all":
        debug_log(f"[DEBUG DETALLADO] filter_data - Filtrando por client_id: {client_id}")
        # Si el DataFrame tiene una columna client_id, filtrar directamente
        if 'client_id' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['client_id'] == client_id]
            debug_log(f"[DEBUG DETALLADO] filter_data - Después de filtrar por client_id, quedan {len(filtered_df)} filas")
        else:
            # Si no tiene client_id y tenemos un project_id específico, no filtrar por client_id
            # ya que los datos ya fueron cargados desde los archivos CSV del proyecto
            if project_id and project_id != "all":
                debug_log(f"[DEBUG DETALLADO] filter_data - No se filtra por client_id porque ya tenemos un project_id específico: {project_id}")
            else:
                # Si no tenemos un project_id específico, intentar obtener los proyectos del cliente
                try:
                    from utils.api import get_projects
                    projects = get_projects(client_id=client_id)
                    if projects:
                        project_ids = [p['id'] for p in projects]
                        debug_log(f"[DEBUG DETALLADO] filter_data - Obtenidos {len(project_ids)} proyectos para el cliente {client_id}: {project_ids}")
                        filtered_df = filtered_df[filtered_df['project_id'].isin(project_ids)]
                        debug_log(f"[DEBUG DETALLADO] filter_data - Después de filtrar por proyectos del cliente, quedan {len(filtered_df)} filas")
                    else:
                        debug_log(f"[DEBUG DETALLADO] filter_data - No se encontraron proyectos para el cliente {client_id}")
                except Exception as e:
                    debug_log(f"[DEBUG DETALLADO] filter_data - Error al filtrar por client_id: {str(e)}")
    
    # Filtrar por project_id
    if project_id and project_id != "all":
        debug_log(f"[DEBUG DETALLADO] filter_data - Filtrando por project_id: {project_id}")
        filtered_df = filtered_df[filtered_df['project_id'] == project_id]
        debug_log(f"[DEBUG DETALLADO] filter_data - Después de filtrar por project_id, quedan {len(filtered_df)} filas")
    
    # Filtrar por asset_id
    if asset_id and asset_id != "all":
        debug_log(f"[DEBUG DETALLADO] filter_data - Filtrando por asset_id: {asset_id}")
        filtered_df = filtered_df[filtered_df['asset_id'] == asset_id]
        debug_log(f"[DEBUG DETALLADO] filter_data - Después de filtrar por asset_id, quedan {len(filtered_df)} filas")
    
    # Filtrar por consumption_tags (nueva implementación)
    if consumption_tags and isinstance(consumption_tags, list) and len(consumption_tags) > 0:
        debug_log(f"[DEBUG DETALLADO] filter_data - Filtrando por consumption_tags: {consumption_tags}")
        # Mapear los tags a tipos de consumo legibles
        consumption_types = [TAGS_TO_CONSUMPTION_TYPE.get(tag, tag) for tag in consumption_tags]
        debug_log(f"[DEBUG DETALLADO] filter_data - Tipos de consumo mapeados: {consumption_types}")
        # Filtrar por los tipos de consumo mapeados
        filtered_df = filtered_df[filtered_df['consumption_type'].isin(consumption_types)]
        debug_log(f"[DEBUG DETALLADO] filter_data - Después de filtrar por consumption_tags, quedan {len(filtered_df)} filas")
        # Mostrar los tipos de consumo únicos en el DataFrame filtrado
        unique_consumption_types = filtered_df['consumption_type'].unique()
        debug_log(f"[DEBUG DETALLADO] filter_data - Tipos de consumo únicos en el DataFrame filtrado: {unique_consumption_types}")
    # Mantener compatibilidad con el parámetro consumption_type (deprecated)
    elif consumption_type and consumption_type != "all":
        debug_log(f"[DEBUG DETALLADO] filter_data - Filtrando por consumption_type (deprecated): {consumption_type}")
        # Verificar si consumption_type es una lista o un string
        if isinstance(consumption_type, list):
            # Si es una lista, usar isin para filtrar
            filtered_df = filtered_df[filtered_df['consumption_type'].isin(consumption_type)]
        else:
            # Si es un string, usar == para filtrar
            filtered_df = filtered_df[filtered_df['consumption_type'] == consumption_type]
        debug_log(f"[DEBUG DETALLADO] filter_data - Después de filtrar por consumption_type, quedan {len(filtered_df)} filas")
    
    # Filtrar por rango de fechas
    if start_date:
        debug_log(f"[DEBUG DETALLADO] filter_data - Filtrando por fecha de inicio: {start_date}")
        filtered_df = filtered_df[filtered_df['date'] >= pd.to_datetime(start_date)]
        debug_log(f"[DEBUG DETALLADO] filter_data - Después de filtrar por fecha de inicio, quedan {len(filtered_df)} filas")
    
    if end_date:
        debug_log(f"[DEBUG DETALLADO] filter_data - Filtrando por fecha de fin: {end_date}")
        filtered_df = filtered_df[filtered_df['date'] <= pd.to_datetime(end_date)]
        debug_log(f"[DEBUG DETALLADO] filter_data - Después de filtrar por fecha de fin, quedan {len(filtered_df)} filas")
    
    debug_log(f"[DEBUG DETALLADO] filter_data - Filtrado completado, DataFrame resultante tiene {len(filtered_df)} filas")
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
    
    # Verificar coincidencia con formato __TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_
    for selected_tag in selected_tags:
        # Si el tag del archivo tiene el formato completo (con __)
        if tag.startswith('__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_') and selected_tag == tag:
            debug_log(f"[DEBUG DETALLADO] tag_matches_selection - Coincidencia exacta con tag completo: '{tag}'")
            return True
            
        # Si el tag seleccionado tiene el formato completo pero el tag del archivo no
        if selected_tag.startswith('_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_') or selected_tag.startswith('__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_'):
            # Normalizar ambos tags para comparación (eliminar _ o __ iniciales)
            clean_selected_tag = selected_tag.replace('_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_', '').replace('__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_', '')
            clean_file_tag = tag.replace('_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_', '').replace('__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_', '')
            
            debug_log(f"[DEBUG DETALLADO] tag_matches_selection - Comparando tags limpios: '{clean_file_tag}' con '{clean_selected_tag}'")
            
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
        
        # Para cada mes, encontrar la última lectura de cada asset
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
            
            # Para cada asset, encontrar la última lectura del mes
            for asset_id in assets:
                # Filtrar por asset y rango de fechas del mes
                asset_month_data = tag_df[
                    (tag_df['asset_id'] == asset_id) & 
                    (tag_df['date'] >= month_start) & 
                    (tag_df['date'] <= month_end)
                ]
                
                if not asset_month_data.empty:
                    # Ordenar por fecha y tomar la última lectura
                    last_reading = asset_month_data.sort_values('date').iloc[-1]
                    # Almacenar el valor en el diccionario
                    consumption_value = last_reading['consumption']
                    month_values[asset_id] = consumption_value
                    debug_log(f"[DEBUG] generate_monthly_readings_by_consumption_type - Asset {asset_id}, Mes {month_name}, Valor: {consumption_value}")
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