from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from utils.logging import get_logger
import pandas as pd
import re

logger = get_logger(__name__)

# Función para formatear valores NFC de forma visible
def format_nfc_value(value):
    """
    Formatea un valor NFC para que sea visible y conserve su formato.
    
    Args:
        value: El valor NFC a formatear
        
    Returns:
        str: Valor formateado para visualización
    """
    if not value:
        return ""

    # Verificar si es un string
    if not isinstance(value, str):
        value = str(value)
    
    # Eliminar espacios en blanco
    value = value.strip()
    
    # Si después de strip es vacío
    if not value:
        return ""
    
    # Normalizar valores hexadecimales en diferentes formatos
    # 1. Si ya tiene formato con ":" (ej: "9F:F3:12:66"), mantenerlo
    # 2. Si es un hexadecimal sin separadores (ej: "9FF31266"), formatearlo con ":"
    # 3. Para otros formatos, añadir un prefijo que asegure visibilidad
    
    if ":" in value:
        # Ya tiene el formato con separadores, sólo asegurar que sea visible
        formatted_value = f"➤ {value.upper()}"
    elif len(value) == 8 and all(c in "0123456789ABCDEFabcdef" for c in value):
        # Convertir formato hexadecimal sin separadores a formato con separadores
        formatted_value = f"➤ {value[0:2]}:{value[2:4]}:{value[4:6]}:{value[6:8]}".upper()
    else:
        # Otros formatos: asegurar que sean visibles con un prefijo
        formatted_value = f"➤ {value}"
    
    # Asegurarse de que nunca devolvemos una cadena vacía cuando hay entrada
    if not formatted_value or formatted_value.strip() == "":
        return f"➤ {value}"  # Fallback: devolver el valor original con el prefijo
        
    return formatted_value

