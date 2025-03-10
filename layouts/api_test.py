from dash import html, dcc
import dash_bootstrap_components as dbc
from dash import Input, Output, State, no_update
import dash
import json
import requests
from utils.logging import get_logger
from utils.auth import AuthService, API_BASE_URL, auth_service
import time
from datetime import datetime
import traceback
import dash_table
import pandas as pd
from utils import api

logger = get_logger(__name__)

# Layout para la página de prueba de la API
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H1("Prueba de API", className="mb-4"),
            html.P("Herramienta para probar la conexión y los endpoints de la API.", className="lead mb-4"),
            
            # Tarjeta de estado de conexión
            dbc.Card([
                dbc.CardHeader("Estado de la Conexión"),
                dbc.CardBody([
                    html.Div(id="api-connection-status")
                ])
            ], className="mb-4 shadow-sm"),
            
            # Botón para probar específicamente el endpoint de proyectos con el client_id problemático
            dbc.Card([
                dbc.CardHeader("Prueba Rápida de Proyectos"),
                dbc.CardBody([
                    html.P("Prueba el endpoint de proyectos con el client_id específico que está causando problemas."),
                    dbc.Button("Probar Endpoint de Proyectos", id="test-projects-button", color="primary", className="mt-2"),
                    html.Div(id="test-projects-results", className="mt-3")
                ])
            ], className="mb-4 shadow-sm"),
            
            # Tarjeta de prueba de endpoints
            dbc.Card([
                dbc.CardHeader("Prueba de Endpoints"),
                dbc.CardBody([
                    # Selector de endpoint
                    dbc.Row([
                        dbc.Col([
                            html.Label("Endpoint"),
                            dbc.Select(
                                id="endpoint-select",
                                options=[
                                    {"label": "Clientes (/clients)", "value": "/clients"},
                                    {"label": "Proyectos (/projects)", "value": "/projects"},
                                    {"label": "Proyectos por Cliente (/projects?client=ID)", "value": "projects_by_client"},
                                    {"label": "Assets (/assets)", "value": "/assets"},
                                    {"label": "Assets por Proyecto (/projects/ID/assets)", "value": "assets_by_project"},
                                    {"label": "Assets por Cliente (/assets?client=ID)", "value": "assets_by_client"},
                                    {"label": "Sensores de Asset (/data/assets/{asset_id}/available-utilities-sensors)", "value": "sensors_with_tags"},
                                    {"label": "Datos de Sensor (/data/assets/time-series/{asset_id})", "value": "sensor_data"},
                                    {"label": "Series Temporales de Asset (/data/assets/time-series/{asset_id})", "value": "asset_time_series"},
                                    {"label": "Obtener UUID de Sensor (/data/assets/{asset_id}/sensors)", "value": "get_sensor_uuid"},
                                    {"label": "Obtener UUID de Sensor (get_sensor_uuid)", "value": "get_sensor_uuid_function"},
                                    {"label": "Dispositivos (/devices)", "value": "/devices"},
                                    {"label": "Métricas (/metrics)", "value": "/metrics"},
                                    {"label": "Accesos (/lock)", "value": "/lock"},
                                    {"label": "Espacios (/spaces)", "value": "/spaces"},
                                    {"label": "Personalizado", "value": "custom"}
                                ],
                                value="/clients",
                                className="mb-3"
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("Método"),
                            dbc.Select(
                                id="method-select",
                                options=[
                                    {"label": "GET", "value": "GET"},
                                    {"label": "POST", "value": "POST"},
                                    {"label": "PUT", "value": "PUT"},
                                    {"label": "DELETE", "value": "DELETE"}
                                ],
                                value="GET",
                                className="mb-3"
                            )
                        ], width=6)
                    ]),
                    
                    # Campo para endpoint personalizado
                    html.Div([
                        html.Label("Endpoint Personalizado"),
                        dbc.Input(
                            id="custom-endpoint-input",
                            type="text",
                            placeholder="Ingrese el endpoint (ej: /users/profile)",
                            className="mb-3"
                        )
                    ], id="custom-endpoint-container", style={"display": "none"}),
                    
                    # Campo para asset_id (para sensores)
                    html.Div([
                        html.Label("ID del Asset"),
                        dbc.Input(
                            id="asset-id-input",
                            type="text",
                            placeholder="Ingrese el ID del asset",
                            className="mb-3"
                        )
                    ], id="asset-id-container", style={"display": "none"}),
                    
                    # Campo para client_id
                    html.Div([
                        html.Label("ID del Cliente"),
                        dbc.Input(
                            id="client-id-input",
                            type="text",
                            placeholder="Ingrese el ID del cliente",
                            className="mb-3"
                        )
                    ], id="client-id-container", style={"display": "none"}),
                    
                    # Campo para project_id
                    html.Div([
                        html.Label("ID del Proyecto"),
                        dbc.Input(
                            id="project-id-input",
                            type="text",
                            placeholder="Ingrese el ID del proyecto",
                            className="mb-3"
                        )
                    ], id="project-id-container", style={"display": "none"}),
                    
                    # Campo para sensor_uuid
                    html.Div([
                        html.Label("UUID del Sensor"),
                        dbc.Input(
                            id="sensor-uuid-input",
                            type="text",
                            placeholder="Ingrese el UUID del sensor",
                            className="mb-3"
                        )
                    ], id="sensor-uuid-container", style={"display": "none"}),
                    
                    # Campo para fecha
                    html.Div([
                        html.Label("Fecha"),
                        dbc.Input(
                            id="date-input",
                            type="date",
                            className="mb-3"
                        )
                    ], id="date-container", style={"display": "none"}),
                    
                    # Campos para get_sensor_uuid
                    html.Div([
                        html.Label("Gateway ID"),
                        dbc.Input(
                            id="gateway-id-input",
                            type="text",
                            placeholder="Ingrese el ID del gateway",
                            className="mb-3"
                        )
                    ], id="gateway-id-container", style={"display": "none"}),
                    
                    html.Div([
                        html.Label("Device ID"),
                        dbc.Input(
                            id="device-id-input",
                            type="text",
                            placeholder="Ingrese el ID del dispositivo",
                            className="mb-3"
                        )
                    ], id="device-id-container", style={"display": "none"}),
                    
                    html.Div([
                        html.Label("Sensor ID"),
                        dbc.Input(
                            id="sensor-id-input",
                            type="text",
                            placeholder="Ingrese el ID del sensor",
                            className="mb-3"
                        )
                    ], id="sensor-id-container", style={"display": "none"}),
                    
                    # Campo para parámetros
                    html.Div([
                        html.Label("Parámetros (JSON)"),
                        dbc.Textarea(
                            id="params-input",
                            placeholder='{"param1": "valor1", "param2": "valor2"}',
                            rows=5,
                            className="mb-3"
                        )
                    ], id="params-container"),
                    
                    # Botón para ejecutar la prueba
                    dbc.Button("Ejecutar", id="run-test-button", color="primary", className="mb-3"),
                    
                    # Spinner para indicar carga
                    dbc.Spinner(html.Div(id="api-test-loading"), color="primary", type="grow", size="sm"),
                    
                    # Resultados de la prueba
                    html.Div(id="api-test-results")
                ])
            ], className="mb-4 shadow-sm"),
            
            # Historial de pruebas
            dbc.Card([
                dbc.CardHeader("Historial de Pruebas"),
                dbc.CardBody([
                    html.Div([
                        html.Table([
                            html.Thead([
                                html.Tr([
                                    html.Th("Hora"),
                                    html.Th("Método"),
                                    html.Th("Endpoint"),
                                    html.Th("Estado")
                                ])
                            ]),
                            html.Tbody(id="api-test-history")
                        ], className="table table-sm")
                    ], style={"overflowY": "auto", "maxHeight": "300px"})
                ])
            ], className="shadow-sm")
        ], width=12)
    ])
])

