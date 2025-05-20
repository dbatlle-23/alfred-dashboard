from dash import html, dcc
import dash_bootstrap_components as dbc
from utils.logging import get_logger

logger = get_logger(__name__)

def create_lock_device_card(device):
    """
    Crea una tarjeta para mostrar un dispositivo de cerradura inteligente
    
    Args:
        device: Diccionario con la información del dispositivo
        
    Returns:
        Componente de tarjeta para el dispositivo
    """
    # Extracción de datos del dispositivo
    device_id = device.get("device_id", "Unknown")
    device_name = device.get("device_name", "Cerradura sin nombre")
    device_type = device.get("device_type", "UNKNOWN")
    connectivity = device.get("connectivity", "UNKNOWN")
    available_actions = device.get("available_actions", [])
    
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
        logger.warning(f"Dispositivo {device_id} no tiene sensor de cerradura ni de puerta comunitaria")
        return None
    
    # Información del sensor
    sensor_name = lock_sensor.get("name", "Cerradura")
    room = lock_sensor.get("room", "Desconocida")
    sensor_id = lock_sensor.get("sensor_id", "0")
    sensor_uuid = lock_sensor.get("sensor_uuid", "")
    
    # Determinar tipo de cerradura
    is_community_door = lock_sensor.get("usage") == "CommunityDoor"
    lock_type = "Puerta Comunitaria" if is_community_door else "Cerradura"
    
    # Determinar el scope (ámbito) del dispositivo
    scope = device.get("scope", {"type": "Project"})
    scope_type = scope.get("type", "Project")
    
    if scope_type == "Project":
        scope_text = "Proyecto"
        scope_badge_color = "primary"  # Azul para proyecto
    elif scope_type == "Asset":
        asset_name = scope.get("name", "Desconocido")
        scope_text = f"Espacio: {asset_name}"
        scope_badge_color = "success"  # Verde para asset/espacio
    else:
        scope_text = "Desconocido"
        scope_badge_color = "secondary"  # Gris para desconocido
    
    # Determinar el color de estado según la conectividad
    if connectivity == "ONLINE":
        status_color = "success"
        status_text = "En línea"
    elif connectivity == "OFFLINE":
        status_color = "danger"
        status_text = "Fuera de línea"
    else:
        status_color = "warning"
        status_text = "Desconocido"
    
    # Botones de acción según permisos disponibles
    action_buttons = []
    
    # Botón de verificación remota
    if "remote_check" in available_actions:
        action_buttons.append(
            dbc.Button(
                html.I(className="fas fa-sync-alt"),
                id={"type": "lock-check-button", "index": device_id},
                color="secondary",
                className="me-2",
                size="sm",
                title="Verificar estado"
            )
        )
    
    # Botones de bloqueo/desbloqueo
    if "lock" in available_actions:
        action_buttons.append(
            dbc.Button(
                html.I(className="fas fa-lock"),
                id={"type": "lock-button", "index": device_id},
                color="danger",
                className="me-2",
                size="sm",
                title="Bloquear"
            )
        )
    
    if "unlock" in available_actions:
        action_buttons.append(
            dbc.Button(
                html.I(className="fas fa-unlock"),
                id={"type": "unlock-button", "index": device_id},
                color="success",
                className="me-2",
                size="sm",
                title="Desbloquear"
            )
        )
    
    # Botón de acceso a historial si está disponible
    if "access_logs" in available_actions:
        action_buttons.append(
            dbc.Button(
                html.I(className="fas fa-history"),
                id={"type": "lock-history-button", "index": device_id},
                color="info",
                className="me-2",
                size="sm",
                title="Ver historial de accesos"
            )
        )
    
    # Crear la tarjeta del dispositivo
    card = dbc.Card([
        dbc.CardBody([
            # Cabecera con título y estado
            dbc.Row([
                dbc.Col([
                    html.H5(sensor_name, className="card-title mb-0"),
                    html.Div([
                        html.I(className="fas fa-map-marker-alt me-2", style={"color": "#3498db"}),
                        html.Span(room or "Ubicación desconocida", style={"fontStyle": "italic"})
                    ], className="mb-2 mt-1 py-1 px-2", style={
                        "backgroundColor": "#e8f4fc",
                        "borderRadius": "4px",
                        "display": "inline-block"
                    })
                ], width=8),
                dbc.Col([
                    html.Div([
                        html.Span(status_text, className=f"badge bg-{status_color} me-1"),
                    ], className="text-end")
                ], width=4)
            ], className="mb-2"),
            
            # Badge de scope/ámbito
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Span(scope_text, className=f"badge bg-{scope_badge_color}")
                    ], className="mb-2")
                ])
            ], className="mb-2"),
            
            # Información adicional
            dbc.Row([
                dbc.Col([
                    html.P([
                        html.Strong("Tipo: "),
                        lock_type
                    ], className="small mb-1"),
                    html.P([
                        html.Strong("Dispositivo: "),
                        device_type
                    ], className="small mb-1"),
                    html.P([
                        html.Strong("ID: "),
                        device_id
                    ], className="small mb-1")
                ])
            ], className="mb-3"),
            
            # Estado de la cerradura (se actualizará mediante callback)
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-question-circle me-2"),
                        "Estado desconocido"
                    ], id={"type": "lock-status", "index": device_id}, className="mb-2 lock-status")
                ])
            ], className="mb-3"),
            
            # Botones de acción
            dbc.Row([
                dbc.Col([
                    html.Div(action_buttons, className="d-flex")
                ])
            ])
        ])
    ], className="mb-3 shadow-sm h-100", id={"type": "lock-card", "index": device_id}, style={"cursor": "pointer"})
    
    # Guardar los datos del dispositivo para usar en callbacks
    store = dcc.Store(
        id={"type": "lock-device-data", "index": device_id},
        data={
            "device_id": device_id,
            "sensor_id": sensor_id,
            "sensor_uuid": sensor_uuid,
            "device_name": device_name,
            "room": room,
            "sensor_name": sensor_name,
            "is_community_door": is_community_door,
            "asset_id": device.get("asset_id"),  # Añadir asset_id para referencia en callbacks
            "scope": scope  # Añadir información de scope para referencia en callbacks
        }
    )
    
    return html.Div([card, store], className="lock-device-container") 