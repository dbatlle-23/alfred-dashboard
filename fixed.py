from dash import html, dcc, callback_context
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
from components.smart_locks.lock_list import create_locks_list
from components.smart_locks.lock_table import create_locks_table
from components.smart_locks.nfc_grid import create_nfc_display_grid, create_lock_type_grid
from utils.logging import get_logger
from utils.error_handlers import handle_exceptions
from utils.api import get_devices, get_nfc_passwords, update_nfc_code_value, get_project_assets, get_asset_devices
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import re

logger = get_logger(__name__)

# Layout para la página de Smart Locks
layout = html.Div([
    # Stores para datos
    dcc.Store(id="smart-locks-data-store"),
    dcc.Store(id="smart-locks-refresh-trigger"),
    dcc.Store(id="smart-locks-view-preference", data={"view": "table"}),  # Default a vista de tabla
    dcc.Store(id="nfc-update-trigger", data={"updated": False}),  # Trigger para actualizar valores NFC
    dcc.Store(id="current-device-store", data=None),  # Almacena información del dispositivo actual
    
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
        dcc.Interval(id="nfc-edit-success-timer", interval=2000, n_intervals=0, max_intervals=1, disabled=True)
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
        prevent_initial_call=True
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
        prevent_initial_call=True
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
        prevent_initial_call=True
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
        prevent_initial_call=True
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
        prevent_initial_call=True
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
        ctx = callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        # Si la pestaña no es la de matriz, devolver un contenedor vacío
        if active_tab != "nfc-grid-tab":
            return html.Div()
        
        # Si no hay datos, mostrar mensaje informativo
        if not devices_data:
            return html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "Seleccione un proyecto y haga clic en 'Mostrar Cerraduras' para ver la matriz."
            ], className="alert alert-info")
        
        # Preprocesar las cerraduras para añadir información específica de NFC si está disponible
        # Este paso ayuda a que el grid detecte correctamente los sensores NFC
        processed_devices = []
        nfc_sensor_count = 0
        devices_with_nfc = 0
        
        for device in devices_data:
            # Crear una copia para no modificar los datos originales
            processed_device = device.copy()
            device_has_nfc = False
            
            # Verificar si tiene asset_id para poder cargar códigos NFC
            asset_id = processed_device.get("asset_id")
            if asset_id:
                # Buscar sensores NFC existentes primero
                for sensor in processed_device.get("sensors", []):
                    if sensor and sensor.get("sensor_type") == "NFC_CODE":
                        # Este es un sensor NFC explícito
                        sensor["is_potential_nfc"] = True
                        nfc_sensor_count += 1
                        device_has_nfc = True
                        # Añadir el valor NFC si existe
                        password = sensor.get("password", "")
                        nfc_password = sensor.get("nfc_password", "")
                        nfc_code = sensor.get("nfc_code", "")
                        if password or nfc_password or nfc_code:
                            sensor["nfc_value"] = password or nfc_password or nfc_code
                
                # Si no se encontraron sensores NFC, buscar potenciales sensores que podrían ser NFC
                if not device_has_nfc:
                    # Marcar sensores que pueden ser NFC
                    for sensor in processed_device.get("sensors", []):
                        if sensor and (
                            "NFC" in str(sensor.get("name", "")).upper() or
                            "CODE" in str(sensor.get("name", "")).upper() or
                            "CÓDIGO" in str(sensor.get("name", "")).upper() or
                            "TARJETA" in str(sensor.get("name", "")).upper() or
                            "CARD" in str(sensor.get("name", "")).upper()
                        ):
                            # Añadir una marca para que se detecte como NFC potencial
                            sensor["is_potential_nfc"] = True
                            nfc_sensor_count += 1
                            device_has_nfc = True
                            
                            # Intentar extraer información de código NFC si existe
                            password = sensor.get("password", "")
                            nfc_password = sensor.get("nfc_password", "")
                            nfc_code = sensor.get("nfc_code", "")
                            
                            # Si hay un código disponible, guardarlo para mostrar inmediatamente
                            if password or nfc_password or nfc_code:
                                sensor["nfc_value"] = password or nfc_password or nfc_code
                
                # Si aún no hay sensors NFC detectados, y el dispositivo es una cerradura,
                # crearemos "sensores virtuales" para ser rellenados desde la API
                if not device_has_nfc:
                    # Verificar si es una cerradura
                    is_lock = False
                    for sensor in processed_device.get("sensors", []):
                        if sensor and sensor.get("sensor_type") == "LOCK":
                            is_lock = True
                            break
                    
                    # Comentamos la creación de sensores virtuales
                    """
                    # Si es una cerradura, añadir sensores virtuales
                    if is_lock:
                        # Si no hay sensores, inicializar la lista
                        if "sensors" not in processed_device or not processed_device["sensors"]:
                            processed_device["sensors"] = []
                        
                        # Crear un sensor NFC virtual
                        virtual_sensor = {
                            "sensor_id": f"virtual_nfc_{processed_device.get('device_id', '')}",
                            "sensor_type": "NFC_CODE",
                            "name": "Código NFC Virtual",
                            "is_potential_nfc": True,
                            "is_virtual": True
                        }
                        
                        # Añadir el sensor virtual a la lista de sensores
                        processed_device["sensors"].append(virtual_sensor)
                        nfc_sensor_count += 1
                        device_has_nfc = True
                        logger.debug(f"Añadido sensor NFC virtual para dispositivo {processed_device.get('device_id', '')}")
                    """
            
            if device_has_nfc:
                devices_with_nfc += 1
            
            processed_devices.append(processed_device)
        
        # Contenedor para la matriz NFC
        nfc_grid = create_nfc_display_grid(filtered_locks=processed_devices, is_loading_locks=False, show_all_sensors=True)
        
        # Añadir información sobre la detección de sensores NFC
        info_section = html.Div([
            html.H4("Matriz de Códigos NFC", className="mb-3"),
            html.Div([
                html.P([
                    html.I(className="fas fa-info-circle me-2"),
                    html.Span([
                        "Esta vista muestra todos los códigos NFC asignados a las cerraduras. ",
                        "Los códigos se cargan automáticamente desde la API y pueden ser editados. ",
                        "Para editar un código, primero debe cargar la tabla y luego hacer clic en la celda correspondiente."
                    ])
                ], className="alert alert-info"),
                html.Div([
                    html.Strong(f"Dispositivos con NFC detectados: {devices_with_nfc}"),
                    html.Span(f" | Total de sensores NFC: {nfc_sensor_count}", className="ms-3"),
                ], className="mb-3 p-2 bg-light rounded border")
            ])
        ])
        
        # Añadir botón para refrescar datos NFC
        refresh_button = html.Div([
            dbc.Button([
                html.I(className="fas fa-sync-alt me-2"),
                "Actualizar Códigos NFC"
            ], id="nfc-refresh-button", color="primary", className="mb-3")
        ])
        
        # Crear un contenedor con toda la información
        return html.Div([
            info_section,
            refresh_button,
            nfc_grid
        ], className="nfc-grid-view mt-4")
    
    # Callback para actualizar los datos NFC cuando se hace clic en el botón de refrescar
    @app.callback(
        Output("nfc-update-trigger", "data", allow_duplicate=True),
        [Input("nfc-refresh-button", "n_clicks")],
        [State("nfc-update-trigger", "data")],
        prevent_initial_call=True
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
        prevent_initial_call=True
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
         Output("nfc-grid-table", "columns", allow_duplicate=True),
         Output("nfc-grid-loading-indicator", "children", allow_duplicate=True),
         Output("nfc-grid-error-container", "children", allow_duplicate=True)],
        [Input("nfc-grid-data-store", "data"),
         Input("nfc-update-trigger", "data")],
        [State("nfc-grid-table", "data"),
         State("nfc-grid-table", "columns"),
         State("jwt-token-store", "data"),
         State("nfc-grid-filter-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[[], [], "", html.Div("Error al cargar datos NFC", className="alert alert-danger")])
    def load_nfc_grid_data(grid_data, update_trigger, current_table_data, current_columns, token_data, filter_data):
        # Verificar que haya datos válidos
        if not grid_data or not current_table_data or not current_columns:
            return current_table_data, current_columns, "", ""
        
        # Verificar autenticación
        token = token_data.get('token') if token_data else None
        if not token:
            return current_table_data, current_columns, "", html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "No se pudo autenticar para obtener códigos NFC."
            ], className="alert alert-warning")
        
        # Obtener los asset_ids únicos para consultar
        asset_ids = grid_data.get("asset_ids", [])
        sensor_ids = grid_data.get("sensor_ids", [])
        if not asset_ids:
            return current_table_data, current_columns, "", html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "No se encontraron espacios (assets) para consultar códigos NFC."
            ], className="alert alert-info")
        
        logger.info(f"Iniciando carga de códigos NFC para {len(asset_ids)} espacios y {len(sensor_ids)} sensores")

        # Iniciar proceso de carga
        loading_indicator = html.Div(f"Cargando códigos NFC para {len(asset_ids)} espacios...", className="text-info")
        
        # Hacer una copia de los datos actuales para no modificar el original
        updated_data = current_table_data.copy() if current_table_data else []
        updated_columns = current_columns.copy() if current_columns else []
        
        # Crear un mapa columna_id -> índice para acceso rápido
        column_id_to_index = {col['id']: i for i, col in enumerate(updated_columns)}
        # Crear un mapa de device_id a índice en la tabla para actualización eficiente
        device_to_index = {row["device_id"]: i for i, row in enumerate(updated_data)}
        
        # Nuevos sensores encontrados (sensor_id -> info)
        new_sensors = {}
        
        # Crear un ThreadPoolExecutor para realizar múltiples solicitudes en paralelo
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Enviar solicitudes para cada asset_id
            futures = [executor.submit(fetch_nfc_passwords_for_asset, asset_id, token) for asset_id in asset_ids]
            
            # Recopilar los resultados
            results = []
            errors = []
            try:
                # Esperar a que todas las solicitudes terminen
                for future in concurrent.futures.as_completed(futures):
                    try:
                        asset_id, data = future.result()
                        if data:
                            results.append((asset_id, data))
                            else:
                            logger.warning(f"No se obtuvieron datos NFC para asset_id: {asset_id}")
                        except Exception as e:
                        errors.append(str(e))
                        logger.error(f"Error al obtener datos NFC: {str(e)}")
            except Exception as e:
                errors.append(str(e))
                logger.error(f"Error en la ejecución de solicitudes paralelas: {str(e)}")
        
        # Si hay errores, mostrarlos
        if errors:
            error_text = f"Se produjeron {len(errors)} errores al obtener datos NFC"
            error_container = html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                error_text
            ], className="alert alert-warning")
            
            if not results:
                return updated_data, updated_columns, "", error_container
        else:
            error_container = ""
            
        # Si no hay resultados después de las solicitudes, mostrar mensaje
        if not results:
            return updated_data, updated_columns, "", html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "No se encontraron datos NFC para los espacios seleccionados."
            ], className="alert alert-info")
            
        # Procesar los resultados
        logger.info(f"Procesando resultados NFC de {len(results)} assets")
        nfc_sensors_found = 0
        total_nfc_codes = 0
        
        # Procesar cada respuesta de asset
        for asset_id, nfc_data in results:
            if not nfc_data or not isinstance(nfc_data, dict) or 'data' not in nfc_data:
                logger.warning(f"Formato de datos inválido para asset_id {asset_id}")
                continue
                
            data_section = nfc_data['data']
            
            # Obtener los dispositivos según el formato de la respuesta
            devices = []
            
            # CASO 1: data.devices es una lista de dispositivos
            if isinstance(data_section, dict) and 'devices' in data_section and isinstance(data_section['devices'], list):
                devices = data_section['devices']
                logger.debug(f"Encontrados {len(devices)} dispositivos en data.devices para asset {asset_id}")
                
            # CASO 2: data es directamente una lista de dispositivos
            elif isinstance(data_section, list):
                devices = data_section
                logger.debug(f"Encontrados {len(devices)} dispositivos en data para asset {asset_id}")
                
            # CASO 3: data es un único dispositivo
            elif isinstance(data_section, dict) and 'device_id' in data_section:
                devices = [data_section]
                logger.debug(f"Encontrado un único dispositivo en data para asset {asset_id}")
                
            # Si no hay dispositivos, continuar con el siguiente asset
            if not devices:
                logger.warning(f"No se encontraron dispositivos para asset_id {asset_id}")
                continue
                
            logger.debug(f"Procesando {len(devices)} dispositivos para asset_id {asset_id}")
                    
            # Mapeo para mayor claridad de los dispositivos encontrados
            device_names = [device.get('device_name', 'Sin nombre') for device in devices]
            logger.info(f"Dispositivos encontrados en asset {asset_id}: {', '.join(device_names)}")
            
            # Procesar cada dispositivo
            for device in devices:
                device_id = device.get('device_id')
                if not device_id:
                    logger.warning(f"Dispositivo sin device_id en asset {asset_id}")
                    continue
                
                device_name = device.get('device_name', 'Sin nombre')
                logger.info(f"Procesando dispositivo {device_id} ({device_name}) en asset {asset_id}")
                    
                # Verificar si este dispositivo está en nuestra tabla
                row_index = device_to_index.get(device_id)
                if row_index is None:
                    logger.warning(f"Dispositivo {device_id} no encontrado en la tabla")
                    continue
                
                # Obtener sensor_passwords del dispositivo
                sensor_passwords = device.get('sensor_passwords', [])
                if not isinstance(sensor_passwords, list):
                    logger.warning(f"sensor_passwords no es una lista para dispositivo {device_id}")
                    continue
                
                logger.info(f"Procesando {len(sensor_passwords)} sensores para dispositivo {device_id}")
                
                # Registrar todos los sensor_ids encontrados y sus valores
                sensor_ids_found = [str(s.get('sensor_id', '')) for s in sensor_passwords if 'sensor_id' in s]
                logger.info(f"Sensor IDs encontrados para dispositivo {device_id}: {', '.join(sensor_ids_found)}")
                
                # Actualizar los valores de sensor en la fila
                for sensor_pw in sensor_passwords:
                    if not isinstance(sensor_pw, dict):
                        continue
                    
                    sensor_id = sensor_pw.get('sensor_id')
                    sensor_name = sensor_pw.get('name', f"Sensor {sensor_id}")
                    if not sensor_id:
                        continue
                    
                    # Verificar si este sensor_id está en nuestras columnas
                    cell_id = f"sensor_{sensor_id}"
                    password_value = sensor_pw.get('password', '')
                    
                    # Siempre registrar todos los sensores/valores en el log para depuración
                    logger.debug(f"Sensor {sensor_id} en dispositivo {device_id}: valor='{password_value}', tipo={type(password_value)}")
                    
                    # DEPURACIÓN ESPECIAL para sensores importantes
                    if sensor_id in ['2', '8', '9', '10']:
                        logger.info(f"[SENSOR IMPORTANTE] Sensor {sensor_id} en dispositivo {device_id}: valor='{password_value}'")
                    
                    # Si la columna existe, actualizar el valor
                    if cell_id in updated_data[row_index]:
                        # Registro especial para sensores con valores detectados
                        if password_value:
                            logger.info(f"Actualizando celda {cell_id} para dispositivo {device_id} con valor '{password_value}'")
                            updated_data[row_index][cell_id] = password_value
                            nfc_sensors_found += 1
                            total_nfc_codes += 1
                            else:
                            # Si no hay valor, indicar que no está asignado
                            updated_data[row_index][cell_id] = "No asignado"
                            logger.debug(f"Sensor {sensor_id} de dispositivo {device_id} no tiene valor asignado")
                        else:
                        # Este sensor no estaba en las columnas originales
                        # Verificar si ya existe en new_sensors para no duplicar
                        if sensor_id not in new_sensors:
                            # Guardar info del sensor para crear nueva columna
                            new_sensors[sensor_id] = {
                                "sensor_id": sensor_id,
                                "name": sensor_name,
                                "sensor_type": sensor_pw.get("sensor_type", "NFC_CODE"),
                            }
                            logger.info(f"Añadida nueva columna para sensor {sensor_id}: 🔑 {sensor_name} ({sensor_pw.get('sensor_type', 'NFC_CODE')})")
                            
                            # Añadir columna a todas las filas
                        for i, row in enumerate(updated_data):
                                if i == row_index and password_value:
                                    # Si es la fila actual y hay valor, usar el password obtenido
                                    row[cell_id] = password_value
                                    logger.info(f"Asignado valor '{password_value}' a nueva columna {cell_id} para dispositivo {device_id}")
                                elif i == row_index:
                                    # Si es la fila actual pero no hay valor
                                    row[cell_id] = "No asignado"
                                else:
                                    # Para otras filas, marcar como N/A
                                row[cell_id] = "N/A"
        
                            # Crear nueva columna en la definición de columnas
                            column_name = f"🔑 {sensor_name} ({sensor_pw.get('sensor_type', 'NFC_CODE')})"
                            updated_columns.append({
                                "name": column_name,
                                "id": cell_id
                            })
                
        # Si se encontraron nuevos sensores, ajustar el orden de las columnas para que los nuevos sensores estén juntos con los demás
        if new_sensors:
            # Separar columnas base y columnas de sensores
            base_columns = [col for col in updated_columns if not col["id"].startswith("sensor_")]
            sensor_columns = [col for col in updated_columns if col["id"].startswith("sensor_")]
            
            # Ordenar las columnas de sensores por ID numérico
            sensor_columns.sort(key=lambda col: int(col["id"].replace("sensor_", "")))
            
            # Recombinar columnas
            updated_columns = base_columns + sensor_columns
            
            # Actualizar el filter_store para incluir los nuevos sensores
            if filter_data and "show_all" in filter_data:
                # Si el filtro es "mostrar todo", aplicar solo base_columns + filtered_columns
                show_all = filter_data["show_all"]
                if not show_all:
                    # Solo aplicar filtro si hay datos en la tabla
                    if updated_data:
                        # Detectar sensores con valores asignados
                        sensors_with_values = set()
                        # Iterar por todas las filas y columnas
                        for row in updated_data:
                            for col in sensor_columns:
                                cell_id = col["id"]
                                if cell_id in row:
                                    value = str(row[cell_id]).strip()
                                    # Comprobar si el valor es válido
                                    if (value and value not in ["N/A", "No asignado", "No Asignado"]) or (":" in value or "-" in value or "." in value):
                                        sensor_id = cell_id.replace("sensor_", "")
                                        sensors_with_values.add(sensor_id)
                                        logger.debug(f"Detectado sensor {sensor_id} con valor: '{value}'")
                        
                        # Registrar sensores con valores para depuración
                        logger.info(f"Sensores con valores detectados: {sorted(list(sensors_with_values))}")
                        
                        # Si hay sensores con valores, aplicar el filtro
                        if sensors_with_values:
                            # Filtrar columnas que tienen valores
                            filtered_columns = [col for col in sensor_columns if col["id"].replace("sensor_", "") in sensors_with_values]
                            updated_columns = base_columns + filtered_columns
                            logger.info(f"Aplicando filtro: mostrando {len(filtered_columns)} de {len(sensor_columns)} columnas de sensores")
                            else:
                            # Si no hay sensores con valores, mostrar todos
                            updated_columns = base_columns + sensor_columns
                            logger.warning("No se detectaron sensores con valores. Se muestran todos.")
        
        # Mensaje de éxito
        success_message = None
        if total_nfc_codes > 0:
            success_message = html.Div([
                html.I(className="fas fa-check-circle me-2"),
                f"Se cargaron {total_nfc_codes} códigos NFC para {nfc_sensors_found} sensores."
            ], className="alert alert-success")
        
        return updated_data, updated_columns, "", success_message

    # Callback para manejar el toggle de mostrar todos los sensores o solo los que tienen valores
    @app.callback(
        [Output("nfc-grid-filter-store", "data"),
         Output("nfc-grid-table", "columns", allow_duplicate=True)],
        [Input("nfc-grid-filter-toggle", "value")],
        [State("nfc-grid-filter-store", "data"),
         State("nfc-grid-data-store", "data"),
         State("nfc-grid-table", "data"),
         State("nfc-grid-table", "columns")],  # Añadir el estado de las columnas actuales
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[{"show_all": False}, []])
    def update_nfc_filter_toggle(show_all, current_filter_data, grid_data, table_data, current_columns):
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
        
        # Detectar sensores con valores en los datos actuales
        sensors_with_values = set()
        
        # Obtener todos los IDs de sensores reales (ya no necesitamos los virtuales)
        all_sensor_columns = set()
        for row in table_data:
            for key in row.keys():
                # Las columnas de sensores empiezan con "sensor_"
                if key.startswith("sensor_") and not key.endswith("_exists") and not key.endswith("_sensor_id") and not key.endswith("_asset_id"):
                    # Filtramos explícitamente los sensores virtuales
                    if "virtual_nfc" not in key:
                        all_sensor_columns.add(key)
        
        # Convertir los nombres de columna "sensor_X" a IDs de sensor "X"
        all_sensor_ids = [col_name.replace("sensor_", "") for col_name in all_sensor_columns]
        logger.info(f"Todos los sensor IDs reales encontrados: {all_sensor_ids}")
        
        # Primero registrar todos los valores para diagnóstico
        sensor_values = {}
        for row in table_data:
            device_id = row.get("device_id", "desconocido")
            for sensor_id in all_sensor_ids:
                cell_id = f"sensor_{sensor_id}"
                if cell_id in row:
                    value = str(row.get(cell_id, "")).strip()
                    if sensor_id not in sensor_values:
                        sensor_values[sensor_id] = []
                    # Registrar el valor junto con el device_id
                    sensor_values[sensor_id].append((device_id, value))
                    
        # Registrar todos los valores encontrados para cada sensor
        for sensor_id, values in sensor_values.items():
            value_count = len([v for _, v in values if v and v != "N/A" and v != "No asignado" and v != "No Asignado"])
            logger.info(f"Sensor {sensor_id}: {value_count} valores detectados de {len(values)} total")
            # Mostar los valores no vacíos
            for device_id, value in values:
                if value and value != "N/A" and value != "No asignado" and value != "No Asignado":
                    logger.info(f"   Device {device_id}, Sensor {sensor_id}: '{value}'")
        
        # Ahora evaluar SOLO los sensores reales, no los virtuales
        for row in table_data:
            device_id = row.get("device_id", "desconocido")
            for sensor_id in all_sensor_ids:
                cell_id = f"sensor_{sensor_id}"
                if cell_id in row:
                    value = str(row.get(cell_id, "")).strip()
                    
                    # Log para depuración
                    logger.debug(f"Evaluando valor para sensor {sensor_id} en device {device_id}: '{value}'")
                    
                    # DEBUG ESPECÍFICO para Sensor 2
                    if sensor_id == "2":
                        logger.info(f"[TOGGLE] SENSOR 2 ENCONTRADO - Device {device_id}, Valor: '{value}'")
                        logger.info(f"[TOGGLE] Tipo de dato: {type(value)}")
                        if ":" in value:
                            logger.info(f"[TOGGLE] CONTIENE DOS PUNTOS (:)")
                        if value and value not in ["N/A", "No asignado", "No Asignado"]:
                            logger.info(f"[TOGGLE] CONTIENE VALOR NO VACÍO")
                    
                    # Comprobar si es un valor válido (mejora en la detección)
                    is_valid = False
                    
                    # Caso 1: No está vacío y no es un valor de "no asignado"
                    if value and value not in ["N/A", "No asignado", "No Asignado"]:
                        is_valid = True
                        logger.debug(f"Valor no vacío detectado: '{value}'")
                    
                    # Caso 2: Es una dirección MAC (formato XX:XX:XX:XX) o similar con separadores
                    if ":" in value or "-" in value or "." in value:
                        is_valid = True
                        logger.debug(f"Detectado formato especial (MAC o similar): {value}")
                    
                    # Caso 3: Es un código hexadecimal (formato 82A08A5D)
                    if re.match(r'^[0-9A-F]{8}$', value, re.IGNORECASE):
                        is_valid = True
                        logger.info(f"Detectado código hexadecimal: {value}")
                    
                    if is_valid:
                        sensors_with_values.add(sensor_id)
                        logger.debug(f"Sensor con valor válido detectado: {sensor_id} = {value}")
        
        # DEBUG ESPECÍFICO: Registrar si se encontró el Sensor 2
        if "2" not in sensors_with_values:
            logger.warning(f"[TOGGLE] SENSOR 2 NO detectado como válido")
        else:
            logger.info(f"[TOGGLE] SENSOR 2 SÍ detectado como válido")
        
        logger.debug(f"Sensores con valores detectados: {len(sensors_with_values)} de {len(all_sensor_ids)}")
        logger.info(f"Lista de sensores con valores: {sorted(list(sensors_with_values))}")
        
        # Crear columnas para todos los sensores
        all_columns = []
        filtered_columns = []
        
        # Si no hay sensores con valores, mostrar todos de todos modos para evitar una tabla vacía
        if not sensors_with_values and not show_all:
            logger.warning("No se detectaron sensores con valores. Se mostrarán todos para evitar una tabla vacía.")
            show_all = True
        
        # Crear columnas para TODOS los sensores encontrados (solo los reales, no virtuales)
        for sensor_id in all_sensor_ids:
            # Obtener el nombre de la columna del current_columns si existe, para mantener el formato
            column_name = f"Sensor {sensor_id}"
            
            # Buscar el nombre actual en las columnas existentes
            if current_columns:  # Verificar que current_columns no sea None
                for col in current_columns:
                    if col.get("id") == f"sensor_{sensor_id}":
                        column_name = col.get("name", column_name)
                        break
            
            column = {"name": column_name, "id": f"sensor_{sensor_id}"}
            all_columns.append(column)
            
            if sensor_id in sensors_with_values:
                filtered_columns.append(column)
        
        # Elegir qué columnas mostrar
        display_columns = columns_base + (all_columns if show_all else filtered_columns)
        
        # Actualizar el store
        updated_filter_data = {"show_all": show_all}
        
        # Log final de modo visualización
        if show_all:
            logger.info(f"Mostrando TODAS las columnas de sensores: {len(all_columns)}")
        else:
            logger.info(f"Mostrando SOLO columnas con valores: {len(filtered_columns)} de {len(all_columns)}")
        
        return updated_filter_data, display_columns

