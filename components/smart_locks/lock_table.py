from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from utils.logging import get_logger

logger = get_logger(__name__)

def create_locks_table(devices=None):
    """
    Crea una tabla para mostrar los dispositivos de cerradura inteligente
    
    Args:
        devices: Lista de dispositivos
        
    Returns:
        Componente con la tabla de dispositivos
    """
    if not devices:
        return html.Div([
            html.I(className="fas fa-info-circle me-2"),
            "Seleccione un proyecto para ver las cerraduras disponibles"
        ], className="alert alert-info")
    
    # Si no hay cerraduras en el proyecto
    if not devices:
        return html.Div([
            html.I(className="fas fa-exclamation-circle me-2"),
            "No se encontraron cerraduras inteligentes en este proyecto"
        ], className="alert alert-warning")
    
    # Preparar datos para la tabla
    table_data = []
    for device in devices:
        # Obtener información del sensor de cerradura (LOCK o CommunityDoor)
        lock_sensor = None
        
        # Primero buscamos un sensor de tipo LOCK
        for sensor in device.get("sensors", []):
            if sensor.get("sensor_type") == "LOCK":
                lock_sensor = sensor
                break
        
        # Si no encontramos un sensor LOCK, buscamos un sensor con usage=CommunityDoor
        if not lock_sensor:
            for sensor in device.get("sensors", []):
                if sensor.get("usage") == "CommunityDoor":
                    lock_sensor = sensor
                    break
        
        if not lock_sensor:
            continue
        
        # Determinar tipo de cerradura
        is_community_door = lock_sensor.get("usage") == "CommunityDoor"
        lock_type = "Puerta Comunitaria" if is_community_door else "Cerradura"
        
        # Determinar estado de conexión
        connectivity = device.get("connectivity", "UNKNOWN")
        if connectivity == "ONLINE":
            status_text = "En línea"
        elif connectivity == "OFFLINE":
            status_text = "Fuera de línea"
        else:
            status_text = "Desconocido"
        
        # Preparar acciones disponibles
        available_actions = device.get("available_actions", [])
        actions_text = ", ".join(action.capitalize() for action in available_actions)
        
        # Determinar el scope (ámbito) del dispositivo
        scope = device.get("scope", {"type": "Project"})
        scope_type = scope.get("type", "Project")
        
        if scope_type == "Project":
            scope_text = "Proyecto"
        elif scope_type == "Asset":
            asset_name = scope.get("name", "Desconocido")
            scope_text = f"Espacio: {asset_name}"
        else:
            scope_text = "Desconocido"
        
        # Crear fila para la tabla
        table_data.append({
            "id": device.get("device_id"),
            "nombre": lock_sensor.get("name", "Cerradura sin nombre"),
            "ubicacion": lock_sensor.get("room", "Desconocida"),
            "tipo": lock_type,
            "dispositivo": device.get("device_type", "Desconocido"),
            "estado": status_text,
            "scope": scope_text,  # Nueva columna para el ámbito
            "acciones": actions_text,
            "asset_id": device.get("asset_id")  # Añadimos asset_id para referencia en callbacks
        })
    
    # Ordenar por nombre
    table_data.sort(key=lambda x: x["nombre"])
    
    # Crear componente de tabla con DataTable
    lock_table = dash_table.DataTable(
        id="smart-locks-table",
        columns=[
            {"name": "Nombre", "id": "nombre"},
            {"name": "Ubicación", "id": "ubicacion"},
            {"name": "Tipo", "id": "tipo"},
            {"name": "Ámbito", "id": "scope"},  # Nueva columna para el ámbito
            {"name": "Dispositivo", "id": "dispositivo"},
            {"name": "Estado", "id": "estado"},
            {"name": "Acciones Disponibles", "id": "acciones"}
        ],
        data=table_data,
        sort_action="native",
        filter_action="native",
        page_size=10,
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "rgb(240, 240, 240)",
            "fontWeight": "bold"
        },
        style_cell={
            "textAlign": "left",
            "padding": "8px"
        },
        style_data_conditional=[
            # Estado styles
            {
                "if": {"column_id": "estado", "filter_query": "{estado} eq 'En línea'"},
                "color": "#198754"  # color verde para 'En línea'
            },
            {
                "if": {"column_id": "estado", "filter_query": "{estado} eq 'Fuera de línea'"},
                "color": "#dc3545"  # color rojo para 'Fuera de línea'
            },
            {
                "if": {"column_id": "estado", "filter_query": "{estado} eq 'Desconocido'"},
                "color": "#ffc107"  # color amarillo para 'Desconocido'
            },
            # Ubicación styles
            {
                "if": {"column_id": "ubicacion"},
                "fontStyle": "italic",
                "backgroundColor": "rgba(0, 123, 255, 0.05)"
            },
            # Scope styles
            {
                "if": {"column_id": "scope", "filter_query": "{scope} contains 'Proyecto'"},
                "backgroundColor": "rgba(0, 0, 255, 0.05)"
            },
            {
                "if": {"column_id": "scope", "filter_query": "{scope} contains 'Espacio'"},
                "backgroundColor": "rgba(0, 128, 0, 0.05)"
            },
            # Hidden columns
            {
                'if': {'column_id': 'id'},
                'display': 'none'
            },
            {
                'if': {'column_id': 'asset_id'},
                'display': 'none'
            }
        ],
        row_selectable=False,
        selected_rows=[],
        export_format="csv",
        style_data={
            'cursor': 'pointer'  # Cambiar el cursor a pointer para indicar que es clickeable
        }
    )
    
    # Añadir botones de acción para cada fila (en una implementación completa)
    # Esto requeriría usar los pattern-matching callbacks de Dash
    
    # Contenedor para la tabla
    return html.Div([
        # Contador de cerraduras
        html.Div([
            html.Strong(f"Cerraduras encontradas: {len(table_data)}"),
        ], className="mb-3"),
        
        # Tabla de cerraduras
        lock_table
    ]) 