"""
Implementación recomendada para la función extract_asset_and_tag.

Este archivo contiene la versión recomendada de la función extract_asset_and_tag
que se puede utilizar para reemplazar la versión actual en utils/data_loader.py.
"""

import os
from typing import Tuple, Optional


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


# Función auxiliar de logging (debe ser reemplazada por la real en la implementación)
def debug_log(message, level="info"):
    """Función auxiliar para logging. Se debe reemplazar por la implementación real."""
    print(message) 