def register_callbacks(app):
    """
    Registra los callbacks para la página de prueba de la API
    
    Args:
        app: Instancia de la aplicación Dash
    """
    
    # Callback para mostrar/ocultar los campos de endpoint personalizado y asset_id
    @app.callback(
        [Output("custom-endpoint-container", "style"),
         Output("asset-id-container", "style"),
         Output("client-id-container", "style"),
         Output("project-id-container", "style"),
         Output("sensor-uuid-container", "style"),
         Output("date-container", "style"),
         Output("gateway-id-container", "style"),
         Output("device-id-container", "style"),
         Output("sensor-id-container", "style"),
         Output("params-container", "style")],
        [Input("endpoint-select", "value")]
    )
    def toggle_endpoint_inputs(endpoint):
        # Inicializar todos los campos como ocultos
        custom_endpoint_style = {"display": "none"}
        asset_id_style = {"display": "none"}
        client_id_style = {"display": "none"}
        project_id_style = {"display": "none"}
        sensor_uuid_style = {"display": "none"}
        date_style = {"display": "none"}
        gateway_id_style = {"display": "none"}
        device_id_style = {"display": "none"}
        sensor_id_style = {"display": "none"}
        params_style = {"display": "block"}  # Siempre mostrar el campo de parámetros
        
        # Mostrar campos según el endpoint seleccionado
        if endpoint == "custom":
            custom_endpoint_style = {"display": "block"}
        elif endpoint == "sensors_with_tags":
            asset_id_style = {"display": "block"}  # Mostrar el campo asset_id para este endpoint
        elif endpoint == "get_sensor_uuid":
            asset_id_style = {"display": "block"}
        elif endpoint == "get_sensor_uuid_function":
            gateway_id_style = {"display": "block"}
            device_id_style = {"display": "block"}
            sensor_id_style = {"display": "block"}
        elif endpoint == "projects_by_client":
            client_id_style = {"display": "block"}
        elif endpoint == "assets_by_project":
            project_id_style = {"display": "block"}
        elif endpoint == "assets_by_client":
            client_id_style = {"display": "block"}
        elif endpoint == "sensor_data":
            asset_id_style = {"display": "block"}
            sensor_uuid_style = {"display": "block"}
            date_style = {"display": "block"}
        elif endpoint == "asset_time_series":
            asset_id_style = {"display": "block"}
            date_style = {"display": "block"}
            # Para este endpoint, los demás parámetros se pasarán en el JSON
        
        return custom_endpoint_style, asset_id_style, client_id_style, project_id_style, sensor_uuid_style, date_style, gateway_id_style, device_id_style, sensor_id_style, params_style
    
    # Callback para verificar el estado de la conexión
    @app.callback(
        Output("api-connection-status", "children"),
        [Input("run-test-button", "n_clicks"),
         Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    def check_connection_status(n_clicks, token_data):
        try:
            # Obtener el token JWT del store
            token = token_data.get('token') if token_data else None
            
            # Si no hay token, mostrar estado no autenticado
            if not token:
                return html.Div([
                    html.I(className="fas fa-times-circle text-danger me-2"),
                    "No autenticado"
                ])
            
            # Verificar autenticación
            if not auth_service.is_authenticated(token):
                return html.Div([
                    html.I(className="fas fa-times-circle text-danger me-2"),
                    "No autenticado"
                ])
            
            # Verificar conexión a la API
            response = auth_service.make_api_request(token, "GET", "clients")
            
            if "error" in response:
                return html.Div([
                    html.I(className="fas fa-times-circle text-danger me-2"),
                    f"Error de conexión: {response.get('error')}"
                ])
            
            return html.Div([
                html.I(className="fas fa-check-circle text-success me-2"),
                "Conectado a la API"
            ])
        except Exception as e:
            logger.error(f"Error al verificar el estado de la conexión: {str(e)}")
            return html.Div([
                html.I(className="fas fa-times-circle text-danger me-2"),
                f"Error: {str(e)}"
            ])
    
    # Callback para probar específicamente el endpoint de proyectos
    @app.callback(
        Output("test-projects-results", "children"),
        [Input("test-projects-button", "n_clicks")],
        [State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def test_projects_endpoint(n_clicks, token_data):
        if not n_clicks:
            return no_update
        
        try:
            # Obtener el token JWT del store
            token = token_data.get('token') if token_data else None
            
            # Si no hay token, mostrar mensaje de error
            if not token:
                return html.Div("No hay una sesión activa. Por favor, inicie sesión nuevamente.", className="alert alert-warning")
            
            # Verificar autenticación
            if not auth_service.is_authenticated(token):
                return html.Div("No hay una sesión activa. Por favor, inicie sesión nuevamente.", className="alert alert-warning")
            
            # Obtener proyectos
            projects = get_projects(jwt_token=token)
            
            # Verificar que projects sea una lista
            if not isinstance(projects, list):
                return html.Div(f"Error: La respuesta no es una lista de proyectos. Tipo recibido: {type(projects)}", className="alert alert-danger")
            
            # Crear tabla de resultados
            if len(projects) == 0:
                return html.Div("No se encontraron proyectos", className="alert alert-info")
            
            # Crear encabezados de tabla basados en las claves del primer proyecto
            if isinstance(projects[0], dict):
                # Obtener todas las claves únicas de todos los proyectos
                all_keys = set()
                for project in projects:
                    if isinstance(project, dict):
                        all_keys.update(project.keys())
                
                # Filtrar y ordenar las claves para la tabla
                important_keys = ['id', 'name', 'client', 'client_id', 'client_name']
                headers = [key for key in important_keys if key in all_keys]
                other_keys = sorted([key for key in all_keys if key not in important_keys])
                headers.extend(other_keys)
                
                # Crear filas de la tabla
                rows = []
                for project in projects:
                    if isinstance(project, dict):
                        row = []
                        for key in headers:
                            value = project.get(key, "")
                            # Formatear el valor para la tabla
                            if isinstance(value, (dict, list)):
                                value = json.dumps(value, ensure_ascii=False)
                            elif value is None:
                                value = ""
                            row.append(value)
                        rows.append(row)
                
                # Crear tabla
                table = dash_table.DataTable(
                    columns=[{"name": h, "id": h} for h in headers],
                    data=[{h: row[i] for i, h in enumerate(headers)} for row in rows],
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'minWidth': '100px', 'width': '100px', 'maxWidth': '300px',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis',
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    page_size=10
                )
                
                return html.Div([
                    html.H5(f"Proyectos encontrados: {len(projects)}"),
                    table
                ])
            else:
                return html.Div(f"Error: El primer proyecto no es un diccionario. Tipo recibido: {type(projects[0])}", className="alert alert-danger")
        
        except Exception as e:
            logger.error(f"Error al probar el endpoint de proyectos: {str(e)}")
            return html.Div(f"Error al probar el endpoint de proyectos: {str(e)}", className="alert alert-danger")
    
    # Callback para ejecutar la prueba de API
    @app.callback(
        [Output("api-test-results", "children"), Output("api-test-loading", "children"), Output("api-test-history", "children")],
        [Input("run-test-button", "n_clicks")],
        [
            State("endpoint-select", "value"),
            State("method-select", "value"),
            State("custom-endpoint-input", "value"),
            State("asset-id-input", "value"),
            State("client-id-input", "value"),
            State("project-id-input", "value"),
            State("sensor-uuid-input", "value"),
            State("date-input", "value"),
            State("params-input", "value"),
            State("api-test-history", "children"),
            State("jwt-token-store", "data")
        ],
        prevent_initial_call=True
    )
    def run_api_test(n_clicks, endpoint, method, custom_endpoint, asset_id, client_id, project_id, sensor_uuid, date, params_json, history, token_data):
        if not n_clicks:
            return no_update, no_update, no_update
        
        start_time = time.time()
        
        # Inicializar params
        params = {}
        if params_json:
            try:
                params = json.loads(params_json)
            except json.JSONDecodeError:
                return html.Div("Error en el formato JSON de los parámetros", className="alert alert-danger"), "", no_update
        
        try:
            # Determinar el endpoint final
            if endpoint == "custom":
                if not custom_endpoint:
                    return html.Div("Por favor, ingrese un endpoint personalizado", className="alert alert-warning"), "", no_update
                final_endpoint = custom_endpoint
            elif endpoint == "sensors_with_tags":
                if not asset_id:
                    return html.Div("Por favor, ingrese el ID del asset", className="alert alert-warning"), "", no_update
                final_endpoint = f"data/assets/{asset_id}/available-utilities-sensors"
                
                # Usar los parámetros proporcionados para este endpoint
                # Los parámetros se pasarán como query params en la solicitud GET
                # No es necesario modificar params aquí, ya que se pasarán automáticamente
            elif endpoint == "get_sensor_uuid":
                if not asset_id:
                    return html.Div("Por favor, ingrese el ID del asset", className="alert alert-warning"), "", no_update
                final_endpoint = f"data/assets/{asset_id}/sensors"
            elif endpoint == "get_sensor_uuid_function":
                # Para este endpoint, necesitamos obtener gateway_id, device_id y sensor_id
                gateway_id = params.get("gateway_id")
                device_id = params.get("device_id")
                sensor_id = params.get("sensor_id")
                
                if not gateway_id or not device_id or not sensor_id:
                    return html.Div("Por favor, ingrese gateway_id, device_id y sensor_id en los parámetros JSON", className="alert alert-warning"), "", no_update
                
                # Llamar directamente a la función get_sensor_uuid
                token = token_data.get('token') if token_data else None
                if not token or not auth_service.is_authenticated(token):
                    return html.Div("No hay una sesión activa. Por favor, inicie sesión nuevamente.", className="alert alert-warning"), "", no_update
                
                try:
                    sensor_uuid = api.get_sensor_uuid(gateway_id, device_id, sensor_id, token)
                    
                    # Crear un resultado personalizado
                    result = {
                        "gateway_id": gateway_id,
                        "device_id": device_id,
                        "sensor_id": sensor_id,
                        "sensor_uuid": sensor_uuid
                    }
                    
                    # Mostrar el resultado
                    result_div = html.Div([
                        html.H5("Resultado de get_sensor_uuid", className="mt-3"),
                        html.Div([
                            html.Strong("Gateway ID: "), html.Span(gateway_id),
                            html.Br(),
                            html.Strong("Device ID: "), html.Span(device_id),
                            html.Br(),
                            html.Strong("Sensor ID: "), html.Span(sensor_id),
                            html.Br(),
                            html.Strong("Sensor UUID: "), html.Span(sensor_uuid, className="text-success fw-bold")
                        ], className="p-3 border rounded")
                    ])
                    
                    # Añadir a la historia
                    history_item = html.Div([
                        html.Hr(),
                        html.P([
                            html.Strong(f"{method} "),
                            html.Span("get_sensor_uuid"),
                            html.Span(f" - {time.strftime('%H:%M:%S')}", className="text-muted")
                        ]),
                        html.Pre(json.dumps(result, indent=2), className="bg-light p-2 rounded")
                    ])
                    
                    if isinstance(history, list):
                        updated_history = [history_item] + history
                    else:
                        updated_history = [history_item]
                    
                    return result_div, "", updated_history
                    
                except Exception as e:
                    logger.error(f"Error al llamar a get_sensor_uuid: {str(e)}")
                    return html.Div(f"Error al llamar a get_sensor_uuid: {str(e)}", className="alert alert-danger"), "", no_update
                
            elif endpoint == "projects_by_client":
                if not client_id:
                    return html.Div("Por favor, ingrese el ID del cliente", className="alert alert-warning"), "", no_update
                final_endpoint = f"projects?client={client_id}"
            elif endpoint == "assets_by_project":
                if not project_id:
                    return html.Div("Por favor, ingrese el ID del proyecto", className="alert alert-warning"), "", no_update
                final_endpoint = f"projects/{project_id}/assets"
            elif endpoint == "assets_by_client":
                if not client_id:
                    return html.Div("Por favor, ingrese el ID del cliente", className="alert alert-warning"), "", no_update
                final_endpoint = f"assets?client={client_id}"
            elif endpoint == "sensor_data":
                if not asset_id or not sensor_uuid:
                    return html.Div("Por favor, ingrese el ID del asset y el UUID del sensor", className="alert alert-warning"), "", no_update
                
                # Construir la URL con los parámetros
                final_endpoint = f"data/assets/time-series/{asset_id}"
                
                # Añadir sensor_uuid y fecha a los parámetros
                params["sensor_uuid"] = sensor_uuid
                if date:
                    params["from"] = date
                    params["until"] = date
                
                # Actualizar params_json
                params_json = json.dumps(params)
            elif endpoint == "asset_time_series":
                if not asset_id:
                    return html.Div("Por favor, ingrese el ID del asset", className="alert alert-warning"), "", no_update
                
                # Construir la URL con los parámetros
                final_endpoint = f"data/assets/time-series/{asset_id}"
                
                # Verificar que los parámetros necesarios estén presentes
                required_params = ["from", "until", "sensor"]
                missing_params = [param for param in required_params if param not in params]
                
                if missing_params:
                    return html.Div(f"Por favor, incluya los siguientes parámetros en el JSON: {', '.join(missing_params)}", className="alert alert-warning"), "", no_update
                
                # Los parámetros ya están en el objeto params, no es necesario modificarlos
                
                # Actualizar params_json por si acaso
                params_json = json.dumps(params)
            else:
                final_endpoint = endpoint
            
            # Obtener el token JWT del store
            token = token_data.get('token') if token_data else None
            
            # Si no hay token, mostrar mensaje de error
            if not token:
                return html.Div("No hay una sesión activa. Por favor, inicie sesión nuevamente.", className="alert alert-warning"), "", no_update
            
            # Verificar autenticación
            if not auth_service.is_authenticated(token):
                return html.Div("No hay una sesión activa. Por favor, inicie sesión nuevamente.", className="alert alert-warning"), "", no_update
            
            # Hacer la solicitud a la API
            logger.debug(f"Ejecutando prueba de API: {method} {final_endpoint}")
            logger.debug(f"Parámetros: {params}")
            
            # Para GET, los parámetros van como query params
            # Para POST/PUT, los parámetros van en el cuerpo de la solicitud
            if method == "GET":
                response = auth_service.make_api_request(token, method, final_endpoint, params=params)
            else:
                response = auth_service.make_api_request(token, method, final_endpoint, data=params)
            
            # Calcular el tiempo de respuesta
            elapsed_time = time.time() - start_time
            
            # Verificar si la respuesta es un diccionario (ya procesado) o un objeto Response
            if isinstance(response, dict):
                response_data = response
                status_code = 200  # Asumimos éxito si ya es un diccionario
                reason = "OK"
            else:
                status_code = response.status_code
                reason = response.reason
                try:
                    response_data = response.json()
                except:
                    response_data = {"text": response.text}
            
            # Mostrar los resultados
            results = html.Div([
                html.H5("Resultado de la prueba", className="mt-3"),
                html.Div([
                    html.Strong("Endpoint: "), html.Span(final_endpoint),
                    html.Br(),
                    html.Strong("Método: "), html.Span(method),
                    html.Br(),
                    html.Strong("Estado: "), html.Span(f"{status_code} {reason}", className="text-success" if status_code < 400 else "text-danger"),
                    html.Br(),
                    html.Strong("Tiempo de respuesta: "), html.Span(f"{elapsed_time:.2f} segundos"),
                    html.Br(),
                    html.Strong("Parámetros: "), html.Pre(json.dumps(params, indent=2, ensure_ascii=False), className="bg-light p-2 rounded small") if params else html.Span("Ninguno"),
                ], className="mb-3"),
                html.H6("Respuesta:"),
                html.Pre(json.dumps(response_data, indent=2, ensure_ascii=False), className="bg-light p-3 rounded")
            ])
            
            # Actualizar el historial
            timestamp = datetime.now().strftime("%H:%M:%S")
            status_badge_class = "bg-success" if status_code < 400 else "bg-danger"
            
            new_history_item = html.Tr([
                html.Td(timestamp),
                html.Td(method),
                html.Td(final_endpoint),
                html.Td(html.Span(str(status_code), className=f"badge {status_badge_class}"))
            ])
            
            # Limitar el historial a los últimos 10 elementos
            if history is None:
                # Si no hay historial previo, crear uno nuevo
                return results, "", html.Table([html.Tbody([new_history_item])], className="table table-sm")
            
            history_body = history.get("props", {}).get("children", [])
            if isinstance(history_body, list) and len(history_body) > 0:
                history_rows = history_body[0].get("props", {}).get("children", [])
                if isinstance(history_rows, list):
                    history_rows = [new_history_item] + history_rows
                    if len(history_rows) > 10:
                        history_rows = history_rows[:10]
                    
                    updated_history = html.Tbody(history_rows)
                    return results, "", html.Table([updated_history], className="table table-sm")
            
            # Si no hay historial previo o no se pudo procesar, crear uno nuevo
            return results, "", html.Table([html.Tbody([new_history_item])], className="table table-sm")
            
        except Exception as e:
            logger.error(f"Error al ejecutar la prueba de API: {str(e)}")
            error_details = html.Div([
                html.H5("Error al ejecutar la prueba", className="text-danger"),
                html.P(f"Mensaje de error: {str(e)}"),
                html.P("Detalles del error:"),
                html.Pre(traceback.format_exc(), className="bg-light p-3 rounded small")
            ])
            return error_details, "", no_update
    
    # Callback para actualizar el placeholder y el valor del campo params_input
    @app.callback(
        [Output("params-input", "placeholder"),
         Output("params-input", "value")],
        [Input("endpoint-select", "value")]
    )
    def update_params_placeholder(endpoint):
        if endpoint == "get_sensor_uuid_function":
            placeholder = "Ingrese los parámetros en formato JSON"
            value = json.dumps({
                "gateway_id": "gateway_123",
                "device_id": "device_456",
                "sensor_id": "sensor_789"
            }, indent=2)
            return placeholder, value
        elif endpoint == "sensors_with_tags":
            placeholder = "Parámetros para sensores de asset"
            value = json.dumps({
                "include_details": True,
                "filter_by_type": "electricity",
                "active_only": True
            }, indent=2)
            return placeholder, value
        elif endpoint == "asset_time_series":
            placeholder = "Parámetros para series temporales de asset"
            value = json.dumps({
                "from": "02-28-2025",
                "until": "03-07-2025",
                "sensor": "",
                "device_id": "374",
                "sensor_id": "0",
                "gateway_id": "100000009117dd3e"
            }, indent=2)
            return placeholder, value
        elif endpoint == "sensor_data":
            placeholder = "Parámetros para datos de sensor"
            value = json.dumps({
                "from": "2023-01-01",
                "until": "2023-01-31",
                "interval": "day",
                "aggregation": "avg"
            }, indent=2)
            return placeholder, value
        elif endpoint == "projects_by_client":
            placeholder = "Parámetros adicionales para proyectos por cliente"
            value = json.dumps({
                "status": "active",
                "limit": 10,
                "offset": 0
            }, indent=2)
            return placeholder, value
        elif endpoint == "assets_by_client":
            placeholder = "Parámetros adicionales para assets por cliente"
            value = json.dumps({
                "type": "building",
                "status": "active",
                "limit": 10
            }, indent=2)
            return placeholder, value
        elif endpoint == "assets_by_project":
            placeholder = "Parámetros adicionales para assets por proyecto"
            value = json.dumps({
                "type": "building",
                "status": "active",
                "include_sensors": True
            }, indent=2)
            return placeholder, value
        else:
            placeholder = "Parámetros adicionales en formato JSON (opcional)"
            return placeholder, "" 