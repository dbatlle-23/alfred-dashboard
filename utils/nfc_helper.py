#!/usr/bin/env python3

from utils.api import get_nfc_passwords
from utils.logging import get_logger

logger = get_logger(__name__)

def fetch_for_asset(asset_id, token):
    """
    Wrapper mejorado para obtener y procesar datos NFC de un asset específico.
    Utiliza el refactorizado get_nfc_passwords de utils.api y reestructura su salida.
    
    Args:
        asset_id (str): ID del asset del cual obtener las contraseñas NFC
        token (str): Token JWT para autenticación
    
    Returns:
        tuple: (success, list_of_devices) donde list_of_devices contiene dispositivos 
               con una lista 'sensors', cada sensor con 'sensor_id', 'name', 'sensor_type', 'password'.
    """
    try:
        logger.info(f"Iniciando fetch_for_asset para asset_id={asset_id}")
        
        # Obtener datos NFC desde la API usando el refactorizado get_nfc_passwords
        # Este ya llama al endpoint /sensor-passwords/deployment/ y hace un pre-procesamiento.
        api_response_dict = get_nfc_passwords(asset_id, token) # Renamed for clarity
        
        if not api_response_dict or not isinstance(api_response_dict, dict) or 'data' not in api_response_dict:
            logger.warning(f"No se obtuvieron datos NFC válidos desde get_nfc_passwords para asset_id={asset_id}. Respuesta: {api_response_dict}")
            return False, []
        
        data_section = api_response_dict['data']
        if not isinstance(data_section, dict) or 'devices' not in data_section:
            logger.warning(f"Sección 'data' o 'data.devices' faltante/inválida en la respuesta de get_nfc_passwords. Data section: {data_section}")
            return False, []

        # devices_from_api_call es una lista de grid_device_objects, 
        # donde cada objeto tiene sensor_X: password como propiedades directas.
        devices_from_api_call = data_section['devices']
        if not isinstance(devices_from_api_call, list):
            logger.warning(f"'data.devices' no es una lista. Contenido: {devices_from_api_call}")
            return False, []
            
        logger.debug(f"fetch_for_asset: {len(devices_from_api_call)} dispositivos recibidos de get_nfc_passwords.")

        processed_devices_output = []
        
        for device_obj_from_api in devices_from_api_call: # This is the grid_device_object
            if not isinstance(device_obj_from_api, dict):
                logger.warning(f"Item en devices_from_api_call no es un diccionario: {device_obj_from_api}")
                continue
            
            # Usar real_device_id como el ID principal para la estructura interna de device_processed
            internal_device_id = device_obj_from_api.get('real_device_id')
            display_device_name = device_obj_from_api.get('device_id') # Este es el nombre para mostrar

            if not internal_device_id:
                logger.warning(f"Dispositivo de API no tiene 'real_device_id': {device_obj_from_api}. Usando 'device_id' como fallback para internal_device_id: {display_device_name}")
                internal_device_id = display_device_name # Fallback, podría ser problemático si no es único/estable
                if not internal_device_id: # Si ambos son None/empty
                    logger.error(f"Dispositivo de API no tiene ni 'real_device_id' ni 'device_id' para usar como identificador. Omitiendo: {device_obj_from_api}")
                    continue
            
            device_processed_for_grid = {
                "device_id": internal_device_id, # El ID real del hardware
                "device_name": device_obj_from_api.get('lock_name', display_device_name), # Usar lock_name si existe, sino el display_name
                "device_type": device_obj_from_api.get('device_type', 'UNKNOWN'),
                "gateway_id": device_obj_from_api.get('gateway_id'),
                "asset_id": asset_id, # asset_id del argumento de la función
                "sensors": [] # Esta lista se poblará ahora
            }
            
            # Extraer datos de sensores desde las claves sensor_X del device_obj_from_api
            nfc_sensors_found_for_device = False
            for key, value in device_obj_from_api.items():
                if key.startswith("sensor_"):
                    sensor_id_str = key.replace("sensor_", "")
                    if sensor_id_str.isdigit(): # Asegurar que es un ID numérico de sensor
                        sensor_entry = {
                            "sensor_id": sensor_id_str,
                            "name": f"NFC {sensor_id_str}", # Nombre genérico
                            "sensor_type": "NFC_CODE",      # Sabemos que estos son NFC_CODE
                            "password": value if value is not None else "" # Usar el valor directamente
                        }
                        device_processed_for_grid["sensors"].append(sensor_entry)
                        nfc_sensors_found_for_device = True
                        logger.debug(f"  Sensor {sensor_id_str} (password: '{value}') añadido a dispositivo procesado {internal_device_id}")
            
            if nfc_sensors_found_for_device:
                processed_devices_output.append(device_processed_for_grid)
                logger.info(f"Dispositivo {internal_device_id} ('{device_processed_for_grid['device_name']}') procesado con {len(device_processed_for_grid['sensors'])} sensores NFC.")
            else:
                logger.info(f"Dispositivo {internal_device_id} ('{device_processed_for_grid['device_name']}') no tenía datos de sensor NFC en formato sensor_X. Excluyendo.")

        logger.info(f"fetch_for_asset: Procesados {len(processed_devices_output)} dispositivos finales para asset {asset_id}")
        return True, processed_devices_output
        
    except Exception as e:
        logger.error(f"Error en fetch_for_asset para asset_id={asset_id}: {str(e)}")
        import traceback
        logger.error(f"Fetch_for_asset Traceback: {traceback.format_exc()}")
        return False, []

