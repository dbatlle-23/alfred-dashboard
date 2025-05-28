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
from utils.nfc_helper import fetch_for_asset as fetch_nfc_passwords_for_asset, get_available_slots, check_card_exists, validate_card_uuid, get_master_card_slot
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import re
from datetime import datetime
import json

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
    # Placeholder para unassign-card-selected-devices
    dcc.Store(id="unassign-card-selected-devices", data={"devices": []}),
    
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
                html.Div([
                    # Sección de botones para asignación/desasignación masiva de tarjetas
                    html.Div([
                        html.H5("Matriz de Tarjetas NFC", className="mb-3"),
                        html.Div(className="d-flex justify-content-between", children=[
                            html.Div(className="d-flex align-items-center", children=[
                                html.Button(
                                    children=[html.I(className="fas fa-sync me-2"), "Actualizar"],
                                    id="nfc-refresh-button",
                                    className="btn btn-outline-primary me-3",
                                    n_clicks=0
                                ),
                                html.Div(
                                    [
                                        dbc.Checklist(
                                            options=[
                                                {"label": "Mostrar todos los sensores", "value": True},
                                            ],
                                            value=[],
                                            id="nfc-grid-filter-toggle",
                                            inline=True,
                                            switch=True
                                        ),
                                    ],
                                    className="mb-0"
                                ),
                            ]),
                            html.Div([
                                html.Button(
                                    children=[html.I(className="fas fa-credit-card me-2"), "Asignar Tarjeta NFC"],
                                    id="master-card-assign-button",
                                    className="btn btn-primary",
                                    n_clicks=0
                                ),
                                html.Button(
                                    children=[html.I(className="fas fa-trash-alt me-2"), "Desasignar Tarjetas"],
                                    id="master-card-unassign-button",
                                    className="btn btn-outline-danger ms-2",
                                    n_clicks=0
                                )
                            ])
                        ]),
                        html.Hr()
                    ], className="mb-4"),
                    
                    # Resto del contenido que se actualizará dinámicamente
                    html.Div(id="nfc-grid-error-container"),
                    html.Div(id="nfc-grid-container", className="mt-2")
                ], className="mt-4")
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
        
        # Modal para asignación masiva de tarjetas NFC
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Asignar Múltiples Tarjetas NFC"), close_button=True),
            dbc.ModalBody([
                html.Div([
                    html.P("Ha seleccionado las siguientes cerraduras:"),
                    html.Div(id="master-card-selected-locks", className="p-3 border rounded mb-3"),
                    
                    html.P("Ingrese los UUIDs de las tarjetas NFC que desea asignar:"),
                    html.Div([
                        dbc.Label("UUIDs de Tarjetas NFC:", className="fw-bold mb-2"),
                        dbc.Textarea(
                            id="master-card-uuid-input",
                            placeholder="Ingrese uno o más UUIDs, separados por líneas nuevas o comas:\n\nEjemplo:\nAA:BB:CC:DD\nEE:FF:00:11, 12:34:56:78\nABCDEF01",
                            rows=6,
                            value="",
                            valid=False,
                            invalid=False,
                            style={"font-family": "monospace", "font-size": "14px"}
                        ),
                        dbc.FormText([
                            "• Puede pegar múltiples UUIDs desde Excel/CSV", html.Br(),
                            "• Formatos soportados: AA:BB:CC:DD, AA-BB-CC-DD, AABBCCDD", html.Br(),
                            "• Separadores: líneas nuevas, comas, espacios", html.Br(),
                            "• Las tarjetas se asignarán a slots disponibles en cada cerradura"
                        ], color="muted", className="mt-2")
                    ], className="mb-3"),
                    
                    dbc.InputGroup([
                        dbc.Button(
                            "Pegar desde Portapapeles", 
                            id="master-card-paste-button", 
                            outline=True, 
                            color="secondary",
                            className="me-2"
                        ),
                        dbc.Button(
                            "Limpiar", 
                            id="master-card-clear-button", 
                            outline=True, 
                            color="warning"
                        )
                    ], className="mb-3"),
                    
                    html.Div(id="master-card-feedback"),
                    
                    html.Div([
                        html.I(className="fas fa-info-circle me-2"),
                        html.Span("Cada tarjeta será asignada a un slot disponible en todas las cerraduras seleccionadas.")
                    ], className="alert alert-info mt-3"),
                    
                    # Resultados después de enviar
                    html.Div(id="master-card-results-container", className="mt-4", style={"display": "none"}),
                    
                    # Spinner para estados de carga
                    dbc.Spinner(id="master-card-loading", color="primary", type="grow", size="sm")
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="master-card-cancel", color="secondary", className="me-auto", n_clicks=0),
                dbc.Button("Asignar Tarjetas", id="master-card-confirm", color="primary", n_clicks=0)
            ])
        ], id="master-card-modal", size="lg", is_open=False),
        
        # Modal para desasignar tarjeta
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Desasignar Múltiples Tarjetas NFC"), close_button=True),
            dbc.ModalBody([
                html.Div([
                    html.P("Ha seleccionado las siguientes cerraduras:"),
                    html.Div(id="unassign-card-selected-locks", className="p-3 border rounded mb-3"),
                    
                    html.P("Ingrese los UUIDs de las tarjetas NFC que desea desasignar (opcional):"),
                    html.Div([
                        dbc.Label("UUIDs de Tarjetas NFC (opcional):", className="fw-bold mb-2"),
                        dbc.Textarea(
                                    id="unassign-card-uuid-input",
                            placeholder="Ingrese uno o más UUIDs para desasignar específicamente:\n\nEjemplo:\nAA:BB:CC:DD\nEE:FF:00:11, 12:34:56:78\nABCDEF01\n\nDeje vacío para desasignar TODAS las tarjetas",
                            rows=6,
                                    value="",
                                    valid=False,
                            invalid=False,
                            style={"font-family": "monospace", "font-size": "14px"}
                        ),
                        dbc.FormText([
                            "• Si especifica UUIDs, solo se desasignarán esas tarjetas", html.Br(),
                            "• Si deja vacío, se desasignarán TODAS las tarjetas", html.Br(),
                            "• Formatos soportados: AA:BB:CC:DD, AA-BB-CC-DD, AABBCCDD", html.Br(),
                            "• Separadores: líneas nuevas, comas, espacios"
                        ], color="muted", className="mt-2")
                    ], className="mb-3"),
                    
                    dbc.InputGroup([
                        dbc.Button(
                            "Pegar desde Portapapeles", 
                            id="unassign-card-paste-button", 
                            outline=True, 
                            color="secondary",
                            className="me-2"
                        ),
                        dbc.Button(
                            "Limpiar", 
                            id="unassign-card-clear-button", 
                            outline=True, 
                            color="warning"
                        ),
                        dbc.Button(
                            "Desasignar TODAS", 
                            id="unassign-card-all-button", 
                            outline=True, 
                            color="danger"
                        )
                    ], className="mb-3"),
                    
                    html.Div(id="unassign-card-feedback"),
                    
                    html.Div([
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        html.Span([
                            "Si no especifica UUIDs, esta acción desasignará ",
                            html.Strong("TODAS"),
                            " las tarjetas NFC de las cerraduras seleccionadas."
                        ])
                    ], className="alert alert-warning mt-3"),
                
                # Resultados después de enviar
                html.Div(id="unassign-card-results-container", className="mt-4", style={"display": "none"}),
                
                # Spinner para estados de carga
                dbc.Spinner(id="unassign-card-loading", color="primary", type="grow", size="sm")
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="unassign-card-cancel", color="secondary", className="me-auto", n_clicks=0),
                dbc.Button("Confirmar Desasignación", id="unassign-card-confirm", color="danger", n_clicks=0)
            ])
        ], id="unassign-card-modal", size="lg", is_open=False),
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
            asset_alias_value = asset.get("alias", "") 
            asset_staircase_value = asset.get("staircase", "") 
            asset_apartment_value = asset.get("apartment", "") 
            
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
                    
                    # Extraer el gateway_id del contenedor (es el uuid a nivel del contenedor)
                    container_gateway_id = device_container.get("uuid")
                    if container_gateway_id:
                        logger.info(f"Extrayendo gateway_id={container_gateway_id} del contenedor para asignarlo a sus dispositivos")
                    
                    # Extraer asset_id del contenedor si existe
                    container_asset_id = device_container.get("asset_id")
                    if container_asset_id and container_asset_id != asset_id:
                        logger.info(f"El contenedor tiene su propio asset_id={container_asset_id} diferente del asset actual={asset_id}")
                    
                    for nested_device in device_container["devices"]:
                        has_lock_sensor = False
                        device_id = nested_device.get("device_id", "desconocido")
                        
                        nested_device["alias"] = asset_alias_value
                        nested_device["staircase"] = asset_staircase_value
                        nested_device["apartment"] = asset_apartment_value

                        # Asegurarse de que el dispositivo tenga el asset_id
                        if "asset_id" not in nested_device:
                            # Prioridad: 1) asset_id del contenedor si existe, 2) asset_id del asset actual
                            if container_asset_id:
                                nested_device["asset_id"] = container_asset_id
                                logger.debug(f"Asignado asset_id={container_asset_id} del contenedor al dispositivo {device_id}")
                            elif asset_id:
                                nested_device["asset_id"] = asset_id
                                logger.debug(f"Asignado asset_id={asset_id} del asset actual al dispositivo {device_id}")
                        
                        # Asignar el gateway_id del contenedor al dispositivo
                        if container_gateway_id and "gateway_id" not in nested_device:
                            nested_device["gateway_id"] = container_gateway_id
                            logger.debug(f"Asignado gateway_id={container_gateway_id} al dispositivo anidado {device_id}")
                        
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
                            # nested_device["alias"] = asset_alias_value # Already added above
                            asset_lock_devices.append(nested_device)
                            logger.debug(f"Dispositivo anidado {device_id} añadido a la lista de cerraduras")
                else:
                    # Procesar dispositivo normal (no anidado)
                    has_lock_sensor = False
                    device_id = device_container.get("device_id", "desconocido")
                    
                    device_container["alias"] = asset_alias_value
                    device_container["staircase"] = asset_staircase_value
                    device_container["apartment"] = asset_apartment_value

                    # ADD THIS CHECK AND ASSIGNMENT:
                    if "asset_id" not in device_container and asset_id: # asset_id is from the outer loop
                        device_container["asset_id"] = asset_id
                        logger.debug(f"Assigned asset_id={asset_id} from outer loop to direct device {device_id}")

                    # Extraer el gateway_id del dispositivo si existe un campo uuid
                    if "uuid" in device_container and "gateway_id" not in device_container:
                        device_container["gateway_id"] = device_container.get("uuid")
                        logger.debug(f"Asignado gateway_id={device_container['gateway_id']} desde uuid al dispositivo {device_id}")
                    
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
                        # device_container["alias"] = asset_alias_value # Already added above
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
        
        # PASO 4: Verificar y asegurar que cada dispositivo tenga gateway_id
        logger.info("Verificando que todos los dispositivos tengan gateway_id...")
        devices_without_gateway = []
        
        for i, device in enumerate(consolidated_devices):
            device_id = device.get("device_id")
            gateway_id = device.get("gateway_id")
            
            if not gateway_id:
                logger.warning(f"Dispositivo {device_id} no tiene gateway_id. Intentando obtenerlo de la API...")
                devices_without_gateway.append((i, device_id))
        
        # Si hay dispositivos sin gateway_id, intentar obtenerlos
        if devices_without_gateway:
            logger.warning(f"Se encontraron {len(devices_without_gateway)} dispositivos sin gateway_id")
            
            # Intentar obtener gateway_id de los passwords NFC (más completo)
            for i, device_id in devices_without_gateway:
                device = consolidated_devices[i]
                asset_id = device.get("asset_id")
                
                if asset_id:
                    try:
                        from utils.api import get_nfc_passwords
                        
                        # Obtener los passwords NFC para este asset
                        nfc_data = get_nfc_passwords(asset_id, token)
                        
                        if nfc_data and isinstance(nfc_data, dict) and 'data' in nfc_data:
                            data_section = nfc_data['data']
                            
                            # Buscar el dispositivo en los datos NFC
                            if isinstance(data_section, dict) and 'devices' in data_section:
                                for nfc_device in data_section['devices']:
                                    if nfc_device.get('device_id') == device_id and 'gateway_id' in nfc_device:
                                        consolidated_devices[i]['gateway_id'] = nfc_device['gateway_id']
                                        logger.info(f"Se obtuvo gateway_id={nfc_device['gateway_id']} para device_id={device_id} desde los datos NFC")
                                        break
                    except Exception as e:
                        logger.error(f"Error al intentar obtener gateway_id para device_id={device_id}: {str(e)}")
        
        # Contar cuántos dispositivos quedaron sin gateway_id
        devices_still_without_gateway = [device.get("device_id") for device in consolidated_devices if not device.get("gateway_id")]
        if devices_still_without_gateway:
            logger.warning(f"Después de intentar obtener los gateway_id, estos dispositivos aún no tienen uno: {devices_still_without_gateway}")
        
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
                
                # Verificar si existe real_device_id en los datos del sensor
                if "real_device_id" in editing_sensor_data:
                    device_id = editing_sensor_data["real_device_id"]
                    logger.info(f"Usando real_device_id: {device_id} para actualización NFC")
                else:
                    device_id = editing_sensor_data.get("device_id")
                    logger.debug(f"Usando device_id normal: {device_id}")
                
                sensor_id = editing_sensor_data.get("sensor_id")
                asset_id = editing_sensor_data.get("asset_id")
                gateway_id = editing_sensor_data.get("gateway_id")
                
                # Verificar que tenemos todos los datos necesarios
                if not device_id or not sensor_id or not asset_id:
                    missing_fields = []
                    if not device_id: missing_fields.append("device_id")
                    if not sensor_id: missing_fields.append("sensor_id")
                    if not asset_id: missing_fields.append("asset_id")
                    
                    logger.error(f"Faltan campos críticos para actualizar código NFC: {', '.join(missing_fields)}")
                    return True, dash.no_update, dash.no_update, html.Div(
                        f"Error: Faltan datos críticos ({', '.join(missing_fields)})",
                        className="alert alert-danger"
                    ), True
                
                # Verificar si tenemos gateway_id
                if not gateway_id:
                    logger.warning(f"No se encontró gateway_id para device_id={device_id}, intentando obtenerlo desde el current_device...")
                    
                    # Intentar obtener gateway_id del current_device
                    if current_device and current_device.get("device_id") == device_id and "gateway_id" in current_device:
                        gateway_id = current_device["gateway_id"]
                        logger.info(f"Se obtuvo gateway_id={gateway_id} desde current_device")
                
                # Validar gateway_id final
                if not gateway_id:
                    logger.error(f"No se pudo obtener gateway_id para device_id={device_id}")
                    return True, dash.no_update, dash.no_update, html.Div(
                        "Error: No se pudo obtener el ID del gateway necesario para esta operación",
                        className="alert alert-danger"
                    ), True
                
                try:
                    # Llamar a la API para actualizar el código NFC
                    from utils.api import update_nfc_code_value
                    
                    logger.info(f"Actualizando código NFC: asset_id={asset_id}, device_id={device_id}, sensor_id={sensor_id}, gateway_id={gateway_id}, value={input_value}")
                    
                    success, response = update_nfc_code_value(
                        asset_id=asset_id,
                        device_id=device_id,
                        sensor_id=sensor_id,
                        new_value=input_value,
                        jwt_token=token,
                        gateway_id=gateway_id,
                        is_master_card=(sensor_id == "7")  # El slot 7 es para tarjetas maestras
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
                        # Categorizar el tipo de error
                        if isinstance(response, dict):
                            error_details = response.get("error", "Error desconocido")
                        else:
                            error_details = str(response)
                        
                        # Detectar errores de autenticación
                        if ("401" in error_details or "unauthorized" in error_details.lower() or 
                            "token" in error_details.lower() or "jwt" in error_details.lower() or
                            "autenticación" in error_details.lower()):
                            error_message = html.Div([
                                html.I(className="fas fa-exclamation-triangle me-2"),
                                html.Strong("Error de autenticación: "),
                                "Su sesión ha expirado. Por favor, recargue la página e inicie sesión nuevamente."
                            ], className="alert alert-warning")
                        elif "503" in error_details:
                            error_message = html.Div([
                                html.I(className="fas fa-exclamation-circle me-2"),
                                "Servicio temporalmente no disponible. Intente más tarde."
                            ], className="alert alert-warning")
                        elif "404" in error_details:
                            error_message = html.Div([
                                html.I(className="fas fa-times-circle me-2"),
                                "Dispositivo o sensor no encontrado."
                            ], className="alert alert-danger")
                        else:
                            error_message = html.Div([
                                html.I(className="fas fa-times-circle me-2"),
                                f"Error al actualizar el código NFC: {error_details}"
                            ], className="alert alert-danger")
                        
                        return True, dash.no_update, dash.no_update, error_message, True
                except Exception as e:
                    # Categorizar excepciones relacionadas con autenticación
                    error_str = str(e)
                    if ("token" in error_str.lower() or "jwt" in error_str.lower() or 
                        "auth" in error_str.lower() or "401" in error_str):
                        error_message = html.Div([
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            html.Strong("Error de autenticación: "),
                            "Su sesión ha expirado. Por favor, recargue la página e inicie sesión nuevamente."
                        ], className="alert alert-warning")
                    else:
                        error_message = html.Div([
                            html.I(className="fas fa-times-circle me-2"),
                            f"Error al actualizar el código NFC: {error_str}"
                        ], className="alert alert-danger")
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
        try:
            # Solo proceder si es la pestaña de matriz NFC
            if not active_tab or active_tab != "nfc-grid-tab" or not devices_data:
                logger.info(f"No actualizando matriz NFC: pestaña={active_tab}, datos disponibles={bool(devices_data)}")
                return dash.no_update
            
            logger.info(f"Actualizando matriz NFC con {len(devices_data)} dispositivos")
            
            # Debug devices data
            if devices_data and len(devices_data) > 0:
                first_device = devices_data[0]
                logger.info(f"First device keys: {list(first_device.keys()) if isinstance(first_device, dict) else 'Not a dict'}")
                
                # Check if important fields exist
                has_device_id = isinstance(first_device, dict) and "device_id" in first_device
                has_asset_id = isinstance(first_device, dict) and "asset_id" in first_device
                
                logger.info(f"Device has device_id: {has_device_id}, asset_id: {has_asset_id}")
                
                # Instead of using the component directly, create our own simplified table for debugging
                from components.smart_locks.nfc_grid import create_nfc_display_grid
                
                # Call the function and log the result
                logger.info("Calling create_nfc_display_grid with the devices data")
                grid_component = create_nfc_display_grid(filtered_locks=devices_data, is_loading_locks=False)
                
                # Log what we got back
                if grid_component:
                    logger.info(f"create_nfc_display_grid returned a component of type: {type(grid_component)}")
                else:
                    logger.error("create_nfc_display_grid returned None or empty component")
                
                return grid_component
            else:
                # Basic fallback if no data
                return html.Div([
                    html.H5("No hay datos de dispositivos disponibles", className="text-warning"),
                    html.P("Intente seleccionar otro proyecto o refrescar los datos.")
                ], className="alert alert-warning")
            
        except Exception as e:
            logger.error(f"Error en update_grid_display: {str(e)}")
            # Return more detailed error message during debugging
            return html.Div([
                html.H5("Error al cargar la matriz", className="text-danger"),
                html.Pre(f"Excepción: {str(e)}")
            ], className="alert alert-danger")
    
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
        """
        Refresca los datos de la matriz NFC cuando se hace clic en el botón de refrescar
        """
        if not n_clicks:
            return dash.no_update
            
        logger.info(f"Refreshing NFC data triggered by button click ({n_clicks})")
        
        # Si current_data es None, inicializarlo
        if current_data is None:
            current_data = {}
            
        # Obtener el contador actual o 0 si no existe
        current_count = current_data.get("count", 0)
        
        # Crear nuevo trigger con timestamp actualizado
        new_data = {
            "refreshed": True,
            "count": current_count + 1,
            "timestamp": time.time()
        }
        
        logger.info(f"New NFC update trigger data: {new_data}")
        
        return new_data
    
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
         State("smart-locks-data-store", "data"), # Added smart-locks-data-store
         State("nfc-grid-filter-store", "data")],
        prevent_initial_call=True,
        id='load_nfc_grid_data_callback'  # Add a unique ID to the callback
    )
    @handle_exceptions(default_return=[[], []])
    def load_nfc_grid_data(grid_data, update_trigger, active_tab, device_update_data, 
                           current_table_data, current_columns, token_data, 
                           smart_locks_store_data, # Added smart_locks_store_data
                           filter_data):
        try:
            logger.info(f"load_nfc_grid_data called: active_tab={active_tab}")
            ctx = dash.callback_context
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
            logger.info(f"Triggered by: {triggered_id}")

            if not grid_data:
                logger.warning("No grid_data for load_nfc_grid_data")
                return current_table_data or [], current_columns or []
            
            if active_tab != "nfc-grid-tab":
                logger.info(f"Not NFC tab (is {active_tab}), no update to NFC grid data.")
                return current_table_data or [], current_columns or []

            token = token_data.get('token') if token_data else None
            if not token:
                logger.warning("No token for load_nfc_grid_data")
                return current_table_data or [], current_columns or []

            asset_ids = grid_data.get("asset_ids", [])
            if not asset_ids:
                logger.warning("No asset_ids in grid_data for load_nfc_grid_data")
                return current_table_data or [], current_columns or []

            # 1. Get consolidated_devices from smart_locks_store_data
            consolidated_devices_for_lookup = smart_locks_store_data if smart_locks_store_data else []

            # 2. Create lookup map for gateway_id
            gateway_lookup = {}
            for dev_lookup in consolidated_devices_for_lookup:
                # Use real_device_id if available, otherwise device_id as key
                lookup_key = dev_lookup.get('real_device_id', dev_lookup.get('device_id'))
                gw_id = dev_lookup.get('gateway_id')
                if lookup_key and gw_id: # Only store if both key and gateway_id are present
                    gateway_lookup[str(lookup_key)] = gw_id # Ensure key is string for matching
            
            logger.debug(f"Gateway lookup map created with {len(gateway_lookup)} entries.")
            if len(gateway_lookup) < 20: # Log content only if it's not too large
                logger.debug(f"Gateway lookup content: {gateway_lookup}")


            from utils.nfc_helper import fetch_for_asset # Already imported at top level, but good for clarity
            from components.smart_locks.nfc_grid.nfc_display_grid import format_nfc_value

            new_table_data = []
            all_sensor_ids_from_api = set()

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_asset = {
                    executor.submit(fetch_for_asset, asset_id, token): asset_id 
                    for asset_id in asset_ids
                }
                
                for future in concurrent.futures.as_completed(future_to_asset):
                    current_asset_id_processed = future_to_asset[future]
                    try:
                        success, devices_from_fetch = future.result()
                        logger.info(f"NFC data received for asset {current_asset_id_processed}: {len(devices_from_fetch) if success else 'Failed or no'} devices")
                        
                        if not success or not devices_from_fetch:
                            continue

                        for device_from_nfc_api in devices_from_fetch:
                            nfc_api_device_id = device_from_nfc_api.get("device_id") # This is the real_device_id
                            if not nfc_api_device_id:
                                logger.warning(f"Device from fetch_for_asset for asset {current_asset_id_processed} is missing device_id: {device_from_nfc_api}")
                                continue
                            
                            nfc_api_device_id_str = str(nfc_api_device_id) # Ensure string for lookup

                            # Determine the authoritative gateway_id
                            nfc_api_gateway_id = device_from_nfc_api.get("gateway_id")
                            final_gateway_id_for_row = nfc_api_gateway_id

                            if not final_gateway_id_for_row or final_gateway_id_for_row == "no_gateway":
                                looked_up_gateway_id = gateway_lookup.get(nfc_api_device_id_str)
                                if looked_up_gateway_id:
                                    final_gateway_id_for_row = looked_up_gateway_id
                                    logger.info(f"Used gateway_id ('{final_gateway_id_for_row}') from smart-locks-data-store for device {nfc_api_device_id_str} (asset {current_asset_id_processed}) as fetched was '{nfc_api_gateway_id}'.")
                                else:
                                    final_gateway_id_for_row = f"gw_unknown_{nfc_api_device_id_str[:4]}" # Fallback, include part of device_id for some uniqueness
                                    logger.warning(f"Gateway_id for device {nfc_api_device_id_str} (asset {current_asset_id_processed}) not in fetched data ('{nfc_api_gateway_id}') or lookup map. Using fallback '{final_gateway_id_for_row}'.")
                            else:
                                logger.debug(f"Using gateway_id ('{final_gateway_id_for_row}') from fetched NFC API data for device {nfc_api_device_id_str} (asset {current_asset_id_processed}).")
                            
                            real_device_id_for_row = nfc_api_device_id_str
                            # Use current_asset_id_processed for the asset_id part of the composite ID
                            composite_row_id = f"{current_asset_id_processed}-{final_gateway_id_for_row}-{real_device_id_for_row}"
                            
                            # --- MODIFICATION FOR STAIRCASE/APARTMENT SOURCE START ---
                            # Get Staircase and Apartment from a device belonging to current_asset_id_processed
                            asset_staircase_for_row = ""
                            asset_apartment_for_row = ""
                            representative_device_for_current_asset = next((
                                dev for dev in consolidated_devices_for_lookup 
                                if str(dev.get("asset_id")) == str(current_asset_id_processed)
                            ), None)

                            if representative_device_for_current_asset:
                                asset_staircase_for_row = representative_device_for_current_asset.get("staircase", "")
                                asset_apartment_for_row = representative_device_for_current_asset.get("apartment", "")
                                logger.debug(f"For asset {current_asset_id_processed}, found representative staircase: '{asset_staircase_for_row}', apartment: '{asset_apartment_for_row}'")
                            else:
                                # Fallback: attempt to get from device_from_nfc_api if fields happen to exist there (unlikely for these)
                                asset_staircase_for_row = device_from_nfc_api.get("asset_staircase", "")
                                asset_apartment_for_row = device_from_nfc_api.get("asset_apartment", "")
                                if not asset_staircase_for_row and not asset_apartment_for_row: # Only log warning if both fallbacks are empty
                                     logger.warning(f"Could not find representative device for asset {current_asset_id_processed} in consolidated_devices_for_lookup to get staircase/apartment. API device also lacks these.")
                            # --- MODIFICATION FOR STAIRCASE/APARTMENT SOURCE END ---

                            # Attempt to get richer display_label from smart_locks_store_data (consolidated_devices_for_lookup) matching the specific device
                            display_label = device_from_nfc_api.get("device_name", f"Device {real_device_id_for_row}") # Default
                            
                            # IMPROVED: Multi-approach device matching with detailed logging
                            matching_device_for_display_label = None
                            matching_approach = "none"
                            
                            # FIXED: Filter devices by current asset first to avoid cross-asset matching
                            asset_specific_devices = [d for d in consolidated_devices_for_lookup 
                                                     if str(d.get("asset_id", "")) == str(current_asset_id_processed)]
                            
                            
                            # Approach 1: Match by real_device_id within current asset
                            matching_device_for_display_label = next((d for d in asset_specific_devices 
                                                                     if str(d.get("real_device_id", "")) == real_device_id_for_row), None)
                            if matching_device_for_display_label:
                                matching_approach = "real_device_id"
                            
                            # Approach 2: Match by device_id within current asset if approach 1 failed
                            if not matching_device_for_display_label:
                                matching_device_for_display_label = next((d for d in asset_specific_devices 
                                                                         if str(d.get("device_id", "")) == real_device_id_for_row), None)
                                if matching_device_for_display_label:
                                    matching_approach = "device_id"
                            
                            # Approach 3: Partial match within current asset (for cases where IDs are similar but not exact)
                            if not matching_device_for_display_label:
                                for candidate_device in asset_specific_devices:
                                    candidate_real_id = str(candidate_device.get("real_device_id", ""))
                                    candidate_device_id = str(candidate_device.get("device_id", ""))
                                    
                                    # Check for partial matches or similar IDs
                                    if (real_device_id_for_row in candidate_real_id or 
                                        candidate_real_id in real_device_id_for_row or
                                        real_device_id_for_row in candidate_device_id or 
                                        candidate_device_id in real_device_id_for_row):
                                        matching_device_for_display_label = candidate_device
                                        matching_approach = "partial_match"
                                        break
                            
                            # Approach 4: Fallback - first device from the same asset (as last resort)
                            if not matching_device_for_display_label and asset_specific_devices:
                                matching_device_for_display_label = asset_specific_devices[0]
                                matching_approach = "same_asset_fallback"
                                logger.warning(f"Device {real_device_id_for_row} using same_asset_fallback approach in asset {current_asset_id_processed} - this may not be accurate")
                            
                            # Process the matched device for display_label
                            if matching_device_for_display_label:
                                params = matching_device_for_display_label.get("parameters", {})
                                room = params.get("room", "")
                                name = params.get("name", "")
                                device_name = matching_device_for_display_label.get("device_name", "")
                                
                                if room and name:
                                    display_label = f"{room} - {name}"
                                elif room:
                                    display_label = room
                                elif name:
                                    display_label = name
                                elif device_name:
                                    display_label = device_name
                                
                                logger.info(f"Device {real_device_id_for_row} enriched display_label: '{display_label}' using {matching_approach} approach in asset {current_asset_id_processed}")
                            else:
                                # Log detailed debugging info when no match is found
                                logger.warning(f"Device {real_device_id_for_row} not found in asset {current_asset_id_processed}. Available devices in this asset:")
                                for i, dev in enumerate(asset_specific_devices[:3]):  # Log first 3 devices only
                                    logger.warning(f"  Device {i+1}: device_id='{dev.get('device_id')}', real_device_id='{dev.get('real_device_id')}', device_name='{dev.get('device_name')}'")
                                if not asset_specific_devices:
                                    logger.warning(f"  No devices found for asset {current_asset_id_processed}")
                                logger.warning(f"Using API device_name fallback: '{display_label}'")
                            
                            lock_name_for_row = device_from_nfc_api.get("device_name", "Sin nombre")

                            row = {
                                "id": composite_row_id, 
                                "device_id": display_label, 
                                "real_device_id": real_device_id_for_row,
                                "lock_name": lock_name_for_row,
                                "asset_name": current_asset_id_processed, 
                                "asset_staircase": asset_staircase_for_row, 
                                "asset_apartment": asset_apartment_for_row, 
                                "gateway_id": final_gateway_id_for_row,
                                "asset_id": current_asset_id_processed 
                            }
                            
                            # Add sensor values from device_from_nfc_api.get("sensors", [])
                            # The sensors in device_from_nfc_api are expected to be { "sensor_id": "X", "password": "Y" }
                            for sensor_detail in device_from_nfc_api.get("sensors", []):
                                sensor_id_val = sensor_detail.get("sensor_id")
                                if sensor_id_val:
                                    all_sensor_ids_from_api.add(str(sensor_id_val))
                                    password = sensor_detail.get("password", "")
                                    row[f"sensor_{sensor_id_val}"] = format_nfc_value(password) if password else ""
                            
                            new_table_data.append(row)
                            # logger.info(f"Added/Updated row for device {real_device_id_for_row} (asset {current_asset_id_processed}): ID='{composite_row_id}', GW='{final_gateway_id_for_row}'")

                    except Exception as e:
                        logger.error(f"Error processing fetched NFC data for asset {current_asset_id_processed}: {str(e)}")
            
            if not new_table_data:
                logger.warning("No data generated by load_nfc_grid_data after processing assets.")
                # Return current data if nothing new was generated, or empty if current is also None
                return current_table_data or [], current_columns or []

            # Dynamically create columns based on all sensor IDs found
            # Include important sensors even if they have no data yet
            important_sensors_ids = {"2", "8", "9", "10"}
            final_sensor_ids_for_columns = sorted(list(all_sensor_ids_from_api.union(important_sensors_ids)), key=lambda x: int(x) if x.isdigit() else x)
            
            base_columns = [
                {"name": "Espacio", "id": "asset_name"},
                {"name": "Staircase", "id": "asset_staircase"},
                {"name": "Apartment", "id": "asset_apartment"},
                {"name": "Nombre Dispositivo", "id": "device_id"},
                {"name": "Cerradura", "id": "lock_name"}
            ]
            
            sensor_columns_built = []
            for s_id in final_sensor_ids_for_columns:
                name = f"NFC {s_id}"
                # if s_id == "7": name = "Tarjeta Maestra" # Example of custom name
                sensor_columns_built.append({"name": name, "id": f"sensor_{s_id}", "editable": True})
            
            all_columns_built = base_columns + sensor_columns_built
            
            # Ensure all rows have all sensor columns, initialized to empty if not present
            for r in new_table_data:
                for s_id_col in final_sensor_ids_for_columns:
                    r.setdefault(f"sensor_{s_id_col}", "")

            logger.info(f"load_nfc_grid_data returning {len(new_table_data)} rows and {len(all_columns_built)} columns")
            
            
            return new_table_data, all_columns_built
                
        except Exception as e:
            logger.error(f"Error in load_nfc_grid_data main try-except: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return current_table_data or [], current_columns or []

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
            {"name": "Espacio", "id": "asset_name"},
            {"name": "Staircase", "id": "asset_staircase"},
            {"name": "Apartment", "id": "asset_apartment"},
            {"name": "Nombre Dispositivo", "id": "device_id"},
            {"name": "Cerradura", "id": "lock_name"},
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
        [Output("master-card-modal", "is_open"),
         Output("master-card-confirm", "disabled")],
        [Input("master-card-assign-button", "n_clicks"),
         Input("master-card-cancel", "n_clicks"),
         Input("master-card-confirm", "n_clicks")],
        [State("master-card-modal", "is_open"),
         State("nfc-grid-table", "selected_row_ids"),
         State("nfc-grid-table", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[False, False])
    def toggle_master_card_modal(assign_clicks, cancel_clicks, confirm_clicks, is_open, selected_row_ids, table_data):
        if not any([assign_clicks, cancel_clicks, confirm_clicks]):
            return is_open, False
        
        ctx = dash.callback_context
        if not ctx.triggered:
            return is_open, False
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == "master-card-assign-button":
            # Solo abrir si hay filas seleccionadas
            if selected_row_ids:
                return True, False
            else:
                return False, True  # Disable confirm button if no rows selected
        elif button_id in ["master-card-cancel", "master-card-confirm"]:
            return False, False
        
        return is_open, False  # Keep the confirm button enabled in other cases

    @app.callback(
        [Output("master-card-selected-locks", "children"),
         Output("master-card-selected-devices", "data")],
        [Input("master-card-modal", "is_open")],
        [State("nfc-grid-table", "selected_row_ids"),
         State("nfc-grid-table", "data"),
         State("smart-locks-data-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[html.Div("No hay cerraduras seleccionadas"), {"devices": []}])
    def update_selected_locks_display(is_open, selected_row_ids, table_data, devices_data):
        logger.info(f"update_selected_locks_display: is_open={is_open}, selected_row_ids={selected_row_ids}")
        if not is_open or not selected_row_ids or not table_data:
            return html.Div("No hay cerraduras seleccionadas"), {"devices": []}

        device_id_to_row = {row["id"]: row for row in table_data if "id" in row}
        selected_data = []
        for composite_id in selected_row_ids:
            parsed_asset_id, parsed_gateway_id, parsed_real_device_id = "unknown_asset", "unknown_gateway", composite_id
            try:
                parts = composite_id.split("-", 2)
                if len(parts) == 3:
                    parsed_asset_id, parsed_gateway_id, parsed_real_device_id = parts
                elif len(parts) == 2: # Fallback for old format
                    parsed_gateway_id, parsed_real_device_id = parts
                    logger.warning(f"Parsing {composite_id} as old 2-part ID for selected_locks_display")
                else:
                    logger.warning(f"Cannot parse {composite_id} into 3 or 2 parts for selected_locks_display")
            except Exception as e:
                logger.error(f"Error parsing composite_id '{composite_id}' in selected_locks_display: {e}")

            if composite_id in device_id_to_row:
                row = device_id_to_row[composite_id]
                row["parsed_asset_id"] = parsed_asset_id
                row["parsed_gateway_id"] = parsed_gateway_id
                row["parsed_real_device_id"] = parsed_real_device_id
                selected_data.append(row)
            else:
                logger.error(f"Composite ID {composite_id} not found in table_data for selected_locks_display")

        if not selected_data:
            return html.Div("No se encontraron datos para las cerraduras seleccionadas"), {"devices": []}

        locks_list = []
        selected_devices_output = []
        all_devices_from_store = devices_data.get("devices", []) if isinstance(devices_data, dict) else devices_data if isinstance(devices_data, list) else []
        
        # Create lookup maps from all_devices_from_store
        store_devices_by_real_id = {str(d.get("real_device_id", d.get("device_id"))): d for d in all_devices_from_store if d.get("real_device_id", d.get("device_id"))}
        store_devices_by_composite_id = {
            f"{d.get('asset_id')}-{d.get('gateway_id')}-{d.get('real_device_id', d.get('device_id'))}": d
            for d in all_devices_from_store if d.get('real_device_id', d.get('device_id')) and d.get('asset_id') and d.get('gateway_id')
        }

        processed_unique_keys = set()
        for row_from_table in selected_data:
            asset_id = row_from_table.get("parsed_asset_id", row_from_table.get("asset_id"))
            gateway_id = row_from_table.get("parsed_gateway_id", row_from_table.get("gateway_id"))
            real_device_id = row_from_table.get("parsed_real_device_id", row_from_table.get("real_device_id"))
            display_name_from_table = row_from_table.get("device_id") # This is the display name (room - name)
            lock_name_from_table = row_from_table.get("lock_name")

            unique_key = f"{asset_id}-{gateway_id}-{real_device_id}"
            if unique_key in processed_unique_keys:
                continue
            processed_unique_keys.add(unique_key)


            staircase_info = row_from_table.get("asset_staircase", "N/A")
            apartment_info = row_from_table.get("asset_apartment", "N/A")

            locks_list.append(html.Div([
                html.Strong(display_name_from_table),
                html.Span(f" - S: {staircase_info}, A: {apartment_info} (ID:{real_device_id}, Asset:{asset_id}, GW:{gateway_id})", style={"fontSize": "0.9em", "color": "gray"})
            ], className="mb-1"))

            full_device_info = None
            if unique_key in store_devices_by_composite_id:
                full_device_info = store_devices_by_composite_id[unique_key]
            elif real_device_id and str(real_device_id) in store_devices_by_real_id:
                full_device_info = store_devices_by_real_id[str(real_device_id)]
            else:
                full_device_info = dict(row_from_table) # Use a copy
            
            # Enrich with parsed/known good values from the row
            final_device_data = {
                **full_device_info, # Start with data from store or row
                "asset_id": asset_id,
                "gateway_id": gateway_id,
                "real_device_id": real_device_id,
                "device_id": display_name_from_table, # Ensure this uses the table display name
                "lock_name": lock_name_from_table,
                "id": row_from_table.get("id") # Preserve the original composite ID from the table row
            }
            selected_devices_output.append(final_device_data)

        if not locks_list:
            return html.Div("No hay cerraduras seleccionadas (después del procesamiento)"), {"devices": []}
        
        logger.info(f"update_selected_locks_display returning {len(selected_devices_output)} devices for modal.")
        return html.Div([html.H6(f"Cerraduras seleccionadas ({len(locks_list)}):", className="mb-2"), 
                         html.Div(locks_list, style={"maxHeight": "200px", "overflowY": "auto"})]), \
               {"devices": selected_devices_output}
    
    # Callback para mostrar las cerraduras seleccionadas en el modal de desasignación
    @app.callback(
        [Output("unassign-card-selected-locks", "children"),
         Output("unassign-card-selected-devices", "data")],
        [Input("unassign-card-modal", "is_open")],
        [State("nfc-grid-table", "selected_row_ids"),
         State("nfc-grid-table", "data"),
         State("smart-locks-data-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[html.Div("No hay cerraduras seleccionadas"), {"devices": []}])
    def update_unassign_selected_locks_display(is_open, selected_row_ids, table_data, devices_data):
        logger.info(f"update_unassign_selected_locks_display: is_open={is_open}, selected_row_ids={selected_row_ids}")
        if not is_open or not selected_row_ids or not table_data:
            return html.Div("No hay cerraduras seleccionadas"), {"devices": []}

        device_id_to_row = {row["id"]: row for row in table_data if "id" in row}
        selected_data = []
        for composite_id in selected_row_ids:
            parsed_asset_id, parsed_gateway_id, parsed_real_device_id = "unknown_asset", "unknown_gateway", composite_id
            try:
                parts = composite_id.split("-", 2)
                if len(parts) == 3:
                    parsed_asset_id, parsed_gateway_id, parsed_real_device_id = parts
                elif len(parts) == 2:
                    parsed_gateway_id, parsed_real_device_id = parts
                    logger.warning(f"Parsing {composite_id} as old 2-part ID for unassign_locks_display")
                else:
                    logger.warning(f"Cannot parse {composite_id} into 3 or 2 parts for unassign_locks_display")
            except Exception as e:
                logger.error(f"Error parsing composite_id '{composite_id}' in unassign_locks_display: {e}")

            if composite_id in device_id_to_row:
                row = device_id_to_row[composite_id]
                row["parsed_asset_id"] = parsed_asset_id
                row["parsed_gateway_id"] = parsed_gateway_id
                row["parsed_real_device_id"] = parsed_real_device_id
                selected_data.append(row)
            else:
                logger.error(f"Composite ID {composite_id} not found in table_data for unassign_locks_display")

        if not selected_data:
            return html.Div("No se encontraron datos para las cerraduras seleccionadas (unassign)"), {"devices": []}

        locks_list_unassign = []
        selected_devices_unassign_output = []
        all_devices_from_store = devices_data.get("devices", []) if isinstance(devices_data, dict) else devices_data if isinstance(devices_data, list) else []
        
        store_devices_by_real_id = {str(d.get("real_device_id", d.get("device_id"))): d for d in all_devices_from_store if d.get("real_device_id", d.get("device_id"))}
        store_devices_by_composite_id = {
            f"{d.get('asset_id')}-{d.get('gateway_id')}-{d.get('real_device_id', d.get('device_id'))}": d
            for d in all_devices_from_store if d.get('real_device_id', d.get('device_id')) and d.get('asset_id') and d.get('gateway_id')
        }

        processed_unique_keys_unassign = set()
        for row_from_table in selected_data:
            asset_id = row_from_table.get("parsed_asset_id", row_from_table.get("asset_id"))
            gateway_id = row_from_table.get("parsed_gateway_id", row_from_table.get("gateway_id"))
            real_device_id = row_from_table.get("parsed_real_device_id", row_from_table.get("real_device_id"))
            display_name_from_table = row_from_table.get("device_id")
            lock_name_from_table = row_from_table.get("lock_name")

            unique_key = f"{asset_id}-{gateway_id}-{real_device_id}"
            if unique_key in processed_unique_keys_unassign:
                continue
            processed_unique_keys_unassign.add(unique_key)


            staircase_info_unassign = row_from_table.get("asset_staircase", "N/A")
            apartment_info_unassign = row_from_table.get("asset_apartment", "N/A")

            locks_list_unassign.append(html.Div([
                html.Strong(display_name_from_table),
                html.Span(f" - S: {staircase_info_unassign}, A: {apartment_info_unassign} (ID:{real_device_id}, Asset:{asset_id}, GW:{gateway_id})", style={"fontSize": "0.9em", "color": "gray"})
            ], className="mb-1"))

            full_device_info = None
            if unique_key in store_devices_by_composite_id:
                full_device_info = store_devices_by_composite_id[unique_key]
            elif real_device_id and str(real_device_id) in store_devices_by_real_id:
                full_device_info = store_devices_by_real_id[str(real_device_id)]
            else:
                full_device_info = dict(row_from_table)
            
            final_device_data = {
                **full_device_info,
                "asset_id": asset_id,
                "gateway_id": gateway_id,
                "real_device_id": real_device_id,
                "device_id": display_name_from_table,
                "lock_name": lock_name_from_table,
                "id": row_from_table.get("id")
            }
            selected_devices_unassign_output.append(final_device_data)

        if not locks_list_unassign:
            return html.Div("No hay cerraduras seleccionadas para desasignar (después del procesamiento)"), {"devices": []}
        
        logger.info(f"update_unassign_selected_locks_display returning {len(selected_devices_unassign_output)} devices for modal.")
        return html.Div([html.H6(f"Cerraduras seleccionadas ({len(locks_list_unassign)}):", className="mb-2"), 
                         html.Div(locks_list_unassign, style={"maxHeight": "200px", "overflowY": "auto"})]), \
               {"devices": selected_devices_unassign_output}
    
    # Callback para la validación del UUID
    @app.callback(
        [Output("master-card-uuid-input", "valid"),
         Output("master-card-uuid-input", "invalid"),
         Output("master-card-feedback", "children")],
        [Input("master-card-uuid-input", "value")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[False, False, html.Div()])
    def validate_multiple_uuid_input(uuid_text):
        if not uuid_text or len(uuid_text.strip()) == 0:
            return False, False, html.Div()
        
        # Función para parsear múltiples UUIDs del texto
        def parse_uuids(text):
            import re
            
            # Normalizar separadores: reemplazar comas y puntos y comas con saltos de línea
            normalized_text = text.replace(',', '\n').replace(';', '\n')
            
            # Dividir por líneas y espacios
            lines = normalized_text.split('\n')
            all_tokens = []
            for line in lines:
                # Dividir cada línea por espacios también
                tokens = line.strip().split()
                all_tokens.extend(tokens)
            
            # Filtrar tokens vacíos
            potential_uuids = [token.strip() for token in all_tokens if token.strip()]
            
            # Validar cada token como UUID
            valid_uuids = []
            invalid_tokens = []
            
            # Patrones para diferentes formatos de UUID
            pattern_colon = r'^([0-9A-F]{2}:){3}[0-9A-F]{2}$'  # AA:BB:CC:DD
            pattern_dash = r'^([0-9A-F]{2}-){3}[0-9A-F]{2}$'   # AA-BB-CC-DD
            pattern_plain = r'^[0-9A-F]{8}$'                   # AABBCCDD
            pattern_long = r'^[0-9A-F]{12,16}$'                # AABBCCDDEE o más largo
            
            for token in potential_uuids:
                token_upper = token.upper()
                
                # Verificar si coincide con algún patrón
                if (re.match(pattern_colon, token_upper, re.IGNORECASE) or 
                    re.match(pattern_dash, token_upper, re.IGNORECASE) or 
                    re.match(pattern_plain, token_upper, re.IGNORECASE) or
                    re.match(pattern_long, token_upper, re.IGNORECASE)):
                    
                    # Normalizar formato a AA:BB:CC:DD para consistencia
                    if ':' not in token_upper and '-' not in token_upper:
                        # Convertir AABBCCDD a AA:BB:CC:DD
                        if len(token_upper) >= 8:
                            formatted = ':'.join([token_upper[i:i+2] for i in range(0, min(8, len(token_upper)), 2)])
                            valid_uuids.append(formatted)
                        else:
                            # Si es muy corto, mantenerlo como está pero marcarlo válido si pasa el patrón
                            valid_uuids.append(token_upper)
                    else:
                        valid_uuids.append(token_upper)
                else:
                    invalid_tokens.append(token)
            
            # Eliminar duplicados manteniendo el orden
            seen = set()
            unique_uuids = []
            for uuid in valid_uuids:
                if uuid not in seen:
                    seen.add(uuid)
                    unique_uuids.append(uuid)
            
            return unique_uuids, invalid_tokens
        
        # Parsear los UUIDs
        valid_uuids, invalid_tokens = parse_uuids(uuid_text)
        
        # Generar feedback
        feedback_components = []
        
        if valid_uuids:
            # Mostrar UUIDs válidos detectados
            feedback_components.append(
                html.Div([
                    html.Div([
                        html.I(className="fas fa-check-circle me-2 text-success"),
                        html.Strong(f"{len(valid_uuids)} tarjeta(s) detectada(s):")
                    ], className="mb-2"),
                    html.Div([
                        html.Small(uuid, className="badge bg-success me-1 mb-1") 
                        for uuid in valid_uuids[:10]  # Mostrar máximo 10 para no saturar
                    ]),
                    html.Small(
                        f"{'... y ' + str(len(valid_uuids) - 10) + ' más' if len(valid_uuids) > 10 else ''}",
                        className="text-muted"
                    ) if len(valid_uuids) > 10 else html.Div()
                ], className="mb-2")
            )
        
        if invalid_tokens:
            # Mostrar tokens inválidos
            feedback_components.append(
                html.Div([
                    html.Div([
                        html.I(className="fas fa-exclamation-triangle me-2 text-warning"),
                        html.Strong(f"{len(invalid_tokens)} token(s) no válido(s):")
                    ], className="mb-2"),
                    html.Div([
                        html.Small(token, className="badge bg-warning text-dark me-1 mb-1") 
                        for token in invalid_tokens[:5]  # Mostrar máximo 5
                    ]),
                    html.Small(
                        f"{'... y ' + str(len(invalid_tokens) - 5) + ' más' if len(invalid_tokens) > 5 else ''}",
                        className="text-muted"
                    ) if len(invalid_tokens) > 5 else html.Div()
                ], className="mb-2")
            )
        
        # Determinar el estado de validación
        has_valid = len(valid_uuids) > 0
        has_invalid = len(invalid_tokens) > 0
        
        if has_valid and not has_invalid:
            # Solo UUIDs válidos
            return True, False, html.Div(feedback_components, className="alert alert-success py-2")
        elif has_valid and has_invalid:
            # Mezcla de válidos e inválidos
            return True, True, html.Div(feedback_components, className="alert alert-warning py-2")
        elif has_invalid and not has_valid:
            # Solo tokens inválidos
            return False, True, html.Div(feedback_components, className="alert alert-danger py-2")
        else:
            # Texto vacío o sin tokens reconocibles
            return False, False, html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "Ingrese uno o más UUIDs de tarjetas NFC"
            ], className="text-muted")
    
    # Función para actualizar una cerradura individual
    def update_master_card_for_lock(device, uuid_value, jwt_token):
        """
        Actualiza el UUID de la tarjeta NFC para una cerradura específica,
        usando cualquier slot disponible.
        
        Args:
            device: Diccionario con datos de la cerradura
            uuid_value: UUID de la tarjeta NFC
            jwt_token: Token JWT para autenticación
            
        Returns:
            Tupla (success, message) con el resultado de la operación
        """
        from utils.nfc_helper import get_available_slots, check_card_exists
        
        # Usar el ID canónico del dispositivo si está disponible
        device_id = device.get("real_device_id", device.get("device_id"))
        # Extraer el gateway_id del dispositivo
        gateway_id = device.get("gateway_id")
        # Extraer el asset_id si está disponible (útil para búsquedas adicionales de gateway_id)
        asset_id = device.get("asset_id")
        # Otros datos útiles para diagnóstico
        display_name = device.get("display_name", device.get("lock_name", "Cerradura desconocida"))
        
        # Registrar todos los datos relevantes para diagnóstico
        logger.info(f"Actualizando tarjeta para: device_id={device_id}, gateway_id={gateway_id}, asset_id={asset_id}, display_name={display_name}")
        
        if not device_id:
            logger.error(f"Falta device_id en la actualización de tarjeta NFC")
            return False, "Falta ID del dispositivo"
            
        if not gateway_id:
            logger.error(f"Falta gateway_id para el dispositivo {device_id}")
            return False, f"Falta el ID del gateway necesario para el dispositivo {device_id}"
        
        if not asset_id:
            logger.warning(f"Falta asset_id para el dispositivo {device_id}. Algunas operaciones podrían fallar.")
        
        try:
            # Verificar si la tarjeta ya existe en algún slot
            card_exists, existing_slot = check_card_exists(device, uuid_value)
            if card_exists:
                logger.info(f"La tarjeta {uuid_value} ya existe en el slot {existing_slot} del dispositivo {device_id}")
                return True, f"La tarjeta ya existe en el slot {existing_slot}"
            
            # Logging para depuración
            logger.debug(f"Buscando slots disponibles para dispositivo {device_id} ({display_name}) con {len(device.get('sensors', []))} sensores")
            
            # Para el caso de dispositivos sin sensores definidos, crear una estructura básica
            if "sensors" not in device or not device["sensors"]:
                logger.warning(f"Dispositivo {device_id} no tiene sensores definidos, creando estructura básica")
                device = {
                    "device_id": device_id,
                    "real_device_id": device_id,
                    "gateway_id": gateway_id,
                    "asset_id": asset_id,
                    "sensors": []  # Lista vacía de sensores
                }
            
            # Encontrar un slot disponible
            available_slots = get_available_slots(device)
            logger.info(f"Slots disponibles para dispositivo {device_id}: {available_slots}")
            
            if not available_slots:
                # En caso de no encontrar slots, usar slots predeterminados como respaldo
                logger.warning(f"No se encontraron slots disponibles para {device_id}, usando slots predeterminados")
                available_slots = [str(i) for i in range(7, 20)]
                if not available_slots:
                    logger.error(f"No hay slots disponibles en el dispositivo {device_id}")
                    return False, "No hay slots disponibles para asignar la tarjeta"
            
            # Usar el primer slot disponible
            slot_number = available_slots[0]
            logger.info(f"Usando slot disponible {slot_number} para dispositivo {device_id}")
            
            # Asegurar formato correcto
            if ":" not in uuid_value and "-" not in uuid_value and len(uuid_value) == 8:
                # Convertir AABBCCDD a AA:BB:CC:DD
                uuid_formatted = ":".join([uuid_value[i:i+2] for i in range(0, len(uuid_value), 2)])
            else:
                uuid_formatted = uuid_value
                
            # Llamar a la API para actualizar el código NFC
            from utils.api import update_nfc_code_value
            
            # Registrar la llamada para diagnóstico
            logger.info(f"Actualizando tarjeta NFC en slot {slot_number} para dispositivo {device_id}, gateway {gateway_id}, UUID: {uuid_formatted}")
            
            success, response = update_nfc_code_value(
                asset_id=asset_id,  # Pasar el asset_id para ayudar a encontrar el gateway_id si falta
                device_id=device_id, 
                sensor_id=slot_number,  # Usamos el slot seleccionado disponible
                new_value=uuid_formatted, 
                jwt_token=jwt_token,
                gateway_id=gateway_id,
                is_master_card=slot_number == "7"  # Es tarjeta maestra si es el slot 7
            )
            
            if success:
                logger.info(f"Tarjeta asignada correctamente al slot {slot_number} para dispositivo {device_id}")
                return True, f"Actualizado correctamente en slot {slot_number}"
            else:
                # Manejar respuesta según su tipo
                error_message = str(response)
                
                # Detectar errores específicos de autenticación
                if "Token expirado" in error_message or "Token JWT expirado" in error_message:
                    logger.error(f"Error de token expirado al actualizar tarjeta NFC para {device_id}")
                    return False, "Error de autenticación: Su sesión ha expirado. Por favor, recargue la página e inicie sesión nuevamente."
                elif "401" in error_message or "Credenciales inválidas" in error_message:
                    logger.error(f"Error de autenticación 401 al actualizar tarjeta NFC para {device_id}")
                    return False, "Error de autenticación: Sus credenciales no son válidas. Por favor, inicie sesión nuevamente."
                elif isinstance(response, dict):
                    error_msg = response.get("error", "Error desconocido")
                    logger.error(f"Error al actualizar tarjeta NFC para {device_id}: {error_msg}")
                    return False, f"Error: {error_msg}"
                elif "503" in str(response):
                    # Manejar específicamente el error 503 Service Unavailable
                    logger.error(f"Error 503 (Servicio no disponible) al actualizar tarjeta NFC para {device_id}")
                    return False, "Error: Servicio no disponible. Intente más tarde."
                elif "404" in str(response):
                    # Manejar específicamente el error 404 Not Found (posible problema de gateway_id)
                    logger.error(f"Error 404 (No encontrado) al actualizar tarjeta NFC para {device_id}. URL posiblemente incorrecta con gateway_id: {gateway_id}")
                    return False, "Error: Dispositivo o endpoint no encontrado. Verifique el gateway_id."
                else:
                    # Si es una cadena u otro tipo, usarla directamente
                    logger.error(f"Error al actualizar tarjeta NFC para {device_id}: {response}")
                    return False, f"Error: {response}"
                
        except Exception as e:
            logger.error(f"Error actualizando tarjeta NFC para {device_id}: {str(e)}")
            return False, f"Error: {str(e)}"
    
    # Función para desasignar una tarjeta maestra de una cerradura individual
    def unassign_master_card_for_lock(device, jwt_token, uuid_value=None):
        """
        Desasigna una tarjeta maestra (o cualquier tarjeta) de una cerradura específica.
        Si se proporciona un UUID, intentará buscar ese UUID específico.
        Si no se proporciona UUID o no se encuentra, desasignará la tarjeta maestra (slot 7).
        
        Args:
            device: Diccionario con datos de la cerradura
            jwt_token: Token JWT para autenticación
            uuid_value: UUID de la tarjeta a desasignar (opcional)
            
        Returns:
            Tupla (success, message) con el resultado de la operación
        """
        from utils.nfc_helper import check_card_exists, get_master_card_slot
        
        # Usar el ID canónico del dispositivo si está disponible
        device_id = device.get("real_device_id", device.get("device_id"))
        # Extraer el gateway_id del dispositivo
        gateway_id = device.get("gateway_id")
        # Extraer el asset_id si está disponible
        asset_id = device.get("asset_id")
        
        # Registrar todos los datos relevantes para diagnóstico
        logger.info(f"Desasignando tarjeta para: device_id={device_id}, gateway_id={gateway_id}, asset_id={asset_id}, uuid_value={uuid_value}")
        
        if not device_id:
            logger.error(f"Falta device_id en la desasignación de tarjeta NFC")
            return False, "No se pudo desasignar la tarjeta: falta identificador del dispositivo"
            
        if not gateway_id:
            logger.error(f"Falta gateway_id para el dispositivo {device_id}")
            return False, f"No se pudo desasignar la tarjeta: falta el ID del gateway para el dispositivo {device_id}"
        
        if not asset_id:
            logger.error(f"Falta asset_id en la desasignación de tarjeta NFC para device_id={device_id}")
            return False, "No se pudo desasignar la tarjeta: falta identificador del asset"
            
        # Obtener datos de sensores para el dispositivo si no tenemos uuid_value
        # o para verificar que el uuid_value existe en el dispositivo
        try:
            from utils.nfc_helper import get_available_slots
            
            # Si hay uuid_value, buscar en qué slots está para desasignar solo esos
            # Si no hay uuid_value, desasignar todos los slots con valores no vacíos
            from utils.api import get_device_sensors
            sensor_data = get_device_sensors(asset_id, device_id, jwt_token, gateway_id)
            
            # Función auxiliar para normalizar UUIDs (eliminar símbolos, espacios, etc.)
            def normalize_uuid(uuid_str):
                if not uuid_str:
                    return ""
                # Eliminar caracteres no alfanuméricos y convertir a mayúsculas
                import re
                # Conservamos sólo letras, números y caracteres ':'
                normalized = re.sub(r'[^A-Za-z0-9:]', '', uuid_str).upper()
                # Eliminar también los dos puntos para una comparación más flexible
                return normalized.replace(':', '')
            
            if uuid_value:
                normalized_uuid = normalize_uuid(uuid_value)
                slots_to_unassign = []
                
                # Buscar en todos los sensores NFC el uuid normalizado
                for sensor_id, sensor_value in sensor_data.items():
                    # Ignorar sensores sin valores
                    if not sensor_value or sensor_value.strip() == '':
                        continue
                    
                    # Normalizar el valor del sensor para comparar
                    normalized_sensor_value = normalize_uuid(sensor_value)
                    
                    # Si coincide con el uuid proporcionado (ignorando casos, símbolos y espacios)
                    if normalized_sensor_value == normalized_uuid:
                        slots_to_unassign.append(sensor_id)
                
                # Si no se encontró la tarjeta específica, verificar si hay una tarjeta maestra (slot 7)
                # y permitir desasignarla independientemente del UUID proporcionado
                if not slots_to_unassign and "7" in sensor_data and sensor_data["7"] and sensor_data["7"].strip():
                    logger.info(f"No se encontró la tarjeta {uuid_value}, pero se desasignará la tarjeta maestra existente")
                    slots_to_unassign.append("7")
                
                if not slots_to_unassign:
                    logger.info(f"La tarjeta {uuid_value} no está asignada al dispositivo {device_id}")
                    return False, f"La tarjeta {uuid_value} no está asignada a la cerradura seleccionada"
                    
                logger.info(f"Encontrada tarjeta {uuid_value} en slots {slots_to_unassign} del dispositivo {device_id}")
            else:
                # Si no se proporciona uuid_value, desasignar todos los slots con valores
                slots_to_unassign = []
                for sensor_id, sensor_value in sensor_data.items():
                    if sensor_value and sensor_value.strip() != '':
                        slots_to_unassign.append(sensor_id)
                
                if not slots_to_unassign:
                    logger.info(f"No hay tarjetas asignadas al dispositivo {device_id}")
                    return False, "No hay tarjetas asignadas a la cerradura seleccionada"
            
            # Desasignar todas las tarjetas encontradas
            success_count = 0
            errors = []
            
            for slot in slots_to_unassign:
                try:
                    from utils.api import update_nfc_code_value
                    
                    # Registrar la llamada para diagnóstico
                    logger.info(f"Desasignando tarjeta NFC en slot {slot} para dispositivo {device_id}, gateway {gateway_id}")
                    
                    success, response = update_nfc_code_value(
                        asset_id=asset_id,
                        device_id=device_id, 
                        sensor_id=slot,
                        new_value="",  # Valor vacío para desasignar
                        jwt_token=jwt_token,
                        gateway_id=gateway_id
                    )
                    
                    if success:
                        success_count += 1
                    else:
                        # Intentar extraer mensaje de error más legible y categorizar errores de autenticación
                        if isinstance(response, dict):
                            error_msg = response.get("error", json.dumps(response))
                        elif "503" in str(response):
                            error_msg = "Servicio no disponible. Intente más tarde."
                        elif "404" in str(response):
                            error_msg = "Dispositivo o endpoint no encontrado."
                        elif "401" in str(response) or "unauthorized" in str(response).lower():
                            error_msg = "Error de autenticación. Su sesión puede haber expirado."
                        elif "token" in str(response).lower() or "jwt" in str(response).lower():
                            error_msg = "Error de autenticación. Su sesión puede haber expirado."
                        else:
                            error_msg = str(response)
                        
                        errors.append(f"Error en slot {slot}: {error_msg}")
                except Exception as e:
                    logger.error(f"Error al desasignar tarjeta en slot {slot}: {str(e)}")
                    # Categorizar excepciones relacionadas con autenticación
                    if "token" in str(e).lower() or "jwt" in str(e).lower() or "auth" in str(e).lower():
                        errors.append(f"Error en slot {slot}: Error de autenticación - {str(e)}")
                    else:
                        errors.append(f"Error en slot {slot}: {str(e)}")
            
            if success_count == len(slots_to_unassign):
                return True, f"Se desasignaron {success_count} tarjetas exitosamente"
            elif success_count > 0:
                return True, f"Se desasignaron {success_count} de {len(slots_to_unassign)} tarjetas. Errores: {'; '.join(errors)}"
            else:
                # Verificar si todos los errores son de autenticación
                auth_error_count = sum(1 for error in errors if "autenticación" in error.lower())
                if auth_error_count == len(errors):
                    return False, "Error de autenticación. Su sesión puede haber expirado."
            # else:
            #    return False, f"No se pudo desasignar ninguna tarjeta. Errores: {'; '.join(errors)}"
                
        except Exception as e:
            logger.error(f"Error al desasignar tarjeta NFC: {str(e)}")
            return False, f"Error al desasignar tarjeta: {str(e)}"
    
    # Callback para asignar la tarjeta maestra a múltiples cerraduras
    @app.callback(
        [Output("unassign-card-modal", "is_open"),
         Output("unassign-card-confirm", "disabled")],
        [Input("master-card-unassign-button", "n_clicks"),
         Input("unassign-card-cancel", "n_clicks"),
         Input("unassign-card-confirm", "n_clicks")],
        [State("unassign-card-modal", "is_open"),
         State("nfc-grid-table", "selected_row_ids"),
         State("nfc-grid-table", "data")]
    )
    @handle_exceptions(default_return=[False, False])
    def toggle_unassign_card_modal(unassign_clicks, cancel_clicks, confirm_clicks, is_open, selected_row_ids, table_data):
        if not any([unassign_clicks, cancel_clicks, confirm_clicks]):
            return is_open, False
        
        ctx = dash.callback_context
        if not ctx.triggered:
            return is_open, False
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == "master-card-unassign-button":
            # Solo abrir si hay filas seleccionadas
            if selected_row_ids:
                return True, False
            else:
                return False, True  # Disable confirm button if no rows selected
        elif button_id in ["unassign-card-cancel", "unassign-card-confirm"]:
            return False, False
        
        return is_open, False  # Keep the confirm button enabled in other cases
    
    # Callback para el botón de pegar desde portapapeles (para desasignación)
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
        Output("unassign-card-uuid-input", "value"),
        Input("unassign-card-paste-button", "n_clicks"),
        prevent_initial_call=True
    )
    
    # Callback para validar el formato de UUID (para desasignación)
    @app.callback(
        [Output("unassign-card-uuid-input", "valid"),
         Output("unassign-card-uuid-input", "invalid"),
         Output("unassign-card-feedback", "children")],
        [Input("unassign-card-uuid-input", "value")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=[False, False, html.Div()])
    def validate_multiple_unassign_uuid_input(uuid_text):
        # Si está vacío, es válido (significa desasignar TODAS las tarjetas)
        if not uuid_text or len(uuid_text.strip()) == 0:
            return False, False, html.Div([
                html.I(className="fas fa-info-circle me-2"),
                html.Strong("Modo: Desasignar TODAS las tarjetas"),
                html.Br(),
                html.Small("Se eliminarán todas las tarjetas NFC de las cerraduras seleccionadas", className="text-muted")
            ], className="alert alert-info py-2")
        
        # Función para parsear múltiples UUIDs del texto (reutilizada de asignación)
        def parse_uuids(text):
            import re
            
            # Normalizar separadores: reemplazar comas y puntos y comas con saltos de línea
            normalized_text = text.replace(',', '\n').replace(';', '\n')
            
            # Dividir por líneas y espacios
            lines = normalized_text.split('\n')
            all_tokens = []
            for line in lines:
                # Dividir cada línea por espacios también
                tokens = line.strip().split()
                all_tokens.extend(tokens)
            
            # Filtrar tokens vacíos
            potential_uuids = [token.strip() for token in all_tokens if token.strip()]
            
            # Validar cada token como UUID
            valid_uuids = []
            invalid_tokens = []
            
            # Patrones para diferentes formatos de UUID
            pattern_colon = r'^([0-9A-F]{2}:){3}[0-9A-F]{2}$'  # AA:BB:CC:DD
            pattern_dash = r'^([0-9A-F]{2}-){3}[0-9A-F]{2}$'   # AA-BB-CC-DD
            pattern_plain = r'^[0-9A-F]{8}$'                   # AABBCCDD
            pattern_long = r'^[0-9A-F]{12,16}$'                # AABBCCDDEE o más largo
            
            for token in potential_uuids:
                token_upper = token.upper()
                
                # Verificar si coincide con algún patrón
                if (re.match(pattern_colon, token_upper, re.IGNORECASE) or 
                    re.match(pattern_dash, token_upper, re.IGNORECASE) or 
                    re.match(pattern_plain, token_upper, re.IGNORECASE) or
                    re.match(pattern_long, token_upper, re.IGNORECASE)):
                    
                    # Normalizar formato a AA:BB:CC:DD para consistencia
                    if ':' not in token_upper and '-' not in token_upper:
                        # Convertir AABBCCDD a AA:BB:CC:DD
                        if len(token_upper) >= 8:
                            formatted = ':'.join([token_upper[i:i+2] for i in range(0, min(8, len(token_upper)), 2)])
                            valid_uuids.append(formatted)
                    else:
                        # Si es muy corto, mantenerlo como está pero marcarlo válido si pasa el patrón
                        valid_uuids.append(token_upper)

                else:
                    invalid_tokens.append(token)
            
            # Eliminar duplicados manteniendo el orden
            seen = set()
            unique_uuids = []
            for uuid in valid_uuids:
                if uuid not in seen:
                    seen.add(uuid)
                    unique_uuids.append(uuid)
            
            return unique_uuids, invalid_tokens
        
        # Parsear los UUIDs
        valid_uuids, invalid_tokens = parse_uuids(uuid_text)
        
        # Generar feedback
        feedback_components = []
        
        if valid_uuids:
            # Mostrar UUIDs válidos detectados
            feedback_components.append(
                html.Div([
                    html.Div([
                        html.I(className="fas fa-trash-alt me-2 text-success"),
                        html.Strong(f"Modo: Desasignar {len(valid_uuids)} tarjeta(s) específica(s):")
                    ], className="mb-2"),
                    html.Div([
                        html.Small(uuid, className="badge bg-danger me-1 mb-1") 
                        for uuid in valid_uuids[:10]  # Mostrar máximo 10 para no saturar
                    ]),
                    html.Small(
                        f"{'... y ' + str(len(valid_uuids) - 10) + ' más' if len(valid_uuids) > 10 else ''}",
                        className="text-muted"
                    ) if len(valid_uuids) > 10 else html.Div()
                ], className="mb-2")
            )
        
        if invalid_tokens:
            # Mostrar tokens inválidos
            feedback_components.append(
                html.Div([
                    html.Div([
                        html.I(className="fas fa-exclamation-triangle me-2 text-warning"),
                        html.Strong(f"{len(invalid_tokens)} token(s) no válido(s):")
                    ], className="mb-2"),
                    html.Div([
                        html.Small(token, className="badge bg-warning text-dark me-1 mb-1") 
                        for token in invalid_tokens[:5]  # Mostrar máximo 5
                    ]),
                    html.Small(
                        f"{'... y ' + str(len(invalid_tokens) - 5) + ' más' if len(invalid_tokens) > 5 else ''}",
                        className="text-muted"
                    ) if len(invalid_tokens) > 5 else html.Div()
                ], className="mb-2")
            )
        
        # Determinar el estado de validación
        has_valid = len(valid_uuids) > 0
        has_invalid = len(invalid_tokens) > 0
        
        if has_valid and not has_invalid:
            # Solo UUIDs válidos
            return True, False, html.Div(feedback_components, className="alert alert-success py-2")
        elif has_valid and has_invalid:
            # Mezcla de válidos e inválidos
            return True, True, html.Div(feedback_components, className="alert alert-warning py-2")
        elif has_invalid and not has_valid:
            # Solo tokens inválidos
            return False, True, html.Div(feedback_components, className="alert alert-danger py-2")
        else:
            # No debería llegar aquí, pero por seguridad
            return False, False, html.Div([
                html.I(className="fas fa-info-circle me-2"),
                "Ingrese UUIDs específicos o deje vacío para desasignar todas las tarjetas"
            ], className="text-muted")

    # Callback para desasignar la tarjeta maestra de múltiples cerraduras
    @app.callback(
        [Output("unassign-card-results-container", "children"),
         Output("unassign-card-results-container", "style"),
         Output("unassign-card-confirm", "disabled", allow_duplicate=True),
         Output("unassign-card-loading", "children"),
         Output("nfc-update-trigger", "data", allow_duplicate=True)],
        [Input("unassign-card-confirm", "n_clicks")],
        [State("unassign-card-uuid-input", "value"),
         State("unassign-card-selected-devices", "data"),
         State("jwt-token-store", "data"),
         State("nfc-update-trigger", "data")],
        prevent_initial_call=True,
        id='unassign_multiple_nfc_cards_callback'  # Cambiar ID para reflejar nueva funcionalidad
    )
    @handle_exceptions(default_return=[None, {"display": "none"}, False, "", dash.no_update])
    def unassign_multiple_nfc_cards(confirm_clicks, uuid_text, selected_devices_data, token_data, current_trigger_data):
        # Si no hay confirmación, no hacer nada
        if not confirm_clicks:
            return None, {"display": "none"}, False, "", dash.no_update
            
        # Si no hay token o dispositivos seleccionados, mostrar error
        if not token_data or not selected_devices_data or not selected_devices_data.get("devices"):
            return html.Div(
                "No hay suficiente información para proceder con la desasignación",
                className="alert alert-danger"
            ), {"display": "block"}, False, "", dash.no_update
            
        token = token_data.get("token")
        if not token:
            return html.Div(
                "No hay autenticación disponible para desasignar las tarjetas",
                className="alert alert-danger"
            ), {"display": "block"}, False, "", dash.no_update
            
        # Función para parsear UUIDs del texto de entrada
        def parse_uuids_from_text(text):
            """Parsea y valida UUIDs múltiples desde el texto de entrada"""
            if not text:
                return []
            
            # Reemplazar múltiples separadores con comas
            import re
            text = re.sub(r'[;|\n\r]+', ',', text.strip())
            text = re.sub(r'\s+', ' ', text)  # Normalizar espacios
            
            # Dividir por comas y espacios
            potential_uuids = [uuid.strip() for uuid in text.replace(' ', ',').split(',') if uuid.strip()]
            
            # Validar y normalizar cada UUID
            valid_uuids = []
            uuid_pattern = re.compile(r'^[0-9A-Fa-f:]{8,}$|^[0-9A-Fa-f-]{8,}$|^[0-9A-Fa-f]{8,}$')
            
            for uuid in potential_uuids:
                if uuid_pattern.match(uuid):
                    # Normalizar formato
                    clean_uuid = uuid.replace(':', '').replace('-', '').upper()
                    if len(clean_uuid) >= 8:
                        valid_uuids.append(uuid)  # Mantener formato original
            
            return valid_uuids
        
        # Parsear UUIDs del input (vacío significa desasignar todas)
        uuid_list = parse_uuids_from_text(uuid_text) if uuid_text and uuid_text.strip() else []
        mode = "specific" if uuid_list else "all"
            
        devices = selected_devices_data.get("devices", [])
        logger.info(f"Desasignando tarjetas ({'específicas' if mode == 'specific' else 'TODAS'}) para {len(devices)} dispositivos")
        
        # Verificar que todos los dispositivos tengan gateway_id
        devices_without_gateway = [d.get("name", f"Device {d.get('device_id', 'unknown')}") 
                                for d in devices if not d.get("gateway_id")]
        
        if devices_without_gateway:
            device_list = ", ".join(devices_without_gateway[:3])
            if len(devices_without_gateway) > 3:
                device_list += f" y {len(devices_without_gateway) - 3} más"
                
            return html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"No se puede continuar: Falta gateway_id en los dispositivos: {device_list}"
            ], className="alert alert-danger"), {"display": "block"}, False, "", dash.no_update
        
        # Mostrar indicador de carga mientras se procesan las actualizaciones
        loading_indicator = dbc.Spinner(size="sm", color="primary")
        
        # Procesar en paralelo para mejor rendimiento
        from concurrent.futures import ThreadPoolExecutor
        import time
        
        results = []
        device_results = {}
        
        def process_device_unassignment(device):
            """Procesa la desasignación para un dispositivo específico"""
            device_name = device.get("name", "Cerradura sin nombre")
            try:
                # Llamar a la nueva función de múltiples tarjetas
                success, message, details = unassign_multiple_cards_for_lock(device, uuid_list, token)
                
                return {
                    "device": device,
                    "device_name": device_name,
                    "success": success,
                    "message": message,
                    "details": details
                }
            except Exception as e:
                logger.error(f"Error desasignando tarjetas para {device_name}: {str(e)}")
                return {
                    "device": device,
                    "device_name": device_name,
                    "success": False,
                    "message": f"Error: {str(e)}",
                    "details": []
                }
        
        # Ejecutar procesamiento en paralelo
        with ThreadPoolExecutor(max_workers=5) as executor:
            device_results_list = list(executor.map(process_device_unassignment, devices))
        
        # Contadores globales
        total_successful = 0
        total_failed = 0
        total_not_found = 0
        total_auth_errors = 0
        devices_with_success = 0
        devices_with_failures = 0
        devices_with_auth_errors = 0
        
        # Procesar resultados de cada dispositivo
        device_summaries = []
        
        for result in device_results_list:
            device_name = result["device_name"]
            success = result["success"]
            message = result["message"]
            details = result["details"]
            
            # Contadores por dispositivo
            device_successful = 0
            device_failed = 0
            device_not_found = 0
            device_auth_errors = 0
            
            # Analizar detalles de cada tarjeta
            for detail in details:
                if detail["status"] == "success":
                    device_successful += 1
                    total_successful += 1
                elif detail["status"] == "not_found":
                    device_not_found += 1
                    total_not_found += 1
                elif detail["status"] == "auth_error":
                    device_auth_errors += 1
                    total_auth_errors += 1
                else:  # failed
                    device_failed += 1
                    total_failed += 1
            
            # Determinar el estatus del dispositivo
            if device_auth_errors > 0:
                devices_with_auth_errors += 1
                status_class = "text-warning"
                icon_class = "fas fa-exclamation-triangle"
            elif device_failed > 0:
                devices_with_failures += 1
                status_class = "text-danger"
                icon_class = "fas fa-times-circle"
            elif device_successful > 0 or device_not_found > 0:
                devices_with_success += 1
                status_class = "text-success"
                icon_class = "fas fa-check-circle"
            else:
                devices_with_failures += 1
                status_class = "text-danger"
                icon_class = "fas fa-times-circle"
            
            # Crear resumen del dispositivo
            device_summary = html.Div([
                html.Div([
                    html.I(className=icon_class, style={"marginRight": "8px"}),
                    html.Strong(f"{device_name}: "),
                    html.Span(message, className=status_class)
                ], className="mb-2"),
                
                # Detalles expandibles si hay múltiples tarjetas
                html.Div([
                    html.Details([
                        html.Summary([
                            html.I(className="fas fa-chevron-right me-2", style={"font-size": "0.8em"}),
                            f"Ver detalles de tarjetas ({len(details)} operaciones)"
                        ], style={"cursor": "pointer", "font-size": "0.9em", "color": "#6c757d"}),
                        html.Div([
                            html.Div([
                                html.Span(f"• {detail['uuid']}: ", className="font-monospace me-2"),
                                html.Span(
                                    detail['message'],
                                    className={
                                        "success": "text-success",
                                        "not_found": "text-info", 
                                        "auth_error": "text-warning",
                                        "failed": "text-danger"
                                    }.get(detail['status'], "text-muted")
                                ),
                                html.Small(
                                    f" (slot {detail['slot']})" if detail.get('slot') else "",
                                    className="text-muted ms-1"
                                )
                            ], className="mb-1") for detail in details
                        ], className="mt-2 ps-3 border-start border-light")
                    ])
                ], className="ms-4") if len(details) > 1 else html.Div()
            ], className="mb-3")
            
            device_summaries.append(device_summary)
        
        # Crear estadísticas del encabezado
        header_stats = []
        
        if mode == "all":
            header_stats.extend([
                html.Span(f"✓ Exitosas: ", className="fw-bold me-1"),
                html.Span(f"{total_successful}", className="text-success me-3"),
                html.Span(f"✗ Fallidas: ", className="fw-bold me-1"),
                html.Span(f"{total_failed}", className="text-danger")
            ])
        else:
            header_stats.extend([
                html.Span(f"✓ Exitosas: ", className="fw-bold me-1"),
                html.Span(f"{total_successful}", className="text-success me-3"),
                html.Span(f"ℹ No encontradas: ", className="fw-bold me-1"),
                html.Span(f"{total_not_found}", className="text-info me-3"),
                html.Span(f"✗ Fallidas: ", className="fw-bold me-1"),
                html.Span(f"{total_failed}", className="text-danger")
            ])
        
        # Añadir información sobre errores de autenticación si los hay
        if total_auth_errors > 0:
            header_stats.extend([
                html.Span(" | ", className="mx-2"),
                html.Span(f"⚠ Auth errors: ", className="fw-bold me-1"),
                html.Span(f"{total_auth_errors}", className="text-warning")
            ])
        
        # Crear el contenedor de resultados
        result_header = html.Div([
            html.H5(f"Resultados de la desasignación {'múltiple' if mode == 'specific' else 'masiva'}", className="mb-3"),
            html.Div(header_stats, className="mb-3")
        ])
        
        # Mensaje final
        if total_failed == 0 and total_auth_errors == 0:
            if mode == "all":
                final_message = html.Div([
                    html.I(className="fas fa-check-circle me-2"),
                    f"Todas las tarjetas desasignadas correctamente de todas las cerraduras ({total_successful} tarjetas en {devices_with_success} dispositivos)"
                ], className="alert alert-success mt-3")
            else:
                if total_not_found > 0:
                    final_message = html.Div([
                        html.I(className="fas fa-info-circle me-2"),
                        f"Operación completada: {total_successful} tarjetas desasignadas, {total_not_found} no se encontraron"
                    ], className="alert alert-info mt-3")
                else:
                    final_message = html.Div([
                        html.I(className="fas fa-check-circle me-2"),
                        f"Todas las tarjetas especificadas desasignadas correctamente ({total_successful} tarjetas)"
                    ], className="alert alert-success mt-3")
        elif total_auth_errors > 0 and total_failed == 0:
            # Solo errores de autenticación
            final_message = html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error de autenticación en {total_auth_errors} operaciones. " +
                f"Su sesión puede haber expirado. Por favor, recargue la página e inicie sesión nuevamente."
            ], className="alert alert-warning mt-3")
        else:
            # Mezcla de errores
            total_errors = total_failed + total_auth_errors
            final_message = html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"La desasignación falló en {total_errors} operaciones: " +
                f"{total_auth_errors} errores de autenticación y {total_failed} otros errores. " +
                f"Revise los detalles para más información."
            ], className="alert alert-warning mt-3")
        
        # Contenedor final de resultados
        results_components = [
            result_header,
            html.Div(device_summaries, className="mt-3"),
            final_message
        ]
        
        # Añadir instrucciones adicionales si hay errores de autenticación
        if total_auth_errors > 0:
            auth_instructions = html.Div([
                html.H6("Instrucciones para resolver errores de autenticación:", className="mt-3 mb-2"),
                html.Ul([
                    html.Li("Recargue la página completa (Ctrl+F5 o Cmd+R)"),
                    html.Li("Inicie sesión nuevamente con sus credenciales"),
                    html.Li("Intente la desasignación de tarjetas nuevamente")
                ], className="mb-0"),
                html.Small(
                    "Nota: Las sesiones expiran automáticamente por seguridad después de un período de inactividad.",
                    className="text-muted"
                )
            ], className="alert alert-light border-warning mt-3")
            results_components.append(auth_instructions)
        
        results_container = html.Div(results_components)
        
        # Actualizar el trigger para refrescar la tabla de NFC
        new_trigger = {"refreshed": True, "timestamp": time.time()}
        
        return results_container, {"display": "block"}, True, loading_indicator, new_trigger

    @app.callback(
        [Output("master-card-results-container", "children"),
         Output("master-card-results-container", "style"),
         Output("master-card-confirm", "disabled", allow_duplicate=True),
         Output("master-card-loading", "children"),
         Output("nfc-update-trigger", "data", allow_duplicate=True)],
        [Input("master-card-confirm", "n_clicks")],
        [State("master-card-uuid-input", "value"),
         State("master-card-selected-devices", "data"),
         State("jwt-token-store", "data"),
         State("nfc-update-trigger", "data")],
        prevent_initial_call=True,
        id='assign_multiple_nfc_cards_callback'  # Cambiar ID para reflejar nueva funcionalidad
    )
    @handle_exceptions(default_return=[None, {"display": "none"}, False, "", dash.no_update])
    def assign_multiple_nfc_cards(confirm_clicks, uuid_text, selected_devices_data, token_data, current_trigger_data):
        # Si no hay confirmación, no hacer nada
        if not confirm_clicks:
            return None, {"display": "none"}, False, "", dash.no_update
        
        # Validar el texto de UUIDs
        if not uuid_text or not uuid_text.strip():
            return html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "Debe ingresar al menos un UUID válido para las tarjetas NFC"
            ], className="alert alert-danger"), {"display": "block"}, True, "", dash.no_update
        
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
                "No hay cerraduras seleccionadas para asignar tarjetas NFC"
            ], className="alert alert-warning"), {"display": "block"}, True, "", dash.no_update
        
        selected_devices = selected_devices_data.get("devices", [])
        if not selected_devices:
            return html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "No hay cerraduras seleccionadas para asignar tarjetas NFC"
            ], className="alert alert-warning"), {"display": "block"}, True, "", dash.no_update
        
        # Parsear múltiples UUIDs del texto
        def parse_uuids_from_text(text):
            if not text:
                return []
            
            import re
            
            # Normalizar separadores
            normalized_text = text.replace(',', '\n').replace(';', '\n')
            
            # Dividir por líneas y espacios
            lines = normalized_text.split('\n')
            all_tokens = []
            for line in lines:
                tokens = line.strip().split()
                all_tokens.extend(tokens)
            
            # Filtrar y validar tokens
            potential_uuids = [token.strip() for token in all_tokens if token.strip()]
            valid_uuids = []
            
            # Patrones para validación
            pattern_colon = r'^([0-9A-F]{2}:){3}[0-9A-F]{2}$'
            pattern_dash = r'^([0-9A-F]{2}-){3}[0-9A-F]{2}$'
            pattern_plain = r'^[0-9A-F]{8}$'
            pattern_long = r'^[0-9A-F]{12,16}$'
            
            for token in potential_uuids:
                token_upper = token.upper()
                
                if (re.match(pattern_colon, token_upper, re.IGNORECASE) or 
                    re.match(pattern_dash, token_upper, re.IGNORECASE) or 
                    re.match(pattern_plain, token_upper, re.IGNORECASE) or
                    re.match(pattern_long, token_upper, re.IGNORECASE)):
                    
                    # Normalizar formato
                    if ':' not in token_upper and '-' not in token_upper:
                        if len(token_upper) >= 8:
                            formatted = ':'.join([token_upper[i:i+2] for i in range(0, min(8, len(token_upper)), 2)])
                            valid_uuids.append(formatted)
                        else:
                            valid_uuids.append(token_upper)
                    else:
                        valid_uuids.append(token_upper)
            
            # Eliminar duplicados manteniendo orden
            seen = set()
            unique_uuids = []
            for uuid in valid_uuids:
                if uuid not in seen:
                    seen.add(uuid)
                    unique_uuids.append(uuid)
            
            return unique_uuids
        
        # Parsear los UUIDs
        uuid_list = parse_uuids_from_text(uuid_text)
        
        if not uuid_list:
            return html.Div([
                html.I(className="fas fa-exclamation-circle me-2"),
                "No se detectaron UUIDs válidos en el texto ingresado"
            ], className="alert alert-danger"), {"display": "block"}, True, "", dash.no_update
        
        # Indicador de carga
        loading_indicator = html.Div(
            f"Procesando {len(uuid_list)} tarjeta(s) en {len(selected_devices)} cerradura(s)...",
            className="text-info"
        )
        
        # Procesar cada dispositivo con múltiples UUIDs
        device_results = []
        total_successful = 0
        total_failed = 0
        total_already_assigned = 0
        total_auth_errors = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Crear un futuro para cada dispositivo
            future_to_device = {
                executor.submit(
                    update_multiple_cards_for_lock, 
                    device, 
                    uuid_list, 
                    token
                ): device for device in selected_devices
            }
            
            # Procesar los resultados
            for future in concurrent.futures.as_completed(future_to_device):
                device = future_to_device[future]
                device_name = device.get("display_name", device.get("lock_name", "Cerradura desconocida"))
                
                try:
                    success, message, card_details = future.result()
                    
                    # Contar resultados por tipo
                    device_successful = sum(1 for detail in card_details if detail["status"] == "success")
                    device_already_assigned = sum(1 for detail in card_details if detail["status"] == "already_assigned")
                    device_auth_errors = sum(1 for detail in card_details if detail["status"] == "auth_error")
                    device_failed = sum(1 for detail in card_details if detail["status"] == "failed")
                    
                    total_successful += device_successful
                    total_already_assigned += device_already_assigned
                    total_auth_errors += device_auth_errors
                    total_failed += device_failed
                    
                    # Determinar icono y clase CSS
                    if device_auth_errors > 0:
                        icon_class = "fas fa-exclamation-triangle text-warning"
                        row_class = "table-warning"
                    elif device_failed > 0:
                        icon_class = "fas fa-times-circle text-danger"
                        row_class = "table-danger"
                    elif device_successful > 0:
                        icon_class = "fas fa-check-circle text-success"
                        row_class = "table-success"
                    else:
                        icon_class = "fas fa-info-circle text-info"
                        row_class = "table-info"
                    
                    # Crear detalles de tarjetas para este dispositivo
                    card_details_html = []
                    for detail in card_details:
                        status_badge_class = {
                            "success": "bg-success",
                            "already_assigned": "bg-info",
                            "auth_error": "bg-warning text-dark",
                            "failed": "bg-danger"
                        }.get(detail["status"], "bg-secondary")
                        
                        card_details_html.append(
                            html.Div([
                                html.Small(detail["uuid"], className="me-2 font-monospace"),
                                html.Small(detail["message"], className=f"badge {status_badge_class}")
                            ], className="mb-1")
                        )
                    
                    device_results.append({
                        "device_name": device_name,
                        "icon_class": icon_class,
                        "row_class": row_class,
                        "message": message,
                        "card_details": card_details_html,
                        "summary": f"{device_successful}✓ {device_already_assigned}ℹ {device_auth_errors}⚠ {device_failed}✗"
                    })
                    
                except Exception as e:
                    logger.error(f"Error procesando dispositivo {device_name}: {str(e)}")
                    device_results.append({
                        "device_name": device_name,
                        "icon_class": "fas fa-times-circle text-danger",
                        "row_class": "table-danger",
                        "message": f"Error: {str(e)}",
                        "card_details": [],
                        "summary": f"0✓ 0ℹ 0⚠ {len(uuid_list)}✗"
                    })
                    total_failed += len(uuid_list)
        
        # Crear tabla de resultados detallada
        result_rows = []
        for result in device_results:
            result_rows.append(
                html.Tr([
                    html.Td(html.I(className=result["icon_class"])),
                    html.Td(result["device_name"]),
                    html.Td(result["message"]),
                    html.Td(result["summary"], className="font-monospace small"),
                    html.Td(result["card_details"] if result["card_details"] else "N/A")
                ], className=result["row_class"])
            )
        
        # Encabezado de resultados
        total_cards_processed = total_successful + total_failed + total_already_assigned + total_auth_errors
        result_header_stats = [
            html.Span(f"Tarjetas procesadas: ", className="fw-bold me-1"),
            html.Span(f"{len(uuid_list)} en {len(selected_devices)} cerraduras", className="me-3"),
            html.Span(f"Exitosas: ", className="fw-bold me-1"),
            html.Span(f"{total_successful}", className="text-success me-3"),
            html.Span(f"Ya asignadas: ", className="fw-bold me-1"),
            html.Span(f"{total_already_assigned}", className="text-info me-3"),
            html.Span(f"Fallidas: ", className="fw-bold me-1"),
            html.Span(f"{total_failed}", className="text-danger")
        ]
        
        if total_auth_errors > 0:
            result_header_stats.extend([
                html.Span(" | ", className="mx-2"),
                html.Span(f"Errores de autenticación: ", className="fw-bold me-1"),
                html.Span(f"{total_auth_errors}", className="text-warning")
            ])
        
        result_header = html.Div([
            html.H5("Resultados de la Asignación Múltiple", className="mb-3"),
            html.Div(result_header_stats, className="mb-3")
        ])
        
        # Tabla de resultados
        results_table = html.Table([
            html.Thead([
                html.Tr([
                    html.Th(""),
                    html.Th("Cerradura"),
                    html.Th("Resultado General"),
                    html.Th("Resumen", title="✓=Exitosas, ℹ=Ya asignadas, ⚠=Auth error, ✗=Fallidas"),
                    html.Th("Detalles por Tarjeta")
                ])
            ]),
            html.Tbody(result_rows)
        ], className="table table-striped")
        
        # Mensaje final
        if total_failed == 0 and total_auth_errors == 0:
            if total_already_assigned == 0:
                final_message = html.Div([
                    html.I(className="fas fa-check-circle me-2"),
                    f"Todas las tarjetas ({total_successful}) asignadas correctamente"
                ], className="alert alert-success mt-3")
            else:
                final_message = html.Div([
                    html.I(className="fas fa-check-circle me-2"),
                    f"{total_successful} tarjetas asignadas correctamente, {total_already_assigned} ya estaban asignadas"
                ], className="alert alert-success mt-3")
        elif total_auth_errors > 0:
            final_message = html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error de autenticación en {total_auth_errors} asignaciones. Su sesión puede haber expirado."
            ], className="alert alert-warning mt-3")
        else:
            final_message = html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"La asignación falló en {total_failed} casos. Revise los detalles para más información."
            ], className="alert alert-warning mt-3")
        
        # Contenedor final de resultados
        results_components = [
            result_header,
            results_table,
            final_message
        ]
        
        # Añadir instrucciones adicionales si hay errores de autenticación
        if total_auth_errors > 0:
            auth_instructions = html.Div([
                html.H6("Instrucciones para resolver errores de autenticación:", className="mt-3 mb-2"),
                html.Ul([
                    html.Li("Recargue la página completa (Ctrl+F5 o Cmd+R)"),
                    html.Li("Inicie sesión nuevamente con sus credenciales"),
                    html.Li("Intente la asignación de tarjetas nuevamente")
                ], className="mb-0"),
                html.Small(
                    "Nota: Las sesiones expiran automáticamente por seguridad después de un período de inactividad.",
                    className="text-muted"
                )
            ], className="alert alert-light border-warning mt-3")
            results_components.append(auth_instructions)
        
        results_container = html.Div(results_components)
        
        # Crear trigger para actualizar la tabla después de la asignación
        current_count = current_trigger_data.get("count", 0) if current_trigger_data else 0
        updated_trigger = {"updated": True, "count": current_count + 1, "refreshed": True}
        
        return results_container, {"display": "block"}, True, loading_indicator, updated_trigger

    # Callback para actualizar el data store de la matriz NFC cuando se cambia a esta pestaña
    @app.callback(
        Output("nfc-grid-data-store", "data"),
        [Input("smart-locks-tabs", "active_tab"),
         Input("smart-locks-data-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return={"asset_ids": [], "asset_names": {}, "timestamp": ""})
    def update_nfc_grid_data_store(active_tab, devices_data):
        """
        Actualiza el data store para la matriz NFC cuando se cambia a la pestaña correspondiente.
        Esto prepara los datos necesarios para cargar los sensores NFC.
        """
        # Solo proceder si es la pestaña de matriz NFC
        if not active_tab or active_tab != "nfc-grid-tab" or not devices_data:
            logger.info(f"No actualizando nfc-grid-data-store: pestaña={active_tab}, datos disponibles={bool(devices_data)}")
            return dash.no_update
        
        logger.info(f"Actualizando nfc-grid-data-store con {len(devices_data)} dispositivos")
        
        # Log first device structure for debugging
        if devices_data and len(devices_data) > 0:
            logger.info(f"First device structure: {list(devices_data[0].keys()) if isinstance(devices_data[0], dict) else 'Not a dict'}")
            
            # Check if we have gateway_id and real_device_id
            has_gateway_id = any('gateway_id' in d for d in devices_data if isinstance(d, dict))
            has_real_device_id = any('real_device_id' in d for d in devices_data if isinstance(d, dict))
            logger.info(f"Devices have gateway_id: {has_gateway_id}, real_device_id: {has_real_device_id}")
        else:
            logger.warning("No hay dispositivos en devices_data")
        
        # Recolectar todos los asset_ids únicos de los dispositivos
        asset_ids = set()
        asset_names = {}
        
        for device in devices_data:
            asset_id = device.get("asset_id")
            if not asset_id:
                continue
                
            asset_ids.add(asset_id)
            
            # Intentar obtener el nombre del asset del scope si está disponible
            scope = device.get("scope", {})
            if scope.get("type") == "Asset" and "name" in scope:
                asset_names[asset_id] = scope["name"]
                
        logger.info(f"Encontrados {len(asset_ids)} assets únicos para la matriz NFC")
        if asset_ids:
            logger.info(f"Asset IDs: {list(asset_ids)}")
        
        # Devolver los datos formateados para la matriz
        return {
            "asset_ids": list(asset_ids),
            "asset_names": asset_names,
            "timestamp": datetime.now().timestamp()  # Para forzar actualizaciones
        }

    # Callback clientside para detectar clics en botones de asignación/desasignación
    app.clientside_callback(
        """
        function(n_assign, n_unassign) {
            if (n_assign) {
                console.log("Botón de asignación clickeado: " + n_assign + " veces");
            }
            if (n_unassign) {
                console.log("Botón de desasignación clickeado: " + n_unassign + " veces");
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("nfc-grid-error-container", "style"),
        [Input("master-card-assign-button", "n_clicks"),
         Input("master-card-unassign-button", "n_clicks")],
        prevent_initial_call=True
    )

    # Callback específico para manejar directamente los botones de asignación/desasignación
    @app.callback(
        [Output("master-card-modal", "is_open", allow_duplicate=True),
         Output("unassign-card-modal", "is_open", allow_duplicate=True),
         Output("master-card-confirm", "disabled", allow_duplicate=True),
         Output("unassign-card-confirm", "disabled", allow_duplicate=True),
         Output("nfc-grid-error-container", "children")],
        [Input("master-card-assign-button", "n_clicks"),
         Input("master-card-unassign-button", "n_clicks")],
        [State("nfc-grid-table", "selected_row_ids")],
        prevent_initial_call=True,
        id='direct_buttons_handler_callback'
    )
    @handle_exceptions(default_return=[dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update])
    def handle_nfc_buttons_directly(assign_clicks, unassign_clicks, selected_row_ids):
        """
        Callback específico para manejar los botones de asignar/desasignar tarjetas NFC
        """
        ctx = dash.callback_context
        if not ctx.triggered:
            logger.warning("Callback directo de botones NFC activado sin trigger")
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Verificar si hay filas seleccionadas
        if not selected_row_ids or len(selected_row_ids) == 0:
            error_msg = html.Div([
                html.I(className="fas fa-exclamation-circle me-2 text-danger"),
                "Debe seleccionar al menos una cerradura antes de asignar o desasignar tarjetas"
            ], className="alert alert-danger")
            logger.warning(f"Intento de usar {button_id} sin filas seleccionadas")
            return False, False, False, False, error_msg
        
        # Manejar clic en botón de asignación
        if button_id == "master-card-assign-button" and assign_clicks:
            logger.info(f"Abriendo modal de asignación directamente. Filas seleccionadas: {len(selected_row_ids)}")
            return True, False, False, dash.no_update, dash.no_update
            
        # Manejar clic en botón de desasignación
        elif button_id == "master-card-unassign-button" and unassign_clicks:
            logger.info(f"Abriendo modal de desasignación directamente. Filas seleccionadas: {len(selected_row_ids)}")
            return False, True, dash.no_update, False, dash.no_update
            
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # Callbacks adicionales para cerrar los modales
    @app.callback(
        [Output("master-card-modal", "is_open", allow_duplicate=True),
         Output("master-card-confirm", "disabled", allow_duplicate=True)],
        [Input("master-card-cancel", "n_clicks"),
         Input("master-card-confirm", "n_clicks")],
        [State("master-card-modal", "is_open")],
        prevent_initial_call=True,
        id='close_assign_modal_callback'
    )
    def close_assign_modal(cancel_clicks, confirm_clicks, is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update
            
        if is_open:
            return False, False  # Reset disabled state to False
        return dash.no_update, dash.no_update
    
    @app.callback(
        [Output("unassign-card-modal", "is_open", allow_duplicate=True),
         Output("unassign-card-confirm", "disabled", allow_duplicate=True)],
        [Input("unassign-card-cancel", "n_clicks"),
         Input("unassign-card-confirm", "n_clicks")],
        [State("unassign-card-modal", "is_open")],
        prevent_initial_call=True,
        id='close_unassign_modal_callback'
    )
    def close_unassign_modal(cancel_clicks, confirm_clicks, is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update
            
        if is_open:
            return False, False  # Reset disabled state to False
        return dash.no_update, dash.no_update

    # Replace the client-side callback with a server-side version
    @app.callback(
        Output("nfc-grid-error-container", "children", allow_duplicate=True),
        [Input("nfc-grid-table", "selected_rows"),
         Input("nfc-grid-table", "selected_row_ids"),
         Input("nfc-grid-table", "data")],
        prevent_initial_call=True,
        id='debug_selected_rows_callback'  # Add a unique ID
    )
    @handle_exceptions(default_return=dash.no_update)
    def debug_selected_rows(selected_rows, selected_row_ids, data):
        """
        Server-side callback to log selected rows for debugging purposes.
        """
        if not selected_row_ids or not data:
            return dash.no_update
            
        # Log selected row IDs for debugging
        logger.info(f"Selected row IDs: {selected_row_ids}")
        
        # Check for basic parsing errors in composite IDs
        id_to_row = {row.get('id'): row for row in data if 'id' in row}
                
        for row_id in selected_row_ids:
            if row_id not in id_to_row:
                logger.error(f"Row ID {row_id} not found in table data")
                continue
                
            # Verify composite ID format
            try:
                parts = row_id.split("-", 2)
                if len(parts) != 3:
                    logger.warning(f"Row ID '{row_id}' is not in expected 'asset-gateway-device' format (got {len(parts)} parts)")
            except Exception as e:
                logger.error(f"Error parsing row ID '{row_id}': {str(e)}")
        
        return dash.no_update

    # Callback para manejar los botones de pegar y limpiar en el modal de múltiples UUIDs
    @app.callback(
        Output("master-card-uuid-input", "value"),
        [Input("master-card-paste-button", "n_clicks"),
         Input("master-card-clear-button", "n_clicks")],
        [State("master-card-uuid-input", "value")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=dash.no_update)
    def handle_paste_clear_buttons(paste_clicks, clear_clicks, current_value):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
            
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == "master-card-clear-button" and clear_clicks:
            # Limpiar el textarea
            return ""
        elif button_id == "master-card-paste-button" and paste_clicks:
            # Para el botón de pegar, simplemente retornamos el valor actual
            # El pegado real se maneja por el navegador con Ctrl+V
            # Pero podemos mostrar un mensaje o mantener el valor actual
            return current_value if current_value else ""
        
        return dash.no_update

    # Callback para manejar los botones de pegar, limpiar y desasignar todas en el modal de desasignación
    @app.callback(
        Output("unassign-card-uuid-input", "value", allow_duplicate=True),
        [Input("unassign-card-paste-button", "n_clicks"),
         Input("unassign-card-clear-button", "n_clicks"),
         Input("unassign-card-all-button", "n_clicks")],
        [State("unassign-card-uuid-input", "value")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=dash.no_update)
    def handle_unassign_paste_clear_buttons(paste_clicks, clear_clicks, all_clicks, current_value):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
            
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == "unassign-card-clear-button" and clear_clicks:
            # Limpiar el textarea
            return ""
        elif button_id == "unassign-card-all-button" and all_clicks:
            # Limpiar el textarea para activar el modo "desasignar todas"
            return ""
        elif button_id == "unassign-card-paste-button" and paste_clicks:
            # Para el botón de pegar, simplemente retornamos el valor actual
            # El pegado real se maneja por el navegador con Ctrl+V
            return current_value if current_value else ""
        
        return dash.no_update

    # Función para actualizar múltiples tarjetas en una cerradura individual
    def update_multiple_cards_for_lock(device, uuid_list, jwt_token):
        """
        Actualiza múltiples UUIDs de tarjetas NFC para una cerradura específica,
        usando slots disponibles secuencialmente.
        
        Args:
            device: Diccionario con datos de la cerradura
            uuid_list: Lista de UUIDs de tarjetas NFC
            jwt_token: Token JWT para autenticación
            
        Returns:
            Tupla (success, message, details) con el resultado de la operación
        """
        from utils.nfc_helper import get_available_slots, check_card_exists
        
        # Usar el ID numérico real del dispositivo para llamadas API
        # Dar prioridad a 'real_device_id', luego a 'id', y como último recurso 'device_id' (y verificar si es numérico)
        numeric_device_id = device.get("real_device_id")
        if not numeric_device_id:
            numeric_device_id = device.get("id") # 'id' en el contexto de la tabla NFC es el device_id numérico
            if numeric_device_id:
                 logger.info(f"Usando device.get('id') ({numeric_device_id}) como ID numérico porque 'real_device_id' no fue encontrado.")
        
        if not numeric_device_id: # Si sigue sin encontrarse, probar 'device_id' y validar
            potential_numeric_id = device.get("device_id")
            try:
                if potential_numeric_id:
                    int(potential_numeric_id) # Verificar si es convertible a int
                    numeric_device_id = potential_numeric_id
                    logger.warning(f"Usando device.get('device_id') ({numeric_device_id}) como ID numérico porque 'real_device_id' e 'id' no fueron encontrados o no eran numéricos.")
            except (ValueError, TypeError):
                logger.error(f"Error Crítico: 'real_device_id' e 'id' no encontrados, y 'device_id' ('{potential_numeric_id}') no es numérico.")
                return False, f"Error interno: ID de dispositivo no válido para asignación.", []

        # El 'device_id' descriptivo (display_name) para logging
        descriptive_device_id = device.get("device_id") # Esto es el display_label
        if not descriptive_device_id: # Fallback si 'device_id' no es el display_name
            descriptive_device_id = device.get("display_name", device.get("lock_name", "Cerradura desconocida"))

        # Para compatibilidad con el código existente de logs
        device_id = descriptive_device_id

        gateway_id = device.get("gateway_id")
        asset_id = device.get("asset_id")
        
        logger.info(f"Actualizando {len(uuid_list)} tarjetas para: numeric_device_id={numeric_device_id}, descriptive_device_id='{descriptive_device_id}', gateway_id={gateway_id}, asset_id={asset_id}")
        
        if not numeric_device_id: # Chequeo final
            return False, "Falta ID numérico del dispositivo", []
            
        if not gateway_id:
            return False, f"Falta el ID del gateway necesario para el dispositivo {descriptive_device_id} (ID: {numeric_device_id})", []
        
        if not uuid_list or len(uuid_list) == 0:
            return False, "No se proporcionaron UUIDs para asignar", []
        
        try:
            # Para el caso de dispositivos sin sensores definidos, crear una estructura básica
            if "sensors" not in device or not device["sensors"]:
                logger.warning(f"Dispositivo {device_id} no tiene sensores definidos, creando estructura básica")
                device = {
                    "device_id": device_id,
                    "real_device_id": device_id,
                    "gateway_id": gateway_id,
                    "asset_id": asset_id,
                    "sensors": []  # Lista vacía de sensores
                }
            
            # Encontrar slots disponibles
            available_slots = get_available_slots(device)
            logger.info(f"Slots disponibles para dispositivo {device_id}: {available_slots}")
            
            if not available_slots:
                # En caso de no encontrar slots, usar slots predeterminados como respaldo
                logger.warning(f"No se encontraron slots disponibles para {device_id}, usando slots predeterminados")
                available_slots = [str(i) for i in range(7, 99)]
            
            # Verificar si hay suficientes slots para todas las tarjetas
            if len(uuid_list) > len(available_slots):
                return False, f"No hay suficientes slots disponibles. Necesarios: {len(uuid_list)}, Disponibles: {len(available_slots)}", []
            
            # Procesar cada UUID
            results = []
            successful_assignments = 0
            failed_assignments = 0
            already_assigned = 0
            auth_errors = 0
            
            for i, uuid_value in enumerate(uuid_list):
                try:
                    # Verificar si la tarjeta ya existe
                    card_exists, existing_slot = check_card_exists(device, uuid_value)
                    if card_exists:
                        logger.info(f"La tarjeta {uuid_value} ya existe en el slot {existing_slot} del dispositivo {device_id}")
                        results.append({
                            "uuid": uuid_value,
                            "slot": existing_slot,
                            "status": "already_assigned",
                            "message": f"Ya asignada en slot {existing_slot}"
                        })
                        already_assigned += 1
                        continue
                    
                    # Usar el siguiente slot disponible
                    if i < len(available_slots):
                        slot_number = available_slots[i]
                    else:
                        # No debería llegar aquí debido a la verificación anterior
                        results.append({
                            "uuid": uuid_value,
                            "slot": None,
                            "status": "failed",
                            "message": "No hay slots disponibles"
                        })
                        failed_assignments += 1
                        continue
                    
                    # Asegurar formato correcto
                    if ":" not in uuid_value and "-" not in uuid_value and len(uuid_value) == 8:
                        uuid_formatted = ":".join([uuid_value[i:i+2] for i in range(0, len(uuid_value), 2)])
                    else:
                        uuid_formatted = uuid_value
                    
                    # Llamar a la API para actualizar el código NFC
                    from utils.api import update_nfc_code_value
                    
                    logger.info(f"Actualizando tarjeta NFC {uuid_formatted} en slot {slot_number} para dispositivo {device_id}")
                    
                    success, response = update_nfc_code_value(
                        asset_id=asset_id,
                        device_id=str(numeric_device_id), # Usar el ID numérico
                        sensor_id=slot_number,
                        new_value=uuid_formatted,
                        jwt_token=jwt_token,
                        gateway_id=gateway_id,
                        is_master_card=slot_number == "7"
                    )
                    
                    if success:
                        logger.info(f"Tarjeta {uuid_formatted} asignada correctamente al slot {slot_number} para dispositivo {device_id}")
                        results.append({
                            "uuid": uuid_value,
                            "slot": slot_number,
                            "status": "success",
                            "message": f"Asignada al slot {slot_number}"
                        })
                        successful_assignments += 1
                        
                        # Actualizar la estructura del dispositivo para futuras verificaciones
                        # Esto ayuda con las verificaciones de tarjetas ya existentes en la misma operación
                        if "sensors" not in device:
                            device["sensors"] = []
                        
                        # Buscar si ya existe un sensor con este ID, si no, agregarlo
                        sensor_found = False
                        for sensor in device["sensors"]:
                            if str(sensor.get("sensor_id", "")) == str(slot_number):
                                sensor["password"] = uuid_formatted
                                sensor_found = True
                                break
                        
                        if not sensor_found:
                            device["sensors"].append({
                                "sensor_id": slot_number,
                                "password": uuid_formatted,
                                "sensor_type": "NFC_CODE"
                            })
                        else:
                        # Manejar errores específicos
                            error_message = str(response)
                        
                        if "Token expirado" in error_message or "Token JWT expirado" in error_message or "401" in error_message:
                            logger.error(f"Error de autenticación al actualizar tarjeta {uuid_value} para {device_id}")
                            results.append({
                                "uuid": uuid_value,
                                "slot": slot_number,
                                "status": "auth_error",
                                "message": "Error de autenticación"
                            })
                            auth_errors += 1
                        else:
                            logger.error(f"Error al actualizar tarjeta {uuid_value} para {device_id}: {response}")
                            results.append({
                                "uuid": uuid_value,
                                "slot": slot_number,
                                "status": "failed",
                                "message": f"Error: {response}"
                            })
                            failed_assignments += 1
                
                except Exception as e:
                    logger.error(f"Error procesando tarjeta {uuid_value} para {device_id}: {str(e)}")
                    results.append({
                        "uuid": uuid_value,
                        "slot": None,
                        "status": "failed",
                        "message": f"Error: {str(e)}"
                    })
                    failed_assignments += 1
            
            # Determinar el resultado general
            total_processed = successful_assignments + failed_assignments + already_assigned + auth_errors
            
            if successful_assignments == len(uuid_list):
                return True, f"Todas las tarjetas ({successful_assignments}) asignadas correctamente", results
            elif successful_assignments > 0:
                return True, f"{successful_assignments} de {len(uuid_list)} tarjetas asignadas correctamente", results
            elif already_assigned == len(uuid_list):
                return True, f"Todas las tarjetas ({already_assigned}) ya estaban asignadas", results
            elif auth_errors > 0:
                return False, f"Error de autenticación en {auth_errors} tarjetas", results
            else:
                return False, f"No se pudo asignar ninguna tarjeta", results
                
        except Exception as e:
            logger.error(f"Error general actualizando tarjetas para {device_id}: {str(e)}")
            return False, f"Error: {str(e)}", []

    # Función para desasignar múltiples tarjetas NFC de una cerradura específica
    def unassign_multiple_cards_for_lock(device, uuid_list, jwt_token):
        """
        Desasigna múltiples UUIDs de tarjetas NFC de una cerradura específica.
        
        Args:
            device: Diccionario con datos de la cerradura. Se espera que 'real_device_id' contenga el ID numérico
                    y 'device_id' (o 'display_name') el nombre descriptivo.
            uuid_list: Lista de UUIDs de tarjetas NFC a desasignar (vacía = desasignar todas)
            jwt_token: Token JWT para autenticación
            
        Returns:
            Tupla (success, message, details) con el resultado de la operación
        """
        from utils.nfc_helper import check_card_exists # Ensure import
        from utils.api import update_nfc_code_value, get_nfc_passwords # Ensure imports
        
        numeric_device_id = device.get('real_device_id') 
        descriptive_device_id = device.get('device_id') 
        if not descriptive_device_id: 
             descriptive_device_id = device.get('display_name', device.get('lock_name', "Cerradura desconocida"))

        # Use descriptive_device_id for logging consistency with other parts of the code
        device_id_for_log = descriptive_device_id

        if not numeric_device_id:
            logger.error(f"Error Crítico: No se pudo determinar el ID numérico del dispositivo para '{device_id_for_log}'. La clave 'real_device_id' falta en el objeto device: {list(device.keys()) if isinstance(device, dict) else 'Not a dict'}")
            return False, f"Falta ID numérico del dispositivo {device_id_for_log}", []

        gateway_id = device.get('gateway_id')
        asset_id = device.get('asset_id')

        logger.info(f"Desasignando tarjetas para: numeric_device_id={numeric_device_id}, descriptive_device_id='{device_id_for_log}', gateway_id={gateway_id}, asset_id={asset_id}")

        if not gateway_id:
            return False, f"Falta el ID del gateway necesario para el dispositivo {device_id_for_log} (ID: {numeric_device_id})", []
        
        if not asset_id: # Asset ID is crucial for fetching passwords
            logger.error(f"Error Crítico: Falta asset_id para el dispositivo '{device_id_for_log}' (ID: {numeric_device_id}). No se pueden obtener las tarjetas actuales.")
            return False, f"Falta ID de asset para el dispositivo {device_id_for_log}", []

        # --- MODIFIED LOGIC TO FETCH AND USE FRESH NFC DATA ---
        current_nfc_passwords_on_device = {} # Stores {sensor_id: password}
        try:
            logger.info(f"Fetching all NFC data for asset {asset_id} to find device {numeric_device_id}")
            nfc_data_for_asset = get_nfc_passwords(asset_id, jwt_token) 
            # REMOVED DEBUG LOGGING

            if nfc_data_for_asset and isinstance(nfc_data_for_asset, dict) and 'data' in nfc_data_for_asset:
                data_section = nfc_data_for_asset['data']
                devices_in_asset_list = [] 
                
                if isinstance(data_section, dict) and 'devices' in data_section and isinstance(data_section['devices'], list):
                    devices_in_asset_list = data_section['devices']
                elif isinstance(data_section, list):
                    devices_in_asset_list = data_section
                elif isinstance(data_section, dict) and ('device_id' in data_section or 'real_device_id' in data_section) : 
                    devices_in_asset_list = [data_section]
                
                # REMOVED DEBUG LOGGING

                found_device_data_from_asset = None
                for i, device_entry in enumerate(devices_in_asset_list):
                    if not isinstance(device_entry, dict):
                        # REMOVED DEBUG LOGGING
                        continue

                    id_keys_to_check = ['real_device_id', 'device_id', 'id'] 
                    for key in id_keys_to_check:
                        api_id_val = device_entry.get(key)
                        if api_id_val is not None and str(api_id_val) == str(numeric_device_id):
                            # REMOVED DEBUG LOGGING
                            found_device_data_from_asset = device_entry
                            break 
                    if found_device_data_from_asset:
                        break 
                    else:
                        # REMOVED DEBUG LOGGING
                        pass # Replaced logger.debug with pass as it was the only statement in the else block
                        
                if found_device_data_from_asset:
                    # REMOVED DEBUG LOGGING 
                    for key, pw_val in found_device_data_from_asset.items():
                        if key.startswith("sensor_"):
                            sensor_id_val = key.replace("sensor_", "")
                            if pw_val is not None and hasattr(pw_val, 'strip'):
                                stripped_pw = str(pw_val).strip()
                                if stripped_pw:
                                    current_nfc_passwords_on_device[sensor_id_val] = stripped_pw
                                    # REMOVED DEBUG LOGGING
                                else:
                                    # REMOVED DEBUG LOGGING
                                    pass # Replaced logger.debug with pass
                            elif pw_val: 
                                current_nfc_passwords_on_device[sensor_id_val] = str(pw_val)
                                # REMOVED DEBUG LOGGING
                            else:
                                # REMOVED DEBUG LOGGING
                                pass # Replaced logger.debug with pass
                    # REMOVED DEBUG LOGGING
                else:
                    logger.warning(f"Device {numeric_device_id} was NOT FOUND within asset {asset_id} NFC data after checking {len(devices_in_asset_list)} entries.") # Kept warning
            else:
                logger.warning(f"No NFC data in 'data' key or nfc_data_for_asset is not a dict for asset {asset_id}.") # Kept warning

        except Exception as e:
            logger.error(f"Error during parsing of nfc_data_for_asset for device {numeric_device_id}, asset {asset_id}: {str(e)}", exc_info=True)

        device_for_check = {
            "device_id": descriptive_device_id, 
            "real_device_id": numeric_device_id, 
            "sensors": []
        }
        for sensor_id_str, password_str in current_nfc_passwords_on_device.items():
            device_for_check["sensors"].append({
                "sensor_id": sensor_id_str,
                "password": password_str,
                "sensor_type": "NFC_CODE" 
            })
        # REMOVED DEBUG LOGGING
        
        try:
            uuids_to_unassign_details = [] # Stores {"uuid": "...", "slot": "...", "status_override": "..."}

            if not uuid_list: # Mode: unassign all cards currently on device
                logger.info(f"Mode: Unassign ALL cards for device {numeric_device_id} based on fresh data.")
                if not device_for_check["sensors"]:
                    logger.info(f"No active NFC cards found on device {numeric_device_id} (fresh data) to unassign.")
                    return True, "No hay tarjetas activas para desasignar", []
                for sensor in device_for_check["sensors"]:
                    uuids_to_unassign_details.append({"uuid": sensor["password"], "slot": sensor["sensor_id"]})
                if not uuids_to_unassign_details: # Should not happen if device_for_check.sensors was populated
                     return True, "No hay tarjetas activas para desasignar (después de verificar datos frescos)", []
                logger.info(f"Identified {len(uuids_to_unassign_details)} cards to unassign (ALL mode) for device {numeric_device_id}.")

            else: # Mode: unassign specific UUIDs from the input uuid_list
                logger.info(f"Mode: Unassign SPECIFIC cards for device {numeric_device_id}: {uuid_list} using fresh data for checks.")
                for uuid_to_find in uuid_list:
                    card_is_present, slot_found = check_card_exists(device_for_check, uuid_to_find)
                    if card_is_present:
                        uuids_to_unassign_details.append({"uuid": uuid_to_find, "slot": slot_found})
                    else:
                        uuids_to_unassign_details.append({"uuid": uuid_to_find, "slot": None, "status_override": "not_found"})
                
                if not any(d["slot"] is not None for d in uuids_to_unassign_details):
                     logger.info(f"None of the specified UUIDs {uuid_list} were found on device {numeric_device_id} (fresh data).")
                     results_for_not_found = [{"uuid": u, "slot": None, "status": "not_found", "message": "Tarjeta no encontrada"} for u in uuid_list]
                     return True, "Ninguna de las tarjetas especificadas fue encontrada en el dispositivo.", results_for_not_found
            
            if not uuids_to_unassign_details:
                logger.warning(f"No cards identified for unassignment for device {numeric_device_id}. Original list: {uuid_list}")
                return True, "No hay tarjetas para procesar la desasignación", []

            results = []
            successful_unassignments = 0
            failed_unassignments = 0
            not_found_reported = 0 # For cards from uuid_list that were not found on device
            auth_errors = 0

            for unassign_detail in uuids_to_unassign_details:
                uuid_to_remove = unassign_detail["uuid"]
                slot_to_clear = unassign_detail["slot"]

                if unassign_detail.get("status_override") == "not_found":
                    results.append({"uuid": uuid_to_remove, "slot": None, "status": "not_found", "message": "Tarjeta no encontrada"})
                    not_found_reported +=1
                    continue

                if not slot_to_clear: # Should be caught by status_override
                    logger.error(f"Internal logic error: slot_to_clear is None for UUID {uuid_to_remove} without status_override. Skipping.")
                    results.append({"uuid": uuid_to_remove, "slot": None, "status": "failed", "message": "Error interno: slot no identificado"})
                    failed_unassignments+=1
                    continue

                try:
                    logger.info(f"Attempting to unassign card (original UUID: {uuid_to_remove}) from slot {slot_to_clear} on device {numeric_device_id}")
                    success, response = update_nfc_code_value(
                        asset_id=asset_id,
                        device_id=str(numeric_device_id),
                        sensor_id=str(slot_to_clear),
                        new_value="",
                        jwt_token=jwt_token,
                        gateway_id=gateway_id,
                        is_master_card=(str(slot_to_clear) == "7")
                    )

                    if success:
                        logger.info(f"Card from slot {slot_to_clear} unassigned successfully for device {numeric_device_id}.")
                        results.append({"uuid": uuid_to_remove, "slot": slot_to_clear, "status": "success", "message": f"Desasignada del slot {slot_to_clear}"})
                        successful_unassignments += 1
                    else:
                        error_message = str(response)
                        status_to_report = "failed"
                        if "Token expirado" in error_message or "Token JWT expirado" in error_message or "401" in error_message or "unauthorized" in error_message.lower():
                            status_to_report = "auth_error"
                            auth_errors += 1
                        else:
                            failed_unassignments += 1
                        logger.error(f"Failed to unassign card from slot {slot_to_clear} for device {numeric_device_id}: {error_message}")
                        results.append({"uuid": uuid_to_remove, "slot": slot_to_clear, "status": status_to_report, "message": f"Error: {error_message}"})

                except Exception as e_inner:
                    logger.error(f"Exception during unassignment for slot {slot_to_clear}, UUID {uuid_to_remove} on device {numeric_device_id}: {str(e_inner)}")
                    results.append({"uuid": uuid_to_remove, "slot": slot_to_clear, "status": "failed", "message": f"Excepción: {str(e_inner)}"})
                    failed_unassignments += 1
            
            total_processed_ops = successful_unassignments + failed_unassignments + auth_errors
            target_ops = len(uuids_to_unassign_details) - not_found_reported

            if successful_unassignments == target_ops and target_ops > 0 :
                final_message = f"Todas las {successful_unassignments} tarjetas procesadas desasignadas correctamente."
                if not_found_reported > 0 and uuid_list: # Only mention if specific UUIDs were given and some were not found
                    final_message += f" {not_found_reported} tarjetas especificadas no fueron encontradas."
                return True, final_message, results
            elif successful_unassignments > 0:
                final_message = f"{successful_unassignments} tarjetas desasignadas. {failed_unassignments} fallaron. {auth_errors} errores de auth."
                if not_found_reported > 0 and uuid_list:
                    final_message += f" {not_found_reported} no encontradas."
                return True, final_message, results # Overall True if at least one succeeded
            elif not_found_reported == len(uuid_list) and uuid_list: # All specified UUIDs were not found
                 return True, "Ninguna de las tarjetas especificadas fue encontrada en el dispositivo.", results
            elif auth_errors > 0 and successful_unassignments == 0 and failed_unassignments == 0:
                 return False, f"Error de autenticación en {auth_errors} operaciones.", results
            elif target_ops == 0 and not_found_reported > 0: # e.g. specific list given, none found
                 return True, "Ninguna de las tarjetas especificadas para desasignar fue encontrada en el dispositivo.", results
            elif target_ops == 0 and not uuid_list: # e.g. unassign all, but no cards were on device
                 return True, "No había tarjetas activas en el dispositivo para desasignar.", results
            else: 
                final_message = f"No se pudo desasignar: {failed_unassignments} fallaron, {auth_errors} errores de auth."
                if not_found_reported > 0 and uuid_list:
                    final_message += f" {not_found_reported} no encontradas."
                return False, final_message, results

        except Exception as e_outer:
            logger.error(f"Error general en unassign_multiple_cards_for_lock para {numeric_device_id}: {str(e_outer)}", exc_info=True)
            return False, f"Error general procesando desasignaciones: {str(e_outer)}", []
