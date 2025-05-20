from dash import html, dcc, dash_table, callback_context
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
from components.smart_locks.lock_list import create_locks_list
from components.smart_locks.lock_table import create_locks_table
from components.smart_locks.nfc_grid import create_nfc_display_grid, create_lock_type_grid
from utils.logging import get_logger
from utils.error_handlers import handle_exceptions
from utils.api import get_devices, get_nfc_passwords, update_nfc_code_value, get_project_assets, get_asset_devices
from utils.nfc_helper import fetch_for_asset as fetch_nfc_passwords_for_asset
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import re
from datetime import datetime

logger = get_logger(__name__)

# Layout para la página de Smart Locks
layout = html.Div([
    # Stores para datos
    dcc.Store(id="smart-locks-data-store"),
    dcc.Store(id="smart-locks-refresh-trigger"),
    dcc.Store(id="smart-locks-view-preference", data={"view": "table"}),  # Default a vista de tabla
    dcc.Store(id="nfc-update-trigger", data={"updated": False}),  # Trigger para actualizar valores NFC
    dcc.Store(id="current-device-store", data=None),  # Almacena información del dispositivo actual
    # Placeholder para nfc-grid-table para evitar errores en callbacks
    dcc.Store(id="nfc-grid-table", data=[]),
    # Almacena dispositivos seleccionados
    dcc.Store(id="selected-devices-store", data={"selected": []}),
    # Placeholder para nfc-grid-data-store
    dcc.Store(id="nfc-grid-data-store", data={"asset_ids": [], "asset_names": {}, "timestamp": ""}),
    # Store para almacenar el dispositivo a actualizar individualmente
    dcc.Store(id="nfc-device-update-store", data={"device_id": None, "asset_id": None, "timestamp": None}),
    # Store para el filtro de la grid
    dcc.Store(id="nfc-grid-filter-store", data={"show_all": True}),
    # Placeholder para master-card-selected-devices
    dcc.Store(id="master-card-selected-devices", data={"devices": []}),
    
    # Contenedor principal
    dbc.Container([
        # Título y descripción
        html.H2("Gestión de Cerraduras Inteligentes", className="mb-3"),
        html.P("Administre y controle las cerraduras inteligentes de sus proyectos", className="lead mb-4"),
        
        # Filtros
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    # Filtro de cliente
                    dbc.Col([
                        html.Label("Cliente"),
                        dcc.Dropdown(
                            id="smart-locks-client-filter",
                            placeholder="Seleccione un cliente",
                            clearable=False
                        )
                    ], width=4),
                    
                    # Filtro de proyecto
                    dbc.Col([
                        html.Label("Proyecto"),
                        dcc.Dropdown(
                            id="smart-locks-project-filter",
                            placeholder="Seleccione un proyecto",
                            clearable=False,
                            disabled=True
                        )
                    ], width=4),
                    
                    # Botones de acción
                    dbc.Col([
                        html.Div([
                            dbc.Button(
                                "Mostrar Cerraduras",
                                id="smart-locks-show-button",
                                color="primary",
                                className="me-2 mt-4",
                                disabled=True
                            ),
                            dbc.Button(
                                html.I(className="fas fa-sync"), 
                                id="smart-locks-refresh-button",
                                color="light",
                                className="mt-4",
                                disabled=True,
                                title="Actualizar datos"
                            )
                        ], className="d-flex justify-content-end")
                    ], width=4)
                ]),
                
                # Filtro de tipo de cerradura (aparece después de cargar datos)
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Tipo de cerradura"),
                            dcc.Dropdown(
                                id="smart-locks-type-filter",
                                placeholder="Seleccione un tipo de cerradura",
                                clearable=False,
                                options=[]
                            )
                        ], width=8),
                        dbc.Col([
                            html.Div(id="smart-locks-type-filter-info", className="mt-4 pt-1")
                        ], width=4)
                    ])
                ], id="smart-locks-type-filter-container", style={"display": "none"}, className="mt-3")
            ])
        ], className="mb-4"),
        
        # Indicador de carga
        dbc.Spinner(html.Div(id="smart-locks-loading-indicator"), color="primary", type="grow"),
        
        # Pestañas para diferentes vistas
        dbc.Tabs([
            # Pestaña para vista de cerraduras
            dbc.Tab([
                # Toggle para cambiar entre vistas de tabla y grid
                html.Div([
                    html.Div([
                        dbc.ButtonGroup([
                            dbc.Button(
                                [html.I(className="fas fa-table me-1"), " Tabla"],
                                id="smart-locks-table-view-button",
                                color="primary",
                                outline=True,
                                className="view-toggle-button"
                            ),
                            dbc.Button(
                                [html.I(className="fas fa-th-large me-1"), " Grid"],
                                id="smart-locks-grid-view-button",
                                color="primary",
                                outline=True,
                                className="view-toggle-button"
                            )
                        ], className="view-toggle-container")
                    ], className="d-flex justify-content-end mb-3", style={"visibility": "hidden"}, id="smart-locks-view-toggle-container")
                ]),
                
                # Contenedor para la lista de cerraduras
                html.Div(id="smart-locks-list-container", className="mt-2"),
            ], label="Cerraduras", tab_id="locks-tab"),
            
            # Pestaña para vista de matriz NFC
            dbc.Tab([
                # Contenedor para la matriz NFC
                html.Div(id="nfc-grid-container", className="mt-4")
            ], label="Matriz de Códigos NFC", tab_id="nfc-grid-tab"),
        ], id="smart-locks-tabs", active_tab="locks-tab"),
        
        # Modal para detalles y acciones adicionales
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Detalles de Cerradura"), close_button=True),
            dbc.ModalBody([
                # Contenedor de información de la cerradura
                html.Div(id="smart-locks-modal-content", className="lock-details-container"),
                
                # Spinner para estados de carga
                dbc.Spinner(id="smart-locks-modal-loading", color="primary", type="grow", size="sm"),
                
                # Alerta para mensajes de feedback
                html.Div(id="smart-locks-modal-feedback")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cerrar", id="smart-locks-modal-close", className="ms-auto", n_clicks=0)
            ])
        ], id="smart-locks-modal", size="lg", is_open=False, centered=True, backdrop="static"),
        
        # Modal para confirmación de acciones
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Confirmar Acción")),
            dbc.ModalBody(id="smart-locks-confirm-modal-body"),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="smart-locks-confirm-cancel", className="me-2", n_clicks=0),
                dbc.Button("Confirmar", id="smart-locks-confirm-action", color="danger", n_clicks=0)
            ])
        ], id="smart-locks-confirm-modal", size="md", is_open=False),
        
        # Modal para edición de códigos NFC
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Editar Código NFC"), close_button=True),
            dbc.ModalBody([
                # Información del sensor NFC
                html.Div(id="nfc-edit-info", className="mb-3"),
                
                # Campo de edición (actualizado para eliminar FormGroup)
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nuevo valor:", className="fw-bold"),
                        dbc.Input(
                            id="nfc-edit-value-input",
                            type="text",
                            placeholder="Introduce el nuevo código NFC",
                            maxLength=50
                        ),
                        dbc.FormText("El código debe seguir el formato requerido por el dispositivo.", color="muted")
                    ])
                ]),
                
                # Mensajes de error o éxito
                html.Div(id="nfc-edit-feedback", className="mt-3")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="nfc-edit-cancel", className="me-2", n_clicks=0),
                dbc.Button("Guardar", id="nfc-edit-save", color="primary", n_clicks=0)
            ])
        ], id="nfc-edit-modal", size="md", is_open=False),
        
        # Interval para cerrar el modal de edición después de guardar
        dcc.Interval(id="nfc-edit-success-timer", interval=2000, n_intervals=0, max_intervals=1, disabled=True),
        
        # Añadir un nuevo modal para la asignación masiva de tarjetas NFC maestras después del modal nfc-edit-modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Asignar Tarjeta Maestra"), close_button=True),
            dbc.ModalBody([
                # Descripción
                html.P([
                    "Asigne una tarjeta NFC maestra a múltiples cerraduras al mismo tiempo. ",
                    "La tarjeta maestra tendrá acceso a todas las cerraduras seleccionadas."
                ], className="lead"),
                
                # Información de cerraduras seleccionadas
                html.Div([
                    html.H5("Cerraduras Seleccionadas", className="mb-3"),
                    html.Div(id="master-card-selected-locks", className="mb-3")
                ], id="master-card-selection-container"),
                
                # Campo para ingresar el UUID de la tarjeta
                dbc.Row([
                    dbc.Col([
                        dbc.Label("UUID de la Tarjeta Maestra", className="fw-bold"),
                        dbc.InputGroup([
                            dbc.Input(
                                id="master-card-uuid-input",
                                type="text",
                                placeholder="Formato: AA:BB:CC:DD",
                                maxLength=50
                            ),
                            dbc.Button(
                                html.I(className="fas fa-paste"), 
                                id="master-card-paste-button", 
                                color="secondary",
                                title="Pegar desde portapapeles"
                            )
                        ]),
                        dbc.FormText([
                            "Ingrese el UUID de la tarjeta NFC en formato hexadecimal (ej: AA:BB:CC:DD).",
                            html.Br(),
                            "Este código se asignará al slot 7 (tarjeta maestra) de todas las cerraduras seleccionadas."
                        ], color="muted")
                    ])
                ], className="mb-3"),
                
                # Contenedor para mostrar feedback y resultados
                html.Div(id="master-card-feedback", className="mt-3"),
                
                # Sección de resultados (aparece después de enviar)
                html.Div(id="master-card-results-container", className="mt-4", style={"display": "none"}),
                
                # Spinner para estados de carga
                dbc.Spinner(id="master-card-loading", color="primary", type="grow", size="sm")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="master-card-cancel", className="me-2", n_clicks=0),
                dbc.Button("Asignar Tarjeta", id="master-card-confirm", color="primary", n_clicks=0)
            ])
        ], id="master-card-modal", size="lg", is_open=False, backdrop="static"),
        
        # Modal para desasignación masiva de tarjetas NFC maestras
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Desasignar Tarjeta Maestra"), close_button=True),
            dbc.ModalBody([
                # Descripción
                html.P([
                    "Esta acción eliminará la tarjeta maestra (slot 7) de todas las cerraduras seleccionadas. ",
                    html.Span("Esta acción no se puede deshacer.", className="text-danger fw-bold")
                ], className="lead"),
                
                # Información de cerraduras seleccionadas
                html.Div([
                    html.H5("Cerraduras Seleccionadas", className="mb-3"),
                    html.Div(id="unassign-card-selected-locks", className="mb-3")
                ], id="unassign-card-selection-container"),
                
                # Advertencia de confirmación
                dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    "Confirme que desea desasignar la tarjeta maestra de todas las cerraduras seleccionadas. ",
                    "Esta acción eliminará los permisos de acceso de la tarjeta maestra en estas cerraduras."
                ], color="warning", className="mb-3"),
                
                # Contenedor para mostrar feedback y resultados
                html.Div(id="unassign-card-feedback", className="mt-3"),
                
                # Sección de resultados (aparece después de enviar)
                html.Div(id="unassign-card-results-container", className="mt-4", style={"display": "none"}),
                
                # Spinner para estados de carga
                dbc.Spinner(id="unassign-card-loading", color="primary", type="grow", size="sm")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="unassign-card-cancel", className="me-2", n_clicks=0),
                dbc.Button("Desasignar Tarjeta", id="unassign-card-confirm", color="danger", n_clicks=0)
            ])
        ], id="unassign-card-modal", size="lg", is_open=False, backdrop="static")
    ])
])

