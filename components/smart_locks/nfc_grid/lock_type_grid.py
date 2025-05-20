from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from utils.logging import get_logger
import pandas as pd

logger = get_logger(__name__)

def create_lock_type_grid(filtered_locks=None, selected_type=None, is_loading_locks=False):
    """
    Crea una cuadrícula para mostrar las cerraduras de un tipo específico con sus sensores
    
    Args:
        filtered_locks: Lista de cerraduras filtradas
        selected_type: Tipo de cerradura seleccionado
        is_loading_locks: Indica si aún se están cargando las cerraduras
        
    Returns:
        Componente de cuadrícula para mostrar cerraduras y sus sensores
    """
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
            "No se encontraron cerraduras en la selección actual."
        ], className="alert alert-info")
    
    # Si no hay tipo seleccionado, mostrar un mensaje adecuado
    if not selected_type:
        return html.Div([
            html.I(className="fas fa-info-circle me-2"),
            "Seleccione un tipo de cerradura para visualizar la matriz."
        ], className="alert alert-info")
    
    # Filtrar cerraduras por el tipo seleccionado
    locks_of_type = [lock for lock in filtered_locks if lock.get("device_type") == selected_type]
    
    if not locks_of_type or len(locks_of_type) == 0:
        return html.Div([
            html.I(className="fas fa-exclamation-circle me-2"),
            f"No se encontraron cerraduras del tipo '{selected_type}' en la selección actual."
        ], className="alert alert-warning")
    
    # Extraer todos los sensores únicos de las cerraduras del tipo seleccionado
    all_sensors = {}  # Mapa de sensor_id a objeto sensor para tener más información
    
    # Función para verificar si un sensor es válido y no es None
    def is_valid_sensor(sensor):
        return sensor is not None and isinstance(sensor, dict) and sensor.get("sensor_id")
    
    # Extraer información de sensores
    for lock in locks_of_type:
        # Asegurarse de que sensors sea una lista y no None
        sensors_list = lock.get("sensors", []) or []
        
        for sensor in sensors_list:
            if is_valid_sensor(sensor):
                sensor_id = sensor.get("sensor_id", "")
                if sensor_id and sensor_id not in all_sensors:
                    # Guardar el sensor con su id como clave
                    all_sensors[sensor_id] = {
                        "id": sensor_id,
                        "type": sensor.get("sensor_type", "Desconocido"),
                        "name": sensor.get("name", f"Sensor {sensor_id}"),
                        "category": sensor.get("category", "")
                    }
    
    # Ordenar los sensores por ID
    sensor_ids = sorted(all_sensors.keys())
    
    if not sensor_ids:
        return html.Div([
            html.I(className="fas fa-exclamation-circle me-2"),
            f"No se encontraron sensores en las cerraduras del tipo '{selected_type}'."
        ], className="alert alert-warning")
    
    # Crear columnas para la tabla
    columns = [
        {"name": "Dispositivo", "id": "device_info"},
        {"name": "ID", "id": "device_id"},
    ]
    
    # Añadir columnas dinámicas para cada sensor_id
    for sensor_id in sensor_ids:
        sensor_info = all_sensors[sensor_id]
        # Mostrar el nombre del sensor y tipo entre paréntesis
        column_name = f"{sensor_info['name']} ({sensor_info['type']})"
        columns.append({"name": column_name, "id": f"sensor_{sensor_id}"})
    
    # Preparar datos para la tabla
    data = []
    for lock in locks_of_type:
        # Concatenar nombre y ubicación
        device_name = lock.get("device_name", "Sin nombre")
        room = ""
        
        # Buscar información de ubicación del sensor principal (generalmente LOCK)
        for sensor in lock.get("sensors", []) or []:
            if sensor and sensor.get("sensor_type") in ["LOCK", "CommunityDoor"] and sensor.get("room"):
                room = sensor.get("room", "")
                break
        
        # Si no se encontró ubicación en sensor LOCK, buscar en cualquier sensor
        if not room:
            for sensor in lock.get("sensors", []) or []:
                if sensor and sensor.get("room"):
                    room = sensor.get("room", "")
                    break
        
        # Crear el texto combinado de nombre y ubicación
        device_info = device_name
        if room:
            device_info += f" ({room})"
        
        row = {
            "device_id": lock.get("device_id", ""),
            "device_info": device_info,
            "asset_id": lock.get("asset_id", ""),
        }
        
        # Mapear los sensores que tiene este dispositivo por sensor_id
        lock_sensors = {}
        sensors_list = lock.get("sensors", []) or []
        
        for sensor in sensors_list:
            if is_valid_sensor(sensor):
                sensor_id = sensor.get("sensor_id", "")
                if sensor_id:
                    lock_sensors[sensor_id] = sensor
        
        # Crear celdas para cada sensor_id
        for sensor_id in sensor_ids:
            cell_id = f"sensor_{sensor_id}"
            
            # Verificar si este lock tiene este sensor
            if sensor_id in lock_sensors:
                # Mostrar el estado del sensor o un valor por defecto
                sensor_value = lock_sensors[sensor_id].get("value", "")
                row[cell_id] = sensor_value if sensor_value else "Sin valor"
                # También guardamos los IDs para facilitar la búsqueda posterior
                row[f"{cell_id}_exists"] = True
                row[f"{cell_id}_sensor_id"] = sensor_id
            else:
                # Si no existe este sensor en este lock, marcar como N/A
                row[cell_id] = "N/A"
                row[f"{cell_id}_exists"] = False
        
        data.append(row)
    
    # Crear la tabla con los datos preparados
    table = dash_table.DataTable(
        id="lock-type-grid-table",
        columns=columns,
        data=data,
        page_size=20,
        style_table={
            'overflowX': 'auto',
            'overflowY': 'auto',
            'maxHeight': '70vh',
        },
        style_header={
            'backgroundColor': 'rgb(240, 240, 240)',
            'fontWeight': 'bold',
            'textAlign': 'center',
            'position': 'sticky',
            'top': 0,
            'zIndex': 1
        },
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
            'minWidth': '150px',
            'maxWidth': '250px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
        },
        style_data_conditional=[
            {
                'if': {'column_id': col, 'filter_query': f'{{{col}}} eq "N/A"'},
                'backgroundColor': 'rgba(220, 220, 220, 0.5)',
                'color': 'gray',
                'fontStyle': 'italic'
            } for col in [f"sensor_{sid}" for sid in sensor_ids]
        ],
        style_cell_conditional=[
            {
                'if': {'column_id': 'device_id'},
                'display': 'none'
            }
        ],
        fixed_columns={'headers': True, 'data': 1},  # Mantener fija la primera columna
        fixed_rows={'headers': True},
        sort_action='native',
        filter_action='native',
        export_format="csv",
    )
    
    # Store para almacenar los datos de los sensores
    grid_store = dcc.Store(id="lock-type-grid-data-store", data={
        "lock_ids": [lock.get("device_id") for lock in locks_of_type],
        "asset_ids": list(set(lock.get("asset_id") for lock in locks_of_type if lock.get("asset_id"))),
        "sensor_ids": sensor_ids
    })
    
    # Spinner para indicar carga de datos
    loading_spinner = dbc.Spinner(
        html.Div(id="lock-type-grid-loading-indicator", className="text-center my-2"),
        type="border",
        color="primary",
        size="sm"
    )
    
    # Contenedor para mensajes de error
    error_container = html.Div(id="lock-type-grid-error-container")
    
    return html.Div([
        html.H5(f"Matriz de Cerraduras: {selected_type}", className="mb-3"),
        html.P([
            html.I(className="fas fa-info-circle me-2"),
            "Esta vista muestra los sensores de las cerraduras del tipo seleccionado. Las celdas marcadas como N/A indican que el sensor correspondiente no existe en esa cerradura."
        ], className="alert alert-info small mb-3"),
        grid_store,
        error_container,
        loading_spinner,
        html.Div([
            html.Div([
                html.Strong(f"Cerraduras encontradas: {len(locks_of_type)}"),
                html.Span(f" | Sensores detectados: {len(sensor_ids)}", className="ms-3"),
            ], className="mb-2"),
            table
        ], className="lock-type-grid-container")
    ]) 