def get_available_slots(device_data):
    """
    Obtiene los slots disponibles (vacíos) en un dispositivo.
    
    Args:
        device_data (dict): Diccionario con datos del dispositivo incluyendo sensores
        
    Returns:
        list: Lista de IDs de slots disponibles
    """
    try:
        if not device_data or not isinstance(device_data, dict):
            logger.warning("Datos de dispositivo inválidos para buscar slots disponibles")
            return []
            
        # Verificar si tiene sensores
        if "sensors" not in device_data or not device_data["sensors"]:
            logger.warning(f"Dispositivo {device_data.get('device_id')} no tiene sensores definidos")
            # En lugar de devolver vacío, asumimos que todos los slots están disponibles
            return [str(i) for i in range(7, 99)]  # Del 7 al 98
        
        # Lista de todos los posibles slots para códigos NFC (1 al 98)
        # Slots del 1 al 6 suelen ser especiales, así que empezamos desde el 7
        all_slots = [str(i) for i in range(7, 99)]
        
        # Encontrar slots que ya están usados (tienen valor no vacío)
        used_slots = []
        for sensor in device_data["sensors"]:
            if not isinstance(sensor, dict):
                continue
            
            sensor_id = str(sensor.get("sensor_id", ""))
            password = sensor.get("password", "")
            
            # Si el sensor tiene un valor (no vacío) entonces está ocupado
            if sensor_id and password and password.strip():
                used_slots.append(sensor_id)
        
        # Calcular slots disponibles (diferencia entre todos y usados)
        available_slots = [slot for slot in all_slots if slot not in used_slots]
        
        logger.debug(f"Slots disponibles para dispositivo {device_data.get('device_id')}: {available_slots}")
        return available_slots
        
    except Exception as e:
        logger.error(f"Error al obtener slots disponibles: {str(e)}")
        # En caso de error, devolver algunos slots predeterminados que suelen estar disponibles
        return [str(i) for i in range(7, 20)]

def check_card_exists(device_data, card_value):
    """
    Verifica si una tarjeta ya existe en algún slot del dispositivo.
    
    Args:
        device_data (dict): Diccionario con datos del dispositivo incluyendo sensores
        card_value (str): Valor de la tarjeta NFC a verificar
        
    Returns:
        tuple: (exists, slot_id) donde exists es booleano y slot_id es el ID del slot si existe
    """
    try:
        device_id = device_data.get('device_id', 'Unknown') if device_data else 'None'
        
        if not device_data or not isinstance(device_data, dict):
            logger.warning(f"Datos de dispositivo inválidos para verificar tarjeta existente. Device ID: {device_id}")
            return False, None
            
        if "sensors" not in device_data:
            logger.warning(f"No se encontraron sensores en dispositivo {device_id}")
            return False, None
            
        sensors = device_data["sensors"]
        if not sensors:
            logger.warning(f"Lista de sensores vacía en dispositivo {device_id}")
            return False, None
        
        logger.debug(f"Verificando tarjeta {card_value} en dispositivo {device_id} con {len(sensors)} sensores")
        
        # Normalizar el valor de la tarjeta para comparación
        if card_value:
            # Eliminar espacios
            normalized_card = card_value.strip()
            
            # Si es formato AA:BB:CC:DD, convertir a AABBCCDD para comparación
            if ":" in normalized_card:
                normalized_card = normalized_card.replace(":", "")
            
            # Si es formato AA-BB-CC-DD, convertir a AABBCCDD para comparación
            if "-" in normalized_card:
                normalized_card = normalized_card.replace("-", "")
                
            logger.debug(f"Tarjeta normalizada para búsqueda: '{card_value}' → '{normalized_card}'")
        else:
            # Si no hay valor, no puede existir
            return False, None
        
        # Verificar en cada sensor
        found_passwords = []  # Para logging de debug
        comparison_details = []  # Para debug detallado
        for sensor in sensors:
            if not isinstance(sensor, dict):
                continue
            
            sensor_id = str(sensor.get("sensor_id", ""))
            password = sensor.get("password", "")
            
            # Logging de debug para cada sensor con password
            if password and password.strip():
                found_passwords.append(f"slot {sensor_id}: {password}")
            
            # Normalizar el password para comparación
            if password:
                # Eliminar espacios
                normalized_password = password.strip()
                
                # Si es formato AA:BB:CC:DD, convertir a AABBCCDD para comparación
                if ":" in normalized_password:
                    normalized_password = normalized_password.replace(":", "")
                
                # Si es formato AA-BB-CC-DD, convertir a AABBCCDD para comparación
                if "-" in normalized_password:
                    normalized_password = normalized_password.replace("-", "")
                
                # Debug detallado de cada comparación
                comparison_details.append(f"slot {sensor_id}: '{password}' → '{normalized_password}' vs '{normalized_card}' = {normalized_password.upper() == normalized_card.upper()}")
                
                # Comparar los valores normalizados
                if normalized_password.upper() == normalized_card.upper():
                    logger.info(f"Tarjeta {card_value} encontrada en slot {sensor_id} del dispositivo {device_id}")
                    return True, sensor_id
        
        # Log detallado para ayudar en el debug
        logger.debug(f"Comparaciones detalladas: {comparison_details}")
        if found_passwords:
            logger.info(f"Tarjeta {card_value} NO encontrada en dispositivo {device_id}. Tarjetas existentes: {', '.join(found_passwords)}")
        else:
            logger.info(f"Tarjeta {card_value} NO encontrada en dispositivo {device_id}. No hay tarjetas asignadas en ningún slot.")
        
        # Si llegamos aquí, la tarjeta no existe en ningún slot
        return False, None
        
    except Exception as e:
        logger.error(f"Error al verificar tarjeta existente: {str(e)}")
        return False, None