# Registrar callbacks para la página de Smart Locks
def register_callbacks(app):
    """
    Registra los callbacks para la página de Smart Locks
    
    Args:
        app: Instancia de la aplicación Dash
    """
    # Callback para cambiar la vista (tabla o grid)
    @app.callback(
        [Output("smart-locks-view-preference", "data"),
         Output("smart-locks-table-view-button", "outline"),
         Output("smart-locks-grid-view-button", "outline")],
        [Input("smart-locks-table-view-button", "n_clicks"),
         Input("smart-locks-grid-view-button", "n_clicks")],
        [State("smart-locks-view-preference", "data")]
    )
    def toggle_view(table_clicks, grid_clicks, current_view):
        ctx = dash.callback_context
        if not ctx.triggered:
            # Valores por defecto
            return current_view, not current_view.get("view") == "table", not current_view.get("view") == "grid"
        
        # Determinar qué botón se ha pulsado
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if button_id == "smart-locks-table-view-button":
            return {"view": "table"}, False, True
        elif button_id == "smart-locks-grid-view-button":
            return {"view": "grid"}, True, False
        
        # En caso de no reconocer el botón, mantener vista actual
        return current_view, not current_view.get("view") == "table", not current_view.get("view") == "grid"
    
    # Callback para mostrar/ocultar el toggle de vista según haya datos o no
    @app.callback(
        Output("smart-locks-view-toggle-container", "style"),
        [Input("smart-locks-data-store", "data")]
    )
    def toggle_view_container_visibility(data):
        if data:
            return {"visibility": "visible"}
        return {"visibility": "hidden"}
    
    # Callback para mostrar la lista de cerraduras según la vista seleccionada
    @app.callback(
        Output("smart-locks-list-container", "children"),
        [Input("smart-locks-data-store", "data"),
         Input("smart-locks-view-preference", "data")]
    )
    @handle_exceptions(default_return=html.Div("Error al cargar cerraduras", className="alert alert-danger"))
    def update_locks_list(devices_data, view_preference):
        if not devices_data:
            return html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "Seleccione un proyecto y haga clic en 'Mostrar Cerraduras' para ver las cerraduras disponibles"
            ], className="alert alert-info")
        
        view = view_preference.get("view", "table")
        if view == "grid":
            return create_locks_list(devices_data)
        else:
            return create_locks_table(devices_data)
    
    # Callback para cargar la lista de clientes
    @app.callback(
        Output("smart-locks-client-filter", "options"),
        [Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    @handle_exceptions(default_return=[{"label": "Error al cargar", "value": "all"}])
    def load_clients(token_data):
        from utils.api import get_clientes
        
        # Obtener el token JWT del store
        token = token_data.get('token') if token_data else None
        
        # Si no hay token, mostrar opciones por defecto
        if not token:
            logger.info("No hay token JWT disponible para cargar clientes")
            return [{"label": "Seleccione un cliente", "value": ""}]
        
        # Obtener la lista de clientes
        clientes = get_clientes(jwt_token=token)
        
        # Opciones para el dropdown de clientes
        client_options = []
        
        # Extender con los clientes de la API
        for cliente in clientes:
            if not isinstance(cliente, dict):
                continue
                
            # Intentar obtener el nombre y el ID con diferentes claves posibles
            nombre = None
            id_cliente = None
            
            # Posibles claves para el nombre
            for key in ['nombre', 'name', 'client_name', 'nombre_cliente', 'client']:
                if key in cliente:
                    nombre = cliente[key]
                    break
            
            # Posibles claves para el ID
            for key in ['id', 'client_id', 'id_cliente', 'clientId']:
                if key in cliente:
                    id_cliente = cliente[key]
                    break
            
            # Si tenemos tanto nombre como ID, añadir a las opciones
            if nombre and id_cliente is not None:
                client_options.append({"label": nombre, "value": str(id_cliente)})
        
        return client_options
    
    # Callback para cargar la lista de proyectos cuando cambia el cliente seleccionado
    @app.callback(
        [Output("smart-locks-project-filter", "options"),
         Output("smart-locks-project-filter", "disabled")],
        [Input("smart-locks-client-filter", "value"),
         Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    @handle_exceptions(default_return=[[{"label": "Error al cargar", "value": ""}], True])
    def load_projects(client_id, token_data):
        from utils.api import get_projects
        
        # Obtener el token JWT del store
        token = token_data.get('token') if token_data else None
        
        # Si no hay token o cliente seleccionado, mantener deshabilitado
        if not token or not client_id:
            return [{"label": "Seleccione primero un cliente", "value": ""}], True
        
        # Obtener la lista de proyectos para el cliente seleccionado
        projects = get_projects(client_id=client_id, jwt_token=token)
        
        # Opciones para el dropdown de proyectos
        project_options = []
        
        # Extender con los proyectos de la API
        for project in projects:
            if not isinstance(project, dict):
                continue
            
            # Intentar obtener el nombre y el ID con diferentes claves posibles
            nombre = None
            id_proyecto = None
            
            # Posibles claves para el nombre
            for key in ['nombre', 'name', 'project_name', 'nombre_proyecto']:
                if key in project:
                    nombre = project[key]
                    break
            
            # Posibles claves para el ID
            for key in ['id', 'project_id', 'id_proyecto', 'projectId']:
                if key in project:
                    id_proyecto = project[key]
                    break
            
            # Si tenemos tanto nombre como ID, añadir a las opciones
            if nombre and id_proyecto is not None:
                project_options.append({"label": nombre, "value": str(id_proyecto)})
        
        return project_options, False
    
    # Callback para habilitar/deshabilitar el botón de mostrar cerraduras
    @app.callback(
        Output("smart-locks-show-button", "disabled"),
        [Input("smart-locks-project-filter", "value")]
    )
    def toggle_show_button(project_id):
        return not project_id
    
    # Callback para habilitar/deshabilitar el botón de actualizar
    @app.callback(
        Output("smart-locks-refresh-button", "disabled"),
        [Input("smart-locks-data-store", "data")]
    )
    def toggle_refresh_button(data):
        return not data
    
    # Callback para obtener y almacenar datos de cerraduras
    @app.callback(
        [Output("smart-locks-data-store", "data"),
         Output("smart-locks-loading-indicator", "children")],
        [Input("smart-locks-show-button", "n_clicks"),
         Input("smart-locks-refresh-button", "n_clicks"),
         Input("smart-locks-refresh-trigger", "data")],
        [State("smart-locks-project-filter", "value"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[None, ""])
    def load_locks_data(show_clicks, refresh_clicks, refresh_trigger, project_id, token_data):
        if not project_id:
            return None, ""
        
        # Obtener el token JWT del store
        token = token_data.get('token') if token_data else None
        if not token:
            logger.error("No hay token JWT disponible para cargar cerraduras")
            return None, ""
        
        # PASO 1: Obtener los dispositivos a nivel de proyecto (Source A)
        project_devices = get_devices(
            project_id=project_id, 
            jwt_token=token, 
            device_types=["lock", "qr_lock"]  # Filtrar por tipos de cerradura en el servidor
        )
        
        # Filtrar dispositivos de proyecto por sensor para asegurar compatibilidad
        project_lock_devices = []
        for device in project_devices:
            has_lock_sensor = False
            has_community_door = False
            
            # Verificar ambos criterios de identificación
            for sensor in device.get("sensors", []):
                if sensor.get("sensor_type") == "LOCK":
                    has_lock_sensor = True
                if sensor.get("usage") == "CommunityDoor":
                    has_community_door = True
                    
            # Incluir el dispositivo si cumple al menos uno de los criterios
            if has_lock_sensor or has_community_door:
                # Añadir información de scope
                device["scope"] = {"type": "Project"}
                project_lock_devices.append(device)
        
        logger.info(f"Cargados {len(project_lock_devices)} dispositivos de cerradura a nivel de proyecto para {project_id}")
        
        # PASO 2a: Obtener la lista de assets/espacios del proyecto
        assets = get_project_assets(project_id, token)
        
        # PASO 2b: Obtener dispositivos para cada asset
        asset_lock_devices = []
        for asset in assets:
            asset_id = asset.get("id") or asset.get("asset_id")
            asset_name = asset.get("name") or asset.get("nombre")
            
            if not asset_id:
                logger.warning(f"No se pudo determinar el ID del asset: {asset}")
                continue
                
            # Obtener dispositivos del asset
            asset_devices = get_asset_devices(
                asset_id=asset_id,
                jwt_token=token,
                device_types="lock"  # Cambiado: solo usar "lock" para assets
            )
            
            # Añadir logging para diagnosticar el problema
            for i, device in enumerate(asset_devices):
                logger.debug(f"Dispositivo {i+1} de asset {asset_id}: {device}")
            
            # Procesar los dispositivos
            for device_container in asset_devices:
                # Verificar si el dispositivo tiene una estructura anidada con "devices"
                if isinstance(device_container, dict) and "devices" in device_container and isinstance(device_container["devices"], list):
                    # Procesar cada dispositivo dentro del array "devices"
                    logger.debug(f"Encontrado contenedor con {len(device_container['devices'])} dispositivos anidados")
                    
                    for nested_device in device_container["devices"]:
                        has_lock_sensor = False
                        device_id = nested_device.get("device_id", "desconocido")
                        
                        # Asegurarse de que el dispositivo tenga el asset_id
                        if "asset_id" not in nested_device and asset_id:
                            nested_device["asset_id"] = asset_id
                        
                        # Verificar sensores de cerradura en el dispositivo anidado
                        for sensor in nested_device.get("sensors", []):
                            logger.debug(f"Analizando sensor en dispositivo anidado {device_id}: tipo={sensor.get('sensor_type')}, usage={sensor.get('usage')}")
                            
                            if (sensor.get("sensor_type", "").upper() == "LOCK" or
                                sensor.get("type", "").upper() == "LOCK" or
                                sensor.get("usage") == "CommunityDoor" or
                                "lock" in str(sensor.get("sensor_type", "")).lower()):
                                has_lock_sensor = True
                                logger.debug(f"Dispositivo anidado {device_id} identificado como cerradura por su sensor")
                                break
                        
                        # Comprobar tipo de dispositivo
                        device_type = str(nested_device.get("device_type", "")).lower()
                        if not has_lock_sensor and ("lock" in device_type or "cerradura" in device_type):
                            has_lock_sensor = True
                            logger.debug(f"Dispositivo anidado {device_id} identificado como cerradura por su tipo: {device_type}")
                        
                        # Comprobar lock_type si existe
                        lock_type = nested_device.get("lock_type", "")
                        if not has_lock_sensor and lock_type:
                            has_lock_sensor = True
                            logger.debug(f"Dispositivo anidado {device_id} identificado como cerradura por su lock_type: {lock_type}")
                        
                        # Incluir dispositivo si se identificó como cerradura
                        if has_lock_sensor:
                            # Añadir información de scope
                            nested_device["scope"] = {
                                "type": "Asset",
                                "id": asset_id,
                                "name": asset_name
                            }
                            asset_lock_devices.append(nested_device)
                            logger.debug(f"Dispositivo anidado {device_id} añadido a la lista de cerraduras")
                else:
                    # Procesar dispositivo normal (no anidado)
                    has_lock_sensor = False
                    device_id = device_container.get("device_id", "desconocido")
                    
                    # Verificar sensores
                    for sensor in device_container.get("sensors", []):
                        logger.debug(f"Analizando sensor en dispositivo {device_id}: tipo={sensor.get('sensor_type')}, usage={sensor.get('usage')}")
                        
                        if (sensor.get("sensor_type", "").upper() == "LOCK" or
                            sensor.get("type", "").upper() == "LOCK" or
                            sensor.get("usage") == "CommunityDoor" or
                            "lock" in str(sensor.get("sensor_type", "")).lower()):
                            has_lock_sensor = True
                            logger.debug(f"Dispositivo {device_id} identificado como cerradura por su sensor")
                            break
                    
                    # Comprobar tipo de dispositivo
                    device_type = str(device_container.get("device_type", "")).lower()
                    if not has_lock_sensor and ("lock" in device_type or "cerradura" in device_type):
                        has_lock_sensor = True
                        logger.debug(f"Dispositivo {device_id} identificado como cerradura por su tipo: {device_type}")
                    
                    # Incluir dispositivo si se identificó como cerradura
                    if has_lock_sensor:
                        # Añadir información de scope
                        device_container["scope"] = {
                            "type": "Asset",
                            "id": asset_id,
                            "name": asset_name
                        }
                        asset_lock_devices.append(device_container)
                        logger.debug(f"Dispositivo {device_id} añadido a la lista de cerraduras")
                    else:
                        logger.debug(f"Dispositivo {device_id} NO reconocido como cerradura")
        
        logger.info(f"Cargados {len(asset_lock_devices)} dispositivos de cerradura a nivel de asset para {len(assets)} assets del proyecto {project_id}")
        
        # PASO 3: Consolidar los resultados
        consolidated_devices = []
        
        # Función para generar clave única para cada dispositivo
        def get_device_key(device):
            return device.get("device_id", "")
        
        # Primero añadir todos los dispositivos de nivel de asset
        device_keys = set()
        for device in asset_lock_devices:
            device_key = get_device_key(device)
            device_keys.add(device_key)
            consolidated_devices.append(device)
        
        # Luego añadir dispositivos de nivel de proyecto que no estén en los de asset
        for device in project_lock_devices:
            device_key = get_device_key(device)
            if device_key not in device_keys:
                consolidated_devices.append(device)
        
        logger.info(f"Total consolidado: {len(consolidated_devices)} dispositivos de cerradura para el proyecto {project_id}")
        
        return consolidated_devices, ""
    
    # Callback para actualizar el estado de una cerradura específica
    @app.callback(
        Output({"type": "lock-status", "index": ALL}, "children"),
        [Input("smart-locks-data-store", "data"),
         Input({"type": "lock-check-button", "index": ALL}, "n_clicks")],
        [State({"type": "lock-device-data", "index": ALL}, "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[])
    def update_lock_status(devices_data, check_clicks, device_data_list):
        # Si no hay datos de dispositivos, no hacer nada
        if not devices_data:
            return []
        
        # Obtener el contexto para saber qué cerradura se está actualizando
        ctx = dash.callback_context
        triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else None
        
        lock_statuses = []
        for device_data in device_data_list:
            device_id = device_data.get("device_id")
            
            # Buscar el dispositivo en los datos
            device = next((d for d in devices_data if d.get("device_id") == device_id), None)
            
            if not device:
                # Si no se encuentra el dispositivo, estado desconocido
                lock_statuses.append(html.Div([
                    html.I(className="fas fa-question-circle me-2"),
                    "Estado desconocido"
                ]))
                continue
            
            # En un caso real, aquí obtendríamos el estado actual de la cerradura desde la API
            # Por ahora, usamos un estado simulado
            lock_state = "LOCKED"  # Valores posibles: LOCKED, UNLOCKED, UNKNOWN
            
            if lock_state == "LOCKED":
                lock_statuses.append(html.Div([
                    html.I(className="fas fa-lock me-2 text-danger"),
                    "Bloqueada"
                ]))
            elif lock_state == "UNLOCKED":
                lock_statuses.append(html.Div([
                    html.I(className="fas fa-unlock me-2 text-success"),
                    "Desbloqueada"
                ]))
            else:
                lock_statuses.append(html.Div([
                    html.I(className="fas fa-question-circle me-2 text-warning"),
                    "Estado desconocido"
                ]))
        
        return lock_statuses
    
    # Callback para manejar acciones de bloqueo
    @app.callback(
        Output("smart-locks-confirm-modal", "is_open"),
        [Input({"type": "lock-button", "index": ALL}, "n_clicks"),
         Input({"type": "unlock-button", "index": ALL}, "n_clicks"),
         Input("smart-locks-confirm-cancel", "n_clicks"),
         Input("smart-locks-confirm-action", "n_clicks")],
        [State("smart-locks-confirm-modal", "is_open")],
        prevent_initial_call=True
    )
    def toggle_lock_confirm_modal(lock_clicks, unlock_clicks, cancel_clicks, confirm_clicks, is_open):
        ctx = dash.callback_context
        triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else None
        
        # Si el modal está abierto y se hace clic en Cancelar o Confirmar, cerrarlo
        if is_open and (cancel_clicks or confirm_clicks):
            return False
        
        # Si se hace clic en un botón de bloqueo/desbloqueo, abrir el modal
        if any(click for click in lock_clicks if click) or any(click for click in unlock_clicks if click):
            # En una implementación completa, aquí guardaríamos detalles sobre qué acción se está confirmando
            return True
        
        return is_open
    
    # Callback para abrir el modal de detalles al hacer clic en una tarjeta o fila
    @app.callback(
        [Output("smart-locks-modal", "is_open"),
         Output("smart-locks-modal-content", "children"),
         Output("smart-locks-modal-feedback", "children"),
         Output("current-device-store", "data")],
        [Input({"type": "lock-card", "index": ALL}, "n_clicks"),
         Input("smart-locks-table", "active_cell")],
        [State("smart-locks-table", "data"),
         State("smart-locks-data-store", "data"),
         State("smart-locks-modal", "is_open")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[False, "Error al cargar detalles", html.Div("Error al procesar datos", className="alert alert-danger"), None])
    def open_lock_details_modal(card_clicks, active_cell, table_data, devices_data, is_open):
        ctx = dash.callback_context
        triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else None
        
        # Si no hay trigger o no hay datos, no hacer nada
        if not triggered or triggered == '.' or not devices_data:
            return is_open, dash.no_update, dash.no_update, dash.no_update
        
        # Determinar qué dispositivo se ha seleccionado
        selected_device_id = None
        
        # Si el trigger fue un clic en una tarjeta
        if "lock-card" in triggered:
            import json
            # Extraer el índice del dispositivo de la tarjeta
            trigger_dict = json.loads(triggered.split('.')[0])
            selected_device_id = trigger_dict.get('index')
            
        # Si el trigger fue un clic en una fila de la tabla
        elif "smart-locks-table.active_cell" in triggered and active_cell:
            row_idx = active_cell['row']
            if table_data and row_idx < len(table_data):
                selected_device_id = table_data[row_idx]['id']
        
        # Si no se pudo determinar el dispositivo, no hacer nada
        if not selected_device_id:
            return is_open, dash.no_update, dash.no_update, dash.no_update
        
        # Buscar el dispositivo en los datos
        device = next((d for d in devices_data if d.get("device_id") == selected_device_id), None)
        
        if not device:
            return is_open, "No se encontró el dispositivo seleccionado", html.Div(
                "No se pudo encontrar información del dispositivo",
                className="alert alert-warning"
            ), None
            
        # Crear el contenido del modal con la información del dispositivo
        lock_sensor = None
        nfc_sensors = []
        
        # Añadir más logs para diagnosticar el problema
        logger.debug(f"Analizando dispositivo para modal: ID={selected_device_id}, tipo={device.get('device_type')}")
        logger.debug(f"Sensores disponibles en el dispositivo: {[s.get('sensor_type') for s in device.get('sensors', [])]}")
        
        # Buscar el sensor de cerradura y sensores NFC_CODE
        for sensor in device.get("sensors", []):
            if (sensor.get("sensor_type") == "LOCK" or sensor.get("usage") == "CommunityDoor") and not lock_sensor:
                lock_sensor = sensor
                logger.debug(f"Sensor de cerradura encontrado: {sensor.get('sensor_id')}")
            if sensor.get("sensor_type") == "NFC_CODE":
                nfc_sensors.append(sensor)
                logger.debug(f"Sensor NFC encontrado: {sensor.get('sensor_id')}")
        
        logger.info(f"Total de sensores NFC encontrados: {len(nfc_sensors)}")
        
        if not lock_sensor:
            return is_open, "Información de sensor no disponible", html.Div(
                "No se encontró información del sensor de cerradura",
                className="alert alert-warning"
            ), None
        
        # Extraer datos relevantes
        device_id = device.get("device_id", "Unknown")
        device_name = device.get("device_name", "Cerradura sin nombre")
        device_type = device.get("device_type", "UNKNOWN")
        connectivity = device.get("connectivity", "UNKNOWN")
        available_actions = device.get("available_actions", [])
        sensor_name = lock_sensor.get("name", "Cerradura")
        room = lock_sensor.get("room", "Desconocida")
        
        # Importante: Obtener el asset_id del dispositivo
        asset_id = device.get("asset_id")
        logger.debug(f"Asset ID del dispositivo: {asset_id}")
        
        # Determinar estado de conectividad
        if connectivity == "ONLINE":
            status_color = "success"
            status_text = "En línea"
        elif connectivity == "OFFLINE":
            status_color = "danger"
            status_text = "Fuera de línea"
        else:
            status_color = "warning"
            status_text = "Desconocido"
        
        # Determinar tipo de cerradura
        is_community_door = lock_sensor.get("usage") == "CommunityDoor"
        lock_type = "Puerta Comunitaria" if is_community_door else "Cerradura"
        
        # Crear los botones de acción según las acciones disponibles
        action_buttons = []
        
        # Botón de verificación remota
        if "remote_check" in available_actions:
            action_buttons.append(
                dbc.Button(
                    [html.I(className="fas fa-sync-alt me-2"), "Verificar Estado"],
                    id={"type": "modal-check-button", "index": device_id},
                    color="secondary",
                    className="me-2 mb-2",
                    size="md",
                )
            )
        
        # Botones de bloqueo/desbloqueo
        if "lock" in available_actions:
            action_buttons.append(
                dbc.Button(
                    [html.I(className="fas fa-lock me-2"), "Bloquear"],
                    id={"type": "modal-lock-button", "index": device_id},
                    color="danger",
                    className="me-2 mb-2",
                    size="md",
                )
            )
        
        if "unlock" in available_actions:
            action_buttons.append(
                dbc.Button(
                    [html.I(className="fas fa-unlock me-2"), "Desbloquear"],
                    id={"type": "modal-unlock-button", "index": device_id},
                    color="success",
                    className="me-2 mb-2",
                    size="md",
                )
            )
        
        # Botón de acceso a historial si está disponible
        if "access_logs" in available_actions:
            action_buttons.append(
                dbc.Button(
                    [html.I(className="fas fa-history me-2"), "Ver Historial"],
                    id={"type": "modal-history-button", "index": device_id},
                    color="info",
                    className="me-2 mb-2",
                    size="md",
                )
            )
        
        # Si hay actualización de software disponible
        if "software_update" in available_actions:
            action_buttons.append(
                dbc.Button(
                    [html.I(className="fas fa-download me-2"), "Actualizar Software"],
                    id={"type": "modal-update-button", "index": device_id},
                    color="primary",
                    className="me-2 mb-2",
                    size="md",
                )
            )
        
        # Preparar sección de códigos NFC si hay sensores de ese tipo
        nfc_section = []
        # Obtener el scope y asset_id del dispositivo
        scope = device.get("scope", {"type": "Project"})
        scope_type = scope.get("type", "Project")
        
        # Log de diagnóstico para el scope
        logger.debug(f"Scope del dispositivo: tipo={scope_type}, asset_id={asset_id}")
        
        # Ya no generamos la sección de NFC aquí, se generará dinámicamente desde el callback load_api_nfc_sensors
        # Solo actualizamos una variable para indicar si el dispositivo tiene asset_id y es de tipo Asset
        can_have_nfc = asset_id and scope_type == "Asset"
        if can_have_nfc:
            logger.debug(f"Dispositivo {device_id} cumple requisitos para mostrar NFC (asset_id={asset_id} y scope=Asset)")
        else:
            logger.warning(f"No se muestra sección NFC: asset_id={asset_id}, scope_type={scope_type}")
        
        # Determinar texto de scope para mostrar
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
        
        # Crear el contenido del modal
        modal_content = html.Div([
            # Cabecera con nombre y ubicación
            html.Div([
                html.H4(sensor_name, className="mb-2"),
                html.Div([
                    html.I(className="fas fa-map-marker-alt me-2", style={"color": "#3498db"}),
                    html.Span(room or "Ubicación desconocida", style={"fontStyle": "italic"})
                ], className="mb-3 py-1 px-2", style={
                    "backgroundColor": "#e8f4fc",
                    "borderRadius": "4px",
                    "display": "inline-block"
                })
            ], className="mb-2"),
            
            # Badge de scope/ámbito
            html.Div([
                html.Span(scope_text, className=f"badge bg-{scope_badge_color}")
            ], className="mb-4"),
            
            # Información del dispositivo
            dbc.Row([
                # Estado de conectividad
                dbc.Col([
                    html.Div([
                        html.H6("Estado de Conectividad", className="mb-2"),
                        html.Div([
                            html.I(className=f"fas fa-{'check-circle' if connectivity == 'ONLINE' else 'times-circle' if connectivity == 'OFFLINE' else 'question-circle'} me-2"),
                            html.Span(status_text, className=f"text-{status_color}")
                        ], className="d-flex align-items-center")
                    ], className="info-card p-3 mb-3", style={"border": "1px solid #dee2e6", "borderRadius": "8px"})
                ], md=6),
                
                # Estado de la cerradura
                dbc.Col([
                    html.Div([
                        html.H6("Estado de Cerradura", className="mb-2"),
                        html.Div([
                            html.I(className="fas fa-question-circle me-2"),
                            "Desconocido"
                        ], id={"type": "modal-lock-status", "index": device_id}, className="d-flex align-items-center")
                    ], className="info-card p-3 mb-3", style={"border": "1px solid #dee2e6", "borderRadius": "8px"})
                ], md=6)
            ]),
            
            # Detalles del dispositivo
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H6("Detalles del Dispositivo", className="mb-2"),
                        html.Table([
                            html.Tbody([
                                html.Tr([
                                    html.Td("Tipo:", className="fw-bold pe-3"),
                                    html.Td(lock_type)
                                ]),
                                html.Tr([
                                    html.Td("Dispositivo:", className="fw-bold pe-3"),
                                    html.Td(device_type)
                                ]),
                                html.Tr([
                                    html.Td("ID:", className="fw-bold pe-3"),
                                    html.Td(device_id)
                                ])
                            ])
                        ], className="table table-sm")
                    ], className="info-card p-3 mb-4", style={"border": "1px solid #dee2e6", "borderRadius": "8px"})
                ], md=12)
            ]),
            
            # Acciones disponibles
            html.Div([
                html.H5("Acciones", className="mb-3"),
                html.Div(action_buttons, className="d-flex flex-wrap")
            ]),
            
            # Sección de códigos NFC (si hay sensores)
            *nfc_section
        ])
        
        # Limpiar cualquier mensaje de feedback previo
        feedback = html.Div()
        
        # Guardar información relevante del dispositivo para uso en otros callbacks
        device_info = {
            "device_id": device_id,
            "asset_id": asset_id,
            "scope": scope
        }
        logger.info(f"Guardando información del dispositivo en current-device-store: {device_info}")
        
        # Abrir el modal o actualizarlo si ya está abierto
        return True, modal_content, feedback, device_info
    
    # Callback para actualizar el estado de la cerradura en el modal
    @app.callback(
        Output({"type": "modal-lock-status", "index": ALL}, "children"),
        [Input("smart-locks-modal", "is_open"),
         Input({"type": "modal-check-button", "index": ALL}, "n_clicks")],
        [State({"type": "modal-lock-status", "index": ALL}, "id"),
         State("smart-locks-data-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[])
    def update_modal_lock_status(is_open, check_clicks, status_ids, devices_data):
        ctx = dash.callback_context
        triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else None
        
        # Si no hay trigger o no está abierto el modal, no hacer nada
        if not triggered or not is_open:
            return dash.no_update
            
        # Preparar respuesta para cada status-id
        statuses = []
        for status_id in status_ids:
            device_id = status_id.get("index")
            
            # Encontrar el dispositivo en los datos
            device = next((d for d in devices_data if d.get("device_id") == device_id), None)
            
            if not device:
                statuses.append(html.Div([
                    html.I(className="fas fa-question-circle me-2 text-warning"),
                    "Estado desconocido"
                ], className="d-flex align-items-center"))
                continue
                
            # En un caso real, aquí se consultaría el estado actual
            # Por ahora, simulamos un estado de cerradura
            lock_state = "LOCKED"  # Valores posibles: LOCKED, UNLOCKED, UNKNOWN
            
            if lock_state == "LOCKED":
                statuses.append(html.Div([
                    html.I(className="fas fa-lock me-2 text-danger"),
                    "Bloqueada"
                ], className="d-flex align-items-center"))
            elif lock_state == "UNLOCKED":
                statuses.append(html.Div([
                    html.I(className="fas fa-unlock me-2 text-success"),
                    "Desbloqueada"
                ], className="d-flex align-items-center"))
            else:
                statuses.append(html.Div([
                    html.I(className="fas fa-question-circle me-2 text-warning"),
                    "Estado desconocido"
                ], className="d-flex align-items-center"))
        
        return statuses
    
    # Callback para actualizar el Store que activa la actualización de valores NFC
    @app.callback(
        Output("nfc-update-trigger", "data", allow_duplicate=True),
        [Input("nfc-edit-feedback", "children")],
        [State("nfc-update-trigger", "data")],
        prevent_initial_call=True,
        id='update_nfc_trigger_callback'  # Add a unique ID
    )
    def update_nfc_trigger(feedback, current_data):
        # Si hay feedback y es un mensaje de éxito, activar el trigger
        if feedback:
            # En una implementación real, deberíamos verificar si el mensaje es de éxito
            # Por ahora, incrementamos un contador cada vez que hay feedback
            current_count = current_data.get("count", 0) if current_data else 0
            return {"updated": True, "count": current_count + 1}
        return current_data

    # Modificar el callback que carga los valores NFC para usar el nuevo endpoint
    @app.callback(
        Output({"type": "nfc-value", "index": ALL}, "children"),
        [Input("smart-locks-modal", "is_open"),
         Input("nfc-update-trigger", "data")],
        [State({"type": "nfc-sensor-data", "index": ALL}, "data"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[])
    def load_nfc_values(is_open, update_trigger, nfc_sensors_data, token_data):
        ctx = dash.callback_context
        triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else None
        
        # Si no hay trigger o no hay sensores, no hacer nada
        if not triggered or not nfc_sensors_data:
            return dash.no_update
            
        # Si el modal no está abierto y el trigger no es la actualización, no hacer nada
        if not is_open and "nfc-update-trigger" not in triggered:
            return dash.no_update
        
        # Obtener el token JWT
        token = token_data.get('token') if token_data else None
        if not token:
            logger.error("No hay token JWT disponible para cargar valores NFC")
            return ["N/A" for _ in nfc_sensors_data]
        
        # Valores a mostrar para cada sensor
        nfc_values = []
        
        # Cache para las respuestas de la API por asset_id
        nfc_passwords_cache = {}
        
        # Agrupar sensores por asset_id para reducir las llamadas a la API
        sensors_by_asset = {}
        for sensor_data in nfc_sensors_data:
            if not isinstance(sensor_data, dict):
                continue
            
            asset_id = sensor_data.get("asset_id")
            if asset_id:
                if asset_id not in sensors_by_asset:
                    sensors_by_asset[asset_id] = []
                sensors_by_asset[asset_id].append(sensor_data)
                
        logger.debug(f"Agrupados {len(nfc_sensors_data)} sensores en {len(sensors_by_asset)} assets")
        
        # Obtener los valores para cada sensor NFC
        for sensor_data in nfc_sensors_data:
            if not isinstance(sensor_data, dict):
                nfc_values.append("N/A")
                continue
                
            device_id = sensor_data.get("device_id")
            sensor_id = sensor_data.get("sensor_id")
            asset_id = sensor_data.get("asset_id")
            scope = sensor_data.get("scope", {"type": "Project"})
            
            # CAMBIO: Verificar si el dispositivo está asociado a un asset
            # Solo cargar NFC para dispositivos asociados a un asset
            if not asset_id or scope.get("type") != "Asset":
                nfc_values.append("No disponible para este tipo de cerradura")
                continue
            
            if not device_id or not sensor_id:
                nfc_values.append("N/A")
                continue
            
            try:
                # Obtener o cargar del cache los datos de passwords NFC
                if asset_id not in nfc_passwords_cache:
                    logger.info(f"Obteniendo datos NFC para asset_id {asset_id}")
                    nfc_passwords_cache[asset_id] = get_nfc_passwords(asset_id, token)
                
                nfc_passwords_data = nfc_passwords_cache[asset_id]
                
                # Log de depuración para ver el formato de los datos
                logger.debug(f"Datos NFC para {asset_id}: Tipo={type(nfc_passwords_data)}")
                
                if not nfc_passwords_data:
                    logger.warning(f"No se encontraron datos NFC para asset_id {asset_id}")
                    nfc_values.append("No disponible")
                    continue
                
                # Verificar si los datos tienen el formato esperado
                if isinstance(nfc_passwords_data, dict) and 'data' in nfc_passwords_data:
                    data_section = nfc_passwords_data['data']
                    
                    # Inicializar el valor de la contraseña
                    password_value = "No disponible"
                    
                    # Obtener los dispositivos de diferentes formatos posibles
                    devices = []
                    
                    # CASO 1: data es un diccionario con la clave 'devices'
                    if isinstance(data_section, dict) and 'devices' in data_section:
                        if isinstance(data_section['devices'], list):
                            devices = data_section['devices']
                            logger.debug(f"Encontrados {len(devices)} dispositivos en formato estándar")
                    
                    # CASO 2: data es directamente una lista de dispositivos
                    elif isinstance(data_section, list):
                        devices = data_section
                        logger.debug(f"Encontrados {len(devices)} dispositivos en formato de lista")
                    
                    # CASO 3: data es un único dispositivo (diccionario con device_id)
                    elif isinstance(data_section, dict) and 'device_id' in data_section:
                        devices = [data_section]
                        logger.debug("Encontrado un único dispositivo")
                        
                    # Si no se pudo determinar el formato o no hay dispositivos
                    if not devices:
                        logger.error(f"No se pudieron extraer dispositivos del formato: {type(data_section)}")
                        nfc_values.append("N/A")
                        continue
                
                    # Log para depuración de dispositivos
                    device_ids = [dev.get('device_id') for dev in devices if isinstance(dev, dict)]
                    logger.debug(f"Dispositivos disponibles: {device_ids}")
                    
                    # Buscar el dispositivo correspondiente
                    device_found = False
                    for dev in devices:
                        if not isinstance(dev, dict):
                            logger.warning(f"Dispositivo no es un diccionario sino {type(dev)}")
                            continue
                        
                        dev_id = str(dev.get('device_id', ''))
                        requested_id = str(device_id)
                        logger.debug(f"Comparando device_id: API={dev_id}, Solicitado={requested_id}")
                        
                        if dev_id == requested_id:
                            device_found = True
                            # Validar sensor_passwords
                            sensor_passwords = dev.get('sensor_passwords', [])
                            if not isinstance(sensor_passwords, list):
                                logger.warning(f"'sensor_passwords' no es una lista sino {type(sensor_passwords)}")
                                continue
                                
                            logger.debug(f"Encontrado dispositivo {dev_id} con {len(sensor_passwords)} sensores")
                            
                            # Buscar el sensor correspondiente
                            sensor_found = False
                            for sensor_pw in sensor_passwords:
                                if not isinstance(sensor_pw, dict):
                                    logger.warning(f"Contraseña de sensor no es un diccionario sino {type(sensor_pw)}")
                                    continue
                                
                                # Comprobar ambos como strings para evitar problemas de tipo
                                pw_sensor_id = str(sensor_pw.get('sensor_id', ''))
                                requested_sensor_id = str(sensor_id)
                                logger.debug(f"Comparando sensor_id: API={pw_sensor_id}, Solicitado={requested_sensor_id}")
                                
                                if pw_sensor_id == requested_sensor_id:
                                    sensor_found = True
                                    password_value = sensor_pw.get('password', "")
                                    logger.info(f"Encontrado sensor {pw_sensor_id} con valor: {password_value}")
                                    break
                            
                            if not sensor_found:
                                logger.warning(f"No se encontró el sensor {sensor_id} en el dispositivo {device_id}")
                                password_value = "No encontrado"
                            break
                    
                    if not device_found:
                        logger.warning(f"No se encontró el dispositivo {device_id} en la respuesta de la API")
                        password_value = "Dispositivo no encontrado"
                
                    # Si no hay password o está vacío, mostrar "No asignado"
                    if password_value == "":
                        password_value = "No asignado"
                    
                    nfc_values.append(password_value)
                    logger.debug(f"Valor NFC obtenido para sensor {sensor_id}: {password_value}")
                else:
                    logger.error(f"Formato de datos NFC inesperado: {type(nfc_passwords_data)}. No contiene clave 'data'")
                    nfc_values.append("N/A")
                
            except Exception as e:
                logger.error(f"Error al obtener valor NFC: {str(e)}")
                nfc_values.append("Error")
        
        return nfc_values
    
    # Callback para abrir el modal de edición de código NFC
    @app.callback(
        [Output("nfc-edit-modal", "is_open"),
         Output("nfc-edit-info", "children"),
         Output("nfc-edit-value-input", "value"),
         Output("nfc-edit-feedback", "children"),
         Output("nfc-edit-success-timer", "disabled")],
        [Input({"type": "nfc-edit-button", "index": ALL}, "n_clicks"),
         Input("nfc-edit-cancel", "n_clicks"),
         Input("nfc-edit-save", "n_clicks")],
        [State({"type": "nfc-edit-button", "index": ALL}, "id"),
         State({"type": "nfc-sensor-data", "index": ALL}, "data"),
         State({"type": "nfc-value", "index": ALL}, "children"),
         State("nfc-edit-modal", "is_open"),
         State("nfc-edit-value-input", "value"),
         State("jwt-token-store", "data"),
         State("current-device-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[False, "", "", "", True])
    def handle_nfc_edit_modal(edit_clicks, cancel_clicks, save_clicks, button_ids, sensor_data_list, current_values, is_open, input_value, token_data, current_device):
        ctx = dash.callback_context
        triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else None
        
        # Si no hay trigger, no hacer nada
        if not triggered or triggered == '.':
            return is_open, dash.no_update, dash.no_update, dash.no_update, True
        
        # Si se cancela la edición
        if "nfc-edit-cancel" in triggered and cancel_clicks:
            return False, "", "", "", True
        
        # Si se hace clic en editar
        if "nfc-edit-button" in triggered:
            import json
            trigger_id = json.loads(triggered.split('.')[0])
            button_index = trigger_id.get('index')
            
            logger.debug(f"Botón de edición pulsado con índice: {button_index}")
            
            # Buscar el botón que se ha pulsado y el sensor correspondiente
            selected_sensor = None
            current_value = ""
            
            # Logging para depurar el problema
            logger.debug(f"Total de sensores disponibles: {len(sensor_data_list)}")
            
            for i, button_id in enumerate(button_ids):
                if i < len(sensor_data_list):
                    logger.debug(f"Sensor data {i}: {sensor_data_list[i]}")
                
                if button_id.get('index') == button_index and i < len(sensor_data_list):
                    selected_sensor = sensor_data_list[i]
                    logger.debug(f"Sensor seleccionado: {selected_sensor}")
                    
                    if i < len(current_values):
                        current_value = current_values[i]
                    break
            
            if not selected_sensor:
                logger.error(f"No se encontró el sensor correspondiente al botón {button_index}")
                return is_open, dash.no_update, dash.no_update, html.Div(
                    "Error: No se pudo recuperar la información del sensor",
                    className="alert alert-danger"
                ), True
            
            # Verificar que el sensor tenga todos los datos necesarios
            device_id = selected_sensor.get('device_id')
            sensor_id = selected_sensor.get('sensor_id')
            asset_id = selected_sensor.get('asset_id')
            
            # Si falta el asset_id, intentar obtenerlo del current-device-store
            if (not asset_id or asset_id == "No disponible") and current_device:
                asset_id = current_device.get('asset_id')
                selected_sensor['asset_id'] = asset_id
                logger.debug(f"Se usó el asset_id del current-device-store: {asset_id}")
            
            logger.debug(f"Verificando datos para edición - device_id: {device_id}, sensor_id: {sensor_id}, asset_id: {asset_id}")
            
            if not device_id or not sensor_id or not asset_id:
                logger.error(f"Faltan datos críticos del sensor - device_id: {device_id}, sensor_id: {sensor_id}, asset_id: {asset_id}")
                return is_open, dash.no_update, dash.no_update, html.Div(
                    "Error: Datos incompletos del sensor",
                    className="alert alert-danger"
                ), True
            
            # Información del sensor para mostrar en el modal
            sensor_info = html.Div([
                html.H6("Sensor:", className="mb-2"),
                html.Table([
                    html.Tbody([
                        html.Tr([
                            html.Td("Nombre:", className="fw-bold pe-3"),
                            html.Td(selected_sensor.get("name"))
                        ]),
                        html.Tr([
                            html.Td("ID Sensor:", className="fw-bold pe-3"),
                            html.Td(selected_sensor.get("sensor_id"))
                        ]),
                        html.Tr([
                            html.Td("Ubicación:", className="fw-bold pe-3"),
                            html.Td(selected_sensor.get("room") or "No especificada")
                        ])
                    ])
                ], className="table table-sm")
            ])
            
            # Guardar los datos del sensor en un hidden div para usarlos al guardar
            sensor_info_with_data = html.Div([
                sensor_info,
                dcc.Store(
                    id="nfc-editing-sensor-data",
                    data=selected_sensor
                )
            ])
            
            return True, sensor_info_with_data, current_value, "", True
        
        # Si se guarda la edición
        if "nfc-edit-save" in triggered and save_clicks:
            # Obtener los datos del sensor que se está editando
            editing_sensor_data = {}
            
            # En Dash 2.0+, ctx.states es un diccionario de todos los estados
            all_states = ctx.states
            
            # Buscar el estado con ID 'nfc-editing-sensor-data'
            for state_id, state_value in all_states.items():
                if 'nfc-editing-sensor-data' in state_id:
                    logger.debug(f"Encontrado estado de edición: {state_id}")
                    editing_sensor_data = state_value.get('data', {})
                    break
            
            # Si no lo encontramos por el ID completo, buscar por substring
            if not editing_sensor_data:
                for state_id, state_value in all_states.items():
                    if 'nfc-editing-sensor-data' in state_id:
                        editing_sensor_data = state_value
                        break
            
            # Agregar logs para diagnosticar el problema
            logger.debug(f"Datos para guardar NFC: {editing_sensor_data}")
            
            # Obtener los IDs necesarios con valores por defecto para depuración
            device_id = editing_sensor_data.get("device_id", "No disponible")
            sensor_id = editing_sensor_data.get("sensor_id", "No disponible") 
            asset_id = editing_sensor_data.get("asset_id", "No disponible")
            
            # Si falta el asset_id, intentar obtenerlo del current-device-store
            if (not asset_id or asset_id == "No disponible") and current_device:
                asset_id = current_device.get('asset_id')
                editing_sensor_data['asset_id'] = asset_id
                logger.debug(f"Se usó el asset_id del current-device-store: {asset_id}")
            
            # Logging detallado para diagnóstico
            logger.debug(f"Guardando NFC - device_id: {device_id}, sensor_id: {sensor_id}, asset_id: {asset_id}")
            
            # Imprimir todos los estados disponibles para debug
            logger.debug("Estados disponibles en el contexto:")
            for k, v in all_states.items():
                logger.debug(f"  - {k}: {v if not isinstance(v, dict) else 'dict'}")
                
            # Si editing_sensor_data está vacío, intentar reconstruir los datos desde otros estados
            if not editing_sensor_data or not device_id or device_id == "No disponible":
                # Intentar obtener datos del botón que se pulsó
                for k, v in all_states.items():
                    if 'nfc-edit-button' in k and isinstance(v, dict) and 'index' in v:
                        button_index = v.get('index')
                        if button_index:
                            logger.debug(f"Intentando reconstruir datos desde el botón: {button_index}")
                            parts = button_index.split('_')
                            # Formato antiguo: device_id_sensor_id
                            if len(parts) == 2:
                                device_id = parts[0]
                                sensor_id = parts[1]
                                # Si tenemos un current_device, usamos su asset_id
                                if current_device and current_device.get('device_id') == device_id:
                                    asset_id = current_device.get('asset_id')
                                    logger.debug(f"Usando asset_id={asset_id} del current-device-store")
                                # Si no, buscamos el asset_id como antes
                                else:
                                    for asset_k, asset_v in all_states.items():
                                        if 'smart-locks-data-store' in asset_k and asset_v:
                                            # Buscar el dispositivo en los datos
                                            devices = asset_v if isinstance(asset_v, list) else []
                                            for dev in devices:
                                                if dev.get('device_id') == device_id:
                                                    asset_id = dev.get('asset_id')
                                                    logger.debug(f"Reconstruido asset_id: {asset_id}")
                                                    break
                            # Nuevo formato: device_id_sensor_id_asset_id
                            elif len(parts) >= 3:
                                device_id = parts[0]
                                sensor_id = parts[1]
                                asset_id = parts[2]
                                logger.debug(f"Extraído asset_id={asset_id} directamente del índice del botón")
                            break
            
            # Validar que hay un valor
            if not input_value or input_value.strip() == "":
                return True, dash.no_update, dash.no_update, html.Div(
                    "El valor no puede estar vacío",
                    className="alert alert-danger"
                ), True
            
            # Validar que tenemos los datos necesarios
            if not device_id or device_id == "No disponible":
                return True, dash.no_update, dash.no_update, html.Div(
                    f"Falta el ID del dispositivo (device_id: {device_id})",
                    className="alert alert-danger"
                ), True
            
            if not sensor_id or sensor_id == "No disponible":
                return True, dash.no_update, dash.no_update, html.Div(
                    f"Falta el ID del sensor (sensor_id: {sensor_id})",
                    className="alert alert-danger"
                ), True
                
            if not asset_id or asset_id == "No disponible":
                return True, dash.no_update, dash.no_update, html.Div(
                    f"Falta el ID del asset (asset_id: {asset_id})",
                    className="alert alert-danger"
                ), True
            
            try:
                # Obtener el token JWT
                token = token_data.get('token') if token_data else None
                
                if not token:
                    logger.error("No hay token JWT disponible para actualizar valor NFC")
                    return True, dash.no_update, dash.no_update, html.Div(
                        "No hay autenticación disponible para actualizar el valor",
                        className="alert alert-danger"
                    ), True
                
                # Actualizar el valor del código NFC usando la nueva API
                # Usamos el endpoint correcto según la documentación
                gateway_id = device_id  # Por defecto, usar device_id como gateway_id
                logger.debug(f"Actualizando código NFC - asset_id: {asset_id}, device_id: {device_id}, sensor_id: {sensor_id}, valor: {input_value}")
                success, response = update_nfc_code_value(
                    asset_id=asset_id, 
                    device_id=device_id, 
                    sensor_id=sensor_id, 
                    new_value=input_value, 
                    jwt_token=token,
                    gateway_id=gateway_id  # Pasamos el gateway_id (que es igual al device_id en este caso)
                )
                
                if success:
                    # Mensaje de éxito
                    success_message = html.Div(
                        "Código NFC actualizado correctamente",
                        className="alert alert-success"
                    )
                    
                    # Activar el timer para cerrar el modal automáticamente
                    return True, dash.no_update, dash.no_update, success_message, False
                else:
                    # Mensaje de error
                    error_details = response.get("error", "Error desconocido")
                    error_message = html.Div(
                        f"Error al actualizar el código NFC: {error_details}",
                        className="alert alert-danger"
                    )
                    return True, dash.no_update, dash.no_update, error_message, True
            except Exception as e:
                error_message = html.Div(
                    f"Error al actualizar el código NFC: {str(e)}",
                    className="alert alert-danger"
                )
                return True, dash.no_update, dash.no_update, error_message, True
        
        return is_open, dash.no_update, dash.no_update, dash.no_update, True
    
    # Callbacks adicionales para las acciones del modal podrían implementarse aquí
    # - Verificar estado
    # - Bloquear/desbloquear
    # - Ver historial
    # - Actualizar software
    
    # Callback para cerrar el modal
    @app.callback(
        [Output("smart-locks-modal", "is_open", allow_duplicate=True),
         Output("current-device-store", "data", allow_duplicate=True)],
        [Input("smart-locks-modal-close", "n_clicks")],
        [State("smart-locks-modal", "is_open")],
        prevent_initial_call=True,
        id='close_details_modal_callback'  # Add a unique ID
    )
    def close_details_modal(n_clicks, is_open):
        if n_clicks and is_open:
            return False, None
        return is_open, dash.no_update
    
    # Callback para cerrar el modal de edición después de una actualización exitosa
    @app.callback(
        [Output("nfc-edit-modal", "is_open", allow_duplicate=True),
         Output("nfc-edit-success-timer", "disabled", allow_duplicate=True)],
        [Input("nfc-edit-success-timer", "n_intervals")],
        [State("nfc-edit-feedback", "children")],
        prevent_initial_call=True,
        id='close_nfc_edit_modal_after_success_callback'  # Add a unique ID
    )
    def close_nfc_edit_modal_after_success(n_intervals, feedback_content):
        # Solo cerrar si hay intervalos (timer activado) y hay un mensaje de éxito
        if n_intervals and feedback_content:
            # En una implementación real, deberíamos verificar si el feedback es de éxito
            # Esto se podría hacer guardando un indicador en un dcc.Store
            return False, True  # Cerrar el modal y desactivar el timer
        return dash.no_update, dash.no_update

    # Callback para crear sensores NFC virtuales a partir de los datos de la API
    @app.callback(
        Output("smart-locks-refresh-trigger", "data", allow_duplicate=True),
        [Input("smart-locks-modal", "is_open")],
        [State("smart-locks-modal-content", "children"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True,
        id='create_virtual_nfc_sensors_callback'  # Add a unique ID
    )
    @handle_exceptions(default_return={"refreshed": False})
    def create_virtual_nfc_sensors(is_open, modal_content, token_data):
        """
        Este callback se activa cuando se abre el modal y crea sensores NFC virtuales
        a partir de los datos de la API para los dispositivos que no tienen sensores
        NFC explícitamente definidos.
        """
        if not is_open or not modal_content:
            return dash.no_update
        
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
            
        # Obtener el token JWT
        token = token_data.get('token') if token_data else None
        if not token:
            logger.error("No hay token JWT disponible para crear sensores virtuales")
            return dash.no_update
            
        try:
            # Este callback solo observa cambios, no necesita hacer nada más
            # El callback load_nfc_values ya cargará los valores cuando se abra el modal
            return {"refreshed": True, "timestamp": time.time()}
        except Exception as e:
            logger.error(f"Error al crear sensores virtuales: {str(e)}")
            return dash.no_update

    # Callback para cargar y mostrar dinámicamente los sensores NFC
    @app.callback(
        Output("smart-locks-modal-feedback", "children", allow_duplicate=True),
        [Input("smart-locks-modal", "is_open"),
         Input("smart-locks-refresh-trigger", "data")],
        [State("smart-locks-data-store", "data"),
         State("smart-locks-modal", "children"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True,
        id='load_api_nfc_sensors_callback'  # Add a unique ID
    )
    @handle_exceptions(default_return=html.Div())
    def load_api_nfc_sensors(is_open, refresh_trigger, devices_data, modal_children, token_data):
        ctx = dash.callback_context
        if not ctx.triggered or not is_open:
            return dash.no_update
            
        # Obtener el token JWT
        token = token_data.get('token') if token_data else None
        if not token:
            logger.error("No hay token JWT disponible para cargar sensores NFC")
            return dash.no_update
            
        # Intentar obtener el asset_id y device_id del modal actual
        asset_id = None
        device_id = None
        
        # Buscar un elemento con id que contenga "modal-lock-status"
        # Este elemento contiene el device_id como parte de su índice
        try:
            modal_content = modal_children[1] if isinstance(modal_children, list) and len(modal_children) > 1 else None
            if modal_content and 'props' in modal_content and 'children' in modal_content['props']:
                for child in modal_content['props']['children']:
                    if not isinstance(child, dict):
                        continue
                    
                    # Buscar recursivamente objetos con "id" que contengan "modal-lock-status"
                    def find_device_id(obj):
                        if isinstance(obj, dict):
                            if 'props' in obj and 'id' in obj['props']:
                                id_prop = obj['props']['id']
                                if isinstance(id_prop, dict) and id_prop.get('type') == 'modal-lock-status':
                                    return id_prop.get('index')
                            
                            # Buscar en hijos
                            for key, value in obj.items():
                                if key == 'props' and 'children' in value:
                                    result = find_device_id_in_children(value['children'])
                                    if result:
                                        return result
                        return None
                    
                    def find_device_id_in_children(children):
                        if isinstance(children, list):
                            for child in children:
                                result = find_device_id(child)
                                if result:
                                    return result
                        else:
                            return find_device_id(children)
                        return None
                    
                    device_id = find_device_id(child)
                    if device_id:
                        break
        except Exception as e:
            logger.error(f"Error al buscar device_id en el modal: {str(e)}")
            return dash.no_update
        
        if not device_id:
            logger.warning("No se pudo determinar el dispositivo actual del modal")
            return dash.no_update
            
        # Buscar el dispositivo en los datos para obtener el asset_id
        device = next((d for d in devices_data if d.get("device_id") == device_id), None)
        if not device:
            logger.warning(f"No se encontró el dispositivo {device_id} en los datos")
            return dash.no_update
            
        asset_id = device.get("asset_id")
        if not asset_id:
            logger.warning(f"El dispositivo {device_id} no tiene asset_id")
            return dash.no_update
            
        # Comprobar si el dispositivo ya tiene sensores NFC
        has_nfc_sensors = False
        for sensor in device.get("sensors", []):
            if sensor.get("sensor_type") == "NFC_CODE":
                has_nfc_sensors = True
                break
                
        if has_nfc_sensors:
            logger.debug(f"El dispositivo {device_id} ya tiene sensores NFC, no se cargan desde la API")
            return dash.no_update
            
        # Intentar cargar los sensores NFC de la API
        try:
            logger.info(f"Cargando sensores NFC de la API para asset_id {asset_id}")
            nfc_data = get_nfc_passwords(asset_id, token)
            
            if not nfc_data or not isinstance(nfc_data, dict) or 'data' not in nfc_data:
                logger.warning(f"No se obtuvieron datos NFC válidos para {asset_id}")
                return html.Div([
                    html.H5("Códigos NFC", className="mb-3"),
                    html.Div([
                        html.P([
                            html.I(className="fas fa-info-circle me-2 text-info"),
                            "No hay códigos NFC disponibles para este dispositivo."
                        ])
                    ], className="info-card p-3 mb-4", style={"border": "1px solid #dee2e6", "borderRadius": "8px"})
                ], className="mt-4")
                
            data_section = nfc_data['data']
            devices = []
            
            # Extraer dispositivos según el formato
            if isinstance(data_section, dict) and 'devices' in data_section:
                devices = data_section['devices']
            elif isinstance(data_section, list):
                devices = data_section
            else:
                logger.warning(f"Formato inesperado de datos NFC: {type(data_section)}")
                return dash.no_update
                
            # Filtrar dispositivos que coincidan con el device_id
            matching_devices = []
            for dev in devices:
                dev_id = str(dev.get('device_id', ''))
                if dev_id == str(device_id):
                    matching_devices.append(dev)
                    
            if not matching_devices:
                logger.warning(f"No se encontraron dispositivos con ID {device_id} en los datos NFC")
                return html.Div([
                    html.H5("Códigos NFC", className="mb-3"),
                    html.Div([
                        html.P([
                            html.I(className="fas fa-info-circle me-2 text-info"),
                            "No hay códigos NFC disponibles para este dispositivo."
                        ])
                    ], className="info-card p-3 mb-4", style={"border": "1px solid #dee2e6", "borderRadius": "8px"})
                ], className="mt-4")
                
            # Extraer sensores NFC de los dispositivos coincidentes
            nfc_rows = []
            for dev in matching_devices:
                sensor_passwords = dev.get('sensor_passwords', [])
                for sensor_pw in sensor_passwords:
                    if not isinstance(sensor_pw, dict):
                        continue
                        
                    # Solo procesar sensores NFC_CODE
                    if sensor_pw.get('sensor_type') != 'NFC_CODE':
                        continue
                        
                    sensor_id = str(sensor_pw.get('sensor_id', ''))
                    password = sensor_pw.get('password', '')
                    
                    logger.debug(f"Añadiendo sensor NFC de la API: device_id={device_id}, sensor_id={sensor_id}, asset_id={asset_id}")
                    
                    # Datos del sensor para el store con todos los campos necesarios
                    sensor_data = {
                        "device_id": device_id,
                        "sensor_id": sensor_id,
                        "sensor_uuid": "",
                        "name": f"NFC Code {sensor_id}",
                        "room": "",
                        "asset_id": asset_id,
                        "scope": device.get("scope", {"type": "Asset"})
                    }
                    
                    # Verificar que todos los datos críticos estén presentes
                    logger.debug(f"Datos del sensor guardados: device_id={sensor_data['device_id']}, sensor_id={sensor_data['sensor_id']}, asset_id={sensor_data['asset_id']}")
                    
                    # Añadir fila para el sensor NFC
                    nfc_rows.append(
                        html.Tr([
                            html.Td(sensor_id),
                            html.Td(f"NFC Code {sensor_id}"),
                            html.Td("-"),
                            html.Td(password if password else "No asignado"),
                            html.Td([
                                dbc.Button(
                                    html.I(className="fas fa-edit"),
                                    id={"type": "nfc-edit-button", "index": f"{device_id}_{sensor_id}_{asset_id}"},
                                    color="link",
                                    size="sm",
                                    className="p-0",
                                    title="Editar código NFC"
                                ),
                                # Store para guardar información del sensor NFC
                                dcc.Store(
                                    id={"type": "nfc-sensor-data", "index": f"{device_id}_{sensor_id}"},
                                    data=sensor_data
                                )
                            ])
                        ])
                    )
            
            if not nfc_rows:
                logger.warning(f"No se encontraron sensores NFC para el dispositivo {device_id}")
                return html.Div([
                    html.H5("Códigos NFC", className="mb-3"),
                    html.Div([
                        html.P([
                            html.I(className="fas fa-info-circle me-2 text-info"),
                            "Este dispositivo no tiene códigos NFC configurados."
                        ])
                    ], className="info-card p-3 mb-4", style={"border": "1px solid #dee2e6", "borderRadius": "8px"})
                ], className="mt-4")
                
            # Crear la sección de NFC Codes
            nfc_section = html.Div([
                html.H5("Códigos NFC", className="mb-3"),
                html.Div([
                    html.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("ID", className="fw-bold"),
                                html.Th("Nombre", className="fw-bold"),
                                html.Th("Ubicación", className="fw-bold"),
                                html.Th("Valor Actual", className="fw-bold"),
                                html.Th("Acciones", className="fw-bold"),
                            ])
                        ]),
                        html.Tbody(nfc_rows)
                    ], className="table table-striped table-hover")
                ], className="info-card p-3 mb-4", style={"border": "1px solid #dee2e6", "borderRadius": "8px"})
            ], className="mt-4")
            
            return nfc_section
            
        except Exception as e:
            logger.error(f"Error al cargar sensores NFC de la API: {str(e)}")
            return dash.no_update 
    
    # Callback combinado para mostrar la matriz NFC o la matriz por tipo
    @app.callback(
        Output("nfc-grid-container", "children"),
        [Input("smart-locks-tabs", "active_tab"),
         Input("smart-locks-data-store", "data"),
         Input("smart-locks-type-filter", "value")],
        prevent_initial_call=False
    )
    @handle_exceptions(default_return=html.Div("Error al cargar la matriz", className="alert alert-danger"))
    def update_grid_display(active_tab, devices_data, selected_type):
        """
        Prepara y muestra la matriz de códigos NFC cuando el usuario selecciona la pestaña correspondiente.
        """
        # Si la pestaña no es la de matriz NFC, devolver un contenedor vacío
        if active_tab != "nfc-grid-tab":
            return html.Div()
        
        # Si no hay datos, mostrar mensaje informativo
        if not devices_data:
            return html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "Seleccione un proyecto y haga clic en 'Mostrar Cerraduras' para ver la matriz de códigos NFC."
            ], className="alert alert-info")
        
        # Filtrar dispositivos según el tipo seleccionado
        filtered_devices = devices_data
        if selected_type and selected_type != 'all':
            filtered_devices = [d for d in devices_data if d.get('device_type', '').upper() == selected_type]
            logger.info(f"Filtrados {len(filtered_devices)} dispositivos de tipo {selected_type}")
        
        # Extraer información básica de los dispositivos para la matriz
        processed_devices = []
        asset_ids = []
        asset_names = {}
        
        for device in filtered_devices:
            # Verificar que es un dispositivo válido con asset_id
            asset_id = device.get('asset_id')
            if not asset_id:
                continue
                
            # Registrar información del asset
            if asset_id not in asset_ids:
                asset_ids.append(asset_id)
                
            # Guardar nombre del asset para referencia
            asset_name = asset_id  # Usar directamente el assetId
            asset_names[asset_id] = asset_name
            
            # Crear entrada básica del dispositivo
            processed_device = {
                'device_id': device.get('device_id', ''),
                'device_name': device.get('device_name', 'Sin nombre'),
                'device_type': device.get('device_type', '').upper(),
                'asset_id': asset_id,
                'asset_name': asset_id,  # Usar directamente el assetId
                'sensors': device.get('sensors', [])
            }
            
            # Añadir el dispositivo a la lista
            processed_devices.append(processed_device)
        
        # Verificar si hay dispositivos para mostrar
        if not processed_devices:
            return html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "No se encontraron cerraduras con espacios asignados para mostrar en la matriz."
            ], className="alert alert-info")
        
        # Encabezado informativo
        info_section = html.Div([
            html.H4("Matriz de Códigos NFC", className="mb-3"),
            html.Div([
                html.P([
                    html.I(className="fas fa-info-circle me-2"),
                    html.Span([
                        "Esta matriz muestra los códigos NFC asignados a las cerraduras del proyecto. ",
                        "Los códigos pueden ser editados haciendo clic en las celdas correspondientes."
                    ])
                ], className="alert alert-info"),
                html.Div([
                    html.Strong(f"Cerraduras detectadas: {len(processed_devices)}"),
                    html.Span(f" | Total de espacios: {len(asset_ids)}", className="ms-3"),
                ], className="mb-3 p-2 bg-light rounded border")
            ])
        ])
        
        # Contenedor de botones de acción
        action_buttons = html.Div([
            dbc.Button([
                html.I(className="fas fa-sync-alt me-2"),
                "Actualizar Códigos NFC"
            ], id="nfc-refresh-button", color="primary", className="mb-3"),
            dbc.Button([
                html.I(className="fas fa-id-card me-2"),
                "Asignar Tarjeta Maestra"
            ], id="master-card-assign-button", color="primary", className="mb-3 ms-2"),
            dbc.Button([
                html.I(className="fas fa-unlink me-2"),
                "Desasignar Tarjeta Maestra"
            ], id="master-card-unassign-button", color="danger", className="mb-3 ms-2")
        ], className="d-flex")
        
        # Store para almacenar datos para el callback de carga de códigos NFC
        nfc_grid_data_store = dcc.Store(
            id="nfc-grid-data-store",
            data={
                "asset_ids": asset_ids,
                "asset_names": asset_names,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        
        # Store para dispositivos seleccionados para asignación masiva
        selected_devices_store = dcc.Store(
            id="selected-devices-store",
            data={"selected": []}
        )
        
        # Crear trigger para actualización de datos
        update_trigger = dcc.Store(
            id="nfc-update-trigger",
            data={"updated": False, "count": 0}
        )
        
        # Store para almacenar el dispositivo a actualizar individualmente
        device_update_store = dcc.Store(
            id="nfc-device-update-store",
            data={"device_id": None, "asset_id": None, "timestamp": None}
        )
        
        # En lugar de usar create_nfc_display_grid, crear directamente un contenedor vacío
        # que será rellenado por el callback load_nfc_grid_data
        nfc_grid_container = html.Div([
            # Contenedor para filtro
            html.Div([
                dbc.Checklist(
                    options=[
                        {"label": "Mostrar todos los sensores", "value": True}
                    ],
                    value=[True],
                    id="nfc-grid-filter-toggle",
                    switch=True,
                    className="mt-2"
                ),
                html.Div(className="mb-3")
            ], className="d-flex justify-content-between align-items-center"),
            
            # Contenedor de errores 
            html.Div(id="nfc-grid-error-container"),
            
            # Indicador de carga
            dbc.Spinner(html.Div(id="nfc-grid-loading-indicator"), color="primary", type="grow", size="sm"),
            
            # Tabla (modificada para incluir selección de filas)
            dash_table.DataTable(
                id="nfc-grid-table",
                columns=[
                    {"name": "Nombre Dispositivo", "id": "device_id"},
                    {"name": "Cerradura", "id": "lock_name"},
                    {"name": "Espacio", "id": "asset_name"},
                    # Nueva columna para el botón de actualización
                    {"name": "Acciones", "id": "actions"}
                ],
                data=[],
                sort_action="native",
                sort_mode="multi",
                filter_action="native",
                page_action="native",
                page_size=50,
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
                row_selectable="multi",
                export_format="xlsx"
            ),
            
            # Store para el filtro
            dcc.Store(
                id="nfc-grid-filter-store",
                data={"show_all": True}
            )
        ], className="nfc-grid-container mt-3") 
        
        # Devolver contenedor completo
        return html.Div([
            info_section,
            action_buttons,
            nfc_grid_data_store,
            selected_devices_store,
            update_trigger,
            device_update_store,
            nfc_grid_container
        ], className="nfc-grid-view mt-4")
    
    # Callback para actualizar los datos NFC cuando se hace clic en el botón de refrescar
    @app.callback(
        Output("nfc-update-trigger", "data", allow_duplicate=True),
        [Input("nfc-refresh-button", "n_clicks")],
        [State("nfc-update-trigger", "data")],
        prevent_initial_call=True,
        id='refresh_nfc_data_callback'  # Add a unique ID
    )
    @handle_exceptions(default_return={"refreshed": False})
    def refresh_nfc_data(n_clicks, current_data):
        if not n_clicks:
            return dash.no_update
            
        # Incrementar el contador para forzar la actualización
        current_count = current_data.get("count", 0) if current_data else 0
        return {"updated": True, "count": current_count + 1, "refreshed": True}
    
    # Callback para mostrar u ocultar el filtro de tipo de cerradura
    @app.callback(
        Output("smart-locks-type-filter-container", "style"),
        [Input("smart-locks-data-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return={"display": "none"})
    def toggle_type_filter_visibility(devices_data):
        # Siempre ocultar el filtro de tipo, ya que ahora mostramos todos los códigos NFC
        return {"display": "none"}
    
    # Callback para cargar los tipos de cerradura en el filtro
    @app.callback(
        [Output("smart-locks-type-filter", "options"),
         Output("smart-locks-type-filter", "value"),
         Output("smart-locks-type-filter-info", "children")],
        [Input("smart-locks-data-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[[{"label": "Sin tipos disponibles", "value": ""}], None, ""])
    def load_lock_types(devices_data):
        if not devices_data or len(devices_data) == 0:
            return [], None, ""
        
        # Extraer los tipos únicos de cerradura
        device_types = {}  # Usamos un diccionario para contar dispositivos por tipo
        
        for device in devices_data:
            device_type = device.get("device_type", "UNKNOWN")
            device_types[device_type] = device_types.get(device_type, 0) + 1
        
        # Crear las opciones para el dropdown
        options = [{"label": f"{device_type} ({count})", "value": device_type} 
                  for device_type, count in sorted(device_types.items())]
        
        # Mostrar el número total de tipos
        info_text = f"Total: {len(device_types)} tipos de cerradura"
        
        # Devolver las opciones, seleccionar el primer tipo y el texto informativo
        return options, options[0]["value"] if options else None, info_text
    
    # Callback para mostrar la matriz por tipo cuando se selecciona la pestaña y un tipo
    @app.callback(
        [Output("lock-type-grid-table", "data", allow_duplicate=True),
         Output("lock-type-grid-loading-indicator", "children", allow_duplicate=True),
         Output("lock-type-grid-error-container", "children", allow_duplicate=True)],
        [Input("lock-type-grid-data-store", "data")],
        [State("lock-type-grid-table", "data"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True,
        id='load_sensor_values_duplicate_callback'  # Add a unique ID to this callback
    )
    @handle_exceptions(default_return=[[], "", html.Div("Error al cargar datos de sensores", className="alert alert-danger")])
    def load_sensor_values_duplicate(grid_data, current_table_data, token_data):
        # Verificar que haya datos válidos
        if not grid_data or not grid_data.get("asset_ids") or not current_table_data:
            return current_table_data, "", ""
        
        # Verificar autenticación
        token = token_data.get('token') if token_data else None
        if not token:
            return current_table_data, "", html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "No se pudo autenticar para obtener datos de sensores."
            ], className="alert alert-warning")
        
        # Obtener los asset_ids únicos para consultar
        asset_ids = grid_data.get("asset_ids", [])
        if not asset_ids:
            return current_table_data, "", html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "No se encontraron espacios (assets) para consultar valores de sensores."
            ], className="alert alert-info")
        
        # Iniciar proceso de carga de datos de sensores
        errors = []
        updated_data = current_table_data.copy()
        
        # Registrar inicio de proceso
        logger.info(f"Iniciando carga de valores de sensores para {len(asset_ids)} espacios y {len(updated_data)} cerraduras")
        
        # Crear un mapa de device_id a índice en la tabla para actualización eficiente
        device_to_index = {row["device_id"]: i for i, row in enumerate(updated_data)}
        
        # En este caso, solo vamos a actualizar valores básicos que ya tenemos
        # No necesitamos hacer llamadas a la API adicionales en esta fase
        
        # En una implementación real, aquí podrías hacer llamadas a la API para obtener los valores más recientes de los sensores.
        # Por ejemplo:
        # with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        #     future_to_asset = {executor.submit(fetch_sensor_values, asset_id, token): asset_id for asset_id in asset_ids}
        #     ... procesar resultados ...
        
        # Mensaje de éxito
        success_message = html.Div([
            html.I(className="fas fa-check-circle me-2", style={"color": "green"}),
            "Matriz por tipo cargada correctamente."
        ], className="alert alert-success")
        
        return updated_data, "", success_message

    # Callback para cargar datos NFC de la API en la tabla del grid
    @app.callback(
        [Output("nfc-grid-table", "data", allow_duplicate=True),
         Output("nfc-grid-table", "columns", allow_duplicate=True)],
        [Input("nfc-grid-data-store", "data"),
         Input("nfc-update-trigger", "data"),
         Input("smart-locks-tabs", "active_tab"),
         Input("nfc-device-update-store", "data")],  # Nuevo input para actualizaciones individuales
        [State("nfc-grid-table", "data"),
         State("nfc-grid-table", "columns"),
         State("jwt-token-store", "data"),
         State("nfc-grid-filter-store", "data")],
        prevent_initial_call=True,
        id='load_nfc_grid_data_callback'  # Add a unique ID to the callback
    )
    @handle_exceptions(default_return=[[], []])
    def load_nfc_grid_data(grid_data, update_trigger, active_tab, device_update_data, current_table_data, current_columns, token_data, filter_data):
        """
        Carga los códigos NFC para todos los assets seleccionados o para un dispositivo específico.
        """
        # Verificar si el trigger es el cambio de pestaña y no es la pestaña NFC
        ctx = callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        if triggered_id == "smart-locks-tabs" and active_tab != "nfc-grid-tab":
            # Si se cambió a otra pestaña, no hacer nada
            return dash.no_update, dash.no_update
        
        # Verificar que haya datos válidos
        if not grid_data:
            logger.warning("No hay datos de grid disponibles")
            return current_table_data, current_columns
        
        # Verificar autenticación
        token = token_data.get('token') if token_data else None
        if not token:
            return current_table_data, current_columns, html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "No se pudo autenticar para obtener códigos NFC."
            ], className="alert alert-warning")

        # Determinar si es una actualización individual o completa
        update_single_device = False
        target_device_id = None
        target_asset_id = None
        
        if triggered_id == "nfc-device-update-store" and device_update_data:
            target_device_id = device_update_data.get("device_id")
            target_asset_id = device_update_data.get("asset_id")
            
            if target_device_id and target_asset_id:
                update_single_device = True
                logger.info(f"Actualizando dispositivo individual: {target_device_id} (asset_id={target_asset_id})")

        # Importar la función para formatear valores NFC
        from components.smart_locks.nfc_grid.nfc_display_grid import format_nfc_value
        
        # Función auxiliar para formatear un valor NFC
        def process_nfc_value(value):
            if not value:
                return ""  # Celda vacía en lugar de "No asignado"
                
            # Verificar si es un string
            if not isinstance(value, str):
                value = str(value)
                
            # Eliminar espacios
            value = value.strip()
            
            # Si después de strip es vacío
            if not value:
                return ""  # Celda vacía en lugar de "No asignado"
            
            # Formatear el valor
            formatted = format_nfc_value(value)
            
            # Si el formateo devolvió un valor vacío, usar cadena vacía
            return formatted if formatted else ""
        
        # Obtener los asset_ids únicos para consultar
        asset_ids = grid_data.get("asset_ids", [])
        if not asset_ids:
            logger.warning("No hay asset_ids disponibles para consultar")
            return current_table_data, current_columns
            
        # Si es actualización individual, consultar solo el asset del dispositivo
        if update_single_device:
            if target_asset_id in asset_ids:
                asset_ids = [target_asset_id]
            else:
                logger.warning(f"El asset_id {target_asset_id} no está en la lista de assets disponibles")
        
        logger.info(f"Iniciando carga de códigos NFC para {len(asset_ids)} espacios")
        
        # Indicador de carga
        loading_indicator = html.Div(
            f"Cargando códigos NFC {('para dispositivo ' + target_device_id) if update_single_device else ('para ' + str(len(asset_ids)) + ' espacios')}...", 
            className="text-info"
        )
        
        # Columnas básicas que siempre se mostrarán
        base_columns = [
            {"name": "ID", "id": "device_id"},
            {"name": "Cerradura", "id": "lock_name"},
            {"name": "Espacio", "id": "asset_name"}
        ]
        
        # Almacenar todos los sensores NFC encontrados
        all_nfc_sensors = {}  # Mapa: sensor_id -> {detalles del sensor}
        all_devices = []      # Lista de dispositivos procesados con sensores NFC
        
        # Lista de sensores importantes que siempre deben estar presentes
        important_sensors = ["2", "7", "8", "9", "10"]  # Añadido el sensor 7 para tarjeta maestra
        
        # PASO 1: Obtener todos los valores NFC de los assets
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Crear un futuro para cada asset_id
                futures = {
                    executor.submit(fetch_nfc_passwords_for_asset, asset_id, token): asset_id 
                    for asset_id in asset_ids
                }
                
                # Procesar los resultados a medida que se completan
                for future in concurrent.futures.as_completed(futures):
                    asset_id = futures[future]
                    try:
                        # Obtener y procesar datos del asset
                        _, devices = future.result()
                        
                        # Si es actualización individual, filtrar solo el dispositivo específico
                        if update_single_device:
                            devices = [d for d in devices if d.get("device_id") == target_device_id]
                            if not devices:
                                logger.warning(f"No se encontró el dispositivo {target_device_id} en el asset {asset_id}")
                        
                        # Procesar los dispositivos encontrados
                        for device in devices:
                            # Extraer información básica
                            device_id = device.get("device_id")
                            device_name = device.get("device_name", "Sin nombre")
                            
                            # Obtener room y name de parameters si existen
                            parameters = device.get("parameters", {})
                            room = parameters.get("room", "")
                            name = parameters.get("name", "")
                            
                            # Crear etiqueta concatenada, o usar el device_name como respaldo
                            if room and name:
                                display_label = f"{room} - {name}"
                            elif room:
                                display_label = room
                            elif name:
                                display_label = name
                            else:
                                display_label = device.get("device_name", "Sin nombre")
                            
                            # Crear entrada del dispositivo para la tabla
                            device_entry = {
                                "device_id": display_label,  # Concatenación de room + name
                                "lock_name": device_name,
                                "asset_name": asset_id,  # Mostrar directamente el asset_id
                                "asset_id": asset_id,  # Guardar asset_id para el botón de actualización
                                # Almacenar el ID real del dispositivo para operaciones de API
                                "real_device_id": device_id,  
                                # Añadir el botón de actualización
                                "actions": "refresh_button"  # Este valor será reemplazado por el HTML del botón
                            }
                            
                            logger.info(f"Procesando dispositivo {device_id} ({device_name}) con {len(device.get('sensors', []))} sensores")
                            
                            # Extraer sensores NFC
                            has_nfc_sensors = False
                            
                            for sensor in device.get("sensors", []):
                                sensor_id = sensor.get("sensor_id")
                                if not sensor_id:
                                    continue
                                    
                                # Registrar el sensor NFC
                                all_nfc_sensors[sensor_id] = sensor
                                
                                # Añadir el valor NFC a la entrada del dispositivo
                                password = sensor.get("password", "")
                                formatted_value = process_nfc_value(password)
                                device_entry[f"sensor_{sensor_id}"] = formatted_value
                                logger.info(f"Valor NFC extraído para sensor {sensor_id}: '{password}' -> '{formatted_value}'")
                                has_nfc_sensors = True
                            
                            # Asegurar que los sensores importantes siempre estén presentes
                            for sensor_id in important_sensors:
                                if f"sensor_{sensor_id}" not in device_entry:
                                    device_entry[f"sensor_{sensor_id}"] = ""  # Celda vacía en lugar de "No asignado"
                                    logger.info(f"Añadido sensor importante {sensor_id} al dispositivo {device_id} con valor vacío")
                                    
                                    # Si no existe en all_nfc_sensors, crearlo
                                    if sensor_id not in all_nfc_sensors:
                                        all_nfc_sensors[sensor_id] = {
                                            "sensor_id": sensor_id,
                                            "sensor_type": "NFC_CODE",
                                            "name": f"NFC {sensor_id}",
                                            "password": ""
                                        }
                                    
                                    # Marcar que tiene al menos un sensor NFC (aunque sea vacío)
                                    has_nfc_sensors = True
                            
                            # Solo añadir dispositivos que tengan sensores NFC
                            if has_nfc_sensors:
                                # Guardar gateway_id para operaciones de API
                                gateway_id = device.get("gateway_id")
                                
                                # Caso especial para el dispositivo problemático ID 127
                                if device_id == "127" and not gateway_id:
                                    gateway_id = "1000000053eb1d68"
                                    logger.info(f"Asignando gateway_id específico para el dispositivo 127: {gateway_id}")
                                
                                # Solo almacenar gateway_id si existe, no usar device_id como fallback
                                if gateway_id:
                                    device_entry["gateway_id"] = gateway_id
                                    logger.info(f"Gateway ID para dispositivo {device_id}: {gateway_id}")
                                else:
                                    logger.warning(f"No se encontró gateway_id para el dispositivo {device_id}")
                                
                                all_devices.append(device_entry)
                                logger.debug(f"Dispositivo {device_id} añadido con sensores NFC")
                            
                    except Exception as e:
                        logger.error(f"Error al procesar asset {asset_id}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Error general en la carga de NFC: {str(e)}")
            return current_table_data, current_columns
        
        # Si no se encontraron dispositivos con sensores NFC
        if not all_devices:
            no_devices_message = html.Div([
                html.I(className="fas fa-info-circle me-2"),
                f"No se encontraron {'el dispositivo' if update_single_device else 'cerraduras con sensores NFC'} en los espacios seleccionados."
            ], className="alert alert-info")
            
            return [], base_columns
            
        # PASO 2: Si es una actualización individual y tenemos datos actuales, solo actualizar ese dispositivo
        if update_single_device and current_table_data:
            updated_data = list(current_table_data)  # Hacer una copia
            updated_device = None
            
            # Buscar el dispositivo actualizado en los datos nuevos
            for device in all_devices:
                if device.get("device_id") == target_device_id:
                    updated_device = device
                    break
            
            if updated_device:
                # Actualizar el dispositivo en los datos actuales
                device_found = False
                for i, row in enumerate(updated_data):
                    if row.get("device_id") == target_device_id:
                        # Mantener columnas que no son sensores NFC
                        preserved_keys = ["device_id", "lock_name", "asset_name", "asset_id", "real_device_id", "gateway_id", "actions"]
                        updated_row = {k: row[k] for k in preserved_keys if k in row}
                        
                        # Añadir los valores NFC actualizados
                        for key, value in updated_device.items():
                            if key.startswith("sensor_") or key not in preserved_keys:
                                updated_row[key] = value
                        
                        updated_data[i] = updated_row
                        device_found = True
                        break
                
                # Si no se encontró el dispositivo en los datos actuales, añadirlo
                if not device_found:
                    updated_data.append(updated_device)
                
                success_message = html.Div([
                    html.I(className="fas fa-check-circle me-2", style={"color": "green"}),
                    f"Códigos NFC actualizados correctamente para {updated_device.get('lock_name')}."
                ], className="alert alert-success")
                
                # Retornar los datos actualizados y las columnas actuales
                return updated_data, current_columns, success_message
            else:
                # Si no se encontró el dispositivo actualizado, mostrar un mensaje de error
                error_message = html.Div([
                    html.I(className="fas fa-exclamation-circle me-2"),
                    f"No se pudo actualizar el dispositivo {target_device_id}."
                ], className="alert alert-warning")
                
                return current_table_data, current_columns, error_message
            
        # PASO 3: Generar las columnas para todos los sensores NFC encontrados
        sensor_ids = sorted(all_nfc_sensors.keys())
        nfc_columns = []
        
        # Convertir sensor_ids a enteros para ordenarlos numéricamente
        # y luego volver a strings para el procesamiento posterior
        numeric_sensor_ids = []
        non_numeric_ids = []
        
        for sensor_id in sensor_ids:
            try:
                numeric_sensor_ids.append(int(sensor_id))
            except (ValueError, TypeError):
                # Si no se puede convertir a número, mantenerlo como está
                non_numeric_ids.append(sensor_id)
                logger.warning(f"Sensor ID no numérico encontrado: {sensor_id}")
        
        # Ordenar numéricamente y convertir de vuelta a strings
        numeric_sensor_ids.sort()
        non_numeric_ids.sort()
        
        # Combinar los IDs numéricos y no numéricos
        ordered_sensors = [str(id) for id in numeric_sensor_ids] + non_numeric_ids
        
        # Asegurar que los sensores importantes estén presentes
        for imp_id in important_sensors:
            if imp_id not in ordered_sensors and imp_id in all_nfc_sensors:
                # Solo agregar si el sensor existe en all_nfc_sensors
                # Encontrar la posición correcta según su valor numérico
                inserted = False
                for i, sensor_id in enumerate(ordered_sensors):
                    try:
                        if int(imp_id) < int(sensor_id):
                            ordered_sensors.insert(i, imp_id)
                            inserted = True
                            break
                    except (ValueError, TypeError):
                        continue
                
                # Si no se pudo insertar (por ejemplo, si es mayor que todos los demás)
                if not inserted:
                    ordered_sensors.append(imp_id)
        
        logger.info(f"Orden final de sensores: {ordered_sensors}")
        
        # Crear columnas para los sensores en el orden establecido
        for sensor_id in ordered_sensors:
            if sensor_id in all_nfc_sensors:
                sensor = all_nfc_sensors[sensor_id]
                
                # Destacar la columna del slot 7 (tarjeta maestra)
                if sensor_id == "7":
                    sensor_name = "Tarjeta Maestra"
                else:
                    sensor_name = sensor.get("name", f"NFC {sensor_id}")
                
                nfc_columns.append({
                    "name": sensor_name,
                    "id": f"sensor_{sensor_id}",
                    "editable": True
                })
        
        # Aplicar el filtro de sensores si está habilitado
        show_all_sensors = filter_data.get("show_all", True) if filter_data else True
        
        if not show_all_sensors:
            # Detectar sensores que tienen valores asignados
            sensors_with_values = set()
            
            for device in all_devices:
                for sensor_id in sensor_ids:
                    column_id = f"sensor_{sensor_id}"
                    if column_id in device:
                        value = device[column_id]
                        # Considerar solo valores que no sean vacíos y que tengan el prefijo de formato
                        if value and "➤" in value:
                            sensors_with_values.add(sensor_id)
                            break
        
        # Añadir la columna de acciones
        all_columns = base_columns + nfc_columns + [{"name": "Acciones", "id": "actions"}]
        
        # PASO 4: En cada dispositivo, reemplazar "refresh_button" por el botón HTML
        for device in all_devices:
            device_id = device.get("real_device_id", "")  # Usar el ID real del dispositivo
            asset_id = device.get("asset_id", "")
            
            if device_id and asset_id:
                # El valor de "actions" debe ser un string que refleje el HTML del botón
                device["actions"] = f"<button id='refresh-device-{device_id}' class='btn btn-sm btn-outline-primary' data-device-id='{device_id}' data-asset-id='{asset_id}'><i class='fas fa-sync-alt'></i></button>"
        
        # PASO 5: Verificar los valores antes de devolverlos (para debug)
        for device in all_devices:
            logger.info(f"Datos finales del dispositivo {device.get('device_id')} - {device.get('lock_name')}:")
            for key, value in device.items():
                if key.startswith("sensor_"):
                    sensor_id = key.replace("sensor_", "")
                    logger.info(f"  - Sensor {sensor_id}: '{value}'")
        
        # Crear mensaje de éxito
        success_message = html.Div([
            html.I(className="fas fa-check-circle me-2", style={"color": "green"}),
            f"Se encontraron {len(all_devices)} cerraduras con {len(sensor_ids)} tipos de sensores NFC."
        ], className="alert alert-success")
            
        logger.info(f"Carga de NFC completada: {len(all_devices)} dispositivos, {len(sensor_ids)} sensores")
        return all_devices, all_columns

    # Callback para manejar el toggle de mostrar todos los sensores o solo los que tienen valores
    @app.callback(
        [Output("nfc-grid-filter-store", "data"),
         Output("nfc-grid-table", "columns", allow_duplicate=True)],
        [Input("nfc-grid-filter-toggle", "value")],
        [State("nfc-grid-filter-store", "data"),
         State("nfc-grid-data-store", "data"),
         State("nfc-grid-table", "data"),
         State("nfc-grid-table", "columns")],
        prevent_initial_call=True,
        id='update_nfc_filter_toggle_callback'  # Add a unique ID to this callback too
    )
    @handle_exceptions(default_return=[{"show_all": False}, []])
    def update_nfc_filter_toggle(show_all, current_filter_data, grid_data, table_data, current_columns):
        """
        Callback que actualiza las columnas visibles según el filtro seleccionado.
        Esta versión mejorada detecta automáticamente todos los sensores con valores.
        
        Args:
            show_all: Booleano que indica si mostrar todos los sensores
            current_filter_data: Datos actuales del filtro
            grid_data: Datos de la cuadrícula
            table_data: Datos de la tabla
            current_columns: Columnas actuales
        
        Returns:
            Tupla con datos del filtro actualizados y columnas a mostrar
        """
        import re
        
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
        
        # Obtener todas las columnas de sensores existentes
        sensor_columns = [col for col in current_columns if col["id"].startswith("sensor_")]
        sensor_ids = [col["id"].replace("sensor_", "") for col in sensor_columns]
        logger.debug(f"Total de columnas de sensores existentes: {len(sensor_columns)} - IDs: {sensor_ids}")
        
        # MEJORADO: Detectar todos los sensores con valores reales
        sensors_with_values = set()
        
        # Detectar sensores con valores reales
        for row in table_data:
            for col in sensor_columns:
                cell_id = col["id"]
                if cell_id in row:
                    value = str(row[cell_id]).strip() if isinstance(row[cell_id], str) else row[cell_id]
                    # Verificar si el valor es significativo
                    # Consideramos que tiene valor solo si contiene el prefijo de formato "➤"
                    if value and "➤" in value:
                        sensor_id = cell_id.replace("sensor_", "")
                        sensors_with_values.add(sensor_id)
                        logger.debug(f"Detectado sensor {sensor_id} con valor: '{value}'")
                        
                    # Verificar específicamente formatos como MAC addresses
                    if isinstance(value, str) and (":" in value or "-" in value or "." in value):
                        sensor_id = cell_id.replace("sensor_", "")
                        sensors_with_values.add(sensor_id)
                        logger.debug(f"Detectado sensor {sensor_id} con formato especial: '{value}'")
                        
                    # Verificar formato hexadecimal
                    if isinstance(value, str) and re.match(r'^[0-9A-F]{8}$', value, re.IGNORECASE):
                        sensor_id = cell_id.replace("sensor_", "")
                        sensors_with_values.add(sensor_id)
                        logger.debug(f"Detectado sensor {sensor_id} con formato hexadecimal: '{value}'")
        
        logger.debug(f"Sensores con valores detectados: {len(sensors_with_values)} de {len(sensor_ids)}")
        
        if show_all:
            # Si el toggle está activado, mostrar todas las columnas
            display_columns = columns_base + sensor_columns
            logger.debug(f"Mostrando TODAS las columnas: {len(display_columns)} (base: {len(columns_base)}, sensores: {len(sensor_columns)})")
        else:
            # Si el toggle está desactivado, mostrar solo los sensores con valores detectados
            filtered_columns = [col for col in sensor_columns if col["id"].replace("sensor_", "") in sensors_with_values]
            display_columns = columns_base + filtered_columns
            logger.debug(f"Mostrando columnas con valores: {len(display_columns)} (base: {len(columns_base)}, sensores con valores: {len(filtered_columns)})")
        
        # Asegurarnos de que en la lista display_columns estén incluidas TODAS las columnas con valores
        # incluso si show_all=False (esto es para corregir el comportamiento anterior)
        if not show_all:
            # Verificar que todas las columnas con valores estén incluidas
            column_ids_in_display = {col["id"] for col in display_columns}
            for col in sensor_columns:
                if col["id"].replace("sensor_", "") in sensors_with_values and col["id"] not in column_ids_in_display:
                    display_columns.append(col)
                    logger.debug(f"Añadida columna {col['id']} que faltaba pero tiene valores")
        
        return {"show_all": show_all}, display_columns

    # Callback para manejar la actualización de dispositivos individuales
    @app.callback(
        Output("nfc-device-update-store", "data"),
        [Input("nfc-grid-table", "active_cell")],
        [State("nfc-grid-table", "data"),
         State("nfc-grid-table", "derived_virtual_data")],
        prevent_initial_call=True,
        id='handle_device_refresh_callback'  # Add a unique ID to this callback
    )
    @handle_exceptions(default_return={"device_id": None, "asset_id": None, "timestamp": None})
    def handle_device_refresh(active_cell, data, filtered_data):
        """
        Maneja los clics en la columna de acciones para actualizar dispositivos individuales.
        """
        if not active_cell:
            return dash.no_update
            
        # Verificar si se hizo clic en la columna "actions"
        column_id = active_cell.get('column_id')
        if column_id != 'actions':
            return dash.no_update
            
        # Obtener el índice de la fila
        row_index = active_cell.get('row')
        
        # Determinar si debemos usar los datos filtrados o los datos completos
        # (si la tabla tiene filtros aplicados, debemos usar derived_virtual_data)
        effective_data = filtered_data if filtered_data is not None else data
        
        # Verificar que el índice es válido
        if row_index is not None and row_index < len(effective_data):
            # Obtener la fila
            row = effective_data[row_index]
            
            # Extraer device_id y asset_id
            device_id = row.get('device_id')
            asset_id = row.get('asset_id')
            
            if device_id and asset_id:
                logger.info(f"Iniciando actualización para dispositivo {device_id} (asset_id={asset_id})")
                return {
                    "device_id": device_id,
                    "asset_id": asset_id,
                    "timestamp": datetime.now().timestamp()  # Para forzar la actualización
                }
        
        return dash.no_update
        
    # Hack para usar HTML en Dash DataTable (que normalmente no soporta HTML)
    # Esto renderiza los botones como HTML y les da funcionalidad
    @app.callback(
        Output("nfc-grid-container", "children", allow_duplicate=True),
        [Input("nfc-grid-table", "derived_virtual_data"),
         Input("nfc-grid-table", "derived_viewport_data")],
        [State("nfc-grid-container", "children")],
        prevent_initial_call=True,
        id='inject_html_buttons_callback'  # Add a unique ID to this callback too
    )
    @handle_exceptions(default_return=None)
    def inject_html_buttons(virtual_data, viewport_data, children):
        """
        Inyecta JavaScript para convertir cadenas HTML en elementos HTML reales.
        """
        if not virtual_data and not viewport_data:
            return dash.no_update
            
        # JavaScript para convertir cadenas HTML en botones reales
        # y para configurar los controladores de eventos
        js_code = """
        (function() {
            // Función para renderizar celdas HTML
            function renderHtmlCells() {
                const table = document.getElementById('nfc-grid-table');
                if (!table) return;
                
                // Buscar todas las celdas que contienen HTML
                const cells = table.querySelectorAll('td');
                cells.forEach(cell => {
                    const content = cell.textContent || '';
                    if (content.startsWith('<button') && content.includes('refresh-device-')) {
                        cell.innerHTML = content;
                        
                        // Configurar el botón para usar el evento click de la celda
                        const button = cell.querySelector('button');
                        if (button) {
                            // Reemplazar el comportamiento predeterminado del botón
                            button.addEventListener('click', function(e) {
                                // Evitar que se propague al hacer clic en el botón
                                e.stopPropagation();
                                
                                // En su lugar, simular un clic en la celda para activar el callback de Dash
                                const cellEvent = new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                });
                                cell.dispatchEvent(cellEvent);
                            });
                        }
                    }
                });
            }
            
            // Ejecutar después de que la tabla se actualice
            setTimeout(renderHtmlCells, 100);
            
            // También observar cambios en el DOM para detectar actualizaciones de tabla
            const observer = new MutationObserver(mutations => {
                mutations.forEach(mutation => {
                    if (mutation.type === 'childList' && mutation.target.id === 'nfc-grid-table') {
                        renderHtmlCells();
                    }
                });
            });
            
            // Iniciar observación de la tabla
            const targetNode = document.getElementById('nfc-grid-container');
            if (targetNode) {
                observer.observe(targetNode, { childList: true, subtree: true });
            }
        })();
        """
        
        # Crear componente JavaScript
        js_component = html.Script(js_code)
        
        # Si ya existe un componente children, añadir el JavaScript
        if children and isinstance(children, list):
            # Buscar si ya hay un script similar
            has_script = any(isinstance(child, html.Script) and "renderHtmlCells" in getattr(child, 'children', '') for child in children)
            
            if not has_script:
                children.append(js_component)
                return children
        elif children:
            # Si children no es una lista, envolverlo en una
            return [children, js_component]
        
        return dash.no_update
    
    # Callback para abrir el modal de asignación masiva
    @app.callback(
        Output("master-card-modal", "is_open"),
        [Input("master-card-assign-button", "n_clicks"),
         Input("master-card-cancel", "n_clicks"),
         Input("master-card-confirm", "n_clicks")],
        [State("master-card-modal", "is_open"),
         State("nfc-grid-table", "derived_virtual_selected_rows"),
         State("nfc-grid-table", "derived_virtual_data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=False)
    def toggle_master_card_modal(assign_clicks, cancel_clicks, confirm_clicks, is_open, selected_rows, table_data):
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        # Si se hace clic en el botón de asignar
        if triggered_id == "master-card-assign-button":
            # Verificar si hay cerraduras seleccionadas
            if not selected_rows or len(selected_rows) == 0:
                return False  # No abrir modal si no hay selección
            return True
        
        # Si se hace clic en cancelar o confirmar, cerrar el modal
        elif triggered_id in ["master-card-cancel", "master-card-confirm"]:
            return False
        
        return is_open
    
    # Callback para mostrar las cerraduras seleccionadas en el modal
    @app.callback(
        Output("master-card-selected-locks", "children"),
        [Input("master-card-modal", "is_open")],
        [State("nfc-grid-table", "derived_virtual_selected_rows"),
         State("nfc-grid-table", "derived_virtual_data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=html.Div("No hay cerraduras seleccionadas"))
    def update_selected_locks_display(is_open, selected_rows, table_data):
        if not is_open or not selected_rows or not table_data:
            return html.Div("No hay cerraduras seleccionadas")
        
        # Extraer los datos de las cerraduras seleccionadas
        selected_devices = []
        for idx in selected_rows:
            if idx < len(table_data):
                device = table_data[idx]
                device_name = device.get("device_id", "")
                lock_name = device.get("lock_name", "")
                asset_name = device.get("asset_name", "")
                
                selected_devices.append({
                    "device_id": device.get("real_device_id", ""),
                    "gateway_id": device.get("gateway_id", ""),
                    "display_name": f"{device_name} - {lock_name} ({asset_name})"
                })
        
        # Crear lista con las cerraduras seleccionadas
        if not selected_devices:
            return html.Div("No hay cerraduras seleccionadas")
        
        # Si hay muchas cerraduras, mostrar solo algunas y un contador
        max_display = 5
        locks_list = []
        
        for i, device in enumerate(selected_devices):
            if i < max_display:
                locks_list.append(
                    html.Li(device["display_name"], className="mb-1")
                )
            
        # Si hay más cerraduras que el máximo a mostrar
        if len(selected_devices) > max_display:
            locks_list.append(
                html.Li(f"+ {len(selected_devices) - max_display} cerraduras más...", 
                       className="text-muted fst-italic")
            )
        
        # Almacenar en un Store para uso posterior
        selection_display = html.Div([
            html.Ul(locks_list, className="ps-4"),
            html.Div(f"Total: {len(selected_devices)} cerraduras seleccionadas", 
                    className="alert alert-info py-2 mt-2"),
            dcc.Store(id="master-card-selected-devices", 
                     data={"devices": selected_devices})
        ])
        
        return selection_display
    
    # Callback para mostrar las cerraduras seleccionadas en el modal de desasignación
    @app.callback(
        Output("unassign-card-selected-locks", "children"),
        [Input("unassign-card-modal", "is_open")],
        [State("nfc-grid-table", "derived_virtual_selected_rows"),
         State("nfc-grid-table", "derived_virtual_data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=html.Div("No hay cerraduras seleccionadas"))
    def update_unassign_selected_locks_display(is_open, selected_rows, table_data):
        if not is_open or not selected_rows or not table_data:
            return html.Div("No hay cerraduras seleccionadas")
        
        # Extraer los datos de las cerraduras seleccionadas
        selected_devices = []
        for idx in selected_rows:
            if idx < len(table_data):
                device = table_data[idx]
                device_name = device.get("device_id", "")
                lock_name = device.get("lock_name", "")
                asset_name = device.get("asset_name", "")
                
                selected_devices.append({
                    "device_id": device.get("real_device_id", ""),
                    "gateway_id": device.get("gateway_id", ""),
                    "display_name": f"{device_name} - {lock_name} ({asset_name})"
                })
        
        # Crear lista con las cerraduras seleccionadas
        if not selected_devices:
            return html.Div("No hay cerraduras seleccionadas")
        
        # Si hay muchas cerraduras, mostrar solo algunas y un contador
        max_display = 5
        locks_list = []
        
        for i, device in enumerate(selected_devices):
            if i < max_display:
                locks_list.append(
                    html.Li(device["display_name"], className="mb-1")
                )
            
        # Si hay más cerraduras que el máximo a mostrar
        if len(selected_devices) > max_display:
            locks_list.append(
                html.Li(f"+ {len(selected_devices) - max_display} cerraduras más...", 
                       className="text-muted fst-italic")
            )
        
        # Almacenar en un Store para uso posterior
        selection_display = html.Div([
            html.Ul(locks_list, className="ps-4"),
            html.Div(f"Total: {len(selected_devices)} cerraduras seleccionadas", 
                    className="alert alert-info py-2 mt-2"),
            dcc.Store(id="unassign-card-selected-devices", 
                     data={"devices": selected_devices})
        ])
        
        return selection_display
    
    # Callback para la validación del UUID
    @app.callback(
        [Output("master-card-uuid-input", "valid"),
         Output("master-card-uuid-input", "invalid"),
         Output("master-card-feedback", "children")],
        [Input("master-card-uuid-input", "value")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[False, False, html.Div()])
    def validate_uuid_input(uuid_value):
        if not uuid_value or len(uuid_value.strip()) == 0:
            return False, False, html.Div()
        
        # Patrones aceptados para UUID de tarjeta NFC
        # 1. Formato estándar: AA:BB:CC:DD
        # 2. Formato sin separadores: AABBCCDD
        # 3. Formato con guiones: AA-BB-CC-DD
        import re
        
        # Limpiar espacios
        uuid_value = uuid_value.strip()
        
        # Patrón para formato AA:BB:CC:DD o AA-BB-CC-DD
        pattern1 = r'^([0-9A-F]{2}[:\-]){3}[0-9A-F]{2}$'
        
        # Patrón para formato AABBCCDD
        pattern2 = r'^[0-9A-F]{8}$'
        
        if re.match(pattern1, uuid_value, re.IGNORECASE) or re.match(pattern2, uuid_value, re.IGNORECASE):
            return True, False, html.Div(
                "Formato de UUID válido",
                className="text-success"
            )
        else:
            return False, True, html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "Formato de UUID no válido. Use el formato AA:BB:CC:DD o AABBCCDD."
            ], className="alert alert-danger py-2")
    
    # Función para actualizar una cerradura individual
    def update_master_card_for_lock(device, uuid_value, jwt_token):
        """
        Actualiza el UUID de la tarjeta maestra para una cerradura específica.
        
        Args:
            device: Diccionario con datos de la cerradura
            uuid_value: UUID de la tarjeta NFC
            jwt_token: Token JWT para autenticación
            
        Returns:
            Tupla (success, message) con el resultado de la operación
        """
        device_id = device.get("device_id")
        # MODIFICADO: No usar device_id como fallback para gateway_id
        gateway_id = device.get("gateway_id")
        
        if not device_id:
            logger.error(f"Falta device_id en la actualización de tarjeta maestra")
            return False, "Falta ID del dispositivo"
        
        # Caso especial para el dispositivo problemático ID 127
        if device_id == "127" and not gateway_id:
            gateway_id = "1000000053eb1d68"
            logger.info(f"Asignando gateway_id específico para el dispositivo 127: {gateway_id}")
        
        # Verificar si tenemos un gateway_id válido
        if not gateway_id:
            logger.error(f"No se encontró gateway_id para el dispositivo {device_id}")
            return False, f"Error: Falta gateway_id para el dispositivo {device_id}"
        
        # Slot 7 para tarjeta maestra
        slot_number = "7"
        
        try:
            # Asegurar formato correcto
            if ":" not in uuid_value and "-" not in uuid_value and len(uuid_value) == 8:
                # Convertir AABBCCDD a AA:BB:CC:DD
                uuid_formatted = ":".join([uuid_value[i:i+2] for i in range(0, len(uuid_value), 2)])
            else:
                uuid_formatted = uuid_value
                
            # Llamar a la API para actualizar el código NFC
            from utils.api import update_nfc_code_value
            
            # Registrar la llamada para diagnóstico
            logger.info(f"Actualizando tarjeta maestra para dispositivo {device_id}, gateway {gateway_id}, UUID: {uuid_formatted}")
            
            success, response = update_nfc_code_value(
                asset_id=None,  # No se requiere para este endpoint
                device_id=device_id, 
                sensor_id=slot_number,  # Usamos el slot 7 para tarjeta maestra
                new_value=uuid_formatted, 
                jwt_token=jwt_token,
                gateway_id=gateway_id,
                is_master_card=True  # Indicador adicional para la función
            )
            
            if success:
                return True, "Actualizado correctamente"
            else:
                # Manejar respuesta según su tipo
                if isinstance(response, dict):
                    error_msg = response.get("error", "Error desconocido")
                    return False, f"Error: {error_msg}"
                elif "503" in str(response):
                    # Manejar específicamente el error 503 Service Unavailable
                    logger.error(f"Error 503 (Servicio no disponible) al actualizar tarjeta maestra para {device_id}")
                    return False, "Error: Servicio no disponible. Intente más tarde."
                elif "404" in str(response):
                    # Manejar específicamente el error 404 Not Found (posible problema de gateway_id)
                    logger.error(f"Error 404 (No encontrado) al actualizar tarjeta maestra para {device_id}. URL posiblemente incorrecta con gateway_id: {gateway_id}")
                    return False, "Error: Dispositivo o endpoint no encontrado. Verifique el gateway_id."
                else:
                    # Si es una cadena u otro tipo, usarla directamente
                    return False, f"Error: {response}"
                
        except Exception as e:
            logger.error(f"Error actualizando tarjeta maestra: {str(e)}")
            return False, f"Error: {str(e)}"
    
    # Función para desasignar una tarjeta maestra de una cerradura individual
    def unassign_master_card_for_lock(device, jwt_token):
        """
        Desasigna la tarjeta maestra para una cerradura específica.
        
        Args:
            device: Diccionario con datos de la cerradura
            jwt_token: Token JWT para autenticación
            
        Returns:
            Tupla (success, message) con el resultado de la operación
        """
        device_id = device.get("device_id")
        # No usar device_id como fallback para gateway_id
        gateway_id = device.get("gateway_id")
        
        if not device_id:
            logger.error(f"Falta device_id en la desasignación de tarjeta maestra")
            return False, "Falta ID del dispositivo"
        
        # Caso especial para el dispositivo problemático ID 127
        if device_id == "127" and not gateway_id:
            gateway_id = "1000000053eb1d68"
            logger.info(f"Asignando gateway_id específico para el dispositivo 127: {gateway_id}")
        
        # Verificar si tenemos un gateway_id válido
        if not gateway_id:
            logger.error(f"No se encontró gateway_id para el dispositivo {device_id}")
            return False, f"Error: Falta gateway_id para el dispositivo {device_id}"
        
        # Slot 7 para tarjeta maestra
        slot_number = "7"
        
        try:
            # Llamar a la API para desasignar el código NFC (valor vacío)
            from utils.api import update_nfc_code_value
            
            # Registrar la llamada para diagnóstico
            logger.info(f"Desasignando tarjeta maestra para dispositivo {device_id}, gateway {gateway_id}")
            
            # Enviar una cadena vacía como valor para desasignar
            success, response = update_nfc_code_value(
                asset_id=None,  # No se requiere para este endpoint
                device_id=device_id, 
                sensor_id=slot_number,
                new_value="",  # Valor vacío para desasignar
                jwt_token=jwt_token,
                gateway_id=gateway_id,
                is_master_card=True
            )
            
            if success:
                return True, "Desasignado correctamente"
            else:
                # Manejar respuesta según su tipo
                if isinstance(response, dict):
                    error_msg = response.get("error", "Error desconocido")
                    return False, f"Error: {error_msg}"
                elif "503" in str(response):
                    # Manejar específicamente el error 503 Service Unavailable
                    logger.error(f"Error 503 (Servicio no disponible) al desasignar tarjeta maestra para {device_id}")
                    return False, "Error: Servicio no disponible. Intente más tarde."
                elif "404" in str(response):
                    # Manejar específicamente el error 404 Not Found (posible problema de gateway_id)
                    logger.error(f"Error 404 (No encontrado) al desasignar tarjeta maestra para {device_id}. URL posiblemente incorrecta con gateway_id: {gateway_id}")
                    return False, "Error: Dispositivo o endpoint no encontrado. Verifique el gateway_id."
                else:
                    # Si es una cadena u otro tipo, usarla directamente
                    return False, f"Error: {response}"
                
        except Exception as e:
            logger.error(f"Error desasignando tarjeta maestra: {str(e)}")
            return False, f"Error: {str(e)}"
    
    # Callback para asignar la tarjeta maestra a múltiples cerraduras
    @app.callback(
        Output("unassign-card-modal", "is_open"),
        [Input("master-card-unassign-button", "n_clicks"),
         Input("unassign-card-cancel", "n_clicks"),
         Input("unassign-card-confirm", "n_clicks")],
        [State("unassign-card-modal", "is_open"),
         State("nfc-grid-table", "derived_virtual_selected_rows"),
         State("nfc-grid-table", "derived_virtual_data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=False)
    def toggle_unassign_card_modal(unassign_clicks, cancel_clicks, confirm_clicks, is_open, selected_rows, table_data):
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        # Si se hace clic en el botón de desasignar
        if triggered_id == "master-card-unassign-button":
            # Verificar si hay cerraduras seleccionadas
            if not selected_rows or len(selected_rows) == 0:
                return False  # No abrir modal si no hay selección
            return True
        
        # Si se hace clic en cancelar o confirmar, cerrar el modal
        elif triggered_id in ["unassign-card-cancel", "unassign-card-confirm"]:
            return False
        
        return is_open
    
    # Callback para el botón de pegar desde portapapeles
    app.clientside_callback(
        """
        function(n_clicks) {
            if (!n_clicks) return window.dash_clientside.no_update;
            
            return new Promise((resolve, reject) => {
                navigator.clipboard.readText()
                    .then(text => {
                        resolve(text.trim());
                    })
                    .catch(err => {
                        console.error('No se pudo leer del portapapeles:', err);
                        resolve(window.dash_clientside.no_update);
                    });
            });
        }
        """,
        Output("master-card-uuid-input", "value"),
        Input("master-card-paste-button", "n_clicks"),
        prevent_initial_call=True
    )

    # Callback para desasignar la tarjeta maestra de múltiples cerraduras
    @app.callback(
        [Output("unassign-card-results-container", "children"),
         Output("unassign-card-results-container", "style"),
         Output("unassign-card-confirm", "disabled"),
         Output("unassign-card-loading", "children"),
         Output("nfc-update-trigger", "data", allow_duplicate=True)],
        [Input("unassign-card-confirm", "n_clicks")],
        [State("unassign-card-selected-devices", "data"),
         State("jwt-token-store", "data"),
         State("nfc-update-trigger", "data")],
        prevent_initial_call=True,
        id='unassign_master_card_callback'  # Add a unique ID to the callback
    )
    @handle_exceptions(default_return=[None, {"display": "none"}, False, "", dash.no_update])
    def unassign_master_card(confirm_clicks, selected_devices_data, token_data, current_trigger_data):
        # Si no hay confirmación, no hacer nada
        if not confirm_clicks:
            return None, {"display": "none"}, False, "", dash.no_update
        
        # Obtener el token JWT
        token = token_data.get('token') if token_data else None
        if not token:
            return html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "No hay autenticación disponible para actualizar los códigos"
            ], className="alert alert-danger"), {"display": "block"}, True, "", dash.no_update
        
        # Obtener los dispositivos seleccionados
        if not selected_devices_data or "devices" not in selected_devices_data:
            return html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "No hay cerraduras seleccionadas para desasignar tarjeta maestra"
            ], className="alert alert-warning"), {"display": "block"}, True, "", dash.no_update
        
        selected_devices = selected_devices_data.get("devices", [])
        if not selected_devices:
            return html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "No hay cerraduras seleccionadas para desasignar tarjeta maestra"
            ], className="alert alert-warning"), {"display": "block"}, True, "", dash.no_update
        
        # Indicador de carga
        loading_indicator = html.Div(
            f"Procesando {len(selected_devices)} cerraduras...",
            className="text-info"
        )
        
        # Procesar cada dispositivo en paralelo
        results = []
        successful = 0
        failed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Crear un futuro para cada dispositivo
            future_to_device = {
                executor.submit(
                    unassign_master_card_for_lock, 
                    device, 
                    token
                ): device for device in selected_devices
            }
            
            # Procesar los resultados a medida que se completan
            for future in concurrent.futures.as_completed(future_to_device):
                device = future_to_device[future]
                device_name = device.get("display_name", "Cerradura sin nombre")
                
                try:
                    success, message = future.result()
                    
                    if success:
                        successful += 1
                        status_class = "text-success"
                        icon_class = "fas fa-check-circle"
                    else:
                        failed += 1
                        status_class = "text-danger"
                        icon_class = "fas fa-times-circle"
                    
                    results.append({
                        "device": device_name,
                        "success": success,
                        "message": message,
                        "status_class": status_class,
                        "icon_class": icon_class
                    })
                    
                except Exception as e:
                    failed += 1
                    results.append({
                        "device": device_name,
                        "success": False,
                        "message": f"Error: {str(e)}",
                        "status_class": "text-danger",
                        "icon_class": "fas fa-times-circle"
                    })
        
        # Crear mensaje de éxito o error
        if successful > 0:
            success_message = html.Div([
                html.I(className="fas fa-check-circle me-2", style={"color": "green"}),
                f"Se desasignaron {successful} cerraduras correctamente."
            ], className="alert alert-success")
        else:
            error_message = html.Div([
                html.I(className="fas fa-exclamation-circle me-2", style={"color": "red"}),
                f"No se pudieron desasignar {failed} cerraduras."
            ], className="alert alert-danger")
        
        # Ordenar resultados: primero los fallos, después los éxitos
        results = sorted(results, key=lambda x: x["success"])
        
        # Crear la tabla de resultados
        result_rows = []
        for result in results:
            result_rows.append(
                html.Tr([
                    html.Td(html.I(className=result["icon_class"]), className=result["status_class"]),
                    html.Td(result["device"]),
                    html.Td(result["message"], className=result["status_class"])
                ])
            )
        
        # Encabezado de resultados
        result_header = html.Div([
            html.H5("Resultados de la Desasignación", className="mb-3"),
            html.Div([
                html.Span(f"Exitosos: ", className="fw-bold me-1"),
                html.Span(f"{successful} de {len(selected_devices)}", className="text-success me-3"),
                html.Span(f"Fallidos: ", className="fw-bold me-1"),
                html.Span(f"{failed}", className="text-danger")
            ], className="mb-3")
        ])
        
        # Tabla de resultados
        results_table = html.Table([
            html.Thead([
                html.Tr([
                    html.Th(""),
                    html.Th("Cerradura"),
                    html.Th("Resultado")
                ])
            ]),
            html.Tbody(result_rows)
        ], className="table table-striped")
        
        # Mensaje final
        if failed == 0:
            final_message = html.Div([
                html.I(className="fas fa-check-circle me-2"),
                f"Tarjeta maestra desasignada correctamente de todas las cerraduras ({successful})"
            ], className="alert alert-success mt-3")
        else:
            final_message = html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"La desasignación falló en {failed} cerraduras. Revise los detalles para más información."
            ], className="alert alert-warning mt-3")
        
        # Contenedor final de resultados
        results_container = html.Div([
            result_header,
            results_table,
            final_message
        ])
        
        # Crear trigger para actualizar la tabla después de la desasignación
        # Incrementar el contador para forzar la actualización
        current_count = current_trigger_data.get("count", 0) if current_trigger_data else 0
        updated_trigger = {"updated": True, "count": current_count + 1, "refreshed": True}
        
        return results_container, {"display": "block"}, True, loading_indicator, updated_trigger
