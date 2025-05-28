"""
Propuesta de mejora para la función extract_asset_and_tag.

Este módulo contiene una versión mejorada de la función extract_asset_and_tag 
que maneja correctamente el formato de nombre de archivo según PROJECT_CONTEXT.md, 
pero mantiene compatibilidad con los formatos actuales.
"""

import os
from typing import Tuple, Dict, Optional

# Definición del mapeo (copia del original)
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

# Definimos un mapeo inverso para buscar tags basados en la parte final
CONSUMPTION_TYPE_TO_TAG = {}
for tag, consumption_type in TAGS_TO_CONSUMPTION_TYPE.items():
    # Extraer la última parte del tag (después del último guión bajo)
    short_name = tag.split('_')[-1].lower()
    CONSUMPTION_TYPE_TO_TAG[short_name] = tag

def extract_asset_and_tag_improved(filename: str, debug_log=None) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae el ID del asset y el tag del nombre del archivo.
    
    Formatos soportados (en orden de prioridad):
    1. daily_readings_<asset_id>_<consumption_type>.csv (Formato principal según PROJECT_CONTEXT.md)
    2. daily_readings_<asset_id>__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_<tag>.csv
    3. daily_readings_<asset_id>__<tag>.csv
    4. daily_readings_<asset_id>__<tag>_<year>.csv
    
    Args:
        filename: Nombre del archivo
        debug_log: Función opcional para registro de debug
        
    Returns:
        Tupla con (asset_id, tag) o (None, None) si no se puede extraer
    """
    # Función auxiliar para logging si está disponible
    def log(message, level="info"):
        if debug_log:
            debug_log(message, level)
    
    try:
        # Obtener solo el nombre del archivo sin la ruta
        base_filename = os.path.basename(filename)
        log(f"Procesando archivo: {base_filename}")
        
        # Verificar si es un formato conocido
        if 'daily_readings_' not in base_filename:
            log(f"Formato de archivo no reconocido: {base_filename}")
            return None, None
        
        # Remover el prefijo 'daily_readings_'
        filename_without_prefix = base_filename.replace('daily_readings_', '')
        
        # CASO 1: Verificar si el archivo usa el formato del PROJECT_CONTEXT.md: 
        # daily_readings_<asset_id>_<consumption_type>.csv
        if '_' in filename_without_prefix and not filename_without_prefix.startswith('_'):
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
                # Convertir a minúsculas para comparación case-insensitive
                consumption_type_lower = consumption_type_part.lower()
                
                # Buscar en el mapeo inverso
                for short_name, full_tag in CONSUMPTION_TYPE_TO_TAG.items():
                    if short_name in consumption_type_lower or consumption_type_lower in short_name:
                        tag = full_tag
                        break
            
            # Si aún no se encuentra, intentar con formato de prefijo TRANSVERSAL
            if not tag and 'TRANSVERSAL' in consumption_type_part:
                # Normalizar el formato para que tenga un guión bajo al inicio
                tag = '_' + consumption_type_part
            
            # Si sigue sin encontrarse, usar una convención para crear un tag válido
            if not tag:
                # Buscar coincidencias parciales por palabra clave
                for known_tag in TAGS_TO_CONSUMPTION_TYPE.keys():
                    parts_to_check = ["WATER", "ENERGY", "FLOW"]
                    for part in parts_to_check:
                        if part in consumption_type_part and part in known_tag:
                            tag = known_tag
                            break
                    if tag:
                        break
            
            # Si no se ha encontrado ninguna coincidencia, usar el tag original pero estandarizado
            if not tag:
                tag = consumption_type_part
            
            log(f"Formato PROJECT_CONTEXT: Asset ID: {asset_id}, Tag: {tag}")
            return asset_id, tag
        
        # CASO 2: Formato con doble guión bajo y tag transversal
        # daily_readings_<asset_id>__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_<tag>.csv
        elif '__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_' in base_filename:
            # Formato: daily_readings_ASSETID__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_tag_name.csv
            log(f"Detectado formato con __TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_")
            
            # Extraer el asset_id (parte entre daily_readings_ y __)
            asset_id_part = base_filename.split('__')[0]
            asset_id = asset_id_part.replace('daily_readings_', '')
            
            # Extraer el tag completo pero normalizado con un solo guión bajo al inicio
            tag_part = base_filename.split('__')[1]
            # Eliminar la extensión .csv si está presente
            if tag_part.endswith('.csv'):
                tag_part = tag_part[:-4]
            # Normalizar el tag para que tenga un solo guión bajo al inicio
            tag = '_' + tag_part
            
            log(f"Formato con tag transversal: Asset ID: {asset_id}, Tag: {tag}")
            return asset_id, tag
        
        # CASO 3: Formato con doble guión bajo pero sin tag transversal
        # daily_readings_<asset_id>__<tag>.csv
        elif '__' in base_filename:
            parts = base_filename.split('__')
            asset_id = parts[0].replace('daily_readings_', '')
            tag_part = parts[1]
            
            # Eliminar la extensión .csv y posibles años al final
            if tag_part.endswith('.csv'):
                tag_part = tag_part[:-4]
            
            # CASO 4: Verificar si tiene año al final
            # daily_readings_<asset_id>__<tag>_<year>.csv
            if '_' in tag_part and tag_part.split('_')[-1].isdigit():
                # Quitar el año del final
                tag_parts = tag_part.split('_')
                tag = '_'.join(tag_parts[:-1])
            else:
                tag = tag_part
            
            log(f"Formato con doble guión bajo: Asset ID: {asset_id}, Tag: {tag}")
            return asset_id, tag
        
        # Si llegamos aquí, intentar un último esfuerzo para extraer información
        parts = filename_without_prefix.split('_')
        if len(parts) >= 1:
            asset_id = parts[0]
            log(f"Extrayendo asset_id en último intento: {asset_id}")
            
            if len(parts) >= 2:
                # Intentar reconstruir el tag
                tag = '_'.join(parts[1:]).replace('.csv', '')
                return asset_id, tag
            
            return asset_id, 'unknown'
        
        # Si no podemos identificar ningún formato
        log(f"No se pudo identificar ningún formato conocido: {base_filename}", "warning")
        return None, None
        
    except Exception as e:
        if debug_log:
            debug_log(f"Error extrayendo asset_id y tag de {filename}: {str(e)}", "error")
        print(f"No se pudo extraer assetId y tag de {filename}: {str(e)}")
        return None, None

# Función para probar la implementación propuesta
def test_with_examples():
    """Prueba la implementación mejorada con varios ejemplos"""
    test_cases = [
        # Formato PROJECT_CONTEXT.md
        "daily_readings_ASSET123_DOMESTIC_COLD_WATER.csv",
        "daily_readings_DL39NQJXC2T68_DOMESTIC_WATER_GENERAL.csv",
        "daily_readings_VVMJJ3UNY28C_DOMESTIC_ENERGY_GENERAL.csv",
        
        # Formato con tag transversal
        "daily_readings_ASSET123__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_COLD_WATER.csv",
        
        # Formato con doble guión bajo
        "daily_readings_ASSET123__water_consumption.csv",
        
        # Formato con año
        "daily_readings_ASSET123__water_consumption_2025.csv",
        
        # Formatos inválidos
        "readings_ASSET123_water.csv",
        "arbitrary_file_name.csv"
    ]
    
    print("Probando implementación mejorada de extract_asset_and_tag:")
    print("-" * 50)
    
    for filename in test_cases:
        asset_id, tag = extract_asset_and_tag_improved(filename)
        print(f"Archivo: {filename}")
        print(f"  - Asset ID: {asset_id}")
        print(f"  - Tag: {tag}")
        
        # Verificar si el tag puede ser mapeado a un tipo de consumo
        consumption_type = TAGS_TO_CONSUMPTION_TYPE.get(tag, "Desconocido")
        print(f"  - Tipo de consumo: {consumption_type}")
        print("-" * 50)

if __name__ == "__main__":
    # Ejecutar ejemplos de demostración
    test_with_examples() 