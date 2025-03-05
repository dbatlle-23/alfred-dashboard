from dash import html, dcc
import dash_bootstrap_components as dbc
from dash import Input, Output, State, no_update
import dash
import json
import requests
from utils.logging import get_logger
from utils.auth import AuthService, API_BASE_URL
import time
from datetime import datetime
import traceback
import dash_table

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
                    
                    # Campo para parámetros
                    html.Label("Parámetros (JSON)"),
                    dbc.Textarea(
                        id="params-input",
                        placeholder='{"param1": "valor1", "param2": "valor2"}',
                        rows=5,
                        className="mb-3"
                    ),
                    
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
    
    # Callback para mostrar/ocultar el campo de endpoint personalizado
    @app.callback(
        Output("custom-endpoint-container", "style"),
        [Input("endpoint-select", "value")]
    )
    def toggle_custom_endpoint(endpoint):
        if endpoint == "custom":
            return {"display": "block"}
        return {"display": "none"}
    
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
            State("params-input", "value"),
            State("api-test-history", "children"),
            State("jwt-token-store", "data")
        ],
        prevent_initial_call=True
    )
    def run_api_test(n_clicks, endpoint, method, custom_endpoint, params_json, history, token_data):
        if not n_clicks:
            return no_update, no_update, no_update
        
        start_time = time.time()
        
        try:
            # Determinar el endpoint final
            if endpoint == "custom":
                if not custom_endpoint:
                    return html.Div("Por favor, ingrese un endpoint personalizado", className="alert alert-warning"), "", no_update
                final_endpoint = custom_endpoint
            else:
                final_endpoint = endpoint
            
            # Procesar los parámetros JSON
            params = {}
            if params_json:
                try:
                    params = json.loads(params_json)
                except json.JSONDecodeError:
                    return html.Div("Error en el formato JSON de los parámetros", className="alert alert-danger"), "", no_update
            
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
            response = auth_service.make_api_request(token, method, final_endpoint, data=params if method in ["POST", "PUT"] else None, params=params if method == "GET" else None)
            
            # Calcular el tiempo de respuesta
            elapsed_time = time.time() - start_time
            
            # Verificar si la respuesta es un diccionario (ya procesado) o un objeto Response
            if isinstance(response, dict):
                # La respuesta ya es un diccionario (JSON procesado)
                response_data = response
                status_code = 200  # Asumimos éxito si tenemos datos
                reason = "OK"
                
                # Formatear la respuesta como JSON con indentación
                try:
                    formatted_response = json.dumps(response_data, indent=2, ensure_ascii=False, default=str)
                except Exception as e:
                    logger.error(f"Error al formatear la respuesta JSON: {str(e)}")
                    formatted_response = str(response_data)
            else:
                # Es un objeto Response
                status_code = response.status_code
                reason = response.reason
                
                # Formatear la respuesta para mostrarla
                try:
                    # Intentar convertir la respuesta a JSON para mostrarla formateada
                    response_data = response.json()
                    logger.debug(f"Respuesta de API recibida: {type(response_data)}")
                    
                    # Formatear la respuesta como JSON con indentación
                    formatted_response = json.dumps(response_data, indent=2, ensure_ascii=False, default=str)
                except Exception as e:
                    logger.error(f"Error al formatear la respuesta JSON: {str(e)}")
                    # Si no se puede convertir a JSON, mostrar el texto de la respuesta
                    formatted_response = response.text
            
            # Crear el componente de resultados
            status_class = "text-success" if status_code < 400 else "text-danger"
            
            results = html.Div([
                html.H5("Resultados de la prueba"),
                html.Div([
                    html.Span("Estado: ", className="fw-bold"),
                    html.Span(f"{status_code} {reason}", className=status_class)
                ]),
                html.Div([
                    html.Span("Tiempo de respuesta: ", className="fw-bold"),
                    html.Span(f"{elapsed_time:.3f} segundos")
                ]),
                html.Div([
                    html.Span("Respuesta:", className="fw-bold d-block mb-2"),
                    html.Pre(formatted_response, className="bg-light p-3 rounded")
                ])
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