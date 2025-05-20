#!/usr/bin/env python3

from utils.api import get_nfc_passwords
from utils.logging import get_logger

logger = get_logger(__name__)

def fetch_for_asset(asset_id, token):
    """
    Wrapper mejorado para obtener y procesar datos NFC de un asset específico.
    
    Args:
        asset_id (str): ID del asset del cual obtener las contraseñas NFC
        token (str): Token JWT para autenticación
    
    Returns:
        tuple: (asset_id, list_of_devices) donde list_of_devices contiene dispositivos con sus sensores NFC
    """
    try:
        logger.info(f"Obteniendo códigos NFC para asset_id={asset_id}")
        
        # Obtener datos NFC desde la API
        nfc_data = get_nfc_passwords(asset_id, token)
        
        # Validar respuesta
        if not nfc_data or not isinstance(nfc_data, dict) or 'data' not in nfc_data:
            logger.warning(f"No se obtuvieron datos NFC válidos para asset_id={asset_id}")
            return asset_id, []
        
        # Extraer lista de dispositivos de la respuesta
        devices_data = []
        data_section = nfc_data['data']
        
        # Manejar diferentes formatos de respuesta de la API
        if isinstance(data_section, dict) and 'devices' in data_section and isinstance(data_section['devices'], list):
            # Formato estándar: data.devices es una lista de dispositivos
            devices_data = data_section['devices']
            logger.debug(f"Formato estándar: {len(devices_data)} dispositivos encontrados")
            
        elif isinstance(data_section, list):
            # Formato alternativo: data es directamente una lista de dispositivos
            devices_data = data_section
            logger.debug(f"Formato lista: {len(devices_data)} dispositivos encontrados")
            
        elif isinstance(data_section, dict) and 'device_id' in data_section:
            # Formato de dispositivo único: data es un único dispositivo
            devices_data = [data_section]
            logger.debug("Formato de dispositivo único encontrado")
        
        # Procesar cada dispositivo para estandarizar la estructura
        processed_devices = []
        
        # Lista de sensores importantes que siempre deben incluirse
        important_sensors = ["2", "8", "9", "10"]
        
        for device in devices_data:
            if not isinstance(device, dict):
                continue
            
            device_id = device.get('device_id')
            if not device_id:
                continue
            
            # Asegurarse de que device tenga todos los campos necesarios
            device_processed = {
                "device_id": device_id,
                "device_name": device.get('device_name', 'Sin nombre'),
                "device_type": device.get('device_type', 'UNKNOWN'),
                "asset_id": asset_id,
                "sensors": []
            }
            
            # Manejar sensor_passwords
            sensor_passwords = device.get('sensor_passwords', [])
            if sensor_passwords and isinstance(sensor_passwords, list):
                for sensor_pw in sensor_passwords:
                    if not isinstance(sensor_pw, dict):
                        continue
                    
                    sensor_id = str(sensor_pw.get('sensor_id', ''))
                    if not sensor_id:
                        continue
                    
                    # Crear estructura de sensor
                    sensor = {
                        "sensor_id": sensor_id,
                        "name": sensor_pw.get('name', f"Sensor {sensor_id}"),
                        "sensor_type": sensor_pw.get('sensor_type', 'NFC_CODE'),
                        "password": sensor_pw.get('password', '')
                    }
                    
                    # Añadir el sensor a la lista de sensores del dispositivo
                    device_processed["sensors"].append(sensor)
            
            # Asegurar que los sensores importantes estén presentes
            existing_sensor_ids = [s["sensor_id"] for s in device_processed["sensors"]]
            for imp_sensor_id in important_sensors:
                if imp_sensor_id not in existing_sensor_ids:
                    # Crear sensor virtual para IDs importantes
                    virtual_sensor = {
                        "sensor_id": imp_sensor_id,
                        "name": f"NFC {imp_sensor_id}",
                        "sensor_type": "NFC_CODE",
                        "password": "",
                        "is_virtual": True
                    }
                    device_processed["sensors"].append(virtual_sensor)
                    logger.debug(f"Añadido sensor virtual importante {imp_sensor_id} al dispositivo {device_id}")
            
            processed_devices.append(device_processed)
        
        return asset_id, processed_devices
        
    except Exception as e:
        logger.error(f"Error al obtener códigos NFC para asset_id={asset_id}: {str(e)}")
        return asset_id, []