def validate_card_uuid(uuid_value):
    """
    Valida el formato de un UUID de tarjeta NFC.
    
    Args:
        uuid_value (str): Valor del UUID a validar
        
    Returns:
        tuple: (is_valid, message) donde is_valid es booleano y message es un mensaje explicativo
    """
    import re
    
    if not uuid_value or not isinstance(uuid_value, str):
        return False, "El UUID no puede estar vacío"
    
    # Eliminar espacios
    uuid_clean = uuid_value.strip()
    
    # Patrón para formato AA:BB:CC:DD o AA-BB-CC-DD
    pattern1 = r'^([0-9A-F]{2}[:\-]){3}[0-9A-F]{2}$'
    
    # Patrón para formato AABBCCDD
    pattern2 = r'^[0-9A-F]{8}$'
    
    if re.match(pattern1, uuid_clean, re.IGNORECASE) or re.match(pattern2, uuid_clean, re.IGNORECASE):
        return True, "Formato de UUID válido"
    else:
        return False, "Formato de UUID no válido. Use el formato AA:BB:CC:DD o AABBCCDD."

def get_master_card_slot(device_data):
    """
    Identifica el slot que contiene la tarjeta maestra en un dispositivo.
    Normalmente es el slot 7, pero se verifica que tenga valor.
    
    Args:
        device_data (dict): Diccionario con datos del dispositivo incluyendo sensores
        
    Returns:
        str: ID del slot con la tarjeta maestra, o None si no se encuentra
    """
    try:
        if not device_data or not isinstance(device_data, dict) or "sensors" not in device_data:
            logger.warning("Datos de dispositivo inválidos para identificar tarjeta maestra")
            return None
        
        # Primero verificar el slot 7 que es el slot por defecto para tarjetas maestras
        for sensor in device_data["sensors"]:
            if not isinstance(sensor, dict):
                continue
            
            sensor_id = str(sensor.get("sensor_id", ""))
            password = sensor.get("password", "")
            
            # Si es el slot 7 y tiene un valor, es la tarjeta maestra
            if sensor_id == "7" and password and password.strip():
                logger.debug(f"Tarjeta maestra encontrada en slot 7 del dispositivo {device_data.get('device_id')}: {password}")
                return sensor_id
        
        # Si no se encontró en slot 7, buscar en otros slots con etiqueta "master"
        for sensor in device_data["sensors"]:
            if not isinstance(sensor, dict):
                continue
            
            sensor_id = str(sensor.get("sensor_id", ""))
            password = sensor.get("password", "")
            name = sensor.get("name", "").lower()
            
            # Si el nombre contiene "master" o "maestra" y tiene valor, puede ser una tarjeta maestra
            if password and password.strip() and ("master" in name or "maestra" in name):
                logger.debug(f"Tarjeta maestra alternativa encontrada en slot {sensor_id} del dispositivo {device_data.get('device_id')}: {password}")
                return sensor_id
        
        # No se encontró tarjeta maestra
        logger.debug(f"No se encontró tarjeta maestra en el dispositivo {device_data.get('device_id')}")
        return None
        
    except Exception as e:
        logger.error(f"Error al identificar tarjeta maestra: {str(e)}")
        return None
