"""
Este archivo contiene la implementación corregida del callback para el filtro de NFC.
Se debe copiar la función update_nfc_filter_toggle en layouts/smart_locks.py para
reemplazar la implementación existente.
"""

def update_nfc_filter_toggle(show_all, current_filter_data, grid_data, table_data):
    """
    Callback que actualiza las columnas visibles según el filtro seleccionado.
    Esta versión corregida reconoce correctamente los formatos MAC como valores válidos,
    así como los códigos hexadecimales, y fuerza la inclusión de sensores importantes.
    
    Args:
        show_all: Booleano que indica si mostrar todos los sensores
        current_filter_data: Datos actuales del filtro
        grid_data: Datos de la cuadrícula
        table_data: Datos de la tabla
    
    Returns:
        Tupla con datos del filtro actualizados y columnas a mostrar
    """
    import logging
    import re
    logger = logging.getLogger("layouts.smart_locks")
    
    if grid_data is None or not table_data:
        return {"show_all": show_all}, []
    
    # Agregar logs para diagnóstico
    logger.debug(f"Toggle valor: {show_all}")
    
    # Columnas base (siempre visibles)
    columns_base = [
        {"name": "ID", "id": "device_id"},
        {"name": "Cerradura", "id": "lock_name"},
        {"name": "Espacio", "id": "asset_name"},
    ]
    
    # Lista de sensores importantes que siempre deben mostrarse
    important_sensors = ["2", "8", "9", "10"]
    logger.debug(f"Sensores importantes que se incluirán forzosamente: {important_sensors}")
    
    # Detectar sensores con valores en los datos actuales
    sensors_with_values = set()
    
    # Agregar automáticamente los sensores importantes
    for sensor_id in important_sensors:
        sensors_with_values.add(sensor_id)
        logger.debug(f"Sensor importante {sensor_id} añadido forzosamente a sensores_with_values")
    
    # Obtener sensores a partir de los nombres de columna
    sensor_ids = grid_data.get("sensor_ids", [])
    
    for row in table_data:
        for sensor_id in sensor_ids:
            # Omitir evaluación para sensores importantes ya que ya fueron añadidos
            if sensor_id in important_sensors:
                continue
                
            cell_id = f"sensor_{sensor_id}"
            if cell_id in row:
                value = str(row.get(cell_id, "")).strip()
                
                # Log para depuración
                logger.debug(f"Evaluando valor para sensor {sensor_id}: '{value}'")
                
                # Comprobar si es un valor válido
                is_valid = False
                
                # Caso 1: No está vacío y no es un valor de "no asignado"
                if value and value not in ["N/A", "No asignado", "No Asignado"]:
                    is_valid = True
                    logger.debug(f"Sensor {sensor_id} válido por caso 1")
                
                # Caso 2: Es una dirección MAC (formato XX:XX:XX:XX) o similar con separadores
                if ":" in value or "-" in value or "." in value:
                    is_valid = True
                    logger.debug(f"Detectado formato especial (MAC o similar): {value}")
                
                # Caso 3: Es un código hexadecimal (formato 82A08A5D)
                if re.match(r'^[0-9A-F]{8}$', value, re.IGNORECASE):
                    is_valid = True
                    logger.debug(f"Detectado formato hexadecimal: {value}")
                
                if is_valid:
                    sensors_with_values.add(sensor_id)
                    logger.debug(f"Sensor con valor válido detectado: {sensor_id} = {value}")
    
    logger.debug(f"Sensores con valores detectados: {len(sensors_with_values)} de {len(sensor_ids)}")
    
    # Crear columnas para todos los sensores
    all_columns = []
    filtered_columns = []
    
    # Si no hay sensores con valores, mostrar todos de todos modos para evitar una tabla vacía
    if not sensors_with_values and not show_all:
        logger.warning("No se detectaron sensores con valores. Se mostrarán todos para evitar una tabla vacía.")
        show_all = True
    
    for sensor_id in sensor_ids:
        column = {"name": f"Sensor {sensor_id}", "id": f"sensor_{sensor_id}"}
        all_columns.append(column)
        
        if sensor_id in sensors_with_values:
            filtered_columns.append(column)
    
    # Asegurar que las columnas para sensores importantes estén incluidas
    for sensor_id in important_sensors:
        if sensor_id in sensor_ids:  # Solo si el sensor existe en el dataset
            column_id = f"sensor_{sensor_id}"
            column = next((col for col in all_columns if col["id"] == column_id), None)
            if column and column not in filtered_columns:
                filtered_columns.append(column)
                logger.debug(f"Sensor importante {sensor_id} añadido forzosamente a las columnas filtradas")
    
    # Elegir qué columnas mostrar
    display_columns = columns_base + (all_columns if show_all else filtered_columns)
    
    # Log para diagnóstico
    if show_all:
        logger.debug(f"Mostrando TODAS las columnas: {len(display_columns)}")
    else:
        logger.debug(f"Mostrando columnas filtradas: {len(display_columns)} (base: {len(columns_base)}, sensores: {len(filtered_columns)})")
    
    # Actualizar el store
    updated_filter_data = {"show_all": show_all}
    
    return updated_filter_data, display_columns 