# Función para determinar si un sensor es de tipo NFC
def is_nfc_sensor(sensor):
    # Validar que el sensor no sea None
    if sensor is None:
        return False
        
    # NUEVO DEBUG: Analizar sensor en detalle
    sensor_id = sensor.get('sensor_id', 'DESCONOCIDO')
    logger.info(f"[ANÁLISIS] Analizando si el sensor {sensor_id} es NFC")
    
    # CASO ESPECIAL: Forzar reconocimiento para sensores específicos
    if sensor_id in ["2", "8", "9", "10"]:
        logger.info(f"[FORZADO] Sensor {sensor_id} es considerado NFC por ser un ID conocido")
        return True
        
    # Verificar si tiene nuestra marca especial (añadida en el preprocesamiento)
    if sensor.get("is_potential_nfc"):
        logger.info(f"[VÁLIDO] Sensor {sensor_id} tiene marca is_potential_nfc")
        return True
        
    # Verificar diferentes posibles indicadores de que un sensor es de tipo NFC
    # Comprobación principal: directamente buscar sensor_type=NFC_CODE
    if sensor.get("sensor_type") == "NFC_CODE":
        # NUEVO DEBUG: Sensor de tipo NFC_CODE encontrado
        logger.info(f"SENSOR NFC_CODE ENCONTRADO: sensor_id={sensor.get('sensor_id')}")
        return True
    
    # Si tiene el campo sensor_passwords, es muy probable que sea un NFC
    if "sensor_passwords" in sensor and isinstance(sensor["sensor_passwords"], list):
        logger.info(f"[ANÁLISIS] Sensor {sensor_id} tiene {len(sensor['sensor_passwords'])} sensor_passwords")
        for sensor_pw in sensor["sensor_passwords"]:
            if not isinstance(sensor_pw, dict):
                continue
                
            pw_sensor_id = sensor_pw.get("sensor_id", "")
            pw_type = sensor_pw.get("sensor_type", "")
            pw_value = sensor_pw.get("password", "")
            
            logger.info(f"[PW] Anidado {pw_sensor_id}, tipo={pw_type}, password='{pw_value}'")
            
            if pw_sensor_id in ["2", "8", "9", "10"]:
                logger.info(f"[FORZADO-PW] Sensor anidado {pw_sensor_id} es considerado NFC por ID conocido")
                return True
                
            if pw_type == "NFC_CODE" or "NFC" in str(pw_type).upper():
                # NUEVO DEBUG: Sensor con sensor_passwords encontrado
                logger.info(f"SENSOR CON SENSOR_PASSWORDS ENCONTRADO: sensor_id={sensor.get('sensor_id')}")
                return True
                
            if pw_value:
                logger.info(f"[VÁLIDO-PW] Sensor anidado {pw_sensor_id} tiene password no vacío")
                return True
    
    # CASO ESPECIAL: Verificar si el sensor tiene un password no vacío
    password_value = sensor.get("password", "") or sensor.get("nfc_password", "") or sensor.get("nfc_code", "")
    if password_value:
        logger.info(f"[VÁLIDO] Sensor {sensor_id} tiene password='{password_value}'")
        return True
    
    # Comprobar si el tipo contiene "NFC" o "CODE" (insensible a mayúsculas/minúsculas)
    sensor_type = str(sensor.get("sensor_type", "")).upper()
    if "NFC" in sensor_type or "CODE" in sensor_type or "CÓDIGO" in sensor_type or "CODIGO" in sensor_type:
        logger.info(f"[VÁLIDO] Sensor {sensor_id} tipo={sensor_type} contiene palabras clave")
        return True
    
    # Comprobar si el uso o la categoría indica que es NFC
    # Usar str() para asegurar que no haya errores si los valores son None
    sensor_usage = str(sensor.get("usage", "")).upper()
    sensor_category = str(sensor.get("category", "")).upper()
    sensor_name = str(sensor.get("name", "")).upper()
    
    nfc_keywords = ["NFC", "CODE", "CÓDIGO", "CODIGO", "ACCESO", "ACCESS", "TARJETA", "CARD", "TAG", "BADGE"]
    
    for keyword in nfc_keywords:
        if (keyword in sensor_usage or 
            keyword in sensor_category or 
            keyword in sensor_name):
            logger.info(f"[VÁLIDO] Sensor {sensor_id} contiene palabra clave '{keyword}' en sus atributos")
            return True
    
    # Comprobar si hay propiedades específicas que indican capacidad NFC
    if sensor.get("has_nfc") or sensor.get("nfc_enabled") or sensor.get("nfc_password") or sensor.get("password"):
        logger.info(f"[VÁLIDO] Sensor {sensor_id} tiene propiedades NFC específicas")
        return True
        
    # Verificar si hay alguna propiedad que contenga "nfc" en su nombre
    for key, value in sensor.items():
        if isinstance(key, str) and ("nfc" in key.lower() or "code" in key.lower() or "password" in key.lower()):
            logger.info(f"[VÁLIDO] Sensor {sensor_id} tiene propiedad '{key}' relacionada con NFC")
            return True
    
    # Si llegamos aquí, no parece ser un sensor NFC        
    logger.info(f"[RECHAZADO] Sensor {sensor_id} NO es reconocido como NFC")
    return False

