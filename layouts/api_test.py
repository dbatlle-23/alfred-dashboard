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
        [Input("run-test-button", "n_clicks")],
        prevent_initial_call=False
    )
    def check_connection_status(n_clicks):
        try:
            auth_service = AuthService()
            
            # Verificar si hay un token válido
            if not auth_service.is_authenticated():
                return html.Div([
                    html.P("No hay una sesión activa. Por favor, inicie sesión.", className="text-warning"),
                    html.P("Estado: No autenticado", className="text-danger")
                ])
            
            # Obtener información del token
            token = auth_service.get_token()
            token_info = auth_service.get_user_data()
            
            # Mostrar información de la conexión
            return html.Div([
                html.P("Conexión establecida correctamente.", className="text-success"),
                html.P("Estado: Autenticado", className="text-success"),
                html.P([
                    html.Strong("Usuario: "), 
                    html.Span(token_info.get("username", "Desconocido"))
                ]),
                html.P([
                    html.Strong("Token: "), 
                    html.Span(f"{token[:20]}..." if token and len(token) > 20 else token)
                ]),
                html.P([
                    html.Strong("API Base URL: "), 
                    html.Span(API_BASE_URL)
                ])
            ])
        except Exception as e:
            logger.error(f"Error al verificar el estado de la conexión: {str(e)}")
            return html.Div([
                html.P("Error al verificar el estado de la conexión.", className="text-danger"),
                html.P(f"Error: {str(e)}", className="text-danger small")
            ])
    
    # Callback para probar específicamente el endpoint de proyectos
    @app.callback(
        Output("test-projects-results", "children"),
        [Input("test-projects-button", "n_clicks")],
        prevent_initial_call=True
    )
    def test_projects_endpoint(n_clicks):
        if n_clicks is None:
            return no_update
        
        try:
            auth_service = AuthService()
            
            # Verificar autenticación
            if not auth_service.is_authenticated():
                return html.Div("No hay una sesión activa. Por favor, inicie sesión nuevamente.", className="alert alert-warning")
            
            # Obtener el token actual
            token = auth_service.get_token()
            if not token:
                return html.Div("No se pudo obtener el token de autenticación", className="alert alert-warning")
            
            # Client ID problemático
            client_id = "8f4e2492-68e0-4865-a11a-f7093c6019cb"
            
            # Construir la URL completa
            url = f"{API_BASE_URL}/projects"
            
            # Configurar los headers con el token de autenticación
            headers = {
                'Authorization': f'Bearer {str(token)}',
                'Content-Type': 'application/json'
            }
            
            # Probar diferentes variantes de parámetros
            results = []
            
            # 1. Probar con client
            params1 = {"client": client_id}
            logger.debug(f"Prueba 1: GET {url} con parámetros: {params1}")
            response1 = requests.get(url, headers=headers, params=params1)
            results.append(html.Div([
                html.H5("Prueba 1: Parámetro 'client'"),
                html.P(f"URL: {url}?client={client_id}"),
                html.P(f"Código de estado: {response1.status_code}"),
                html.Pre(json.dumps(response1.json() if response1.status_code == 200 else response1.text, indent=2), 
                         className="bg-light p-3 rounded")
            ]))
            
            # 2. Probar con client_id
            params2 = {"client_id": client_id}
            logger.debug(f"Prueba 2: GET {url} con parámetros: {params2}")
            response2 = requests.get(url, headers=headers, params=params2)
            results.append(html.Div([
                html.H5("Prueba 2: Parámetro 'client_id'"),
                html.P(f"URL: {url}?client_id={client_id}"),
                html.P(f"Código de estado: {response2.status_code}"),
                html.Pre(json.dumps(response2.json() if response2.status_code == 200 else response2.text, indent=2), 
                         className="bg-light p-3 rounded")
            ]))
            
            # 3. Probar con clientId
            params3 = {"clientId": client_id}
            logger.debug(f"Prueba 3: GET {url} con parámetros: {params3}")
            response3 = requests.get(url, headers=headers, params=params3)
            results.append(html.Div([
                html.H5("Prueba 3: Parámetro 'clientId'"),
                html.P(f"URL: {url}?clientId={client_id}"),
                html.P(f"Código de estado: {response3.status_code}"),
                html.Pre(json.dumps(response3.json() if response3.status_code == 200 else response3.text, indent=2), 
                         className="bg-light p-3 rounded")
            ]))
            
            # 4. Probar sin parámetros (todos los proyectos)
            logger.debug(f"Prueba 4: GET {url} sin parámetros")
            response4 = requests.get(url, headers=headers)
            
            # Intentar extraer proyectos del cliente específico manualmente
            matching_projects = []
            if response4.status_code == 200:
                try:
                    all_projects = response4.json()
                    
                    # Buscar en diferentes estructuras posibles
                    projects_list = None
                    if isinstance(all_projects, list):
                        projects_list = all_projects
                    elif isinstance(all_projects, dict):
                        if "data" in all_projects and isinstance(all_projects["data"], list):
                            projects_list = all_projects["data"]
                        elif "projects" in all_projects and isinstance(all_projects["projects"], list):
                            projects_list = all_projects["projects"]
                    
                    if projects_list:
                        for project in projects_list:
                            if not isinstance(project, dict):
                                continue
                                
                            # Buscar el client_id en diferentes campos posibles
                            for key in ['client_id', 'clientId', 'id_cliente', 'cliente_id', 'client', 'cliente', 'clienteId', 'idCliente']:
                                if key in project and str(project[key]) == str(client_id):
                                    matching_projects.append(project)
                                    break
                except Exception as e:
                    logger.error(f"Error al procesar proyectos: {str(e)}")
            
            results.append(html.Div([
                html.H5("Prueba 4: Sin parámetros (todos los proyectos)"),
                html.P(f"URL: {url}"),
                html.P(f"Código de estado: {response4.status_code}"),
                html.P(f"Proyectos encontrados para el cliente {client_id}: {len(matching_projects)}"),
                html.Pre(json.dumps(matching_projects, indent=2) if matching_projects else "No se encontraron proyectos para este cliente", 
                         className="bg-light p-3 rounded")
            ]))
            
            return html.Div([
                html.H4("Resultados de las pruebas del endpoint de proyectos"),
                html.P(f"Client ID probado: {client_id}"),
                html.Hr(),
                html.Div(results)
            ])
            
        except Exception as e:
            logger.error(f"Error al probar el endpoint de proyectos: {str(e)}")
            error_details = html.Div([
                html.H5("Error al ejecutar la prueba", className="text-danger"),
                html.P(f"Mensaje de error: {str(e)}"),
                html.P("Detalles del error:"),
                html.Pre(traceback.format_exc(), className="bg-light p-3 rounded small")
            ])
            return error_details
    
    # Callback para ejecutar la prueba de API
    @app.callback(
        [Output("api-test-results", "children"), Output("api-test-loading", "children"), Output("api-test-history", "children")],
        [Input("run-test-button", "n_clicks")],
        [
            State("endpoint-select", "value"),
            State("method-select", "value"),
            State("custom-endpoint-input", "value"),
            State("params-input", "value"),
            State("api-test-history", "children")
        ],
        prevent_initial_call=True
    )
    def run_api_test(n_clicks, endpoint, method, custom_endpoint, params_json, history):
        """Ejecuta una prueba de API y muestra los resultados"""
        if n_clicks is None:
            return no_update, no_update, no_update
        
        start_time = time.time()
        
        # Determinar el endpoint a usar
        if endpoint == "custom":
            if not custom_endpoint:
                return html.Div("Por favor, ingrese un endpoint personalizado", className="alert alert-warning"), "", no_update
            final_endpoint = custom_endpoint
        else:
            final_endpoint = endpoint
        
        # Preparar los parámetros
        params = None
        if params_json:
            try:
                params = json.loads(params_json)
                logger.debug(f"Parámetros para la prueba de API: {params}")
            except json.JSONDecodeError as e:
                return html.Div(f"Error en el formato JSON de los parámetros: {str(e)}", className="alert alert-danger"), "", no_update
        
        # Ejecutar la prueba
        try:
            auth_service = AuthService()
            
            # Verificar autenticación
            if not auth_service.is_authenticated():
                return html.Div("No hay una sesión activa. Por favor, inicie sesión nuevamente.", className="alert alert-warning"), "", no_update
            
            # Obtener el token actual
            token = auth_service.get_token()
            if not token:
                return html.Div("No se pudo obtener el token de autenticación", className="alert alert-warning"), "", no_update
            
            # Hacer la solicitud a la API
            logger.debug(f"Ejecutando prueba de API: {method} {final_endpoint}")
            response = auth_service.make_api_request(method, final_endpoint, data=params if method in ["POST", "PUT"] else None, params=params if method == "GET" else None)
            
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