def fetch_nfc_passwords_for_asset(asset_id, token):
    try:
        # Obtener los datos de códigos NFC para el asset
        nfc_data = get_nfc_passwords(asset_id, token)
        
        # DEBUG: Print raw response for direct inspection
        logger.info(f"===== DEBUG FOR ASSET {asset_id} =====")
        if nfc_data:
            logger.info(f"Raw NFC data keys: {list(nfc_data.keys())}")
            if 'data' in nfc_data:
                if isinstance(nfc_data['data'], list):
                    logger.info(f"Data is a list with {len(nfc_data['data'])} elements")
                    # Check for the specific device we're having trouble with
                    for device in nfc_data['data']:
                        if isinstance(device, dict) and device.get('device_name', '').startswith('RAYONICS_1_F7E7221735CC'):
                            logger.info(f"FOUND TARGET DEVICE: {device.get('device_name')}")
                            logger.info(f"Device keys: {list(device.keys())}")
                            if 'sensor_passwords' in device:
                                logger.info(f"Found {len(device['sensor_passwords'])} sensor_passwords")
                                for sp in device['sensor_passwords']:
                                    logger.info(f"Sensor ID: {sp.get('sensor_id')}, Password: '{sp.get('password')}'")
        
        # Si no se obtuvieron datos, retornar None
        if not nfc_data:
            logger.warning(f"No se obtuvieron datos NFC para asset {asset_id}")
            return asset_id, None
            
        # Normalizar la estructura de datos
        devices = []
        
        # Convertir a estructura estandarizada
        if 'data' in nfc_data and isinstance(nfc_data['data'], list):
            # Si data es una lista (nueva estructura), usarla directamente
            devices = nfc_data['data']
        elif 'data' in nfc_data and isinstance(nfc_data['data'], dict):
            # Si data es un diccionario (estructura anterior), extraer devices
            if 'devices' in nfc_data['data']:
                devices = nfc_data['data']['devices']
            else:
                # Intentar extraer directamente las claves como device_ids
                for key, value in nfc_data['data'].items():
                    if isinstance(value, dict):
                        value['device_id'] = key
                        devices.append(value)
        
        # Normalizamos la estructura para cada dispositivo
        for device in devices:
            # Asegurarnos de que cada dispositivo tenga sensor_passwords
            if 'sensor_passwords' not in device:
                device['sensor_passwords'] = []
                
                # Si hay sensors, intentar extraer passwords de ahí
                if 'sensors' in device and isinstance(device['sensors'], list):
                    for sensor in device['sensors']:
                        if isinstance(sensor, dict) and 'password' in sensor:
                            password_entry = {
                                'sensor_id': sensor.get('sensor_id', ''),
                                'password': sensor.get('password', ''),
                                'name': sensor.get('name', f"Sensor {sensor.get('sensor_id', '')}"),
                                'sensor_type': sensor.get('sensor_type', 'NFC_CODE')
                            }
                            device['sensor_passwords'].append(password_entry)
        
        # Retornar el asset_id y los datos procesados
        return asset_id, {'data': devices}
    except Exception as e:
        logger.error(f"Error en fetch_nfc_passwords_for_asset para asset {asset_id}: {str(e)}")
        return asset_id, None