# Función para extraer información de sensores NFC
def extract_nfc_sensor_info(lock):
    nfc_sensors = {}
    nfc_sensor_ids = []
    has_nfc = False
    
    # Log device that we're extracting from
    logger.info(f"Extract NFC info from: device_id={lock.get('device_id')}, type={lock.get('device_type')}")
    if lock.get('real_device_id'):
        logger.info(f"Device has real_device_id: {lock.get('real_device_id')}")
    if lock.get('gateway_id'):
        logger.info(f"Device has gateway_id: {lock.get('gateway_id')}")
    
    # Check if this is a door lock device type that should have NFC capabilities
    device_type = lock.get('device_type', '').upper()
    is_door_lock = ('DOORLOCK' in device_type or 
                   'LOCK' in device_type or 
                   'ACCESS' in device_type or
                   'NFC' in device_type)
    
    logger.info(f"Device type '{device_type}' - Is door lock: {is_door_lock}")
    
    # Asegurarse de que sensors sea una lista y no None
    sensors_list = lock.get("sensors", []) or []
    
    # DEBUG: Detalles del lock para extracción de sensores
    logger.info(f"Extrayendo sensores para lock {lock.get('device_id')} - {lock.get('device_name')}")
    logger.info(f"Cantidad de sensores en este lock: {len(sensors_list)}")
    
    # Log sensor types
    if sensors_list:
        sensor_types = [s.get('sensor_type') for s in sensors_list if s is not None]
        logger.info(f"Sensor types in this lock: {sensor_types}")
    
    # MEJORA: Siempre agregar sensores importantes conocidos (2, 8, 9, 10)
    important_sensors = ["2", "8", "9", "10"]
    
    # Procesar cada sensor en el dispositivo
    for sensor in sensors_list:
        if sensor is None:
            continue
            
        try:
            sensor_id = str(sensor.get('sensor_id', ''))
            if not sensor_id:
                continue
            
            logger.info(f"Procesando sensor {sensor_id} en lock {lock.get('device_id')}")
            
            # Verificar si es un sensor NFC
            sensor_type = sensor.get("sensor_type", "")
            is_nfc = (sensor_type == "NFC_CODE" or 
                     "NFC" in str(sensor_type).upper() or
                     sensor_id in important_sensors)
            
            # Log why this sensor was considered NFC or not
            logger.info(f"Sensor {sensor_id} - type={sensor_type}, considered NFC: {is_nfc}, important: {sensor_id in important_sensors}")
            
            # Si es un sensor NFC o uno importante, incluirlo
            if is_nfc or sensor_id in important_sensors:
                # Obtener el valor del código NFC
                password = (sensor.get("password", "") or 
                           sensor.get("nfc_password", "") or 
                           sensor.get("nfc_code", ""))
                
                logger.info(f"Sensor NFC encontrado: {sensor_id} (tipo={sensor_type}, password={password})")
                
                # Crear entrada para este sensor
                nfc_sensors[sensor_id] = {
                    "sensor_id": sensor_id,
                    "sensor_type": sensor_type or "NFC_CODE",
                    "name": sensor.get("name", f"NFC {sensor_id}"),
                    "device_id": lock.get("device_id", ""),
                    "device_name": lock.get("device_name", "Sin nombre"),
                    "asset_id": lock.get("asset_id", ""),
                    "asset_name": lock.get("alias", lock.get("room", lock.get("asset_name", "Desconocido"))),
                    "password": password,
                    "nfc_password": password,
                    "nfc_code": password,
                    "is_nested_nfc": False
                }
                
                nfc_sensor_ids.append(sensor_id)
                has_nfc = True
                
        except Exception as e:
            logger.error(f"Error al procesar sensor: {str(e)}")
            continue
    
    # ENHANCEMENT: For door lock devices, always ensure important NFC sensors exist
    # even if no explicit NFC sensors are defined
    if is_door_lock:
        logger.info(f"Door lock device detected: {lock.get('device_id')} - Ensuring NFC sensor availability")
        has_nfc = True  # Door lock devices inherently have NFC capabilities
        
        # Asegurar que los sensores importantes siempre estén presentes
        # aunque no existan explícitamente en el dispositivo
        for sensor_id in important_sensors:
            if sensor_id not in nfc_sensors:
                logger.info(f"Añadiendo sensor importante {sensor_id} para dispositivo de cerradura {lock.get('device_id')}")
                nfc_sensors[sensor_id] = {
                    "sensor_id": sensor_id,
                    "sensor_type": "NFC_CODE",
                    "name": f"NFC {sensor_id}",
                    "device_id": lock.get("device_id", ""),
                    "device_name": lock.get("device_name", "Sin nombre"),
                    "asset_id": lock.get("asset_id", ""),
                    "asset_name": lock.get("alias", lock.get("room", lock.get("asset_name", "Desconocido"))),
                    "password": "",
                    "nfc_password": "",
                    "nfc_code": "",
                    "is_nested_nfc": False,
                    "is_important": True,
                    "is_virtual": True  # Mark as virtual since it's auto-created
                }
                nfc_sensor_ids.append(sensor_id)
    else:
        # For non-door lock devices, only add important sensors if they already had some NFC detection
        for sensor_id in important_sensors:
            if sensor_id not in nfc_sensors and has_nfc:
                logger.info(f"Añadiendo sensor importante {sensor_id} que no estaba presente en el dispositivo {lock.get('device_id')}")
                nfc_sensors[sensor_id] = {
                    "sensor_id": sensor_id,
                    "sensor_type": "NFC_CODE",
                    "name": f"NFC {sensor_id}",
                    "device_id": lock.get("device_id", ""),
                    "device_name": lock.get("device_name", "Sin nombre"),
                    "asset_id": lock.get("asset_id", ""),
                    "asset_name": lock.get("alias", lock.get("room", lock.get("asset_name", "Desconocido"))),
                    "password": "",
                    "nfc_password": "",
                    "nfc_code": "",
                    "is_nested_nfc": False,
                    "is_important": True
                }
                nfc_sensor_ids.append(sensor_id)
    
    # Devolver la información de sensores NFC encontrados
    result = {
        "has_nfc": has_nfc,
        "nfc_sensor_ids": nfc_sensor_ids,
        "nfc_sensors": nfc_sensors
    }
    
    logger.info(f"Resultado de extract_nfc_sensor_info para {lock.get('device_id')}: {has_nfc} con {len(nfc_sensor_ids)} sensores (is_door_lock: {is_door_lock})")
    
    return result

def create_nfc_display_grid(filtered_locks=None, is_loading_locks=False, asset_id_filter=None, show_all_sensors=False):
    """
    Crea una cuadrícula para mostrar los códigos NFC de las cerraduras filtradas
    
    Args:
        filtered_locks: Lista de cerraduras filtradas con sensores NFC
        is_loading_locks: Indica si aún se están cargando las cerraduras
        asset_id_filter: Filtro actual de asset_id para agrupar las cerraduras
        show_all_sensors: Si es True, muestra todos los sensores; si es False, solo muestra los que tienen valores asignados
        
    Returns:
        Componente de cuadrícula para mostrar códigos NFC
    """
    # DEBUG: Inicio de la función
    logger.info("============== INICIO DEBUG NFC_DISPLAY_GRID ==============")
    logger.info(f"show_all_sensors={show_all_sensors}, filtered_locks={len(filtered_locks) if filtered_locks else 0}")
    
    # NEW: Log gateway_id and real_device_id for each lock in filtered_locks
    if filtered_locks:
        logger.info("Debugging gateway_id and real_device_id in filtered_locks:")
        for i, lock in enumerate(filtered_locks[:5]): # Log first 5 locks for brevity
            current_device_id = lock.get('device_id', 'N/A_device')
            current_real_device_id = lock.get('real_device_id', current_device_id) # Use device_id if real_device_id is absent
            current_gateway_id = lock.get('gateway_id', 'N/A_gateway')
            logger.info(f"Lock {i}: device_id='{current_device_id}', real_device_id='{current_real_device_id}', gateway_id='{current_gateway_id}'")
    
    try:
        # Si no hay cerraduras o están cargando, mostrar un mensaje adecuado
        if is_loading_locks:
            return dbc.Spinner(
                html.Div("Cargando cerraduras...", className="text-center my-5"),
                type="grow",
                color="primary"
            )
        
        if not filtered_locks or len(filtered_locks) == 0:
            return html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "No se encontraron cerraduras con sensores NFC en la selección actual."
            ], className="alert alert-info")
        
        # DEBUG: Imprimir device_ids y tipos
        logger.info(f"Dispositivos encontrados: {[lock.get('device_id') for lock in filtered_locks]}")
        logger.info(f"Tipos de dispositivos: {[lock.get('device_type') for lock in filtered_locks]}")
        
        # Extraer todas las cerraduras que tienen un asset_id (no incluir cerraduras de proyecto)
        locks_with_asset = [lock for lock in filtered_locks if lock.get("asset_id")]
        
        if not locks_with_asset or len(locks_with_asset) == 0:
            return html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "No se encontraron cerraduras asociadas a espacios (assets) en la selección actual."
            ], className="alert alert-warning")
        
        # Recolectar todos los sensores NFC
        all_nfc_sensors = []
        sensor_id_to_info = {}  # Mapa sensor_id -> info para referencia rápida
        total_sensors = 0
        
        for lock in locks_with_asset:
            # Contar todos los sensores para estadísticas
            total_sensors += len(lock.get("sensors", []) or [])
            
            # Extraer sensores NFC
            nfc_info = extract_nfc_sensor_info(lock)
            
            if nfc_info and nfc_info.get("has_nfc"):
                # Agregar los sensores NFC a la lista general
                for sensor_id, sensor_data in nfc_info.get("nfc_sensors", {}).items():
                    all_nfc_sensors.append(sensor_data)
                    sensor_id_to_info[sensor_id] = sensor_data
        
        # DEBUG: Resumir sensores encontrados
        logger.info(f"RESUMEN DE SENSORES: Total general={total_sensors}, NFC encontrados={len(all_nfc_sensors)}")
        logger.info(f"IDs de sensores NFC: {[s.get('sensor_id') for s in all_nfc_sensors]}")
        
        # Obtener los IDs de sensores únicos y ordenarlos
        sensor_ids = sorted(list(set(sensor.get("sensor_id") for sensor in all_nfc_sensors)))
        
        # MECANISMO DE RESPALDO: Asegurar que los sensores importantes siempre estén presentes
        important_sensors = ["2", "8", "9", "10"]
        
        # Agregar sensores importantes si faltan
        for sensor_id in important_sensors:
            if sensor_id not in sensor_ids:
                sensor_ids.append(sensor_id)
                logger.info(f"Sensor importante {sensor_id} añadido a la lista de sensores")
        
        # Ordenar numéricamente en lugar de alfabéticamente
        try:
            # Separar los IDs numéricos de los no numéricos
            numeric_ids = []
            non_numeric_ids = []
            
            for sid in sensor_ids:
                try:
                    numeric_ids.append(int(sid))
                except (ValueError, TypeError):
                    non_numeric_ids.append(sid)
            
            # Ordenar ambas listas
            numeric_ids.sort()
            non_numeric_ids.sort()
            
            # Combinar de vuelta a una lista ordenada
            sensor_ids = [str(num_id) for num_id in numeric_ids] + non_numeric_ids
            
        except Exception as e:
            logger.error(f"Error al ordenar IDs de sensores numéricamente: {str(e)}")
            # En caso de error, usar ordenación estándar
            sensor_ids = sorted(sensor_ids)
        
        # DEBUG: Sensor IDs ordenados después de agregar importantes
        logger.info(f"Sensor IDs finales: {sensor_ids}")
        
        if not sensor_ids:
            return html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "No se encontraron sensores compatibles con NFC en las cerraduras seleccionadas."
            ], className="alert alert-warning")
        
        # Crear columnas para la tabla
        columns = [
            {"name": "Espacio", "id": "asset_name"},
            {"name": "Staircase", "id": "asset_staircase"},
            {"name": "Apartment", "id": "asset_apartment"},
            {"name": "Nombre Dispositivo", "id": "device_id"},
            {"name": "Cerradura", "id": "lock_name"},
        ]
        
        # Agregar columnas para cada tipo de sensor
        for sensor_id in sensor_ids:
            columns.append({
                "name": f"NFC {sensor_id}",
                "id": f"sensor_{sensor_id}",
                "editable": True
            })
        
        # Preparar datos para la tabla
        table_data = []
        
        # Crear una fila para cada dispositivo
        for lock in locks_with_asset:
            device_id = lock.get("device_id", "")
            real_device_id = lock.get("real_device_id", device_id)  # Use real_device_id if available
            if not device_id:
                continue
            
            # Extraer datos básicos del dispositivo y parameters
            parameters = lock.get("parameters", {})
            room = parameters.get("room", "")
            name = parameters.get("name", "")
            
            # Log detallado para display_label
            logger.info(
                f"DisplayLabel Gen: device_id='{lock.get('device_id')}', "
                f"real_device_id='{lock.get('real_device_id', lock.get('device_id'))}', "
                f"lock_device_name='{lock.get('device_name', 'N/A')}', "
                f"params_dict='{parameters}', "
                f"extracted_room='{room}', extracted_name='{name}'"
            )
            
            # Crear etiqueta concatenada, o usar el device_name como respaldo
            if room and name:
                display_label = f"{room} - {name}"
            elif room:
                display_label = room
            elif name:
                display_label = name
            else:
                display_label = lock.get("device_name", "Sin nombre")
                
            # Log the ID values we're using
            logger.info(f"Device row ID values - device_id: {device_id}, real_device_id: {real_device_id}")
            
            # Get the gateway_id, use a fallback if necessary
            gateway_id = lock.get("gateway_id", "no_gateway")
            asset_id_for_row = lock.get("asset_id", "no_asset") # Get asset_id for the row ID
            
            # Additional debug for gateway_id
            logger.info(f"Device {device_id} (Asset {asset_id_for_row}): Retrieved gateway_id='{gateway_id}' from lock data")
            if gateway_id == "no_gateway":
                logger.warning(f"Device {device_id} (Asset {asset_id_for_row}): No gateway_id found in original data, using fallback value")
                # Try to find gateway_id in any property with 'gateway' in the name
                for key, value in lock.items():
                    if "gateway" in key.lower() and value:
                        logger.info(f"Device {device_id} (Asset {asset_id_for_row}): Found potential gateway in field '{key}': '{value}'")
                        gateway_id = value
                        logger.info(f"Device {device_id} (Asset {asset_id_for_row}): Using alternate gateway_id source: '{gateway_id}'")
                        break
            
            if asset_id_for_row == "no_asset":
                logger.error(f"CRITICAL: Device {device_id} (real_id {real_device_id}) is missing asset_id for unique row ID construction!")
                # Potentially skip this row or assign a placeholder if this case is possible and needs handling

            # Construct a unique composite ID for the row using asset_id, gateway_id and real_device_id
            unique_row_id = f"{asset_id_for_row}-{gateway_id}-{real_device_id}"
            
            logger.info(f"Created unique composite row ID: {unique_row_id} for device {real_device_id} in asset {asset_id_for_row}")
            
            row = {
                "id": unique_row_id,  # Use the new composite ID
                "device_id": display_label, 
                "real_device_id": real_device_id, 
                "lock_name": lock.get("device_name", "Sin nombre"),
                "asset_name": asset_id_for_row, 
                "asset_staircase": lock.get("staircase", ""), 
                "asset_apartment": lock.get("apartment", ""), 
                "gateway_id": gateway_id, 
                "asset_id": asset_id_for_row 
            }
            
            # Inicializar columnas de sensores con celdas vacías en lugar de "N/A"
            for sensor_id in sensor_ids:
                row[f"sensor_{sensor_id}"] = ""
            
            # Agregar la fila a los datos de la tabla
            table_data.append(row)
        
        # Log the structure of table_data and the first row as an example
        logger.info(f"create_nfc_display_grid - table_data tiene {len(table_data)} filas")
        if table_data:
            sample_row = table_data[0]
            logger.info(f"Sample row structure: {list(sample_row.keys())}")
            logger.info(f"Sample row id: {sample_row.get('id')}")
            logger.info(f"Full row content: {sample_row}")
        
        logger.info(f"Preparados {len(table_data)} dispositivos para la matriz con {len(columns)} columnas")
        
        # Crear componente de tabla
        nfc_grid_table = dash_table.DataTable(
            id="nfc-grid-table",
            columns=columns,
            data=table_data,
            sort_action="native",
            sort_mode="multi",
            filter_action="native",
            page_action="native",
            page_size=50,
            row_selectable="multi",
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
                "fontFamily": "Arial, sans-serif",
                "padding": "8px"
            },
            style_header={
                "backgroundColor": "#f8f9fa",
                "fontWeight": "bold",
                "border": "1px solid #ddd"
            },
            style_data_conditional=[
                {
                    "if": {"column_id": "lock_name"},
                    "fontWeight": "bold"
                },
                {
                    "if": {"state": "selected"},
                    "backgroundColor": "#e2efff",
                    "border": "1px solid #3c78d8"
                }
            ],
            editable=True,
            cell_selectable=True,
            export_format="xlsx"
        )
        
        # Crear Store para almacenar datos de la matriz
        data_store = dcc.Store(
            id="nfc-grid-filter-store",
            data={"show_all": show_all_sensors}
        )
        
        # Crear un interruptor para filtrar sensores con/sin valores
        filter_toggle = dbc.Checklist(
            options=[
                {"label": "Mostrar todos los sensores", "value": True}
            ],
            value=[True] if show_all_sensors else [],
            id="nfc-grid-filter-toggle",
            switch=True,
            className="mt-2"
        )
        
        # Componente completo de la matriz NFC
        return html.Div([
            data_store,
            
            # Información y controles
            html.Div([
                filter_toggle,
                html.Div(className="mb-3")
            ], className="d-flex justify-content-between align-items-center"),
            
            # Contenedor de errores
            html.Div(id="nfc-grid-error-container"),
            
            # Indicador de carga
            dbc.Spinner(html.Div(id="nfc-grid-loading-indicator"), color="primary", type="grow", size="sm"),
            
            # Tabla de la matriz
            nfc_grid_table
            
        ], className="nfc-grid-container mt-3")
        
    except Exception as e:
        logger.error(f"Error en create_nfc_display_grid: {str(e)}")
        # Return detailed error for debugging
        return html.Div([
            html.H5("Error al generar matriz NFC", className="text-danger"),
            html.Pre(f"Excepción: {str(e)}")
        ], className="alert alert-danger") 