from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash
import pandas as pd
from datetime import datetime, timedelta
import os
from enum import Enum
import dash_table
from io import StringIO
import json
import plotly.express as px
import calendar

# Importar módulos de utilidades
from utils.data_loader import (
    load_all_csv_data, 
    get_projects_with_data, 
    get_assets_with_data, 
    get_consumption_types,
    filter_data,
    aggregate_data_by_project,
    aggregate_data_by_asset,
    aggregate_data_by_consumption_type,
    TAGS_TO_CONSUMPTION_TYPE,
    aggregate_data_by_month_and_asset,
    generate_monthly_readings_by_consumption_type
)
from utils.chart_generator import (
    create_time_series_chart,
    create_bar_chart,
    create_consumption_comparison_chart,
    create_consumption_trend_chart,
    create_consumption_distribution_chart,
    create_heatmap
)
from utils.api import get_clientes, get_projects, get_assets, get_project_assets, get_daily_readings_for_year_multiple_tags_project_parallel

# Definir el enum de tags de consumo
class ConsumptionTags(Enum):
    DOMESTIC_COLD_WATER = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_COLD_WATER"
    DOMESTIC_ENERGY_GENERAL = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL"
    DOMESTIC_HOT_WATER = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER"
    DOMESTIC_WATER_GENERAL = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL"
    PEOPLE_FLOW_IN = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_IN"
    PEOPLE_FLOW_OUT = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_OUT"
    THERMAL_ENERGY_COOLING = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_COOLING"
    THERMAL_ENERGY_HEAT = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT"

# Mapeo de tags a nombres legibles
CONSUMPTION_TAGS_MAPPING = {
    ConsumptionTags.DOMESTIC_COLD_WATER.value: "Agua fría sanitaria",
    ConsumptionTags.DOMESTIC_ENERGY_GENERAL.value: "Energía general",
    ConsumptionTags.DOMESTIC_HOT_WATER.value: "Agua caliente sanitaria",
    ConsumptionTags.DOMESTIC_WATER_GENERAL.value: "Agua general",
    ConsumptionTags.PEOPLE_FLOW_IN.value: "Flujo entrante de personas",
    ConsumptionTags.PEOPLE_FLOW_OUT.value: "Flujo saliente de personas",
    ConsumptionTags.THERMAL_ENERGY_COOLING.value: "Energía térmica frío",
    ConsumptionTags.THERMAL_ENERGY_HEAT.value: "Energía térmica calor"
}

def debug_log(message):
    """
    Función para mostrar logs de depuración solo cuando la aplicación está en modo debug
    
    Args:
        message: Mensaje a mostrar
    """
    # Mostrar siempre el mensaje en la consola
    print(message)
    
    # Guardar el mensaje en un archivo de log
    try:
        with open('debug_log.txt', 'a') as f:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Error al escribir en el archivo de log: {str(e)}")

# Layout para la página de Metrics
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H1("Análisis de Consumos", className="mb-4"),
            html.P("Visualiza y analiza el consumo de suministros en distintos edificios.", className="lead mb-4"),
            
            # Indicador de filtro activo
            html.Div(id="metrics-filter-indicator", className="mb-3"),
            
            # Mensaje de carga de datos
            html.Div(
                id="metrics-data-loading-message",
                className="alert alert-info mb-3",
                children=[
                    html.I(className="fas fa-spinner fa-spin me-2"),
                    "Cargando datos de consumo..."
                ],
                style={"display": "none"}
            ),
            
            # Mensaje de instrucción inicial
            html.Div(
                id="metrics-initial-message",
                className="alert alert-info mb-3",
                children=[
                    html.I(className="fas fa-info-circle me-2"),
                    "Seleccione un cliente, opcionalmente un proyecto, y al menos un tipo de consumo. Luego haga clic en 'Visualizar Consumos' para ver los resultados."
                ],
                style={"display": "block"}
            ),
            
            # Filtros iniciales (Cliente, Proyecto y Tipos de Consumo)
            dbc.Card([
                dbc.CardHeader("Selección", className="bg-primary text-white"),
                dbc.CardBody([
                    dbc.Row([
                        # Filtro de cliente
                        dbc.Col([
                            html.Label("Cliente:", className="fw-bold"),
                            dcc.Dropdown(
                                id="metrics-client-filter",
                                options=[],
                                value=None,
                                clearable=False,
                                className="mb-3"
                            )
                        ], md=6),
                        
                        # Filtro de proyecto
                        dbc.Col([
                            html.Label("Proyecto (opcional):", className="fw-bold"),
                            dcc.Dropdown(
                                id="metrics-project-filter",
                                options=[],
                                value="all",
                                clearable=False,
                                className="mb-3",
                                disabled=True
                            )
                        ], md=6),
                    ]),
                    
                    # Filtro de tipos de consumo
                    dbc.Row([
                        dbc.Col([
                            html.Label("Tipos de Consumo:", className="fw-bold"),
                            dcc.Dropdown(
                                id="metrics-consumption-tags-filter",
                                options=[
                                    {"label": CONSUMPTION_TAGS_MAPPING[tag.value], "value": tag.value}
                                    for tag in ConsumptionTags
                                ],
                                value=[],
                                multi=True,
                                clearable=True,
                                placeholder="Seleccione al menos un tipo de consumo",
                                className="mb-3",
                                disabled=True
                            )
                        ], md=12),
                    ]),
                    
                    # Botón de visualización
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "Visualizar Consumos",
                                id="metrics-analyze-button",
                                color="primary",
                                className="w-100 mt-2",
                                disabled=True
                            )
                        ], md=6),
                        dbc.Col([
                            dbc.Button(
                                "Actualizar Lecturas",
                                id="metrics-update-readings-button",
                                color="success",
                                className="w-100 mt-2",
                                disabled=True
                            )
                        ], md=6),
                    ]),
                    
                    # Resultados de la actualización de lecturas
                    dbc.Row([
                        dbc.Col([
                            html.Div(id="metrics-update-readings-result", className="mt-3")
                        ], md=12)
                    ])
                ])
            ], className="mb-4 shadow-sm"),
            
            # Contenedor para los filtros adicionales y visualizaciones (inicialmente oculto)
            html.Div([
                # Filtros adicionales
                dbc.Card([
                    dbc.CardHeader("Filtros Adicionales", className="bg-primary text-white"),
                    dbc.CardBody([
                        dbc.Row([
                        # Filtro de asset
                        dbc.Col([
                            html.Label("Asset:"),
                            dcc.Dropdown(
                                id="metrics-asset-filter",
                                options=[
                                    {"label": "Todos los assets", "value": "all"}
                                ],
                                value="all",
                                clearable=False,
                                className="mb-3"
                            )
                            ], md=6),
                        
                            # Filtro de rango de fechas
                        dbc.Col([
                                html.Label("Período de tiempo:"),
                            dcc.Dropdown(
                                    id="metrics-date-period",
                                options=[
                                        {"label": "Último mes", "value": "last_month"},
                                        {"label": "Últimos 3 meses", "value": "last_3_months"},
                                        {"label": "Último año", "value": "last_year"},
                                        {"label": "Personalizado", "value": "custom"}
                                    ],
                                    value="last_month",
                                clearable=False,
                                className="mb-3"
                                ),
                                # Contenedor para el selector de fechas personalizado (inicialmente oculto)
                                html.Div([
                            dcc.DatePickerRange(
                                id="metrics-date-range",
                                start_date=(datetime.now() - timedelta(days=30)).date(),
                                end_date=datetime.now().date(),
                                display_format="DD/MM/YYYY",
                                        className="mb-3 w-100"
                            )
                                ], id="metrics-custom-date-container", style={"display": "none"})
                        ], md=6),
                        ]),
                        
                        dbc.Row([
                        # Filtro de período de tiempo para tendencias
                        dbc.Col([
                            html.Label("Agrupación temporal:"),
                            dcc.RadioItems(
                                id="metrics-time-period",
                                options=[
                                    {"label": "Diario", "value": "D"},
                                    {"label": "Semanal", "value": "W"},
                                    {"label": "Mensual", "value": "M"}
                                ],
                                value="M",
                                inline=True,
                                className="mb-3"
                            )
                            ], md=12)
                    ]),
                    ])
                ], className="mb-4 shadow-sm"),
                    
                # Tabla de lecturas mensuales por asset
                    dbc.Row([
                        dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Lecturas Mensuales por Asset"),
                            dbc.CardBody([
                                html.Div(id="metrics-monthly-readings-table")
                            ])
                        ], className="shadow-sm")
                    ], className="mb-4"),
                ]),
                
                # Tablas de lecturas mensuales por tipo de consumo
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Lecturas Mensuales por Tipo de Consumo"),
                            dbc.CardBody([
                                html.Div(id="metrics-monthly-readings-by-consumption-type")
                            ])
                        ], className="shadow-sm")
                    ], className="mb-4"),
                ]),
            
            # Tarjetas de métricas
            dbc.Row([
                # Métrica 1: Consumo total
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Consumo Total", className="card-title text-center"),
                            html.H2(id="metrics-total-consumption", className="text-center text-primary mb-0"),
                            html.P(id="metrics-total-consumption-unit", className="text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Métrica 2: Promedio diario
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Promedio Diario", className="card-title text-center"),
                            html.H2(id="metrics-daily-average", className="text-center text-primary mb-0"),
                            html.P(id="metrics-daily-average-unit", className="text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
                
                # Métrica 3: Tendencia
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Tendencia", className="card-title text-center"),
                            html.H2(id="metrics-trend", className="text-center mb-0"),
                            html.P(id="metrics-trend-period", className="text-center mt-2 mb-0")
                        ])
                    ], className="shadow-sm")
                ], md=4, className="mb-4"),
            ]),
            
            # Gráficos
            dbc.Row([
                # Gráfico 1: Evolución temporal
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Evolución temporal del consumo"),
                        dbc.CardBody([
                            dcc.Graph(id="metrics-time-series-chart")
                        ])
                    ], className="shadow-sm")
                ], md=12, className="mb-4"),
            ]),
            
            dbc.Row([
                # Gráfico 2: Comparativa por tipo de consumo
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Comparativa por tipo de consumo"),
                        dbc.CardBody([
                            dcc.Graph(id="metrics-consumption-type-chart")
                        ])
                    ], className="shadow-sm")
                ], md=6, className="mb-4"),
                
                # Gráfico 3: Distribución de consumo
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Distribución de consumo"),
                        dbc.CardBody([
                            dcc.Graph(id="metrics-distribution-chart")
                        ])
                    ], className="shadow-sm")
                ], md=6, className="mb-4"),
            ]),
            
            # Gráfico 4: Tendencias de consumo
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Tendencias de consumo"),
                        dbc.CardBody([
                            dcc.Graph(id="metrics-trend-chart")
                        ])
                    ], className="shadow-sm")
                ], className="mb-4"),
            ]),
            
            # Gráfico 5: Comparativa entre assets
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Comparativa entre assets"),
                        dbc.CardBody([
                            dcc.Graph(id="metrics-assets-comparison-chart")
                        ])
                    ], className="shadow-sm")
                ], className="mb-4"),
            ]),
            ], id="metrics-visualization-container", style={"display": "none"}),
            
            # Store para almacenar los datos cargados
            dcc.Store(id="metrics-data-store"),
            
            # Store para almacenar el cliente seleccionado
            dcc.Store(id="metrics-selected-client-store", data={}),
            
            # Store para almacenar los tipos de consumo seleccionados
            dcc.Store(id="metrics-selected-consumption-tags-store", data={}),
            
            # Modal para mostrar análisis detallado de consumo
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(id="metrics-detail-modal-title")),
                    dbc.ModalBody(id="metrics-detail-modal-body"),
                    dbc.ModalFooter(
                        dbc.Button("Cerrar", id="metrics-detail-close-button", className="ms-auto", n_clicks=0)
                    ),
                ],
                id="metrics-detail-modal",
                size="xl",
                is_open=False,
            ),
        ]),
        
        # Modal para mostrar detalles de consumo
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(id="consumption-detail-modal-title")),
                dbc.ModalBody(id="consumption-detail-modal-body"),
                dbc.ModalFooter(
                    dbc.Button("Cerrar", id="close-consumption-detail-modal", className="ms-auto")
                ),
            ],
            id="consumption-detail-modal",
            size="xl",
            is_open=False,
        ),
        
        # Store para guardar datos seleccionados
        dcc.Store(id="selected-consumption-data")
    ])
])

# Registrar callbacks para la página de Metrics
def register_callbacks(app):
    # Callback para cargar la lista de clientes
    @app.callback(
        Output("metrics-client-filter", "options"),
        [Input("url", "pathname"),
         Input("jwt-token-store", "data")]
    )
    def load_client_options(pathname, token_data):
        if pathname != "/metrics":
            return dash.no_update
        
        try:
            # Obtener el token JWT directamente del store
            token = token_data.get('token') if token_data else None
            
            if not token:
                print("[ERROR METRICS] load_client_options - No se encontró token JWT")
                return []
            
            # Obtener la lista de clientes usando el token
            clientes = get_clientes(jwt_token=token)
            
            if clientes and isinstance(clientes, list):
                # Verificar si son datos reales o fallback
                is_fallback = any("FALLBACK" in str(client.get('nombre', '')) for client in clientes[:5])
                
                if is_fallback:
                    print("[WARN METRICS] load_client_options - Se obtuvieron datos de fallback, intentando obtener datos reales")
                    
                    # Intentar hacer una solicitud directa a la API
                    from utils.auth import auth_service
                    endpoint = "clients"
                    response = auth_service.make_api_request(token, "GET", endpoint)
                    
                    if isinstance(response, dict) and "error" not in response:
                        # Extraer clientes de la respuesta
                        from utils.api import extract_list_from_response
                        clientes = extract_list_from_response(response, lambda: [], "clients")
                
                # Crear las opciones para el dropdown
                options = []
                for client in clientes:
                    if isinstance(client, dict) and "id" in client:
                        # Buscar el nombre en diferentes claves posibles
                        client_name = None
                        for key in ['nombre', 'name', 'client_name', 'nombre_cliente']:
                            if key in client and client[key]:
                                client_name = client[key]
                                break
                        
                        if not client_name:
                            client_name = f"Cliente {client['id']}"
                        
                        options.append({"label": client_name, "value": client['id']})
                
                print(f"[INFO METRICS] load_client_options - Se cargaron {len(options)} clientes")
                return options
            
            print("[WARN METRICS] load_client_options - No se obtuvieron clientes")
            return []
        except Exception as e:
            print(f"[ERROR METRICS] load_client_options: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
    
    # Callback para habilitar/deshabilitar el dropdown de proyectos y almacenar el cliente seleccionado
    @app.callback(
        [Output("metrics-project-filter", "disabled"),
         Output("metrics-consumption-tags-filter", "disabled"),
         Output("metrics-selected-client-store", "data")],
        [Input("metrics-client-filter", "value")]
    )
    def update_project_state(client_id):
        if client_id:
            # Almacenar el cliente seleccionado y habilitar los dropdowns
            return False, False, {"client_id": client_id}
        else:
            # Deshabilitar los dropdowns si no hay cliente seleccionado
            return True, True, None
    
    # Callback para almacenar los tipos de consumo seleccionados
    @app.callback(
        Output("metrics-selected-consumption-tags-store", "data"),
        [Input("metrics-consumption-tags-filter", "value")]
    )
    def update_consumption_tags_store(consumption_tags):
        return {"consumption_tags": consumption_tags}
    
    # Callback para habilitar/deshabilitar los botones de análisis y actualización
    @app.callback(
        [Output("metrics-analyze-button", "disabled"),
         Output("metrics-update-readings-button", "disabled")],
        [Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-consumption-tags-filter", "value")]
    )
    def update_buttons_state(client_id, project_id, consumption_tags):
        # El botón de visualizar consumos se habilita cuando hay un cliente seleccionado y al menos un tipo de consumo
        visualize_disabled = True
        update_readings_disabled = True
        
        if client_id and consumption_tags and len(consumption_tags) > 0:
            visualize_disabled = False
            
            # El botón de actualizar lecturas se habilita solo si además hay un proyecto específico seleccionado
            if project_id and project_id != "all":
                update_readings_disabled = False
        
        return visualize_disabled, update_readings_disabled
    
    # Callback para actualizar las opciones de filtro de proyecto basado en el cliente seleccionado
    @app.callback(
        [Output("metrics-project-filter", "options"),
         Output("metrics-project-filter", "value")],
        [Input("metrics-selected-client-store", "data"),
         Input("url", "pathname")],
        [State("jwt-token-store", "data")]
    )
    def update_project_options(client_selection, pathname, token_data):
        if pathname != "/metrics" or not client_selection:
            return dash.no_update, dash.no_update
        
        try:
            # Inicializar las opciones con la opción "Todos los proyectos"
            options = [{"label": "Todos los proyectos", "value": "all"}]
            
            # Obtener el ID del cliente seleccionado
            client_id = client_selection.get("client_id")
            
            if not client_id:
                return options, "all"
                
            # Obtener el token JWT directamente del store
            token = token_data.get('token') if token_data else None
            
            if not token:
                print("[ERROR METRICS] update_project_options - No se encontró token JWT")
                return options, "all"
            
            print(f"[INFO METRICS] update_project_options - Obteniendo proyectos para cliente: {client_id}")
            
            # Intentar obtener proyectos directamente de la API
            from utils.auth import auth_service
            endpoint = "projects"
            # Usar 'client' en lugar de 'client_id' como parámetro
            params = {"client": client_id} if client_id != "all" else {}
            
            print(f"[INFO METRICS] update_project_options - Realizando solicitud a la API: {endpoint} con parámetros: {params}")
            response = auth_service.make_api_request(token, "GET", endpoint, params=params)
            
            projects = []
            
            # Verificar si la respuesta contiene datos
            if isinstance(response, dict) and "error" not in response:
                # Extraer proyectos de la respuesta
                from utils.api import extract_list_from_response
                projects = extract_list_from_response(response, lambda x: [], "projects", client_id)
                
                # Si no se encontraron proyectos, buscar en otras estructuras de la respuesta
                if not projects:
                    print("[WARN METRICS] update_project_options - No se encontraron proyectos en la estructura estándar, buscando en otras estructuras")
                    
                    # Buscar en estructuras anidadas
                    if "data" in response and isinstance(response["data"], dict):
                        data = response["data"]
                        if "projects" in data and isinstance(data["projects"], list):
                            projects = data["projects"]
                            print(f"[INFO METRICS] update_project_options - Proyectos encontrados en data.projects: {len(projects)}")
                        elif "items" in data and isinstance(data["items"], list):
                            projects = data["items"]
                            print(f"[INFO METRICS] update_project_options - Proyectos encontrados en data.items: {len(projects)}")
                    elif "data" in response and isinstance(response["data"], list):
                        # Si 'data' es una lista, usarla directamente
                        projects = response["data"]
                        print(f"[INFO METRICS] update_project_options - Proyectos encontrados en data: {len(projects)}")
                    
                    # Buscar en la raíz de la respuesta
                    if not projects:
                        for key, value in response.items():
                            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict) and "id" in value[0]:
                                projects = value
                                print(f"[INFO METRICS] update_project_options - Proyectos encontrados en {key}: {len(projects)}")
                                break
            
            # Si no se encontraron proyectos con la solicitud directa, intentar con get_projects
            if not projects:
                print("[WARN METRICS] update_project_options - No se encontraron proyectos con la solicitud directa, intentando con get_projects")
                from utils.api import get_projects
                projects = get_projects(client_id=client_id, jwt_token=token)
            
            # Verificar si los proyectos son datos de fallback
            is_fallback = any("FALLBACK" in str(p.get('name', '')) for p in projects[:5] if isinstance(p, dict))
            
            if is_fallback:
                print("[WARN METRICS] update_project_options - Se obtuvieron datos de fallback, intentando una última vez con solicitud directa")
                
                # Intentar una solicitud directa a la URL completa
                import requests
                from utils.api import BASE_URL
                
                try:
                    url = f"{BASE_URL}/projects"
                    headers = auth_service.get_auth_headers_from_token(token)
                    
                    # Usar 'client' en lugar de 'client_id' como parámetro
                    direct_params = {"client": client_id} if client_id != "all" else {}
                    
                    # Realizar la solicitud directa
                    response = requests.get(url, headers=headers, params=direct_params, timeout=10)
                    
                    if response.status_code >= 200 and response.status_code < 300:
                        print(f"[INFO METRICS] update_project_options - Solicitud directa exitosa: {response.status_code}")
                        try:
                            response_data = response.json()
                            
                            # Buscar proyectos en la respuesta
                            if isinstance(response_data, list):
                                projects = response_data
                            elif isinstance(response_data, dict):
                                # Buscar en diferentes estructuras
                                for key in ["data", "projects", "items", "results"]:
                                    if key in response_data and isinstance(response_data[key], list):
                                        projects = response_data[key]
                                        break
                                
                                # Si no se encontró en las claves comunes, buscar en cualquier lista
                                if not projects:
                                    for key, value in response_data.items():
                                        if isinstance(value, list) and len(value) > 0:
                                            projects = value
                                            break
                        except ValueError:
                            print(f"[ERROR METRICS] update_project_options - La respuesta directa no es JSON válido")
                except Exception as e:
                    print(f"[ERROR METRICS] update_project_options - Error en la solicitud directa: {str(e)}")
                
                # Ya no necesitamos redefinir options aquí
            if projects:
                # Filtrar proyectos por cliente si es necesario
                if client_id != "all":
                    filtered_projects = []
                    for project in projects:
                        # Verificar si el proyecto pertenece al cliente seleccionado
                        project_client_id = None
                        
                        # Buscar el client_id en diferentes estructuras posibles
                        if "client" in project and isinstance(project["client"], dict) and "id" in project["client"]:
                            project_client_id = str(project["client"]["id"])
                        elif "client_id" in project:
                            project_client_id = str(project["client_id"])
                        elif "client" in project and not isinstance(project["client"], dict):
                            project_client_id = str(project["client"])
                        
                        if project_client_id and project_client_id == str(client_id):
                            filtered_projects.append(project)
                    
                    # Solo usar los proyectos filtrados si se encontraron
                    if filtered_projects:
                        projects = filtered_projects
                
                # Crear las opciones para el dropdown
                for project in projects:
                    if isinstance(project, dict) and "id" in project:
                        # Buscar el nombre en diferentes claves posibles
                        project_name = None
                        for key in ['name', 'nombre', 'project_name', 'nombre_proyecto']:
                            if key in project and project[key]:
                                project_name = project[key]
                                break
                        
                        if not project_name:
                            project_name = f"Proyecto {project['id']}"
                        
                        # Verificar si ya existe esta opción
                        if not any(opt["value"] == project['id'] for opt in options):
                            options.append({"label": project_name, "value": project['id']})
                
                print(f"[INFO METRICS] update_project_options - Se cargaron {len(options)-1} proyectos para el cliente {client_id}")
            else:
                print(f"[WARN METRICS] update_project_options - No se encontraron proyectos para el cliente {client_id}")
                
                # Si no se encontraron proyectos, usar el fallback como último recurso
                from utils.api import get_projects_fallback
                fallback_projects = get_projects_fallback(client_id)
                
                if fallback_projects:
                    for project in fallback_projects:
                        if isinstance(project, dict) and "id" in project:
                            project_name = project.get("name", f"Proyecto {project['id']}")
                            options.append({"label": project_name, "value": project['id']})
                    
                    print(f"[INFO METRICS] update_project_options - Se cargaron {len(options)-1} proyectos de fallback")
            
            return options, "all"
        except Exception as e:
            print(f"[ERROR METRICS] update_project_options: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return [{"label": "Todos los proyectos", "value": "all"}], "all"
    
    # Callback para cargar los datos cuando se hace clic en el botón de análisis
    @app.callback(
        Output("metrics-data-store", "data"),
        [Input("metrics-analyze-button", "n_clicks")],
        [State("metrics-client-filter", "value"),
         State("metrics-project-filter", "value"),
         State("metrics-consumption-tags-filter", "value")],
        prevent_initial_call=True
    )
    def load_data(n_clicks, client_id, project_id, consumption_tags):
        if not n_clicks or not client_id or not consumption_tags or len(consumption_tags) == 0:
            debug_log(f"[DEBUG DETALLADO] load_data - Condiciones no cumplidas: n_clicks={n_clicks}, client_id={client_id}, consumption_tags={consumption_tags}")
            return None
            
        try:
            # Obtener el token JWT del almacenamiento
            token = None
            try:
                from dash import callback_context
                token_store = callback_context.states.get('jwt-token-store.data')
                if token_store:
                    token = token_store
                    debug_log(f"[DEBUG DETALLADO] load_data - Token JWT obtenido del almacenamiento")
            except Exception as e:
                debug_log(f"[DEBUG DETALLADO] load_data - Error al obtener token JWT: {str(e)}")
            
            # Log para depuración
            debug_log(f"[DEBUG DETALLADO] load_data - Iniciando carga de datos para cliente: {client_id}, proyecto: {project_id}, tipos de consumo: {consumption_tags}")
            
            # Log crítico para verificar el valor exacto de project_id
            debug_log(f"[DEBUG CRÍTICO] load_data - Valor exacto de project_id que se pasará a load_all_csv_data: '{project_id}', tipo: {type(project_id)}")
            
            # Cargar solo los archivos CSV correspondientes a los tags de consumo seleccionados
            debug_log(f"[DEBUG DETALLADO] load_data - Llamando a load_all_csv_data con consumption_tags={consumption_tags}, project_id={project_id}")
            df = load_all_csv_data(consumption_tags=consumption_tags, project_id=project_id, jwt_token=token)
            debug_log(f"[DEBUG DETALLADO] load_data - load_all_csv_data completado, DataFrame tiene {len(df) if df is not None else 0} filas")
            
            # Aplicar todos los filtros de una sola vez
            debug_log(f"[DEBUG DETALLADO] load_data - Aplicando todos los filtros: client_id={client_id}, project_id={project_id}, consumption_tags={consumption_tags}")
            df = filter_data(df, client_id=client_id, project_id=project_id, consumption_tags=consumption_tags)
            debug_log(f"[DEBUG DETALLADO] load_data - Filtrado completado, DataFrame tiene {len(df) if df is not None else 0} filas")
            
            # Verificar si hay datos después de filtrar
            if df.empty:
                debug_log(f"[DEBUG DETALLADO] load_data - No hay datos después de aplicar todos los filtros")
                return None
                
            # Mostrar los tipos de consumo únicos en el DataFrame final
            unique_consumption_types = df['consumption_type'].unique()
            debug_log(f"[DEBUG DETALLADO] load_data - Tipos de consumo únicos en el DataFrame final: {unique_consumption_types}")
            
            # Limitar la cantidad de datos para evitar problemas de serialización
            debug_log(f"[DEBUG DETALLADO] load_data - Limitando datos para serialización")
            
            # Seleccionar solo las columnas necesarias
            columns_to_keep = ['date', 'asset_id', 'consumption', 'consumption_type', 'project_id', 'tag']
            df = df[columns_to_keep]
            
            # Convertir la columna de fecha a string para evitar problemas de serialización
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            
            # Limitar a un máximo de filas si es necesario (por ejemplo, 10000 filas)
            if len(df) > 10000:
                debug_log(f"[DEBUG DETALLADO] load_data - Limitando DataFrame de {len(df)} a 10000 filas")
                df = df.sample(10000, random_state=42)
            
            # Convertir a formato JSON para almacenar en dcc.Store
            try:
                json_data = df.to_json(date_format='iso', orient='split')
                debug_log(f"[DEBUG DETALLADO] load_data - Datos convertidos a JSON correctamente")
                return json_data
            except Exception as e:
                print(f"[ERROR DETALLADO] load_data - Error al convertir a JSON: {str(e)}")
                
                # Intentar con un enfoque más seguro
                debug_log(f"[DEBUG DETALLADO] load_data - Intentando con un enfoque alternativo")
                
                # Convertir a diccionario y luego a JSON
                try:
                    data_dict = {
                        'columns': df.columns.tolist(),
                        'data': df.values.tolist()
                    }
                    json_data = json.dumps(data_dict)
                    debug_log(f"[DEBUG DETALLADO] load_data - Datos convertidos a JSON correctamente con enfoque alternativo")
                    return json_data
                except Exception as e2:
                    print(f"[ERROR DETALLADO] load_data - Error al convertir a JSON con enfoque alternativo: {str(e2)}")
                    return None
        except Exception as e:
            print(f"[ERROR DETALLADO] load_data - Error al cargar los datos: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None
    
    # Callback para mostrar/ocultar el contenedor de visualizaciones
    @app.callback(
        Output("metrics-visualization-container", "style"),
        [Input("metrics-data-store", "data")]
    )
    def toggle_visualization_container(json_data):
        if json_data:
            return {"display": "block"}
        else:
            return {"display": "none"}
    
    # Callback para actualizar las opciones de filtro de asset
    @app.callback(
        [Output("metrics-asset-filter", "options"),
         Output("metrics-asset-filter", "value")],
        [Input("metrics-project-filter", "value"),
         Input("metrics-selected-client-store", "data"),
         Input("metrics-data-store", "data")],
        [State("jwt-token-store", "data")]
    )
    def update_asset_options(project_id, client_selection, json_data, token_data):
        # Solo actualizar cuando hay datos cargados
        if not json_data or not client_selection:
                return [{"label": "Todos los assets", "value": "all"}], "all"
                
        try:
            # Obtener el ID del cliente seleccionado
            client_id = client_selection.get("client_id")
            
            if not client_id:
                return [{"label": "Todos los assets", "value": "all"}], "all"
            
            # Obtener el token JWT directamente del store
            token = token_data.get('token') if token_data else None
            
            if not token:
                print("[ERROR METRICS] update_asset_options - No se encontró token JWT")
                return [{"label": "Todos los assets", "value": "all"}], "all"
            
            # Si no se ha seleccionado un proyecto específico, mostrar opciones genéricas
            if not project_id or project_id == "all":
                    try:
                        # Intentar obtener assets para el cliente seleccionado
                        assets = get_assets(client_id=client_id, jwt_token=token)
                        if assets:
                        # Crear las opciones para el dropdown
                            options = [{"label": "Todos los assets", "value": "all"}]
                            options.extend([
                                {"label": a.get("name", f"Asset {a['id']}"), "value": a['id']} 
                                for a in assets
                            ])
                        
                            print(f"[INFO METRICS] update_asset_options - Se cargaron {len(options)-1} assets para el cliente {client_id}")
                            return options, "all"
                        else:
                            print(f"[WARNING METRICS] update_asset_options - No se encontraron assets para el cliente {client_id}")
                    except Exception as e:
                        print(f"[ERROR METRICS] Error al cargar assets para el cliente {client_id}: {str(e)}")
            else:
                # Si se ha seleccionado un proyecto específico, obtener los assets de ese proyecto
                try:
                    # Intentar obtener assets para el proyecto seleccionado
                    assets = get_project_assets(project_id, jwt_token=token)
                    
                    if assets:
                        options = [{"label": "Todos los assets", "value": "all"}]
                        options.extend([
                            {"label": asset.get("name", f"Asset {asset['id']}"), "value": asset["id"]}
                            for asset in assets if isinstance(asset, dict) and "id" in asset
                        ])
                        
                        print(f"[INFO METRICS] update_asset_options - Se cargaron {len(options)-1} assets para el proyecto {project_id}")
                        return options, "all"
                    else:
                        print(f"[WARNING METRICS] update_asset_options - No se encontraron assets para el proyecto {project_id}")
                except Exception as e:
                    print(f"[ERROR METRICS] Error al cargar assets para el proyecto {project_id}: {str(e)}")
                
                # Método alternativo: usar los datos ya cargados
                try:
                    # Usar los datos ya cargados
                    df = pd.read_json(StringIO(json_data), orient='split')
                    assets = get_assets_with_data(df, project_id)
                    if assets:
                        # Crear las opciones para el dropdown
                        options = [{"label": "Todos los assets", "value": "all"}]
                        options.extend([
                            {"label": a.get("nombre", f"Asset {a['id']}"), "value": a['id']} 
                            for a in assets
                        ])
                        
                        print(f"[INFO METRICS] update_asset_options - Se cargaron {len(options)-1} assets de los datos")
                        return options, "all"
                    else:
                        print(f"[WARNING METRICS] update_asset_options - No se encontraron assets de los datos")
                except Exception as e:
                    print(f"[ERROR METRICS] Error al cargar datos para assets: {str(e)}")
                
                # Si todo falla, devolver opción por defecto
                return [{"label": "Todos los assets", "value": "all"}], "all"
        except Exception as e:
            print(f"[ERROR METRICS] Error al actualizar opciones de asset: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return [{"label": "Todos los assets", "value": "all"}], "all"
    
    # Callback para mostrar/ocultar los mensajes
    @app.callback(
        [Output("metrics-data-loading-message", "style"),
         Output("metrics-initial-message", "style")],
        [Input("metrics-data-store", "data"),
         Input("metrics-analyze-button", "n_clicks")]
    )
    def toggle_messages(json_data, n_clicks):
        # Si no se ha hecho clic en el botón, mostrar el mensaje inicial
        if not n_clicks:
            return {"display": "none"}, {"display": "block"}
        
        # Si se ha hecho clic pero no hay datos, mostrar el mensaje de carga
        if json_data is None:
            return {"display": "block"}, {"display": "none"}
        
        # Si hay datos, ocultar ambos mensajes
        return {"display": "none"}, {"display": "none"}
    
    # Callback para actualizar el indicador de filtro
    @app.callback(
        Output("metrics-filter-indicator", "children"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-period", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")],
        [State("jwt-token-store", "data")]
    )
    def update_filter_indicator(json_data, client_id, project_id, asset_id, consumption_tags, date_period, start_date, end_date, token_data):
        # Si no hay datos, no mostrar filtros aplicados
        if not json_data:
            return html.Div()
        
        try:
            # Obtener el token JWT directamente del store
            token = token_data.get('token') if token_data else None
            
            # Crear lista de filtros aplicados
            filters = []
            
            # Añadir filtro de cliente
            if client_id:
                # Intentar obtener el nombre del cliente
                try:
                    clientes = get_clientes(jwt_token=token)
                    
                    # Verificar si son datos de fallback
                    if any("FALLBACK" in str(client.get('nombre', '')) for client in clientes[:5] if isinstance(client, dict)):
                        # Intentar hacer una solicitud directa a la API
                        if token:
                            from utils.auth import auth_service
                            endpoint = "clients"
                            response = auth_service.make_api_request(token, "GET", endpoint)
                            
                            if isinstance(response, dict) and "error" not in response:
                                # Extraer clientes de la respuesta
                                from utils.api import extract_list_from_response
                                clientes = extract_list_from_response(response, lambda: [], "clients")
                    
                    # Buscar el cliente por ID
                    client_match = None
                    if clientes and isinstance(clientes, list):
                        for client in clientes:
                            if isinstance(client, dict) and "id" in client and str(client["id"]) == str(client_id):
                                client_match = client
                                break
                    
                    # Obtener el nombre del cliente
                    if client_match:
                        # Buscar el nombre en diferentes claves posibles
                        client_name = None
                        for key in ['nombre', 'name', 'client_name', 'nombre_cliente']:
                            if key in client_match:
                                client_name = client_match[key]
                                break
                        
                        if not client_name:
                            client_name = f"Cliente {client_id}"
                    else:
                        client_name = f"Cliente {client_id}"
                    
                    filters.append(f"Cliente: {client_name}")
                except Exception as e:
                    print(f"[ERROR METRICS] update_filter_indicator - Error al obtener nombre del cliente: {str(e)}")
                    filters.append(f"Cliente: {client_id}")
            
            # Añadir filtro de proyecto
            if project_id and project_id != "all":
                # Intentar obtener el nombre del proyecto
                try:
                    projects = get_projects(client_id=client_id, jwt_token=token)
                    
                    # Verificar si son datos de fallback
                    if not projects or any("FALLBACK" in str(p.get('name', '')) for p in projects[:5] if isinstance(p, dict)):
                        # Intentar hacer una solicitud directa a la API
                        if token:
                            from utils.auth import auth_service
                            endpoint = f"projects?client_id={client_id}"
                            response = auth_service.make_api_request(token, "GET", endpoint)
                            
                            if isinstance(response, dict) and "error" not in response:
                                # Extraer proyectos de la respuesta
                                from utils.api import extract_list_from_response
                                projects = extract_list_from_response(response, lambda x: [], "projects", client_id)
                    
                    # Buscar el proyecto por ID
                    project_match = None
                    if projects and isinstance(projects, list):
                        for project in projects:
                            if isinstance(project, dict) and "id" in project and str(project["id"]) == str(project_id):
                                project_match = project
                                break
                    
                    # Si no se encuentra, intentar con el fallback
                    if not project_match:
                        from utils.api import get_projects_fallback
                        projects_fallback = get_projects_fallback(client_id)
                        for project in projects_fallback:
                            if isinstance(project, dict) and "id" in project and str(project["id"]) == str(project_id):
                                project_match = project
                                break
                    
                    # Obtener el nombre del proyecto
                    if project_match:
                        # Buscar el nombre en diferentes claves posibles
                        project_name = None
                        for key in ['nombre', 'name', 'project_name', 'nombre_proyecto']:
                            if key in project_match:
                                project_name = project_match[key]
                                break
                        
                        if not project_name:
                            project_name = f"Proyecto {project_id}"
                    else:
                        project_name = f"Proyecto {project_id}"
                    
                    filters.append(f"Proyecto: {project_name}")
                except Exception as e:
                    print(f"[ERROR METRICS] update_filter_indicator - Error al obtener nombre del proyecto: {str(e)}")
                    filters.append(f"Proyecto: {project_id}")
            
            # Añadir filtro de asset
            if asset_id and asset_id != "all":
                # Intentar obtener el nombre del asset
                try:
                    assets = get_assets(project_id=project_id if project_id != "all" else None, 
                                       client_id=client_id, 
                                       jwt_token=token)
                    
                    # Verificar si son datos de fallback
                    if not assets or any("FALLBACK" in str(a.get('name', '')) for a in assets[:5] if isinstance(a, dict)):
                        # Intentar hacer una solicitud directa a la API
                        if token:
                            from utils.auth import auth_service
                            endpoint = f"assets?project_id={project_id if project_id != 'all' else ''}&client_id={client_id}"
                            response = auth_service.make_api_request(token, "GET", endpoint)
                            
                            if isinstance(response, dict) and "error" not in response:
                                # Extraer assets de la respuesta
                                from utils.api import extract_list_from_response
                                assets = extract_list_from_response(response, lambda: [], "assets")
                    
                    # Buscar el asset por ID
                    asset_match = None
                    if assets and isinstance(assets, list):
                        for asset in assets:
                            if isinstance(asset, dict) and "id" in asset and str(asset["id"]) == str(asset_id):
                                asset_match = asset
                                break
                    
                    # Obtener el nombre del asset
                    if asset_match:
                        # Buscar el nombre en diferentes claves posibles
                        asset_name = None
                        for key in ['nombre', 'name', 'asset_name', 'nombre_asset']:
                            if key in asset_match:
                                asset_name = asset_match[key]
                                break
                        
                        if not asset_name:
                            asset_name = f"Asset {asset_id}"
                    else:
                        asset_name = f"Asset {asset_id}"
                    
                    filters.append(f"Asset: {asset_name}")
                except Exception as e:
                    print(f"[ERROR METRICS] update_filter_indicator - Error al obtener nombre del asset: {str(e)}")
                    filters.append(f"Asset: {asset_id}")
            
            # Añadir filtro de tipos de consumo
            if consumption_tags:
                filters.append(f"Tipos de consumo: {', '.join(consumption_tags)}")
            
            # Añadir filtro de período
            if date_period and date_period != "custom":
                # Mostrar el nombre del período predefinido
                period_names = {
                    "last_month": "Último mes",
                    "last_3_months": "Últimos 3 meses",
                    "last_year": "Último año"
                }
                period_name = period_names.get(date_period, date_period)
                filters.append(f"Período: {period_name}")
            else:
                # Mostrar el rango de fechas personalizado
                try:
                    from datetime import datetime
                    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                    formatted_start_date = start_date_obj.strftime("%d/%m/%Y")
                    formatted_end_date = end_date_obj.strftime("%d/%m/%Y")
                    filters.append(f"Período: {formatted_start_date} a {formatted_end_date}")
                except:
                    filters.append(f"Período: {start_date} a {end_date}")
            
            if filters:
                return html.Div([
                    html.I(className="fas fa-filter me-2"),
                    f"Filtros aplicados: {', '.join(filters)}"
                ], className="alert alert-primary")
            
            return ""
        except Exception as e:
            print(f"[ERROR METRICS] update_filter_indicator - Error general: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            # En caso de error, mostrar los filtros básicos
            basic_filters = []
            if client_id:
                basic_filters.append(f"Cliente: {client_id}")
            if project_id and project_id != "all":
                basic_filters.append(f"Proyecto: {project_id}")
            if asset_id and asset_id != "all":
                basic_filters.append(f"Asset: {asset_id}")
            if consumption_tags:
                basic_filters.append(f"Tipos de consumo: {', '.join(consumption_tags)}")
                
            # Añadir filtro de período
            if date_period and date_period != "custom":
                # Mostrar el nombre del período predefinido
                period_names = {
                    "last_month": "Último mes",
                    "last_3_months": "Últimos 3 meses",
                    "last_year": "Último año"
                }
                period_name = period_names.get(date_period, date_period)
                basic_filters.append(f"Período: {period_name}")
            elif start_date and end_date:
                basic_filters.append(f"Período: {start_date} a {end_date}")
            
            if basic_filters:
                return html.Div([
                    html.I(className="fas fa-filter me-2"),
                    f"Filtros aplicados: {', '.join(basic_filters)}"
                ], className="alert alert-primary")
            
            return ""
    
    # Callback para actualizar las métricas
    @app.callback(
        [Output("metrics-total-consumption", "children"),
         Output("metrics-total-consumption-unit", "children"),
         Output("metrics-daily-average", "children"),
         Output("metrics-daily-average-unit", "children"),
         Output("metrics-trend", "children"),
         Output("metrics-trend-period", "children"),
         Output("metrics-trend", "className")],
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_metrics(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date):
        if not json_data:
            return "N/A", "", "N/A", "", "N/A", "", "text-center text-muted"
        
        try:
            # Convertir los datos JSON a DataFrame
            df = pd.read_json(StringIO(json_data), orient='split')
            
            # Filtrar los datos según los criterios seleccionados
            filtered_df = filter_data(
                df, 
                client_id=client_id if client_id != "all" else None,
                project_id=project_id if project_id != "all" else None,
                asset_id=asset_id if asset_id != "all" else None,
                consumption_type=consumption_tags if consumption_tags else None,
                start_date=start_date,
                end_date=end_date
            )
            
            if filtered_df.empty:
                return "N/A", "", "N/A", "", "N/A", "", "text-center text-muted"
            
            # Calcular el consumo total
            total_consumption = filtered_df['value'].sum()
            
            # Determinar la unidad según el tipo de consumo
            unit = ""
            if consumption_tags:
                if "Agua" in consumption_tags:
                    unit = "m³"
                elif "Energía" in consumption_tags:
                    unit = "kWh"
                elif "Flujo" in consumption_tags:
                    unit = "personas"
            
            # Calcular el promedio diario
            days = (filtered_df['date'].max() - filtered_df['date'].min()).days
            days = max(1, days)  # Evitar división por cero
            daily_average = total_consumption / days
            
            # Calcular la tendencia
            # Dividir los datos en dos mitades y comparar
            if len(filtered_df) >= 2:
                mid_point = len(filtered_df) // 2
                first_half = filtered_df.iloc[:mid_point]['value'].mean()
                second_half = filtered_df.iloc[mid_point:]['value'].mean()
                
                if first_half > 0:  # Evitar división por cero
                    trend_percentage = ((second_half - first_half) / first_half) * 100
                    
                    if trend_percentage > 0:
                        trend_text = f"↑ {abs(trend_percentage):.1f}%"
                        trend_class = "text-center text-danger"  # Rojo para aumento (negativo en consumo)
                    elif trend_percentage < 0:
                        trend_text = f"↓ {abs(trend_percentage):.1f}%"
                        trend_class = "text-center text-success"  # Verde para disminución (positivo en consumo)
                    else:
                        trend_text = "→ 0%"
                        trend_class = "text-center text-muted"
                else:
                    trend_text = "N/A"
                    trend_class = "text-center text-muted"
            else:
                trend_text = "N/A"
                trend_class = "text-center text-muted"
            
            # Formatear los valores para mostrar
            total_formatted = f"{total_consumption:,.1f}"
            daily_formatted = f"{daily_average:,.1f}"
            
            return (
                total_formatted,
                unit,
                daily_formatted,
                unit + "/día" if unit else "",
                trend_text,
                "comparando primera y segunda mitad del período",
                trend_class
            )
        
        except Exception as e:
            print(f"Error al actualizar métricas: {str(e)}")
            return "Error", "", "Error", "", "Error", "", "text-center text-danger"
    
    # Callback para actualizar el gráfico de evolución temporal
    @app.callback(
        Output("metrics-time-series-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_time_series_chart(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date):
        if not json_data:
            # Crear un gráfico vacío con mensaje
            empty_df = pd.DataFrame()
            return create_time_series_chart(empty_df, title="Haga clic en 'Analizar Datos' para ver los resultados")
        
        try:
            # Convertir los datos JSON a DataFrame
            df = pd.read_json(StringIO(json_data), orient='split')
            
            # Filtrar los datos según los criterios seleccionados
            filtered_df = filter_data(
                df, 
                client_id=client_id if client_id != "all" else None,
                project_id=project_id if project_id != "all" else None,
                asset_id=asset_id if asset_id != "all" else None,
                consumption_type=consumption_tags if consumption_tags else None,
                start_date=start_date,
                end_date=end_date
            )
            
            # Determinar qué columna usar para colorear las líneas
            color_column = None
            if asset_id == "all" and consumption_tags:
                color_column = "consumption_type"
            elif asset_id == "all":
                color_column = "asset_id"
            elif consumption_tags:
                color_column = "consumption_type"
            
            # Crear el gráfico de evolución temporal
            title = "Evolución temporal del consumo"
            if project_id != "all":
                title += f" - Proyecto {project_id}"
            if asset_id != "all":
                title += f" - Asset {asset_id}"
            if consumption_tags:
                title += f" - {', '.join(consumption_tags)}"
            
            return create_time_series_chart(
                filtered_df, 
                color_column=color_column,
                title=title
            )
        
        except Exception as e:
            print(f"Error al actualizar gráfico de evolución temporal: {str(e)}")
            return {}
    
    # Callback para actualizar el gráfico de tipos de consumo
    @app.callback(
        Output("metrics-consumption-type-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_consumption_type_chart(json_data, client_id, project_id, asset_id, start_date, end_date):
        if not json_data:
            # Crear un gráfico vacío con mensaje
            empty_df = pd.DataFrame()
            return create_bar_chart(empty_df, "", title="Haga clic en 'Analizar Datos' para ver los resultados")
        
        try:
            # Convertir los datos JSON a DataFrame
            df = pd.read_json(StringIO(json_data), orient='split')
            
            # Filtrar los datos según los criterios seleccionados
            filtered_df = filter_data(
                df, 
                client_id=client_id if client_id != "all" else None,
                project_id=project_id if project_id != "all" else None,
                asset_id=asset_id if asset_id != "all" else None,
                start_date=start_date,
                end_date=end_date
            )
            
            # Crear el gráfico de comparativa por tipo de consumo
            title = "Comparativa por tipo de consumo"
            if project_id != "all":
                title += f" - Proyecto {project_id}"
            if asset_id != "all":
                title += f" - Asset {asset_id}"
            
            return create_consumption_comparison_chart(
                filtered_df,
                group_column="consumption_type",
                title=title
            )
        
        except Exception as e:
            print(f"Error al actualizar gráfico de comparativa por tipo de consumo: {str(e)}")
            return {}
    
    # Callback para actualizar el gráfico de distribución
    @app.callback(
        Output("metrics-distribution-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_distribution_chart(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date):
        if not json_data:
            # Crear un gráfico vacío con mensaje
            empty_df = pd.DataFrame()
            return create_consumption_distribution_chart(empty_df, group_column="consumption_type", title="Haga clic en 'Analizar Datos' para ver los resultados")
        
        try:
            # Convertir los datos JSON a DataFrame
            df = pd.read_json(StringIO(json_data), orient='split')
            
            # Filtrar los datos según los criterios seleccionados
            filtered_df = filter_data(
                df, 
                client_id=client_id if client_id != "all" else None,
                project_id=project_id if project_id != "all" else None,
                asset_id=asset_id if asset_id != "all" else None,
                consumption_type=consumption_tags if consumption_tags else None,
                start_date=start_date,
                end_date=end_date
            )
            
            # Determinar qué columna usar para la distribución
            group_column = "consumption_type"
            if consumption_tags:
                group_column = "consumption_type"
            if asset_id != "all" and consumption_tags:
                group_column = "asset_id"
            if asset_id != "all" and project_id == "all":
                group_column = "project_id"
            
            # Crear el gráfico de distribución
            title = "Distribución de consumo"
            if project_id != "all":
                title += f" - Proyecto {project_id}"
            if asset_id != "all":
                title += f" - Asset {asset_id}"
            if consumption_tags:
                title += f" - {', '.join(consumption_tags)}"
            
            return create_consumption_distribution_chart(
                filtered_df,
                group_column=group_column,
                title=title
            )
        
        except Exception as e:
            print(f"Error al actualizar gráfico de distribución: {str(e)}")
            return {}
    
    # Callback para actualizar el gráfico de tendencia
    @app.callback(
        Output("metrics-trend-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date"),
         Input("metrics-time-period", "value")]
    )
    def update_trend_chart(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date, time_period):
        if not json_data:
            # Crear un gráfico vacío con mensaje
            empty_df = pd.DataFrame()
            return create_consumption_trend_chart(empty_df, title="Haga clic en 'Analizar Datos' para ver los resultados")
        
        try:
            # Convertir los datos JSON a DataFrame
            df = pd.read_json(StringIO(json_data), orient='split')
            
            # Filtrar los datos según los criterios seleccionados
            filtered_df = filter_data(
                df, 
                client_id=client_id if client_id != "all" else None,
                project_id=project_id if project_id != "all" else None,
                asset_id=asset_id if asset_id != "all" else None,
                consumption_type=consumption_tags if consumption_tags else None,
                start_date=start_date,
                end_date=end_date
            )
            
            # Determinar qué columna usar para agrupar
            group_column = None
            if asset_id == "all" and consumption_tags:
                group_column = "consumption_type"
            elif asset_id == "all":
                group_column = "asset_id"
            elif consumption_tags:
                group_column = "consumption_type"
            
            # Crear el gráfico de tendencias
            title = "Tendencias de consumo"
            if project_id != "all":
                title += f" - Proyecto {project_id}"
            if asset_id != "all":
                title += f" - Asset {asset_id}"
            if consumption_tags:
                title += f" - {', '.join(consumption_tags)}"
            
            return create_consumption_trend_chart(
                filtered_df,
                time_period=time_period,
                group_column=group_column,
                title=title
            )
        
        except Exception as e:
            print(f"Error al actualizar gráfico de tendencias: {str(e)}")
            return {}
    
    # Callback para actualizar el gráfico de comparativa entre assets
    @app.callback(
        Output("metrics-assets-comparison-chart", "figure"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_assets_comparison_chart(json_data, client_id, project_id, consumption_tags, start_date, end_date):
        if not json_data:
            # Crear un gráfico vacío con mensaje
            empty_df = pd.DataFrame()
            return create_bar_chart(empty_df, "", title="Haga clic en 'Analizar Datos' para ver los resultados")
        
        try:
            # Convertir los datos JSON a DataFrame
            df = pd.read_json(StringIO(json_data), orient='split')
            
            # Filtrar los datos según los criterios seleccionados
            filtered_df = filter_data(
                df, 
                client_id=client_id if client_id != "all" else None,
                project_id=project_id if project_id != "all" else None,
                consumption_tags=consumption_tags if consumption_tags else None,
                start_date=start_date,
                end_date=end_date
            )
            
            # Crear el gráfico de comparativa entre assets
            title = "Comparativa entre assets"
            if project_id != "all":
                title += f" - Proyecto {project_id}"
            if consumption_tags:
                title += f" - {', '.join(consumption_tags)}"
            
            return create_consumption_comparison_chart(
                filtered_df,
                group_column="asset_id",
                title=title
            )
        
        except Exception as e:
            print(f"Error al actualizar gráfico de comparativa entre assets: {str(e)}")
            return {}
    
    # Callback para mostrar la tabla de lecturas mensuales por asset
    @app.callback(
        Output("metrics-monthly-readings-table", "children"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_monthly_readings_table(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date):
        if not json_data:
            return html.Div("No hay datos disponibles. Seleccione un cliente, proyecto y tipo de consumo, y haga clic en 'Visualizar Consumos'.")
        
        try:
            # Importar json al principio de la función
            import json
            
            # Convertir los datos JSON a DataFrame
            try:
                # Intentar el formato estándar primero
                df = pd.read_json(StringIO(json_data), orient='split')
            except Exception as e:
                # Si falla, intentar con el formato alternativo
                try:
                    data_dict = json.loads(json_data)
                    df = pd.DataFrame(data_dict['data'], columns=data_dict['columns'])
                except Exception as e2:
                    debug_log(f"[ERROR] Error al convertir JSON a DataFrame: {str(e)} / {str(e2)}")
                    return html.Div(f"Error al procesar los datos: {str(e2)}", className="alert alert-danger")
            
            # Asegurarse de que la fecha esté en formato datetime
            if 'date' not in df.columns:
                debug_log("[ERROR] La columna 'date' no está presente en el DataFrame")
                return html.Div("Error: Los datos no contienen la columna 'date'.", className="alert alert-danger")
            
            df['date'] = pd.to_datetime(df['date'])
            
            # Aplicar filtros adicionales si es necesario
            filtered_df = df.copy()
            
            if asset_id and asset_id != "all":
                filtered_df = filtered_df[filtered_df['asset_id'] == asset_id]
            
            if start_date:
                filtered_df = filtered_df[filtered_df['date'] >= pd.to_datetime(start_date)]
            
            if end_date:
                filtered_df = filtered_df[filtered_df['date'] <= pd.to_datetime(end_date)]
            
            # Agregar los datos por mes y asset
            try:
                monthly_data = aggregate_data_by_month_and_asset(filtered_df)
            except Exception as e:
                debug_log(f"[ERROR] Error al agregar datos por mes y asset: {str(e)}")
                return html.Div(f"Error al agregar datos: {str(e)}", className="alert alert-danger")
            
            if monthly_data.empty:
                return html.Div("No hay datos disponibles para los filtros seleccionados.")
            
            # Verificar que las columnas necesarias estén presentes
            required_columns = ['asset_id', 'year_month', 'consumption_type', 'consumption', 'date']
            missing_columns = [col for col in required_columns if col not in monthly_data.columns]
            if missing_columns:
                debug_log(f"[ERROR] Faltan columnas en el DataFrame: {missing_columns}")
                return html.Div(f"Error: Faltan columnas en los datos: {', '.join(missing_columns)}", className="alert alert-danger")
            
            # Seleccionar las columnas relevantes para la tabla
            table_data = monthly_data[required_columns].copy()
            
            # Formatear la fecha para mostrarla de forma más legible
            table_data['date'] = table_data['date'].dt.strftime('%Y-%m-%d')
            
            # Añadir una columna para el botón de regenerar
            table_data['regenerate'] = 'Regenerar'
            
            # Añadir un identificador único a cada fila
            table_data['row_id'] = table_data.apply(
                lambda row: f"{row['asset_id']}_{row['consumption_type']}_{row['year_month']}", 
                axis=1
            )
            
            # Renombrar las columnas para la tabla
            table_data = table_data.rename(columns={
                'asset_id': 'Asset ID',
                'year_month': 'Mes',
                'consumption_type': 'Tipo de Consumo',
                'consumption': 'Consumo',
                'date': 'Fecha de Lectura',
                'regenerate': 'Acción',
                'row_id': 'row_id'
            })
            
            # Crear la tabla
            table = dash_table.DataTable(
                id='table-monthly-readings',
                columns=[
                    {"name": col, "id": col} for col in table_data.columns if col not in ['Acción', 'row_id']
                ] + [
                    {"name": "Acción", "id": "Acción", "presentation": "markdown"}
                ],
                data=[
                    {
                        **row,
                        'Acción': f"[Regenerar](regenerate_{row['Asset ID']}_{row['Tipo de Consumo']}_{row['Mes']})" if row['Consumo'] == 'Error' else 
                                f"[Ver detalles](details_{row['Asset ID']}_{row['Tipo de Consumo']}_{row['Mes']}) | [Actualizar](update_{row['Asset ID']}_{row['Tipo de Consumo']}_{row['Mes']})"
                    } 
                    for i, row in enumerate(table_data.to_dict('records'))
                ],
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                    'cursor': 'pointer'  # Indicar que las celdas son clickeables
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    },
                    {
                        'if': {'filter_query': '{Consumo} = "Error"'},
                        'backgroundColor': '#ffcccc',  # Fondo rojo claro para errores
                        'color': '#990000'  # Texto rojo oscuro
                    },
                    {
                        'if': {'column_id': 'Acción'},
                        'textAlign': 'center',
                        'width': '120px'
                    },
                    {
                        'if': {'column_id': 'Acción', 'filter_query': '{Consumo} = "Error"'},
                        'cursor': 'pointer',
                        'textDecoration': 'none'
                    }
                ],
                page_size=15,
                sort_action='native',
                filter_action='native',
                export_format='csv',
                # Habilitar la selección de celdas
                cell_selectable=True,
                selected_cells=[],
                # Guardar los datos originales para acceder a ellos cuando se haga clic
                derived_virtual_data=table_data.to_dict('records'),
                # Añadir tooltip para indicar que se puede hacer clic
                tooltip_data=[
                    {
                        column: {'value': 'Haz clic para ver detalles' if column != 'Acción' else 
                                ('Haz clic en un icono: 👁️ Ver detalles | 🔄 Actualizar lecturas' if row['Consumo'] != 'Error' else 
                                 '🔄 Regenerar lectura con error'), 
                                'type': 'text'}
                        for column in table_data.columns
                    }
                    for row in table_data.to_dict('records')
                ],
                tooltip_duration=None
            )
            
            # Crear un componente para almacenar los datos originales
            data_store = dcc.Store(
                id='store-monthly-readings-data',
                data=json.dumps({
                    'data': table_data.to_dict('records'),
                    'original_df': json_data
                })
            )
            
            return html.Div([
                html.H4("Lecturas Mensuales por Asset"),
                html.Button("Export", id="export-monthly-readings-btn", className="btn btn-primary mb-3"),
                data_store,
                table,
                # Añadir un modal para mostrar los detalles
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle("Detalles de Consumo"), close_button=True),
                        dbc.ModalBody(id="consumption-detail-modal-body"),
                        dbc.ModalFooter(
                            dbc.Button("Cerrar", id="close-consumption-detail-modal", className="ms-auto")
                        ),
                    ],
                    id="consumption-detail-modal",
                    size="lg",
                    is_open=False,
                ),
                # Añadir un modal para actualizar lecturas de un asset específico
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle("Actualizar Lecturas de Asset"), close_button=True),
                        dbc.ModalBody(id="update-asset-readings-modal-body"),
                        dbc.ModalFooter([
                            dbc.Button("Cancelar", id="close-update-asset-readings-modal", className="me-2"),
                            dbc.Button("Confirmar", id="confirm-update-asset-readings", color="primary")
                        ]),
                    ],
                    id="update-asset-readings-modal",
                    size="md",
                    is_open=False,
                ),
                # Store para datos de actualización de asset
                dcc.Store(id="update-asset-readings-data"),
                # Añadir un modal para confirmar la regeneración de lecturas
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle("Regenerar Lecturas"), close_button=True),
                        dbc.ModalBody(id="regenerate-readings-modal-body"),
                        dbc.ModalFooter([
                            dbc.Button("Cancelar", id="cancel-regenerate-readings", className="me-2"),
                            dbc.Button("Confirmar", id="confirm-regenerate-readings", color="primary")
                        ]),
                    ],
                    id="regenerate-readings-modal",
                    size="md",
                    is_open=False,
                ),
                # Store para datos de regeneración
                dcc.Store(id="regenerate-readings-data"),
            ])
        
        except Exception as e:
            import traceback
            error_msg = f"Error al actualizar tabla de lecturas mensuales: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div(error_msg, className="alert alert-danger")
    
    # Callback para actualizar las tablas de lecturas mensuales por tipo de consumo
    @app.callback(
        Output("metrics-monthly-readings-by-consumption-type", "children"),
        [Input("metrics-data-store", "data"),
         Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-asset-filter", "value"),
         Input("metrics-consumption-tags-filter", "value"),
         Input("metrics-date-range", "start_date"),
         Input("metrics-date-range", "end_date")]
    )
    def update_monthly_readings_by_consumption_type(json_data, client_id, project_id, asset_id, consumption_tags, start_date, end_date):
        if not json_data or not consumption_tags:
            return html.Div("Seleccione al menos un tipo de consumo para visualizar las lecturas mensuales.")
        
        try:
            # Importar json al principio de la función
            import json
            
            debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - Iniciando actualización de tablas")
            
            # Convertir los datos JSON a DataFrame
            try:
                df = pd.read_json(StringIO(json_data), orient='split')
                debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - DataFrame cargado con formato 'split'")
            except Exception as e:
                debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - Error al cargar DataFrame con formato 'split': {str(e)}")
                # Intentar un formato alternativo si el anterior falla
                df = pd.DataFrame(json.loads(json_data))
                debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - DataFrame cargado con formato alternativo")
            
            debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - DataFrame shape: {df.shape}")
            debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - Columnas: {df.columns.tolist()}")
            
            # Asegurar que la columna 'date' es de tipo datetime
            if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
                df['date'] = pd.to_datetime(df['date'])
            
            # Filtrar por asset si es necesario
            if asset_id and asset_id != "all":
                df = df[df['asset_id'] == asset_id]
                debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - Filtrado por asset_id: {asset_id}, filas restantes: {len(df)}")
            
            # Filtrar por rango de fechas
            if start_date and end_date:
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)
                df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - Filtrado por fechas: {start_date} a {end_date}, filas restantes: {len(df)}")
            
            # Si no hay datos después de filtrar, mostrar un mensaje
            if df.empty:
                debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - No hay datos después de filtrar")
                return html.Div("No hay datos disponibles para los filtros seleccionados.", className="alert alert-warning")
            
            # Verificar si hay datos de consumo
            if 'consumption' not in df.columns:
                debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - No hay columna 'consumption' en el DataFrame")
                # Intentar encontrar una columna que pueda contener los valores de consumo
                numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
                debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - Columnas numéricas disponibles: {numeric_columns}")
                
                if numeric_columns:
                    # Usar la primera columna numérica como consumo
                    df['consumption'] = df[numeric_columns[0]]
                    debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - Usando columna {numeric_columns[0]} como consumo")
                else:
                    debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - No hay columnas numéricas disponibles")
                    return html.Div("No se encontraron datos de consumo en los datos cargados.", className="alert alert-warning")
            
            # Generar las tablas por tipo de consumo
            tables_by_consumption_type = generate_monthly_readings_by_consumption_type(df, consumption_tags, start_date, end_date)
            
            # Si no hay tablas, mostrar un mensaje
            if not tables_by_consumption_type:
                debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - No se generaron tablas")
                return html.Div("No se encontraron lecturas para los tipos de consumo seleccionados.", className="alert alert-warning")
            
            debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - Se generaron {len(tables_by_consumption_type)} tablas")
            
            # Crear un componente para cada tabla
            tables_components = []
            
            for consumption_type, table_df in tables_by_consumption_type.items():
                debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - Procesando tabla para {consumption_type}")
                
                # Crear una copia del DataFrame para no modificar el original
                display_df = table_df.copy()
                
                # Mostrar información sobre los valores en el DataFrame
                for col in display_df.columns:
                    if col != 'Asset':
                        non_null_values = display_df[col].dropna()
                        debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - Columna {col}, valores no nulos: {len(non_null_values)}, ejemplo: {non_null_values.iloc[0] if len(non_null_values) > 0 else 'N/A'}")
                
                # Formatear los valores numéricos
                for col in display_df.columns:
                    if col != 'Asset':
                        # Convertir la columna a tipo string para evitar problemas de tipo de datos
                        display_df[col] = display_df[col].apply(
                            lambda x: f"{float(x):.2f}" if pd.notnull(x) and (isinstance(x, (int, float)) or str(x).replace('.', '', 1).isdigit()) else "-"
                        )
                
                # Crear la tabla
                table = dash_table.DataTable(
                    id=f'table-{consumption_type.replace(" ", "-").lower()}',
                    columns=[{"name": col, "id": col} for col in display_df.columns],
                    data=display_df.to_dict('records'),
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'center',
                        'padding': '10px',
                        'minWidth': '100px',
                        'cursor': 'pointer'  # Cambiar el cursor a pointer para indicar que es clickeable
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold',
                        'textAlign': 'center'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    # Habilitar la selección de celdas
                    cell_selectable=True,
                    # Permitir solo una celda seleccionada a la vez
                    selected_cells=[],
                    # Añadir un ID de datos personalizado para cada celda
                    derived_virtual_data=display_df.to_dict('records'),
                    # Añadir un tooltip para indicar que se puede hacer clic
                    tooltip_data=[
                        {
                            column: {'value': 'Haga clic para ver detalles', 'type': 'text'}
                            for column in display_df.columns if column != 'Asset'
                        }
                        for _ in range(len(display_df))
                    ],
                    tooltip_duration=None
                )
                
                # Crear un componente para esta tabla
                table_component = html.Div([
                    html.H5(f"Lecturas de {consumption_type}", className="mt-4 mb-3"),
                    table,
                    # Añadir un store para guardar los datos originales de esta tabla
                    dcc.Store(
                        id=f'store-data-{consumption_type.replace(" ", "-").lower()}',
                        data={
                            'consumption_type': consumption_type,
                            'original_data': df[df['tag'] == consumption_type].to_json(date_format='iso', orient='split')
                        }
                    )
                ], className="mb-4")
                
                tables_components.append(table_component)
            
            return html.Div(tables_components)
            
        except Exception as e:
            import traceback
            error_msg = f"Error al actualizar las tablas de lecturas mensuales por tipo de consumo: {str(e)}"
            debug_log(f"[DEBUG] update_monthly_readings_by_consumption_type - {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div(error_msg)
    
    # Función para generar un gráfico de consumo diario para un asset y mes específico
    def generate_daily_consumption_chart(df, asset_id, month, year, consumption_type):
        """
        Genera un gráfico de consumo diario para un asset y mes específico.
        
        Args:
            df: DataFrame con los datos
            asset_id: ID del asset
            month: Mes (formato: MM)
            year: Año (formato: YYYY)
            consumption_type: Tipo de consumo
            
        Returns:
            Componente de gráfico o mensaje de advertencia
        """
        try:
            # Filtrar por asset_id y consumption_type
            filtered_df = df[
                (df['asset_id'] == asset_id) & 
                (df['consumption_type'] == consumption_type)
            ].copy()
            
            # Asegurarse de que la fecha esté en formato datetime
            filtered_df['date'] = pd.to_datetime(filtered_df['date'])
            
            # Filtrar por mes y año
            filtered_df = filtered_df[
                (filtered_df['date'].dt.month == int(month)) & 
                (filtered_df['date'].dt.year == int(year))
            ]
            
            if filtered_df.empty:
                return html.Div("No hay datos disponibles para generar el gráfico.", className="alert alert-warning")
            
            # Ordenar por fecha
            filtered_df = filtered_df.sort_values('date')
            
            # Crear el gráfico
            fig = px.line(
                filtered_df, 
                x='date', 
                y='consumption',
                title=f"Consumo diario - {asset_id} - {month}/{year} - {consumption_type}",
                labels={'date': 'Fecha', 'consumption': 'Consumo'},
                markers=True
            )
            
            # Personalizar el diseño
            fig.update_layout(
                xaxis_title="Fecha",
                yaxis_title="Consumo",
                plot_bgcolor='white',
                hovermode='closest',
                height=400
            )
            
            return dcc.Graph(figure=fig)
        
        except Exception as e:
            debug_log(f"[ERROR] Error al generar gráfico de consumo diario: {str(e)}")
            return html.Div(f"Error al generar el gráfico: {str(e)}", className="alert alert-danger")

    # Función para generar estadísticas de consumo para un asset y mes específico
    def generate_consumption_stats(df, asset_id, month, year, consumption_type):
        """
        Genera estadísticas de consumo para un asset y mes específico.
        
        Args:
            df: DataFrame con los datos
            asset_id: ID del asset
            month: Mes (formato: MM)
            year: Año (formato: YYYY)
            consumption_type: Tipo de consumo
            
        Returns:
            Componente HTML con estadísticas
        """
        try:
            # Filtrar por asset_id y consumption_type
            filtered_df = df[
                (df['asset_id'] == asset_id) & 
                (df['consumption_type'] == consumption_type)
            ].copy()
            
            # Asegurarse de que la fecha esté en formato datetime
            filtered_df['date'] = pd.to_datetime(filtered_df['date'])
            
            # Filtrar por mes y año
            filtered_df = filtered_df[
                (filtered_df['date'].dt.month == int(month)) & 
                (filtered_df['date'].dt.year == int(year))
            ]
            
            if filtered_df.empty:
                return html.Div("No hay datos disponibles para calcular estadísticas.", className="alert alert-warning")
            
            # Calcular estadísticas
            stats = {
                "Mínimo": filtered_df['consumption'].min(),
                "Máximo": filtered_df['consumption'].max(),
                "Promedio": filtered_df['consumption'].mean(),
                "Mediana": filtered_df['consumption'].median(),
                "Desviación estándar": filtered_df['consumption'].std(),
                "Consumo total": filtered_df['consumption'].sum(),
                "Días con datos": len(filtered_df)
            }
            
            # Crear tabla de estadísticas
            stats_table = html.Table(
                # Encabezado
                [html.Tr([html.Th("Estadística"), html.Th("Valor")])] +
                # Filas
                [html.Tr([html.Td(k), html.Td(f"{v:.2f}" if isinstance(v, (int, float)) else v)]) for k, v in stats.items()],
                className="table table-striped table-bordered"
            )
            
            return html.Div([
                html.H5("Estadísticas de consumo"),
                stats_table
            ])
        
        except Exception as e:
            debug_log(f"[ERROR] Error al generar estadísticas de consumo: {str(e)}")
            return html.Div(f"Error al calcular estadísticas: {str(e)}", className="alert alert-danger")

    # Función para generar una tabla de lecturas diarias para un asset y mes específico
    def generate_daily_readings_table(df, asset_id, month, year, consumption_type):
        """
        Genera una tabla de lecturas diarias para un asset y mes específico.
        
        Args:
            df: DataFrame con los datos
            asset_id: ID del asset
            month: Mes (formato: MM)
            year: Año (formato: YYYY)
            consumption_type: Tipo de consumo
            
        Returns:
            Componente de tabla o mensaje de advertencia
        """
        try:
            # Filtrar por asset_id y consumption_type
            filtered_df = df[
                (df['asset_id'] == asset_id) & 
                (df['consumption_type'] == consumption_type)
            ].copy()
            
            # Asegurarse de que la fecha esté en formato datetime
            filtered_df['date'] = pd.to_datetime(filtered_df['date'])
            
            # Filtrar por mes y año
            filtered_df = filtered_df[
                (filtered_df['date'].dt.month == int(month)) & 
                (filtered_df['date'].dt.year == int(year))
            ]
            
            if filtered_df.empty:
                return html.Div("No hay lecturas disponibles para este período.", className="alert alert-warning")
            
            # Ordenar por fecha
            filtered_df = filtered_df.sort_values('date')
            
            # Formatear la fecha para mostrarla de forma más legible
            filtered_df['date'] = filtered_df['date'].dt.strftime('%Y-%m-%d')
            
            # Crear un DataFrame para la tabla
            table_df = filtered_df[['date', 'consumption']].copy()
            
            # Renombrar las columnas
            table_df = table_df.rename(columns={
                'date': 'Fecha',
                'consumption': 'Consumo'
            })
            
            # Formatear valores numéricos
            table_df['Consumo'] = table_df['Consumo'].apply(
                lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x
            )
            
            # Crear la tabla
            table = dash_table.DataTable(
                columns=[{"name": col, "id": col} for col in table_df.columns],
                data=table_df.to_dict('records'),
                style_table={'overflowY': 'auto', 'maxHeight': '300px'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                page_size=10,
                sort_action='native'
            )
            
            return html.Div([
                html.H5("Lecturas diarias"),
                table
            ])
        
        except Exception as e:
            debug_log(f"[ERROR] Error al generar tabla de lecturas diarias: {str(e)}")
            return html.Div(f"Error al generar la tabla: {str(e)}", className="alert alert-danger")
    
    # Callback para detectar clics en las celdas de la tabla y mostrar el modal
    @app.callback(
        [Output("consumption-detail-modal", "is_open"),
         Output("consumption-detail-modal-body", "children"),
         Output("consumption-detail-modal", "title"),
         Output("update-asset-readings-modal", "is_open"),
         Output("update-asset-readings-modal-body", "children"),
         Output("update-asset-readings-data", "data"),
         Output("regenerate-readings-modal", "is_open"),
         Output("regenerate-readings-modal-body", "children"),
         Output("regenerate-readings-data", "data")],
        [Input("table-monthly-readings", "active_cell"),
         Input("close-consumption-detail-modal", "n_clicks"),
         Input("close-update-asset-readings-modal", "n_clicks"),
         Input("cancel-regenerate-readings", "n_clicks"),
         Input("confirm-regenerate-readings", "n_clicks")],
        [State("table-monthly-readings", "derived_virtual_data"),
         State("table-monthly-readings", "derived_virtual_indices"),
         State("table-monthly-readings", "page_current"),
         State("table-monthly-readings", "page_size"),
         State("table-monthly-readings", "data"),
         State("store-monthly-readings-data", "data"),
         State("consumption-detail-modal", "is_open"),
         State("update-asset-readings-modal", "is_open"),
         State("metrics-project-filter", "value"),
         State("metrics-consumption-tags-filter", "value"),
         State("jwt-token-store", "data")]
    )
    def show_consumption_detail_modal(active_cell, close_detail_clicks, close_update_clicks, cancel_clicks, confirm_clicks, 
                                     derived_virtual_data, derived_virtual_indices, page_current, page_size, full_table_data, stored_data, 
                                     detail_is_open, update_is_open, project_id, consumption_tags, token_data):
        debug_log("=== INICIO DEL CALLBACK show_consumption_detail_modal ===")
        debug_log(f"active_cell: {active_cell}")
        debug_log(f"page_current: {page_current}")
        debug_log(f"page_size: {page_size}")
        debug_log(f"derived_virtual_data length: {len(derived_virtual_data) if derived_virtual_data else 0}")
        debug_log(f"derived_virtual_indices length: {len(derived_virtual_indices) if derived_virtual_indices else 0}")
        debug_log(f"full_table_data length: {len(full_table_data) if full_table_data else 0}")
        
        ctx = dash.callback_context
        
        if not ctx.triggered:
            debug_log("No hay trigger, retornando valores por defecto")
            return False, None, "", False, None, None, False, None, None
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Log para depuración
        debug_log(f"[DEBUG] Trigger: {trigger_id}")
        debug_log(f"[DEBUG] Página actual: {page_current}, Tamaño de página: {page_size}")
        
        # Si se hizo clic en el botón de cerrar detalles
        if trigger_id == "close-consumption-detail-modal":
            debug_log("Cerrando modal de detalles")
            return False, None, "", update_is_open, None, None, False, None, None
            
        # Si se hizo clic en el botón de cerrar actualización
        if trigger_id == "close-update-asset-readings-modal":
            debug_log("Cerrando modal de actualización")
            return detail_is_open, dash.no_update, dash.no_update, False, None, None, False, None, None
        
        # Si no hay celda activa o no hay datos, no hacer nada
        if not active_cell or not derived_virtual_data:
            debug_log(f"[DEBUG] No hay celda activa o datos: active_cell={active_cell}, derived_virtual_data_length={len(derived_virtual_data) if derived_virtual_data else 0}")
            return detail_is_open, None, "", update_is_open, None, None, False, None, None
        
        try:
            # Importar json al principio de la función
            import json
            
            # Obtener los datos de la celda seleccionada
            row = active_cell["row"]
            col = active_cell["column"]
            col_id = active_cell["column_id"]
            
            # Log para depuración
            debug_log(f"[DEBUG] Celda seleccionada: row={row}, col={col}, col_id={col_id}")
            
            # Calcular el índice real basado en la página actual y el tamaño de página
            # Si page_current es None, asumimos que estamos en la primera página (0)
            current_page = 0 if page_current is None else page_current
            # Si page_size es None, usamos un valor predeterminado (15 es el valor que se usa en la tabla)
            items_per_page = 15 if page_size is None else page_size
            
            # Calcular el índice absoluto (considerando todas las páginas)
            absolute_row_index = (current_page * items_per_page) + row
            
            debug_log(f"[DEBUG] Índice de fila calculado: página {current_page} * {items_per_page} + {row} = {absolute_row_index}")
            
            # Verificar si tenemos índices virtuales disponibles
            if derived_virtual_indices and len(derived_virtual_indices) > row:
                # Si tenemos índices virtuales, los usamos para obtener el índice real
                virtual_index = derived_virtual_indices[row]
                debug_log(f"[DEBUG] Índice virtual para la fila {row}: {virtual_index}")
            
            # Si se hizo clic en la columna Asset ID, no mostrar detalles
            if col_id == "Asset ID":
                debug_log("Se hizo clic en la columna Asset ID, no mostrando detalles")
                return detail_is_open, None, "", update_is_open, None, None, False, None, None
            
            # Obtener los datos de la fila seleccionada
            # Usamos derived_virtual_data que contiene los datos de la página actual
            if row >= len(derived_virtual_data):
                debug_log(f"[ERROR] Índice de fila {row} fuera de rango para derived_virtual_data con longitud {len(derived_virtual_data)}")
                return detail_is_open, None, "", update_is_open, None, None, False, None, None
            
            # Obtener datos de la fila usando el índice absoluto calculado
            if full_table_data and len(full_table_data) > absolute_row_index:
                row_data = full_table_data[absolute_row_index]
                debug_log(f"[DEBUG] Usando datos de la fila con índice absoluto {absolute_row_index}")
            else:
                row_data = derived_virtual_data[row]
                debug_log(f"[DEBUG] Usando datos de la fila con índice relativo {row}")
            
            # Log para depuración
            debug_log(f"[DEBUG] Datos de la fila seleccionada: {row_data}")
            debug_log(f"[DEBUG] Row ID: {row_data.get('row_id', 'No disponible')}")
            
            # IMPORTANTE: Siempre usar los datos del enlace en lugar de confiar en los datos de la fila
            # Esto es necesario porque los índices virtuales no funcionan correctamente con la paginación
            if col_id == "Acción":
                cell_value = row_data["Acción"]
                debug_log(f"[DEBUG] Valor de la celda Acción: {cell_value}")
                
                # Extraer el tipo de acción y los parámetros del enlace
                if "regenerate_" in cell_value:
                    # Formato: [Regenerar](regenerate_asset_id_consumption_type_month_year)
                    debug_log(f"[DEBUG] Acción Regenerar detectada")
                    
                    # Extraer los parámetros del enlace
                    link_parts = cell_value.split("regenerate_")[1].split(")")[0].split("_")
                    if len(link_parts) >= 3:
                        # Reconstruir asset_id, consumption_type y month_year
                        asset_id = link_parts[0]
                        consumption_type = link_parts[1]
                        month_year = "_".join(link_parts[2:])
                        
                        debug_log(f"[DEBUG] Parámetros extraídos del enlace: asset_id={asset_id}, consumption_type={consumption_type}, month_year={month_year}")
                        
                        # Preparar datos para regenerar lecturas del asset específico
                        # Extraer el tag correspondiente al tipo de consumo
                        tag = None
                        for tag_value, consumption_name in TAGS_TO_CONSUMPTION_TYPE.items():
                            if consumption_name == consumption_type:
                                tag = tag_value
                                break
                        
                        if not tag and consumption_tags:
                            # Si no se encontró el tag, usar el primero de los seleccionados
                            tag = consumption_tags[0]
                        
                        # Crear contenido del modal de regeneración
                        regenerate_content = html.Div([
                            html.P([
                                "¿Desea regenerar las lecturas para el asset ",
                                html.Strong(asset_id),
                                " con tipo de consumo ",
                                html.Strong(consumption_type),
                                "?"
                            ]),
                            html.P("Esta acción consultará la API para obtener nuevos datos y reemplazará el archivo de lecturas existente."),
                            html.Div(id="regenerate-readings-status", className="mt-3")
                        ])
                        
                        # Guardar datos necesarios para la regeneración
                        regenerate_data = {
                            "asset_id": asset_id,
                            "consumption_type": consumption_type,
                            "tag": tag,
                            "project_id": project_id,
                            "token": token_data,
                            "month_year": month_year
                        }
                        
                        # Log para depuración
                        debug_log(f"[DEBUG] Datos para regeneración: {regenerate_data}")
                        debug_log("=== FIN DEL CALLBACK show_consumption_detail_modal (Regenerar) ===")
                        
                        # Mostrar el modal de regeneración
                        return False, None, "", False, None, None, True, regenerate_content, json.dumps(regenerate_data)
                
                elif "update_" in cell_value:
                    # Formato: [Actualizar](update_asset_id_consumption_type_month_year)
                    debug_log(f"[DEBUG] Acción Actualizar detectada")
                    
                    # Extraer los parámetros del enlace
                    link_parts = cell_value.split("update_")[1].split(")")[0].split("_")
                    if len(link_parts) >= 3:
                        # Reconstruir asset_id, consumption_type y month_year
                        asset_id = link_parts[0]
                        consumption_type = link_parts[1]
                        month_year = "_".join(link_parts[2:])
                        
                        debug_log(f"[DEBUG] Parámetros extraídos del enlace: asset_id={asset_id}, consumption_type={consumption_type}, month_year={month_year}")
                        
                        # Preparar datos para actualizar lecturas del asset específico
                        # Extraer el tag correspondiente al tipo de consumo
                        tag = None
                        for tag_value, consumption_name in TAGS_TO_CONSUMPTION_TYPE.items():
                            if consumption_name == consumption_type:
                                tag = tag_value
                                break
                        
                        if not tag and consumption_tags:
                            # Si no se encontró el tag, usar el primero de los seleccionados
                            tag = consumption_tags[0]
                        
                        # Crear contenido del modal de actualización
                        update_content = html.Div([
                            html.P([
                                "¿Desea actualizar las lecturas para el asset ",
                                html.Strong(asset_id),
                                " con tipo de consumo ",
                                html.Strong(consumption_type),
                                "?"
                            ]),
                            html.P("Esta acción consultará la API para obtener nuevos datos y actualizará el archivo de lecturas."),
                            html.Div(id="update-asset-readings-status", className="mt-3")
                        ])
                        
                        # Guardar datos necesarios para la actualización
                        update_data = {
                            "asset_id": asset_id,
                            "consumption_type": consumption_type,
                            "tag": tag,
                            "project_id": project_id,
                            "token": token_data
                        }
                        
                        debug_log("=== FIN DEL CALLBACK show_consumption_detail_modal (Actualizar) ===")
                        return False, None, "", True, update_content, json.dumps(update_data), False, None, None
                
                elif "details_" in cell_value:
                    # Formato: [Ver detalles](details_asset_id_consumption_type_month_year)
                    debug_log(f"[DEBUG] Acción Ver detalles detectada")
                    
                    # Extraer los parámetros del enlace
                    link_parts = cell_value.split("details_")[1].split(")")[0].split("_")
                    if len(link_parts) >= 3:
                        # Reconstruir asset_id, consumption_type y month_year
                        asset_id = link_parts[0]
                        consumption_type = link_parts[1]
                        month_year = "_".join(link_parts[2:])
                        
                        debug_log(f"[DEBUG] Parámetros extraídos del enlace: asset_id={asset_id}, consumption_type={consumption_type}, month_year={month_year}")
                else:
                    # Si no se reconoce la acción, no hacer nada
                    debug_log(f"[DEBUG] Acción no reconocida: {cell_value}")
                    debug_log("=== FIN DEL CALLBACK show_consumption_detail_modal (Acción no reconocida) ===")
                    return detail_is_open, None, "", update_is_open, None, None, False, None, None
            
# Obtener datos básicos de la fila si no se han obtenido de los enlaces
            if "asset_id" not in locals() or "consumption_type" not in locals() or "month_year" not in locals():
                asset_id = row_data["Asset ID"]
                consumption_type = row_data["Tipo de Consumo"]
                month_year = row_data["Mes"]
                debug_log(f"[DEBUG] Datos básicos obtenidos de la fila: asset_id={asset_id}, consumption_type={consumption_type}, month_year={month_year}")
            else:
                debug_log(f"[DEBUG] Usando datos básicos obtenidos de los enlaces: asset_id={asset_id}, consumption_type={consumption_type}, month_year={month_year}")

            # Extraer el mes y el año
            year, month = month_year.split("-")
            
            # Cargar los datos originales
            try:
                original_data = json.loads(stored_data)
                original_df_json = original_data["original_df"]
                
                # Convertir los datos JSON a DataFrame
                try:
                    # Intentar el formato estándar primero
                    df = pd.read_json(StringIO(original_df_json), orient='split')
                except Exception as e:
                    # Si falla, intentar con el formato alternativo
                    try:
                        data_dict = json.loads(original_df_json)
                        df = pd.DataFrame(data_dict['data'], columns=data_dict['columns'])
                    except Exception as e2:
                        debug_log(f"[ERROR] Error al convertir JSON a DataFrame en modal: {str(e)} / {str(e2)}")
                        debug_log("=== FIN DEL CALLBACK show_consumption_detail_modal (Error JSON) ===")
                        return True, html.Div(f"Error al procesar los datos: {str(e2)}", className="alert alert-danger"), "Error", False, None, None, False, None, None
                
                # Asegurarse de que la fecha esté en formato datetime
                df['date'] = pd.to_datetime(df['date'])
            except Exception as e:
                debug_log(f"[ERROR] Error al cargar datos originales en modal: {str(e)}")
                debug_log("=== FIN DEL CALLBACK show_consumption_detail_modal (Error datos) ===")
                return True, html.Div(f"Error al cargar datos: {str(e)}", className="alert alert-danger"), "Error", False, None, None, False, None, None
            
            # Crear el título del modal
            modal_title = f"Detalles de consumo - {asset_id} - {month}/{year} - {consumption_type}"
            
            # Generar el contenido del modal
            modal_content = []
            
            # Si el consumo es "Error", mostrar un mensaje especial
            if row_data["Consumo"] == "Error":
                debug_log(f"[DEBUG] Consumo con error para asset_id={asset_id}")
                modal_content.append(
                    html.Div(
                        "No hay datos disponibles para este período o se produjo un error al obtener los datos.",
                        className="alert alert-warning mb-3"
                    )
                )
                
                # Añadir información de diagnóstico
                modal_content.append(
                    html.Div([
                        html.H5("Información de diagnóstico"),
                        html.P([
                            html.Strong("Asset ID: "), asset_id
                        ]),
                        html.P([
                            html.Strong("Tipo de consumo: "), consumption_type
                        ]),
                        html.P([
                            html.Strong("Período: "), f"{month}/{year}"
                        ]),
                        html.P([
                            html.Strong("Estado: "), "Error - No hay datos disponibles"
                        ]),
                        html.Hr(),
                        html.H5("Opciones de diagnóstico"),
                        html.Div([
                            dbc.Button(
                                "Ver datos fuente", 
                                id="view-source-data-btn", 
                                color="primary", 
                                className="me-2"
                            ),
                            dbc.Button(
                                "Verificar conexión con sensor", 
                                id="check-sensor-btn", 
                                color="info", 
                                className="me-2"
                            ),
                            dbc.Button(
                                "Ver logs de error", 
                                id="view-error-logs-btn", 
                                color="warning", 
                                className="me-2"
                            ),
                            dbc.Button(
                                "Obtener lecturas en tiempo real", 
                                id="get-realtime-readings-btn", 
                                color="success", 
                                className="me-2"
                            ),
                            dbc.Button(
                                "Actualizar lecturas", 
                                id="update-readings-from-detail-btn", 
                                color="danger", 
                                className="me-2"
                            )
                        ], className="mb-3"),
                        html.Div(id="error-diagnosis-results"),
                        dcc.Store(id="error-diagnosis-data", data=json.dumps({
                            "asset_id": asset_id,
                            "consumption_type": consumption_type,
                            "year": year,
                            "month": month,
                            "project_id": project_id
                        }))
                    ])
                )
                
                debug_log("=== FIN DEL CALLBACK show_consumption_detail_modal (Error) ===")
                return True, modal_content, modal_title, False, None, None, False, None, None
            
            # Filtrar el DataFrame para el asset y tipo de consumo seleccionados
            filtered_df = df[(df['asset_id'] == asset_id) & (df['consumption_type'] == consumption_type)]
            
            # Log para depuración
            debug_log(f"[DEBUG] DataFrame filtrado: {len(filtered_df)} filas para asset_id={asset_id}, consumption_type={consumption_type}")
            
            # Generar gráfico de consumo diario
            daily_chart = generate_daily_consumption_chart(filtered_df, asset_id, month, year, consumption_type)
            
            # Generar estadísticas de consumo
            stats_content = generate_consumption_stats(filtered_df, asset_id, month, year, consumption_type)
            
            # Generar tabla de lecturas diarias
            daily_readings_table = generate_daily_readings_table(filtered_df, asset_id, month, year, consumption_type)
            
            # Añadir todos los elementos al contenido del modal
            modal_content.extend([
                html.Div([
                    html.H5("Consumo diario"),
                    daily_chart
                ], className="mb-4"),
                html.Div([
                    html.H5("Estadísticas"),
                    stats_content
                ], className="mb-4"),
                html.Div([
                    html.H5("Lecturas diarias"),
                    daily_readings_table
                ])
            ])
            
            debug_log("=== FIN DEL CALLBACK show_consumption_detail_modal (Ver detalles) ===")
            return True, modal_content, modal_title, False, None, None, False, None, None
            
        except Exception as e:
            debug_log(f"[ERROR] Error en callback show_consumption_detail_modal: {str(e)}")
            import traceback
            debug_log(traceback.format_exc())
            debug_log("=== FIN DEL CALLBACK show_consumption_detail_modal (Exception) ===")
            return True, html.Div(f"Error: {str(e)}", className="alert alert-danger"), "Error", False, None, None, False, None, None
    
    # Callback para cerrar el modal
    @app.callback(
        Output('consumption-detail-modal', 'is_open', allow_duplicate=True),
        [Input('close-consumption-detail-modal', 'n_clicks')],
        [State('consumption-detail-modal', 'is_open')],
        prevent_initial_call=True
    )
    def close_consumption_detail_modal(n_clicks, is_open):
        if n_clicks:
            return False
        return is_open
    
    # Callback para mostrar los datos fuente cuando hay un error
    @app.callback(
        Output("error-diagnosis-results", "children"),
        [Input("view-source-data-btn", "n_clicks"),
         Input("check-sensor-btn", "n_clicks"),
         Input("view-error-logs-btn", "n_clicks"),
         Input("get-realtime-readings-btn", "n_clicks"),
         Input("update-readings-from-detail-btn", "n_clicks")],
        [State("error-diagnosis-data", "data")],
        prevent_initial_call=True
    )
    def show_error_diagnosis(view_source_clicks, check_sensor_clicks, view_logs_clicks, get_realtime_clicks, update_clicks, diagnosis_data):
        ctx = dash.callback_context
        if not ctx.triggered:
            return None
        
        try:
            # Importar json al principio de la función
            import json
            import os
            from datetime import datetime
            
            # Obtener el ID del botón que fue clickeado
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            # Obtener los datos de diagnóstico
            if not diagnosis_data:
                return html.Div("No hay datos disponibles para el diagnóstico.", className="alert alert-warning")
            
            data = json.loads(diagnosis_data)
            asset_id = data.get("asset_id")
            consumption_type = data.get("consumption_type")
            year = data.get("year")
            month = data.get("month")
            
            # Ejecutar la función correspondiente según el botón clickeado
            if button_id == "view-source-data-btn":
                return show_source_data(asset_id, consumption_type, year, month)
            elif button_id == "check-sensor-btn":
                return check_sensor_connection(asset_id, consumption_type)
            elif button_id == "view-error-logs-btn":
                return show_error_logs(asset_id, consumption_type, year, month)
            elif button_id == "get-realtime-readings-btn":
                return get_realtime_readings(asset_id, consumption_type)
            elif button_id == "update-readings-from-detail-btn":
                return update_readings_from_detail(asset_id, consumption_type)
            
            return None
        
        except Exception as e:
            import traceback
            error_msg = f"Error al realizar diagnóstico: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div(error_msg, className="alert alert-danger")

    # Función para mostrar los datos fuente
    def show_source_data(asset_id, consumption_type, year, month):
        try:
            # Mapear el tipo de consumo a su tag correspondiente
            consumption_tag_map = {
                "Energía térmica calor": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT",
                "Energía térmica frío": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_COOLING",
                "Agua fría": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_COLD_WATER",
                "Agua caliente": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER",
                "Agua caliente sanitaria": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER",
                "Agua general": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL",
                "Energía general": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL",
                "Flujo de personas entrada": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_IN",
                "Flujo de personas salida": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_OUT"
            }
            
            # Obtener el tag correspondiente al tipo de consumo
            consumption_tag = consumption_tag_map.get(consumption_type)
            
            # Si no se encuentra una coincidencia exacta, intentar una búsqueda parcial
            if not consumption_tag:
                debug_log(f"[INFO] Tipo de consumo no encontrado exactamente: {consumption_type}, intentando búsqueda parcial")
                
                # Buscar coincidencias parciales
                for key, value in consumption_tag_map.items():
                    if key in consumption_type or consumption_type in key:
                        consumption_tag = value
                        debug_log(f"[INFO] Coincidencia parcial encontrada: {key} -> {value}")
                        break
            
            # Si aún no se encuentra, intentar mapear por palabras clave
            if not consumption_tag:
                debug_log(f"[INFO] No se encontró coincidencia parcial para: {consumption_type}, intentando mapeo por palabras clave")
                
                consumption_type_lower = consumption_type.lower()
                if "calor" in consumption_type_lower or "térmica calor" in consumption_type_lower:
                    consumption_tag = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT"
                elif "frío" in consumption_type_lower or "térmica frío" in consumption_type_lower:
                    consumption_tag = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_COOLING"
                elif "agua fría" in consumption_type_lower:
                    consumption_tag = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_COLD_WATER"
                elif "agua caliente" in consumption_type_lower:
                    consumption_tag = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER"
                elif "agua" in consumption_type_lower:
                    consumption_tag = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL"
                elif "energía" in consumption_type_lower:
                    consumption_tag = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL"
                elif "entrada" in consumption_type_lower:
                    consumption_tag = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_IN"
                elif "salida" in consumption_type_lower:
                    consumption_tag = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_OUT"
            
            if not consumption_tag:
                return html.Div([
                    html.H5("Tipo de consumo no reconocido"),
                    html.P(f"No se pudo mapear el tipo de consumo: '{consumption_type}' a un tag de consumo."),
                    html.P("Tipos de consumo reconocidos:"),
                    html.Ul([html.Li(key) for key in consumption_tag_map.keys()]),
                    html.Hr(),
                    html.P("Por favor, contacte con el administrador del sistema para añadir este tipo de consumo al mapeo.")
                ], className="alert alert-warning")
            
            # Carpeta principal de datos analizados
            analyzed_data_folder = os.path.join("data", "analyzed_data")
            
            # Verificar si la carpeta principal existe
            if not os.path.exists(analyzed_data_folder):
                return html.Div([
                    html.H5("Carpeta de datos no encontrada"),
                    html.P(f"La carpeta principal de datos no existe: {analyzed_data_folder}"),
                    html.Hr(),
                    html.P("Información de búsqueda:"),
                    html.Ul([
                        html.Li(f"Asset ID: {asset_id}"),
                        html.Li(f"Tipo de consumo: {consumption_type}"),
                        html.Li(f"Tag de consumo: {consumption_tag}"),
                        html.Li(f"Ruta buscada: {analyzed_data_folder}")
                    ]),
                    html.Hr(),
                    html.P("Posibles causas:"),
                    html.Ul([
                        html.Li("La carpeta de datos podría estar en una ubicación diferente"),
                        html.Li("La carpeta de datos podría no existir o tener un nombre diferente"),
                        html.Li("Podría haber un problema de permisos para acceder a la carpeta")
                    ])
                ], className="alert alert-warning")
            
            # Buscar carpetas de proyectos
            project_folders = []
            for folder_name in os.listdir(analyzed_data_folder):
                folder_path = os.path.join(analyzed_data_folder, folder_name)
                if os.path.isdir(folder_path):
                    project_folders.append(folder_name)
            
            if not project_folders:
                return html.Div(f"No se encontraron carpetas de proyectos en {analyzed_data_folder}", className="alert alert-warning")
            
            # Buscar archivos CSV que coincidan con el asset_id y el tag
            matching_files = []
            for project_id in project_folders:
                project_folder = os.path.join(analyzed_data_folder, project_id)
                file_pattern = f"daily_readings_{asset_id}_{consumption_tag}.csv"
                
                for filename in os.listdir(project_folder):
                    if filename.startswith(f"daily_readings_{asset_id}_") and consumption_tag in filename and filename.endswith(".csv"):
                        matching_files.append({
                            "project_id": project_id,
                            "filename": filename,
                            "full_path": os.path.join(project_folder, filename)
                        })
            
            if not matching_files:
                return html.Div([
                    html.H5("No se encontraron archivos de datos"),
                    html.P(f"No se encontraron archivos CSV para el asset {asset_id} con el tag {consumption_tag}."),
                    html.Hr(),
                    html.P("Información de búsqueda:"),
                    html.Ul([
                        html.Li(f"Asset ID: {asset_id}"),
                        html.Li(f"Tipo de consumo: {consumption_type}"),
                        html.Li(f"Tag de consumo: {consumption_tag}"),
                        html.Li(f"Patrón de búsqueda: daily_readings_{asset_id}_{consumption_tag}.csv"),
                        html.Li(f"Carpetas de proyectos revisadas: {', '.join(project_folders)}")
                    ]),
                    html.Hr(),
                    html.P("Posibles causas:"),
                    html.Ul([
                        html.Li("El asset no tiene datos para este tipo de consumo"),
                        html.Li("El archivo CSV podría tener un nombre diferente al esperado"),
                        html.Li("El asset podría pertenecer a un proyecto diferente")
                    ])
                ], className="alert alert-warning")
            
            # Crear opciones para el dropdown de selección de archivo
            file_options = [
                {"label": f"{file['filename']} (Proyecto: {file['project_id']})", "value": i}
                for i, file in enumerate(matching_files)
            ]
            
            # Crear componentes para seleccionar y mostrar archivos
            file_selector = html.Div([
                html.H5("Archivos encontrados:"),
                dcc.Dropdown(
                    id="file-selector-dropdown",
                    options=file_options,
                    value=0 if matching_files else None,
                    clearable=False,
                    style={"marginBottom": "15px"}
                ),
                html.Div([
                    html.Button(
                        "Cargar archivo seleccionado", 
                        id="load-selected-file-btn", 
                        className="btn btn-primary me-2"
                    ),
                    html.Button(
                        "Eliminar archivo", 
                        id="delete-source-file-btn", 
                        className="btn btn-danger",
                        title="Eliminar el archivo de datos fuente si está corrupto"
                    ),
                ], className="d-flex mb-3"),
                # Almacenar información para el botón de cargar archivo
                dcc.Store(
                    id="file-selector-data",
                    data=json.dumps({
                        "matching_files": [file["full_path"] for file in matching_files],
                        "asset_id": asset_id,
                        "consumption_type": consumption_type,
                        "year": year,
                        "month": month
                    })
                ),
                # Contenedor para mostrar el contenido del archivo
                html.Div(id="file-content-container"),
                
                # Modal de confirmación para eliminar archivo
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle("Confirmar eliminación"), close_button=True),
                        dbc.ModalBody(id="delete-file-confirm-body"),
                        dbc.ModalFooter([
                            dbc.Button("Cancelar", id="cancel-delete-file", className="me-2"),
                            dbc.Button("Eliminar", id="confirm-delete-file", color="danger")
                        ]),
                    ],
                    id="delete-file-confirm-modal",
                    is_open=False,
                ),
                # Store para datos de eliminación
                dcc.Store(id="delete-file-data"),
            ])
            
            # Intentar cargar el primer archivo encontrado para mostrar algo inicialmente
            if matching_files:
                try:
                    file_path = matching_files[0]["full_path"]
                    df = pd.read_csv(file_path)
                    
                    # Filtrar por año y mes si es posible
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        df_filtered = df[
                            (df['date'].dt.year == int(year)) & 
                            (df['date'].dt.month == int(month))
                        ]
                        
                        if not df_filtered.empty:
                            df = df_filtered
                    
                    # Crear una tabla con los datos
                    table = dash_table.DataTable(
                        id="source-data-table",
                        data=df.to_dict('records'),
                        columns=[{"name": col, "id": col} for col in df.columns],
                        style_table={'overflowX': 'auto', 'maxHeight': '400px'},
                        style_cell={
                            'textAlign': 'left',
                            'padding': '10px',
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                        page_size=10,
                        filter_action='native',
                        sort_action='native',
                        export_format='csv'
                    )
                    
                    # Mostrar información del archivo y la tabla
                    file_content = html.Div([
                        html.H5(f"Datos fuente para {asset_id} - {consumption_type}"),
                        html.P(f"Archivo: {matching_files[0]['filename']}"),
                        html.P(f"Proyecto: {matching_files[0]['project_id']}"),
                        html.P(f"Período: {month}/{year}"),
                        html.Hr(),
                        html.Div([
                            html.P(f"Total de filas: {len(df)}"),
                            html.P(f"Columnas: {', '.join(df.columns)}"),
                        ]),
                        html.Hr(),
                        table
                    ])
                    
                    # Actualizar el contenedor con el contenido del archivo
                    return html.Div([
                        file_selector,
                        html.Hr(),
                        file_content
                    ])
                
                except Exception as e:
                    return html.Div([
                        file_selector,
                        html.Div(f"Error al cargar el archivo: {str(e)}", className="alert alert-danger mt-3")
                    ])
            
            return file_selector
        
        except Exception as e:
            import traceback
            error_msg = f"Error al mostrar datos fuente: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div(error_msg, className="alert alert-danger")
    
    # Función para verificar la conexión con el sensor
    def check_sensor_connection(asset_id, consumption_type):
        # Esta función simularía una verificación de conexión con el sensor
        # En un entorno real, aquí se haría una llamada a la API o al sistema que gestiona los sensores
        
        return html.Div([
            html.H5("Verificación de conexión con sensor"),
            html.P(f"Asset ID: {asset_id}"),
            html.P(f"Tipo de consumo: {consumption_type}"),
            html.Hr(),
            html.Div([
                html.P("Esta funcionalidad permite verificar el estado de la conexión con el sensor asociado a este asset."),
                html.P("Posibles causas de error:"),
                html.Ul([
                    html.Li("El sensor podría estar desconectado o sin energía"),
                    html.Li("Problemas de comunicación en la red"),
                    html.Li("El sensor podría estar mal configurado"),
                    html.Li("El gateway podría estar fuera de línea"),
                    html.Li("El sensor podría estar dañado o requerir mantenimiento")
                ]),
                html.P("Acciones recomendadas:"),
                html.Ul([
                    html.Li("Verificar la alimentación eléctrica del sensor"),
                    html.Li("Comprobar la conectividad de red"),
                    html.Li("Revisar la configuración del sensor en el sistema"),
                    html.Li("Verificar el estado del gateway"),
                    html.Li("Contactar al equipo de mantenimiento para una inspección física")
                ])
            ], className="alert alert-info")
        ])
    
    # Función para mostrar los logs de error
    def show_error_logs(asset_id, consumption_type, year, month):
        # Esta función simularía la obtención de logs de error
        # En un entorno real, aquí se buscarían logs en archivos o en una base de datos
        
        # Crear algunos logs de ejemplo para mostrar
        example_logs = [
            {"timestamp": f"{year}-{month}-01 08:15:22", "level": "WARNING", "message": f"No se pudo obtener lectura del sensor para {asset_id}"},
            {"timestamp": f"{year}-{month}-01 09:30:45", "level": "ERROR", "message": f"Timeout al conectar con el sensor para {asset_id}"},
            {"timestamp": f"{year}-{month}-02 10:45:12", "level": "ERROR", "message": f"Datos recibidos inválidos para {asset_id}"},
            {"timestamp": f"{year}-{month}-03 07:20:33", "level": "WARNING", "message": f"Valor fuera de rango para {asset_id}: -1.0"},
            {"timestamp": f"{year}-{month}-05 14:10:05", "level": "ERROR", "message": f"No se pudo establecer conexión con el gateway para {asset_id}"}
        ]
        
        # Crear una tabla con los logs de ejemplo
        logs_table = html.Table([
            html.Thead(
                html.Tr([
                    html.Th("Timestamp", style={"width": "25%"}),
                    html.Th("Nivel", style={"width": "15%"}),
                    html.Th("Mensaje", style={"width": "60%"})
                ])
            ),
            html.Tbody([
                html.Tr([
                    html.Td(log["timestamp"]),
                    html.Td(log["level"], style={"color": "red" if log["level"] == "ERROR" else "orange"}),
                    html.Td(log["message"])
                ]) for log in example_logs
            ])
        ], className="table table-striped table-bordered")
        
        return html.Div([
            html.H5("Logs de error"),
            html.P(f"Asset ID: {asset_id}"),
            html.P(f"Tipo de consumo: {consumption_type}"),
            html.P(f"Período: {month}/{year}"),
            html.Hr(),
            html.P("Logs de ejemplo (en un entorno real, estos serían logs reales del sistema):"),
            logs_table,
            html.Hr(),
            html.Div([
                html.P("Posibles causas de error basadas en los logs:"),
                html.Ul([
                    html.Li("Problemas de conectividad con el sensor o gateway"),
                    html.Li("Timeout en las comunicaciones"),
                    html.Li("Datos inválidos o fuera de rango recibidos del sensor"),
                    html.Li("Problemas de configuración del sensor")
                ]),
                html.P("Acciones recomendadas:"),
                html.Ul([
                    html.Li("Verificar la configuración del sensor en el sistema"),
                    html.Li("Comprobar la conectividad de red"),
                    html.Li("Revisar los parámetros de calibración del sensor"),
                    html.Li("Contactar al equipo de soporte técnico para asistencia")
                ])
            ], className="alert alert-info")
        ])
    
    # Callback para manejar el botón de actualizar lecturas
    @app.callback(
        Output("metrics-update-readings-result", "children"),
        [Input("metrics-update-readings-button", "n_clicks")],
        [State("metrics-project-filter", "value"),
         State("metrics-consumption-tags-filter", "value"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def update_readings(n_clicks, project_id, consumption_tags, token_data):
        if not n_clicks:
            return ""
        
        if not project_id or project_id == "all":
            return html.Div([
                html.P("Debe seleccionar un proyecto específico para actualizar las lecturas.", className="text-danger")
            ])
        
        if not consumption_tags or len(consumption_tags) == 0:
            return html.Div([
                html.P("Debe seleccionar al menos un tipo de consumo para actualizar las lecturas.", className="text-danger")
            ])
        
        # Obtener el token JWT si está disponible
        token = None
        if token_data and "token" in token_data:
            token = token_data["token"]
        
        # Llamar a la función para actualizar las lecturas
        result = get_daily_readings_for_year_multiple_tags_project_parallel(project_id, consumption_tags, token=token)
        
        if result["success"]:
            return html.Div([
                html.P(result["message"], className="text-success"),
                html.P(f"Total de assets: {result.get('total_assets', 0)}", className="text-info"),
                html.P(f"Assets procesados con éxito: {result.get('success_count', 0)}", className="text-info"),
                html.P(f"Assets con errores: {result.get('error_count', 0)}", className="text-info")
            ])
        else:
            return html.Div([
                html.P(f"Error: {result['message']}", className="text-danger")
            ])
    
    # Callback para mostrar/ocultar el selector de fechas personalizado y calcular las fechas según el período
    @app.callback(
        [Output("metrics-custom-date-container", "style"),
         Output("metrics-date-range", "start_date"),
         Output("metrics-date-range", "end_date")],
        [Input("metrics-date-period", "value")]
    )
    def update_date_range(period):
        today = datetime.now().date()
        
        if period == "custom":
            # Mostrar el selector de fechas personalizado
            return {"display": "block"}, (today - timedelta(days=30)), today
        else:
            # Ocultar el selector de fechas personalizado y calcular las fechas según el período
            if period == "last_month":
                start_date = today - timedelta(days=30)
            elif period == "last_3_months":
                start_date = today - timedelta(days=90)
            elif period == "last_year":
                start_date = today - timedelta(days=365)
            else:
                # Valor por defecto: último mes
                start_date = today - timedelta(days=30)
                
            return {"display": "none"}, start_date, today
    
    # Callback para cargar el archivo seleccionado
    @app.callback(
        Output("file-content-container", "children"),
        [Input("load-selected-file-btn", "n_clicks")],
        [State("file-selector-dropdown", "value"),
         State("file-selector-data", "data")],
        prevent_initial_call=True
    )
    def load_selected_file(n_clicks, selected_file_index, selector_data):
        if not n_clicks or selected_file_index is None or not selector_data:
            return None
        
        try:
            # Importar json al principio de la función
            import json
            import os
            
            # Cargar los datos del selector
            data = json.loads(selector_data)
            matching_files = data.get("matching_files", [])
            asset_id = data.get("asset_id")
            consumption_type = data.get("consumption_type")
            year = data.get("year")
            month = data.get("month")
            
            if not matching_files or selected_file_index >= len(matching_files):
                return html.Div("No se encontraron archivos o índice inválido.", className="alert alert-warning")
            
            # Obtener la ruta del archivo seleccionado
            file_path = matching_files[selected_file_index]
            
            # Extraer el nombre del archivo y el proyecto de la ruta
            file_name = os.path.basename(file_path)
            project_id = os.path.basename(os.path.dirname(file_path))
            
            # Verificar si el archivo existe
            if not os.path.exists(file_path):
                return html.Div(f"El archivo no existe: {file_path}", className="alert alert-warning")
            
            # Cargar el archivo CSV
            try:
                df = pd.read_csv(file_path)
                
                # Filtrar por año y mes si es posible
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df_filtered = df[
                        (df['date'].dt.year == int(year)) & 
                        (df['date'].dt.month == int(month))
                    ]
                    
                    if not df_filtered.empty:
                        filtered_rows = len(df_filtered)
                        total_rows = len(df)
                        df = df_filtered
                        filter_info = f"Mostrando {filtered_rows} de {total_rows} filas (filtrado por {month}/{year})"
                    else:
                        filter_info = f"No se encontraron datos para el período {month}/{year}"
                else:
                    filter_info = "No se pudo filtrar por fecha (columna 'date' no encontrada)"
                
                # Crear una tabla con los datos
                table = dash_table.DataTable(
                    id="source-data-table",
                    data=df.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in df.columns],
                    style_table={'overflowX': 'auto', 'maxHeight': '400px'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '10px',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    page_size=10,
                    filter_action='native',
                    sort_action='native',
                    export_format='csv'
                )
                
                # Mostrar información del archivo y la tabla
                return html.Div([
                    html.H5(f"Datos fuente para {asset_id} - {consumption_type}"),
                    html.P(f"Archivo: {file_name}"),
                    html.P(f"Proyecto: {project_id}"),
                    html.P(f"Período: {month}/{year}"),
                    html.Div(filter_info, className="alert alert-info"),
                    html.Hr(),
                    html.Div([
                        html.P(f"Total de filas: {len(df)}"),
                        html.P(f"Columnas: {', '.join(df.columns)}"),
                    ]),
                    html.Hr(),
                    table
                ])
            
            except Exception as e:
                return html.Div(f"Error al cargar el archivo: {str(e)}", className="alert alert-danger")
        
        except Exception as e:
            import traceback
            error_msg = f"Error al cargar archivo seleccionado: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div(error_msg, className="alert alert-danger")
    
    # Función para obtener lecturas en tiempo real
    def get_realtime_readings(asset_id, consumption_type):
        try:
            # Importar las funciones necesarias
            from utils.api import get_sensors_with_tags, get_sensor_value_for_date
            import datetime
            import pandas as pd
            import os
            
            # Mapear el tipo de consumo a su tag correspondiente
            consumption_tag_map = {
                "Energía térmica calor": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT",
                "Energía térmica frío": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_COOLING",
                "Agua fría": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_COLD_WATER",
                "Agua caliente": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER",
                "Agua caliente sanitaria": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER",
                "Agua general": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL",
                "Energía general": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL",
                "Flujo de personas entrada": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_IN",
                "Flujo de personas salida": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_OUT"
            }
            
            # Obtener el tag correspondiente al tipo de consumo
            consumption_tag = consumption_tag_map.get(consumption_type)
            
            # Si no se encuentra una coincidencia exacta, intentar una búsqueda parcial
            if not consumption_tag:
                for key, value in consumption_tag_map.items():
                    if key in consumption_type or consumption_type in key:
                        consumption_tag = value
                        break
            
            if not consumption_tag:
                return html.Div([
                    html.H5("Tipo de consumo no reconocido"),
                    html.P(f"No se pudo mapear el tipo de consumo: '{consumption_type}' a un tag de consumo."),
                    html.P("Tipos de consumo reconocidos:"),
                    html.Ul([html.Li(key) for key in consumption_tag_map.keys()]),
                ], className="alert alert-warning")
            
            # Obtener la fecha actual para mostrar en la interfaz
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            
            # Crear un componente para mostrar el progreso y los resultados
            results_container = html.Div(id="realtime-readings-results")
            
            # Obtener los sensores asociados al asset
            debug_log(f"[INFO] Obteniendo sensores para el asset {asset_id} con tag {consumption_tag}")
            
            # Crear un componente para mostrar la información de los sensores
            sensor_info_container = html.Div([
                html.H5("Información de sensores"),
                html.P("Obteniendo información de sensores..."),
                html.Div(className="spinner-border text-primary", role="status"),
            ], id="sensor-info-container")
            
            # Buscar archivos CSV que coincidan con el asset_id y el tag
            analyzed_data_folder = os.path.join("data", "analyzed_data")
            matching_files = []
            csv_data = None
            
            if os.path.exists(analyzed_data_folder):
                for project_folder in os.listdir(analyzed_data_folder):
                    project_path = os.path.join(analyzed_data_folder, project_folder)
                    if os.path.isdir(project_path):
                        for filename in os.listdir(project_path):
                            if filename.startswith(f"daily_readings_{asset_id}_") and consumption_tag in filename and filename.endswith(".csv"):
                                file_path = os.path.join(project_path, filename)
                                matching_files.append({
                                    "project_id": project_folder,
                                    "filename": filename,
                                    "full_path": file_path
                                })
            
            # Cargar datos del CSV si existe
            csv_data_container = None
            if matching_files:
                try:
                    file_path = matching_files[0]["full_path"]
                    csv_data = pd.read_csv(file_path)
                    
                    # Mostrar información del CSV
                    csv_data_container = html.Div([
                        html.H5("Datos almacenados en CSV"),
                        html.P(f"Archivo: {matching_files[0]['filename']}"),
                        html.P(f"Proyecto: {matching_files[0]['project_id']}"),
                        html.P(f"Total de filas: {len(csv_data)}"),
                        html.P(f"Columnas: {', '.join(csv_data.columns)}"),
                        html.Hr(),
                        dash_table.DataTable(
                            id="csv-data-table",
                            data=csv_data.head(10).to_dict('records'),
                            columns=[{"name": col, "id": col} for col in csv_data.columns],
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '10px',
                                'whiteSpace': 'normal',
                                'height': 'auto',
                            },
                            style_header={
                                'backgroundColor': 'rgb(230, 230, 230)',
                                'fontWeight': 'bold'
                            },
                        ),
                        html.P("Mostrando las primeras 10 filas", className="text-muted mt-2"),
                    ])
                except Exception as e:
                    csv_data_container = html.Div([
                        html.H5("Error al cargar datos del CSV"),
                        html.P(f"Error: {str(e)}"),
                    ], className="alert alert-warning")
            else:
                csv_data_container = html.Div([
                    html.H5("No se encontraron archivos CSV"),
                    html.P(f"No se encontraron archivos CSV para el asset {asset_id} con el tag {consumption_tag}."),
                ], className="alert alert-warning")
            
            # Crear un formulario para obtener parámetros adicionales
            form = html.Div([
                html.H5("Obtener lecturas en tiempo real"),
                html.P(f"Asset ID: {asset_id}"),
                html.P(f"Tipo de consumo: {consumption_type} ({consumption_tag})"),
                html.Hr(),
                
                # Selector de rango de fechas predefinido
                html.Div([
                    html.Label("Seleccione un rango de fechas:"),
                    dcc.RadioItems(
                        id="realtime-date-range",
                        options=[
                            {'label': 'Fecha específica', 'value': 'specific'},
                            {'label': 'Última semana', 'value': 'last_week'},
                            {'label': 'Último mes', 'value': 'last_month'},
                            {'label': 'Últimos 3 meses', 'value': 'last_3_months'},
                            {'label': 'Últimos 6 meses', 'value': 'last_6_months'},
                            {'label': 'Últimos 12 meses', 'value': 'last_12_months'},
                            {'label': 'Este año', 'value': 'this_year'},
                            {'label': 'Año pasado', 'value': 'last_year'},
                        ],
                        value='specific',
                        className="mb-3"
                    ),
                ], className="mb-3"),
                
                # Selector de fecha específica (visible solo cuando se selecciona "Fecha específica")
                html.Div([
                    html.Label("Fecha específica:"),
                    dcc.DatePickerSingle(
                        id="realtime-date-picker",
                        date=current_date,
                        display_format="YYYY-MM-DD",
                        className="mb-3"
                    ),
                ], id="realtime-specific-date-container", className="mb-3"),
                
                # Botón para obtener la lectura
                html.Div([
                    dbc.Button(
                        "Obtener lecturas del sensor", 
                        id="fetch-reading-btn", 
                        color="primary",
                        className="me-2"
                    ),
                    # Almacenar información para el botón de obtener lectura
                    dcc.Store(
                        id="realtime-reading-data",
                        data=json.dumps({
                            "asset_id": asset_id,
                            "consumption_type": consumption_type,
                            "consumption_tag": consumption_tag
                        })
                    ),
                ], className="mt-3"),
                
                # Contenedor para mostrar los resultados
                html.Div(id="fetch-reading-results", className="mt-4")
            ])
            
            return html.Div([
                form,
                html.Hr(),
                csv_data_container,
                html.Hr(),
                html.H5("Información de diagnóstico"),
                html.P("Esta funcionalidad permite obtener lecturas en tiempo real del sensor asociado a este asset."),
                html.P("Para obtener lecturas, siga estos pasos:"),
                html.Ol([
                    html.Li("Seleccione un rango de fechas o una fecha específica."),
                    html.Li("Haga clic en el botón 'Obtener lecturas del sensor'."),
                ]),
                html.P("El sistema buscará automáticamente los sensores asociados al asset y al tipo de consumo seleccionado."),
                html.Hr(),
                html.Div([
                    html.P("Posibles causas de error:"),
                    html.Ul([
                        html.Li("El sensor no está configurado correctamente en el sistema."),
                        html.Li("No hay datos disponibles para las fechas seleccionadas."),
                        html.Li("Problemas de conectividad con el API."),
                        html.Li("Credenciales de acceso inválidas o expiradas."),
                    ]),
                ], className="alert alert-info")
            ])
        
        except Exception as e:
            import traceback
            error_msg = f"Error al obtener lecturas en tiempo real: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div(error_msg, className="alert alert-danger")
    
    # Callback para obtener lecturas en tiempo real
    @app.callback(
        Output("fetch-reading-results", "children"),
        [Input("fetch-reading-btn", "n_clicks")],
        [State("realtime-date-picker", "date"),
         State("realtime-reading-data", "data"),
         State("jwt-token-store", "data"),
         State("realtime-date-range", "value")],
        prevent_initial_call=True
    )
    def fetch_reading(n_clicks, date_str, reading_data, token_data, date_range):
        if not n_clicks:
            return None
        
        try:
            # Importar las funciones necesarias
            from utils.api import get_sensors_with_tags, get_sensor_value_for_date
            import json
            import datetime
            import pandas as pd
            import os
            
            # Cargar los datos de lectura
            data = json.loads(reading_data)
            asset_id = data.get("asset_id")
            consumption_type = data.get("consumption_type")
            consumption_tag = data.get("consumption_tag")
            
            # Obtener el token JWT si está disponible
            token = None
            if token_data and "token" in token_data:
                token = token_data["token"]
            
            # Convertir la fecha a formato YYYY-MM-DD para mostrar en la interfaz
            if date_str:
                date_obj = datetime.datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
                formatted_date_display = date_obj.strftime("%Y-%m-%d")
                # Convertir la fecha al formato MM-DD-YYYY que espera la API
                formatted_date_api = date_obj.strftime("%m-%d-%Y")
            else:
                date_obj = datetime.datetime.now()
                formatted_date_display = date_obj.strftime("%Y-%m-%d")
                formatted_date_api = date_obj.strftime("%m-%d-%Y")
            
            # Mostrar información de la solicitud
            request_info = html.Div([
                html.H5("Información de la solicitud"),
                html.P(f"Asset ID: {asset_id}"),
                html.P(f"Tipo de consumo: {consumption_type}"),
                html.P(f"Tag de consumo: {consumption_tag}"),
                html.P(f"Fecha: {formatted_date_display}"),
                html.P(f"Fecha (formato API): {formatted_date_api}", className="text-muted"),
            ])
            
            # Obtener los sensores asociados al asset
            debug_log(f"[INFO] Obteniendo sensores para el asset {asset_id}")
            sensors = get_sensors_with_tags(asset_id, token)
            
            if not sensors:
                return html.Div([
                    request_info,
                    html.Hr(),
                    html.Div([
                        html.H5("No se encontraron sensores"),
                        html.P(f"No se encontraron sensores asociados al asset {asset_id}."),
                        html.P("Posibles causas:"),
                        html.Ul([
                            html.Li("El asset no tiene sensores configurados."),
                            html.Li("Problemas de conectividad con el API."),
                            html.Li("Credenciales de acceso inválidas o expiradas."),
                        ]),
                    ], className="alert alert-warning")
                ])
            
            # Filtrar los sensores por el tag de consumo
            matching_sensors = []
            for sensor in sensors:
                tag_name = sensor.get("tag_name", "")
                if consumption_tag in tag_name:
                    matching_sensors.append(sensor)
            
            if not matching_sensors:
                return html.Div([
                    request_info,
                    html.Hr(),
                    html.Div([
                        html.H5("No se encontraron sensores para el tipo de consumo"),
                        html.P(f"No se encontraron sensores asociados al tag {consumption_tag}."),
                        html.P("Sensores disponibles:"),
                        html.Ul([html.Li(f"{sensor.get('tag_name', 'Sin tag')} (Sensor ID: {sensor.get('sensor_id', 'N/A')})") for sensor in sensors]),
                    ], className="alert alert-warning")
                ])
            
            # Crear una tabla con la información de los sensores
            sensor_table = html.Table([
                html.Thead(
                    html.Tr([
                        html.Th("Sensor ID"),
                        html.Th("Tag Name"),
                        html.Th("Sensor Type"),
                        html.Th("Gateway ID"),
                        html.Th("Device ID"),
                        html.Th("Sensor UUID")
                    ])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(sensor.get("sensor_id", "N/A")),
                        html.Td(sensor.get("tag_name", "N/A")),
                        html.Td(sensor.get("sensor_type", "N/A")),
                        html.Td(sensor.get("gateway_id", "N/A")),
                        html.Td(sensor.get("device_id", "N/A")),
                        html.Td(sensor.get("sensor_uuid", "N/A"))
                    ]) for sensor in matching_sensors
                ])
            ], className="table table-striped table-bordered")
            
            # Mostrar información de los sensores
            sensor_info = html.Div([
                html.H5("Sensores encontrados"),
                html.P(f"Se encontraron {len(matching_sensors)} sensores asociados al tag {consumption_tag}."),
                sensor_table
            ])
            
            # Obtener lecturas para cada sensor
            readings_results = []
            
            for i, sensor in enumerate(matching_sensors):
                device_id = sensor.get("device_id")
                sensor_id = sensor.get("sensor_id")
                gateway_id = sensor.get("gateway_id")
                tag_name = sensor.get("tag_name")
                
                try:
                    debug_log(f"[INFO] Obteniendo lectura para sensor {i+1}/{len(matching_sensors)}: device_id={device_id}, sensor_id={sensor_id}, gateway_id={gateway_id}")
                    
                    # Llamar a la API para obtener la lectura con el formato de fecha correcto
                    value, timestamp = get_sensor_value_for_date(
                        asset_id=asset_id,
                        device_id=device_id,
                        sensor_id=sensor_id,
                        gateway_id=gateway_id,
                        date=formatted_date_api,  # Usar el formato MM-DD-YYYY
                        token=token
                    )
                    
                    # Añadir el resultado a la lista
                    readings_results.append({
                        "sensor_id": sensor_id,
                        "tag_name": tag_name,
                        "value": value,
                        "timestamp": timestamp,
                        "status": "success" if value != "Sin datos disponibles" and value != "Error" else "error"
                    })
                    
                except Exception as e:
                    error_msg = f"Error al obtener lectura para sensor {sensor_id}: {str(e)}"
                    debug_log(f"[ERROR] {error_msg}")
                    
                    # Añadir el error a la lista
                    readings_results.append({
                        "sensor_id": sensor_id,
                        "tag_name": tag_name,
                        "value": "Error",
                        "timestamp": None,
                        "status": "error",
                        "error_msg": str(e)
                    })
            
            # Crear una tabla con los resultados de las lecturas
            readings_table = html.Table([
                html.Thead(
                    html.Tr([
                        html.Th("Sensor ID"),
                        html.Th("Tag Name"),
                        html.Th("Valor"),
                        html.Th("Timestamp"),
                        html.Th("Estado")
                    ])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(reading.get("sensor_id", "N/A")),
                        html.Td(reading.get("tag_name", "N/A")),
                        html.Td(reading.get("value", "N/A"), style={"color": "green" if reading.get("status") == "success" else "red"}),
                        html.Td(reading.get("timestamp", "N/A")),
                        html.Td(
                            "Éxito" if reading.get("status") == "success" else "Error", 
                            style={"color": "green" if reading.get("status") == "success" else "red"}
                        )
                    ]) for reading in readings_results
                ])
            ], className="table table-striped table-bordered")
            
            # Mostrar resultados de las lecturas
            readings_info = html.Div([
                html.H5("Resultados de las lecturas"),
                html.P(f"Se obtuvieron {len(readings_results)} lecturas para la fecha {formatted_date_display}."),
                readings_table
            ])
            
            # Comparar con los datos del CSV si están disponibles
            csv_comparison = None
            
            # Buscar archivos CSV que coincidan con el asset_id y el tag
            analyzed_data_folder = os.path.join("data", "analyzed_data")
            matching_files = []
            
            if os.path.exists(analyzed_data_folder):
                for project_folder in os.listdir(analyzed_data_folder):
                    project_path = os.path.join(analyzed_data_folder, project_folder)
                    if os.path.isdir(project_path):
                        for filename in os.listdir(project_path):
                            if filename.startswith(f"daily_readings_{asset_id}_") and consumption_tag in filename and filename.endswith(".csv"):
                                file_path = os.path.join(project_path, filename)
                                matching_files.append({
                                    "project_id": project_folder,
                                    "filename": filename,
                                    "full_path": file_path
                                })
            
            if matching_files:
                try:
                    file_path = matching_files[0]["full_path"]
                    csv_data = pd.read_csv(file_path)
                    
                    # Convertir la fecha a formato datetime
                    if 'date' in csv_data.columns:
                        csv_data['date'] = pd.to_datetime(csv_data['date'])
                        
                        # Filtrar por la fecha seleccionada
                        csv_filtered = csv_data[csv_data['date'].dt.date == date_obj.date()]
                        
                        if not csv_filtered.empty:
                            # Obtener el valor del CSV para la fecha seleccionada
                            csv_value = csv_filtered.iloc[0].get('value', 'N/A')
                            
                            # Obtener el valor de la lectura en tiempo real
                            realtime_value = "N/A"
                            for reading in readings_results:
                                if reading.get("status") == "success":
                                    realtime_value = reading.get("value", "N/A")
                                    break
                            
                            # Comparar los valores
                            if realtime_value != "N/A" and csv_value != "N/A":
                                try:
                                    realtime_value_float = float(realtime_value)
                                    csv_value_float = float(csv_value)
                                    
                                    # Calcular la diferencia
                                    difference = realtime_value_float - csv_value_float
                                    percentage_diff = (difference / csv_value_float) * 100 if csv_value_float != 0 else 0
                                    
                                    # Mostrar la comparación
                                    csv_comparison = html.Div([
                                        html.H5("Comparación con datos almacenados"),
                                        html.P(f"Valor en tiempo real: {realtime_value}"),
                                        html.P(f"Valor almacenado en CSV: {csv_value}"),
                                        html.P(f"Diferencia: {difference:.2f} ({percentage_diff:.2f}%)"),
                                        html.P(
                                            "Los valores coinciden." if abs(percentage_diff) < 1 else "Los valores no coinciden.",
                                            style={"color": "green" if abs(percentage_diff) < 1 else "red", "fontWeight": "bold"}
                                        )
                                    ], className="alert alert-info")
                                except (ValueError, TypeError):
                                    csv_comparison = html.Div([
                                        html.H5("Comparación con datos almacenados"),
                                        html.P(f"Valor en tiempo real: {realtime_value}"),
                                        html.P(f"Valor almacenado en CSV: {csv_value}"),
                                        html.P("No se pudo realizar la comparación numérica.")
                                    ], className="alert alert-warning")
                            else:
                                csv_comparison = html.Div([
                                    html.H5("Comparación con datos almacenados"),
                                    html.P(f"Valor en tiempo real: {realtime_value}"),
                                    html.P(f"Valor almacenado en CSV: {csv_value}"),
                                    html.P("No se pudo realizar la comparación.")
                                ], className="alert alert-warning")
                        else:
                            csv_comparison = html.Div([
                                html.H5("Comparación con datos almacenados"),
                                html.P(f"No se encontraron datos en el CSV para la fecha {formatted_date_display}.")
                            ], className="alert alert-warning")
                    else:
                        csv_comparison = html.Div([
                            html.H5("Comparación con datos almacenados"),
                            html.P("El CSV no contiene una columna 'date' para filtrar por fecha.")
                        ], className="alert alert-warning")
                    
                except Exception as e:
                    csv_comparison = html.Div([
                        html.H5("Error al comparar con datos almacenados"),
                        html.P(f"Error: {str(e)}")
                    ], className="alert alert-danger")
            else:
                csv_comparison = html.Div([
                    html.H5("Comparación con datos almacenados"),
                    html.P(f"No se encontraron archivos CSV para el asset {asset_id} con el tag {consumption_tag}.")
                ], className="alert alert-warning")
            
            # Retornar todos los componentes
            return html.Div([
                request_info,
                html.Hr(),
                sensor_info,
                html.Hr(),
                readings_info,
                html.Hr(),
                csv_comparison
            ])
            
        except Exception as e:
            import traceback
            error_msg = f"Error al procesar la solicitud: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div(error_msg, className="alert alert-danger")
    
    # Callback para mostrar u ocultar el selector de fecha específica
    @app.callback(
        Output("realtime-specific-date-container", "style"),
        [Input("realtime-date-range", "value")]
    )
    def toggle_specific_date_container(date_range):
        if date_range == "specific":
            return {"display": "block"}
        else:
            return {"display": "none"}
    
    # Callback para mostrar el modal de regeneración de lecturas
    @app.callback(
        [Output("regenerate-readings-modal", "is_open", allow_duplicate=True),
         Output("regenerate-readings-modal-body", "children", allow_duplicate=True),
         Output("regenerate-readings-data", "data", allow_duplicate=True)],
        [Input("table-monthly-readings", "active_cell"),
         Input("cancel-regenerate-readings", "n_clicks"),
         Input("confirm-regenerate-readings", "n_clicks")],
        [State("table-monthly-readings", "derived_virtual_data"),
         State("regenerate-readings-modal", "is_open"),
         State("metrics-project-filter", "value"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def handle_regenerate_readings_click(active_cell, cancel_clicks, confirm_clicks, table_data, is_open, project_id, token_data):
        # Este callback ya no se utiliza, pero se mantiene para evitar errores
        return dash.no_update, dash.no_update, dash.no_update
    
    # Callback para regenerar las lecturas cuando se confirma
    @app.callback(
        [Output("regenerate-readings-status", "children"),
         Output("metrics-data-store", "data", allow_duplicate=True)],
        [Input("confirm-regenerate-readings", "n_clicks")],
        [State("regenerate-readings-data", "data"),
         State("metrics-data-store", "data")],
        prevent_initial_call=True
    )
    def regenerate_readings(n_clicks, regenerate_data_json, current_data):
        if not n_clicks or not regenerate_data_json:
            return None, dash.no_update
        
        try:
            # Importar json al principio de la función
            import json
            import time
            
            # Cargar los datos de regeneración
            regenerate_data = json.loads(regenerate_data_json)
            asset_id = regenerate_data.get("asset_id")
            tag = regenerate_data.get("tag")
            project_id = regenerate_data.get("project_id")
            token_data = regenerate_data.get("token")
            
            if not asset_id or not tag or not project_id:
                return html.Div("Error: Faltan datos necesarios para la regeneración.", className="alert alert-danger"), dash.no_update
            
            # Obtener el token JWT si está disponible
            token = None
            if token_data and "token" in token_data:
                token = token_data["token"]
            
            # Asegurar que existe la carpeta del proyecto
            from utils.api import ensure_project_folder_exists, get_daily_readings_for_tag
            project_folder = ensure_project_folder_exists(project_id)
            
            # Crear componente de progreso
            progress_div = html.Div([
                html.P(f"Regenerando lecturas para el asset {asset_id}...", id="regenerate-progress-text"),
                dbc.Progress(id="regenerate-progress-bar", value=0, striped=True, animated=True),
                html.Div(id="regenerate-progress-details")
            ])
            
            # Actualizar el componente de progreso para mostrar que estamos iniciando
            progress_div.children[0] = html.P(f"Iniciando regeneración de lecturas para el asset {asset_id}...")
            progress_div.children[1] = dbc.Progress(value=10, striped=True, animated=True)
            
            # Regenerar las lecturas para el asset y tag específicos
            try:
                debug_log(f"[DEBUG] regenerate_readings - Regenerando lecturas para asset {asset_id}, tag {tag}")
                
                # Actualizar progreso
                progress_div.children[0] = html.P(f"Obteniendo información del sensor para el asset {asset_id}...")
                progress_div.children[1] = dbc.Progress(value=20, striped=True, animated=True)
                
                # Eliminar el archivo existente si existe
                file_name = f"daily_readings_{asset_id}_{tag}.csv"
                file_path = os.path.join(project_folder, file_name)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        debug_log(f"[DEBUG] regenerate_readings - Archivo existente eliminado: {file_path}")
                    except Exception as e:
                        debug_log(f"[ERROR] regenerate_readings - Error al eliminar archivo existente: {str(e)}")
                
                # Actualizar progreso
                progress_div.children[0] = html.P(f"Descargando nuevas lecturas para el asset {asset_id}...")
                progress_div.children[1] = dbc.Progress(value=40, striped=True, animated=True)
                
                # Obtener nuevas lecturas
                get_daily_readings_for_tag(asset_id, tag, project_folder, token)
                
                # Actualizar progreso
                progress_div.children[0] = html.P(f"Procesando datos...")
                progress_div.children[1] = dbc.Progress(value=80, striped=True, animated=True)
                
                # Verificar si el archivo se creó correctamente
                if os.path.exists(file_path):
                    # Actualizar progreso
                    progress_div.children[0] = html.P(f"Lecturas regeneradas con éxito para el asset {asset_id}.", className="text-success")
                    progress_div.children[1] = dbc.Progress(value=100, color="success")
                    progress_div.children.append(html.P("Haga clic en 'Visualizar Consumos' para ver los datos actualizados.", className="text-info mt-3"))
                    
                    # Añadir botón para cerrar el modal
                    progress_div.children.append(
                        html.Div([
                            dbc.Button("Cerrar", id="close-regenerate-readings-modal", className="mt-3")
                        ], className="text-center")
                    )
                    
                    # Añadir botón para refrescar los datos
                    progress_div.children.append(
                        html.Div([
                            dbc.Button("Refrescar Datos", id="refresh-after-regenerate", color="primary", className="mt-3 me-2"),
                            dbc.Button("Cerrar", id="close-regenerate-readings-modal", className="mt-3")
                        ], className="text-center")
                    )
                    
                    return progress_div, current_data
                else:
                    # Actualizar progreso con error
                    progress_div.children[0] = html.P(f"Error: No se pudo crear el archivo de lecturas.", className="text-danger")
                    progress_div.children[1] = dbc.Progress(value=100, color="danger")
                    
                    return progress_div, dash.no_update
            except Exception as e:
                # Actualizar progreso con error
                error_message = html.Div([
                    html.P(f"Error al regenerar lecturas: {str(e)}", className="text-danger"),
                    dbc.Progress(value=100, color="danger")
                ])
                return error_message, dash.no_update
                
        except Exception as e:
            import traceback
            error_msg = f"Error al procesar la solicitud: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div(error_msg, className="alert alert-danger"), dash.no_update
    
    # Callback para actualizar la tabla después de regenerar lecturas
    @app.callback(
        Output("metrics-monthly-readings-table", "children", allow_duplicate=True),
        [Input("metrics-data-store", "data")],
        prevent_initial_call=True
    )
    def refresh_table_after_regeneration(json_data):
        # Este callback se activará cuando se actualice el data store
        # Simplemente activamos el callback original de la tabla
        return update_monthly_readings_table(json_data, None, None, None, None, None, None)
    
    # Callback para eliminar el archivo de datos fuente
    @app.callback(
        Output("file-content-container", "children", allow_duplicate=True),
        [Input("delete-source-file-btn", "n_clicks")],
        [State("file-selector-dropdown", "value"),
         State("file-selector-data", "data")],
        prevent_initial_call=True
    )
    def delete_source_file(n_clicks, selected_file_index, selector_data):
        if not n_clicks or selected_file_index is None or not selector_data:
            return dash.no_update
        
        try:
            # Decodificar los datos del selector
            data = json.loads(selector_data)
            matching_files = data.get("matching_files", [])
            asset_id = data.get("asset_id", "")
            consumption_type = data.get("consumption_type", "")
            
            if not matching_files or selected_file_index >= len(matching_files):
                return html.Div("No se ha seleccionado un archivo válido.", className="alert alert-warning")
            
            # Obtener la ruta del archivo seleccionado
            file_path = matching_files[selected_file_index]
            
            # Verificar si el archivo existe
            if not os.path.exists(file_path):
                return html.Div(f"El archivo no existe: {file_path}", className="alert alert-warning")
            
            # Crear una copia de seguridad antes de eliminar
            backup_path = f"{file_path}.bak"
            try:
                import shutil
                shutil.copy2(file_path, backup_path)
                debug_log(f"[INFO] Se ha creado una copia de seguridad del archivo: {backup_path}")
            except Exception as e:
                debug_log(f"[WARNING] No se pudo crear una copia de seguridad: {str(e)}")
            
            # Eliminar el archivo
            os.remove(file_path)
            debug_log(f"[INFO] Se ha eliminado el archivo: {file_path}")
            
            # Mostrar mensaje de éxito
            return html.Div([
                html.H5("Archivo eliminado correctamente"),
                html.P(f"El archivo {os.path.basename(file_path)} ha sido eliminado."),
                html.P("Se ha creado una copia de seguridad con extensión .bak"),
                html.P([
                    "Para regenerar los datos, cierre este modal y haga clic en ",
                    html.Strong("Regenerar"),
                    " en la fila correspondiente de la tabla."
                ]),
                html.Hr(),
                html.P("Información del archivo eliminado:"),
                html.Ul([
                    html.Li(f"Asset ID: {asset_id}"),
                    html.Li(f"Tipo de consumo: {consumption_type}"),
                    html.Li(f"Ruta del archivo: {file_path}"),
                    html.Li(f"Copia de seguridad: {backup_path}")
                ])
            ], className="alert alert-success")
            
        except Exception as e:
            import traceback
            error_msg = f"Error al eliminar el archivo: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div([
                html.H5("Error al eliminar el archivo"),
                html.P(error_msg),
                html.Pre(traceback.format_exc())
            ], className="alert alert-danger")

    # Callback para mostrar el modal de confirmación de eliminación
    @app.callback(
        [Output("delete-file-confirm-modal", "is_open"),
         Output("delete-file-confirm-body", "children"),
         Output("delete-file-data", "data")],
        [Input("delete-source-file-btn", "n_clicks"),
         Input("cancel-delete-file", "n_clicks"),
         Input("confirm-delete-file", "n_clicks")],
        [State("file-selector-dropdown", "value"),
         State("file-selector-data", "data"),
         State("delete-file-confirm-modal", "is_open")],
        prevent_initial_call=True
    )
    def toggle_delete_file_modal(delete_clicks, cancel_clicks, confirm_clicks, 
                                selected_file_index, selector_data, is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            return False, "", None
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Si se hace clic en cancelar o confirmar, cerrar el modal
        if trigger_id in ["cancel-delete-file", "confirm-delete-file"]:
            return False, "", dash.no_update
        
        # Si no hay archivo seleccionado o datos del selector, no hacer nada
        if selected_file_index is None or not selector_data:
            return dash.no_update, dash.no_update, dash.no_update
        
        try:
            # Decodificar los datos del selector
            data = json.loads(selector_data)
            matching_files = data.get("matching_files", [])
            asset_id = data.get("asset_id", "")
            consumption_type = data.get("consumption_type", "")
            
            if not matching_files or selected_file_index >= len(matching_files):
                return dash.no_update, dash.no_update, dash.no_update
            
            # Obtener la ruta del archivo seleccionado
            file_path = matching_files[selected_file_index]
            file_name = os.path.basename(file_path)
            
            # Crear el contenido del modal
            modal_content = html.Div([
                html.P([
                    "¿Está seguro de que desea eliminar el archivo ",
                    html.Strong(file_name),
                    "?"
                ]),
                html.P("Esta acción no se puede deshacer. Se creará una copia de seguridad del archivo antes de eliminarlo."),
                html.Hr(),
                html.P("Información del archivo:"),
                html.Ul([
                    html.Li(f"Asset ID: {asset_id}"),
                    html.Li(f"Tipo de consumo: {consumption_type}"),
                    html.Li(f"Ruta del archivo: {file_path}")
                ])
            ])
            
            # Guardar los datos necesarios para la eliminación
            delete_data = {
                "file_path": file_path,
                "asset_id": asset_id,
                "consumption_type": consumption_type
            }
            
            return True, modal_content, json.dumps(delete_data)
        
        except Exception as e:
            import traceback
            error_msg = f"Error al preparar la eliminación del archivo: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return dash.no_update, dash.no_update, dash.no_update

    # Callback para eliminar el archivo de datos fuente
    @app.callback(
        Output("file-content-container", "children", allow_duplicate=True),
        [Input("confirm-delete-file", "n_clicks")],
        [State("delete-file-data", "data")],
        prevent_initial_call=True
    )
    def delete_source_file(n_clicks, delete_data_json):
        if not n_clicks or not delete_data_json:
            return dash.no_update
        
        try:
            # Decodificar los datos de eliminación
            data = json.loads(delete_data_json)
            file_path = data.get("file_path", "")
            asset_id = data.get("asset_id", "")
            consumption_type = data.get("consumption_type", "")
            
            # Verificar si el archivo existe
            if not os.path.exists(file_path):
                return html.Div(f"El archivo no existe: {file_path}", className="alert alert-warning")
            
            # Crear una copia de seguridad antes de eliminar
            backup_path = f"{file_path}.bak"
            try:
                import shutil
                shutil.copy2(file_path, backup_path)
                debug_log(f"[INFO] Se ha creado una copia de seguridad del archivo: {backup_path}")
            except Exception as e:
                debug_log(f"[WARNING] No se pudo crear una copia de seguridad: {str(e)}")
            
            # Eliminar el archivo
            os.remove(file_path)
            debug_log(f"[INFO] Se ha eliminado el archivo: {file_path}")
            
            # Mostrar mensaje de éxito
            return html.Div([
                html.H5("Archivo eliminado correctamente"),
                html.P(f"El archivo {os.path.basename(file_path)} ha sido eliminado."),
                html.P("Se ha creado una copia de seguridad con extensión .bak"),
                html.P([
                    "Para regenerar los datos, cierre este modal y haga clic en ",
                    html.Strong("Regenerar"),
                    " en la fila correspondiente de la tabla."
                ]),
                html.Hr(),
                html.P("Información del archivo eliminado:"),
                html.Ul([
                    html.Li(f"Asset ID: {asset_id}"),
                    html.Li(f"Tipo de consumo: {consumption_type}"),
                    html.Li(f"Ruta del archivo: {file_path}"),
                    html.Li(f"Copia de seguridad: {backup_path}")
                ])
            ], className="alert alert-success")
            
        except Exception as e:
            import traceback
            error_msg = f"Error al eliminar el archivo: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div([
                html.H5("Error al eliminar el archivo"),
                html.P(error_msg),
                html.Pre(traceback.format_exc())
            ], className="alert alert-danger")

    # Función para actualizar las lecturas desde el detalle de consumo
    def update_readings_from_detail(asset_id, consumption_type):
        try:
            # Importar todas las dependencias necesarias
            import json
            import os
            import pandas as pd
            from datetime import datetime, timedelta
            from utils.api import get_daily_readings_for_tag, get_sensors_with_tags
            from utils.logging import get_logger
            from utils.auth import auth_service
            
            # Configurar logger
            logger = get_logger(__name__)
            logger.info(f"Iniciando actualización de lecturas para asset_id={asset_id}, consumption_type={consumption_type}")
            
            # Mapear el tipo de consumo a su tag correspondiente
            consumption_tag_map = {
                "Energía térmica calor": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT",
                "Energía térmica frío": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_COOLING",
                "Agua fría": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_COLD_WATER",
                "Agua caliente": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER",
                "Agua caliente sanitaria": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER",
                "Agua general": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL",
                "Energía general": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL",
                "Flujo de personas entrada": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_IN",
                "Flujo de personas salida": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_OUT"
            }
            
            # Obtener el tag correspondiente al tipo de consumo
            consumption_tag = None
            
            # Intentar coincidencia exacta
            for key, value in consumption_tag_map.items():
                if key == consumption_type:
                    consumption_tag = value
                    break
            
            # Si no hay coincidencia exacta, intentar coincidencia parcial
            if not consumption_tag:
                for key, value in consumption_tag_map.items():
                    if key in consumption_type or consumption_type in key:
                        consumption_tag = value
                        break
            
            # Si aún no hay coincidencia, usar el mapeo de ConsumptionTags
            if not consumption_tag:
                manual_mapping = {
                    "Agua caliente sanitaria": ConsumptionTags.DOMESTIC_HOT_WATER.value,
                    "Agua fría sanitaria": ConsumptionTags.DOMESTIC_COLD_WATER.value,
                    "Energía eléctrica general": ConsumptionTags.DOMESTIC_ENERGY_GENERAL.value,
                    "Agua general": ConsumptionTags.DOMESTIC_WATER_GENERAL.value,
                    "Flujo de personas (entrada)": ConsumptionTags.PEOPLE_FLOW_IN.value,
                    "Flujo de personas (salida)": ConsumptionTags.PEOPLE_FLOW_OUT.value,
                    "Energía térmica (frío)": ConsumptionTags.THERMAL_ENERGY_COOLING.value,
                    "Energía térmica (calor)": ConsumptionTags.THERMAL_ENERGY_HEAT.value
                }
                consumption_tag = manual_mapping.get(consumption_type)
            
            if not consumption_tag:
                return html.Div([
                    html.H5("Tipo de consumo no reconocido"),
                    html.P(f"No se pudo mapear el tipo de consumo: '{consumption_type}' a un tag de consumo."),
                    html.P("Tipos de consumo reconocidos:"),
                    html.Ul([html.Li(key) for key in consumption_tag_map.keys()]),
                    html.Hr(),
                    html.P("Por favor, contacte con el administrador del sistema para añadir este tipo de consumo al mapeo.")
                ], className="alert alert-warning")
            
            # Buscar el proyecto al que pertenece el asset
            # Primero, buscar en todas las carpetas de proyectos
            analyzed_data_folder = os.path.join("data", "projects")
            if not os.path.exists(analyzed_data_folder):
                os.makedirs(analyzed_data_folder, exist_ok=True)
                return html.Div([
                    html.H5("Carpeta de proyectos no encontrada"),
                    html.P(f"Se ha creado la carpeta de proyectos: {analyzed_data_folder}"),
                    html.P("Por favor, seleccione un proyecto en el filtro principal y actualice las lecturas desde allí.")
                ], className="alert alert-warning")
            
            # Buscar el proyecto que contiene el asset
            project_id = None
            for folder_name in os.listdir(analyzed_data_folder):
                folder_path = os.path.join(analyzed_data_folder, folder_name)
                if os.path.isdir(folder_path):
                    # Buscar archivos que contengan el asset_id
                    for filename in os.listdir(folder_path):
                        if f"daily_readings_{asset_id}_" in filename:
                            project_id = folder_name
                            break
                    if project_id:
                        break
            
            if not project_id:
                # Si no se encuentra el proyecto, usar el primer proyecto disponible
                projects = [folder for folder in os.listdir(analyzed_data_folder) 
                           if os.path.isdir(os.path.join(analyzed_data_folder, folder))]
                if projects:
                    project_id = projects[0]
                else:
                    return html.Div([
                        html.H5("No se encontraron proyectos"),
                        html.P("No se encontraron carpetas de proyectos para actualizar las lecturas."),
                        html.P("Por favor, seleccione un proyecto en el filtro principal y actualice las lecturas desde allí.")
                    ], className="alert alert-warning")
            
            # Obtener el token JWT si está disponible
            token = None
            try:
                token = auth_service.get_token()
                logger.info(f"Token JWT obtenido: {token[:10]}..." if token else "No se pudo obtener el token JWT")
            except Exception as e:
                logger.error(f"Error al obtener el token JWT: {str(e)}")
                # Intentar obtener el token de otra forma si es necesario
                try:
                    # Intentar obtener el token desde el servicio de autenticación directamente
                    from utils.auth import AuthService
                    auth_service_instance = AuthService()
                    token = auth_service_instance.get_token()
                    logger.info(f"Token JWT obtenido desde AuthService: {token[:10]}..." if token else "No se pudo obtener el token JWT desde AuthService")
                except Exception as e2:
                    logger.error(f"Error al obtener el token JWT desde AuthService: {str(e2)}")
                    # No hay más opciones para obtener el token
            
            # Carpeta del proyecto
            project_folder = os.path.join(analyzed_data_folder, project_id)
            
            # Mostrar mensaje de progreso
            progress_message = html.Div([
                html.H5("Actualizando lecturas..."),
                html.P(f"Asset ID: {asset_id}"),
                html.P(f"Tipo de consumo: {consumption_type}"),
                html.P(f"Tag: {consumption_tag}"),
                html.P(f"Proyecto: {project_id}"),
                html.Hr(),
                dbc.Spinner(size="sm", color="primary", type="grow"),
                html.P("Este proceso puede tardar unos minutos. Por favor, espere...")
            ], className="alert alert-info")
            
            # Llamar a la función para obtener las lecturas diarias
            try:
                debug_log(f"[INFO] Llamando a get_daily_readings_for_tag para asset_id={asset_id}, tag={consumption_tag}, project_folder={project_folder}")
                logger.info(f"Llamando a get_daily_readings_for_tag para asset_id={asset_id}, tag={consumption_tag}, project_folder={project_folder}")
                
                # Verificar que todos los parámetros son válidos
                if not asset_id:
                    raise ValueError("El asset_id no puede estar vacío")
                if not consumption_tag:
                    raise ValueError("El tag de consumo no puede estar vacío")
                if not project_folder:
                    raise ValueError("La carpeta del proyecto no puede estar vacía")
                
                # Verificar que la carpeta del proyecto existe
                if not os.path.exists(project_folder):
                    os.makedirs(project_folder, exist_ok=True)
                    logger.info(f"Se ha creado la carpeta del proyecto: {project_folder}")
                
                # Importar explícitamente la función para asegurar que se está utilizando la correcta
                from utils.api import get_daily_readings_for_tag
                
                # Mostrar los parámetros exactos que se están pasando
                debug_log(f"[DEBUG] Parámetros para get_daily_readings_for_tag: asset_id='{asset_id}', tag_name='{consumption_tag}', project_folder='{project_folder}', token='{token[:10]}...' if token else 'None'")
                logger.info(f"Parámetros para get_daily_readings_for_tag: asset_id='{asset_id}', tag_name='{consumption_tag}', project_folder='{project_folder}', token='{token[:10]}...' if token else 'None'")
                
                # Llamar a la función con los parámetros correctos
                updated_data = get_daily_readings_for_tag(asset_id, consumption_tag, project_folder, token)
                
                # Mostrar el resultado exacto
                if updated_data is not None:
                    debug_log(f"[DEBUG] get_daily_readings_for_tag devolvió un DataFrame con {len(updated_data)} filas")
                    logger.info(f"get_daily_readings_for_tag devolvió un DataFrame con {len(updated_data)} filas")
                    # Mostrar las primeras filas para depuración
                    debug_log(f"[DEBUG] Primeras filas del DataFrame: {updated_data.head().to_dict()}")
                    logger.info(f"Primeras filas del DataFrame: {updated_data.head().to_dict()}")
                else:
                    debug_log("[DEBUG] get_daily_readings_for_tag devolvió None")
                    logger.warning("get_daily_readings_for_tag devolvió None")

                debug_log(f"[INFO] Resultado de get_daily_readings_for_tag: {'Datos actualizados' if updated_data is not None else 'Sin datos'}")
                
                # Verificar si se actualizaron los datos
                if updated_data is not None:
                    # Verificar si el archivo se creó correctamente
                    file_name = f"daily_readings_{asset_id}_{consumption_tag}.csv"
                    file_path = os.path.join(project_folder, file_name)
                    if os.path.exists(file_path):
                        logger.info(f"Archivo creado/actualizado correctamente: {file_path}")
                        # Verificar el contenido del archivo
                        try:
                            df = pd.read_csv(file_path)
                            logger.info(f"El archivo contiene {len(df)} registros")
                            # Mostrar las primeras filas para depuración
                            debug_log(f"[DEBUG] Primeras filas del archivo CSV: {df.head().to_dict()}")
                            logger.info(f"Primeras filas del archivo CSV: {df.head().to_dict()}")
                            
                            # Verificar si hay registros para el mes actual
                            current_month = datetime.now().strftime("%Y-%m")
                            df['date'] = pd.to_datetime(df['date'])
                            current_month_data = df[df['date'].dt.strftime("%Y-%m") == current_month]
                            logger.info(f"Registros para el mes actual ({current_month}): {len(current_month_data)}")
                        except Exception as e:
                            logger.error(f"Error al leer el archivo creado: {str(e)}")
                    else:
                        logger.error(f"El archivo no se creó correctamente: {file_path}")
                        
                    return html.Div([
                        html.H5("Lecturas actualizadas correctamente"),
                        html.P(f"Asset ID: {asset_id}"),
                        html.P(f"Tipo de consumo: {consumption_type}"),
                        html.P(f"Tag: {consumption_tag}"),
                        html.P(f"Proyecto: {project_id}"),
                        html.Hr(),
                        html.P("Las lecturas se han actualizado correctamente."),
                        html.P("Para ver los cambios, cierre este modal y haga clic en 'Visualizar Consumos' en la página principal."),
                        html.Div([
                            dbc.Button(
                                "Refrescar datos", 
                                id="refresh-data-btn", 
                                color="primary", 
                                className="mt-3",
                                n_clicks=0
                            ),
                            dcc.Store(
                                id="refresh-data-store",
                                data=json.dumps({
                                    "asset_id": asset_id,
                                    "consumption_type": consumption_type,
                                    "project_id": project_id,
                                    "tag": consumption_tag
                                })
                            )
                        ])
                    ], className="alert alert-success")
                else:
                    logger.error(f"No se pudieron actualizar las lecturas para asset_id={asset_id}, tag={consumption_tag}")
                    return html.Div([
                        html.H5("No se pudieron actualizar las lecturas"),
                        html.P(f"Asset ID: {asset_id}"),
                        html.P(f"Tipo de consumo: {consumption_type}"),
                        html.P(f"Tag: {consumption_tag}"),
                        html.P(f"Proyecto: {project_id}"),
                        html.Hr(),
                        html.P("No se pudieron obtener nuevas lecturas. Consulte los logs para más detalles.")
                    ], className="alert alert-warning")
            except Exception as e:
                import traceback
                error_msg = f"Error al actualizar lecturas: {str(e)}"
                debug_log(f"[ERROR] {error_msg}")
                debug_log(traceback.format_exc())
                return html.Div([
                    html.H5("Error al actualizar lecturas"),
                    html.P(f"Asset ID: {asset_id}"),
                    html.P(f"Tipo de consumo: {consumption_type}"),
                    html.P(f"Tag: {consumption_tag}"),
                    html.P(f"Proyecto: {project_id}"),
                    html.Hr(),
                    html.P(error_msg),
                    html.Pre(traceback.format_exc())
                ], className="alert alert-danger")
        
        except Exception as e:
            import traceback
            error_msg = f"Error al preparar la actualización de lecturas: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div([
                html.H5("Error al preparar la actualización de lecturas"),
                html.P(error_msg),
                html.Pre(traceback.format_exc())
            ], className="alert alert-danger")

    # Callback para refrescar los datos después de actualizar las lecturas
    @app.callback(
        Output("metrics-data-store", "data", allow_duplicate=True),
        [Input("refresh-data-btn", "n_clicks")],
        [State("refresh-data-store", "data"),
         State("metrics-data-store", "data")],
        prevent_initial_call=True
    )
    def refresh_data_after_update(n_clicks, refresh_data_json, current_data):
        if not n_clicks or not refresh_data_json:
            return dash.no_update
        
        try:
            # Importar las funciones necesarias
            import json
            import pandas as pd
            import os
            from io import StringIO
            
            # Decodificar los datos de refresco
            refresh_data = json.loads(refresh_data_json)
            asset_id = refresh_data.get("asset_id")
            consumption_type = refresh_data.get("consumption_type")
            project_id = refresh_data.get("project_id")
            tag = refresh_data.get("tag")
            
            debug_log(f"[INFO] Refrescando datos para asset {asset_id}, tipo de consumo {consumption_type}")
            
            # Si no hay datos actuales, no podemos refrescar
            if not current_data:
                debug_log(f"[WARNING] No hay datos actuales para refrescar")
                return dash.no_update
            
            # Convertir los datos actuales a DataFrame
            try:
                # Intentar el formato estándar primero
                df = pd.read_json(StringIO(current_data), orient='split')
            except Exception:
                # Si falla, intentar con el formato alternativo
                try:
                    data_dict = json.loads(current_data)
                    df = pd.DataFrame(data_dict['data'], columns=data_dict['columns'])
                except Exception as e:
                    debug_log(f"[ERROR] Error al convertir JSON a DataFrame: {str(e)}")
                    return dash.no_update
            
            # Actualizar los datos para el asset y tipo de consumo específicos
            # Esto es solo un ejemplo, en realidad necesitaríamos cargar los datos actualizados
            # desde el archivo CSV y actualizar el DataFrame
            
            # Actualizar los datos para el asset y tipo de consumo específicos
            # Cargar los datos actualizados desde el archivo CSV
            try:
                # Ruta al archivo CSV
                file_name = f"daily_readings_{asset_id}_{tag}.csv"
                file_path = os.path.join("data", "projects", project_id, file_name)
                
                if os.path.exists(file_path):
                    # Cargar los datos actualizados
                    updated_csv_data = pd.read_csv(file_path)
                    
                    # Convertir la columna 'date' a datetime
                    updated_csv_data["date"] = pd.to_datetime(updated_csv_data["date"])
                    
                    # Filtrar las filas del DataFrame original que no corresponden al asset_id
                    df_filtered = df[df['asset_id'] != asset_id]
                    
                    # Preparar los datos del CSV para combinarlos con el DataFrame
                    csv_for_df = updated_csv_data.copy()
                    csv_for_df['asset_id'] = asset_id
                    
                    # Mapear el tipo de consumo
                    reverse_mapping = {v: k for k, v in CONSUMPTION_TAGS_MAPPING.items()}
                    display_consumption_type = reverse_mapping.get(tag, consumption_type)
                    csv_for_df['consumption_type'] = display_consumption_type
                    
                    # Renombrar columnas para que coincidan con el DataFrame
                    csv_for_df = csv_for_df.rename(columns={'value': 'consumption'})
                    
                    # Asegurarse de que todas las columnas necesarias estén presentes
                    required_columns = set(df.columns)
                    for col in required_columns:
                        if col not in csv_for_df.columns:
                            if col == 'year_month':
                                csv_for_df['year_month'] = csv_for_df['date'].dt.strftime('%Y-%m')
                            else:
                                csv_for_df[col] = None
                    
                    # Seleccionar solo las columnas que están en el DataFrame original
                    csv_for_df = csv_for_df[df.columns]
                    
                    # Combinar los DataFrames
                    combined_df = pd.concat([df_filtered, csv_for_df])
                    
                    # Ordenar por fecha
                    combined_df = combined_df.sort_values(by=['date'])
                    
                    # Reemplazar el DataFrame original
                    df = combined_df
                    
                    debug_log(f"[INFO] Datos actualizados correctamente desde el archivo CSV: {file_path}")
                else:
                    debug_log(f"[WARNING] No se encontró el archivo CSV: {file_path}")
            except Exception as e:
                import traceback
                error_msg = f"Error al cargar datos desde CSV: {str(e)}"
                debug_log(f"[ERROR] {error_msg}")
                debug_log(traceback.format_exc())
            
            # Convertir el DataFrame actualizado de nuevo a JSON
            updated_json_data = df.to_json(orient='split', date_format='iso')
            
            return updated_json_data
        
        except Exception as e:
            import traceback
            error_msg = f"Error al refrescar datos: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return dash.no_update

    # Callback para actualizar lecturas de un asset específico cuando se confirma
    @app.callback(
        [Output("update-asset-readings-status", "children"),
         Output("metrics-data-store", "data", allow_duplicate=True)],
        [Input("confirm-update-asset-readings", "n_clicks")],
        [State("update-asset-readings-data", "data"),
         State("metrics-data-store", "data")],
        prevent_initial_call=True
    )
    def update_asset_readings(n_clicks, update_data_json, current_data):
        if not n_clicks or not update_data_json:
            return None, dash.no_update
        
        try:
            # Importar json al principio de la función
            import json
            
            # Cargar los datos de actualización
            update_data = json.loads(update_data_json)
            asset_id = update_data.get("asset_id")
            tag = update_data.get("tag")
            project_id = update_data.get("project_id")
            token_data = update_data.get("token")
            
            if not asset_id or not tag or not project_id:
                return html.Div("Error: Faltan datos necesarios para la actualización.", className="alert alert-danger"), dash.no_update
            
            # Obtener el token JWT si está disponible
            token = None
            if token_data and "token" in token_data:
                token = token_data["token"]
            
            # Asegurar que existe la carpeta del proyecto
            from utils.api import ensure_project_folder_exists, get_daily_readings_for_tag
            project_folder = ensure_project_folder_exists(project_id)
            
            # Actualizar las lecturas para el asset y tag específicos
            try:
                debug_log(f"[DEBUG] update_asset_readings - Actualizando lecturas para asset {asset_id}, tag {tag}")
                get_daily_readings_for_tag(asset_id, tag, project_folder, token)
                
                # Mostrar mensaje de éxito
                success_message = html.Div([
                    html.P(f"Lecturas actualizadas con éxito para el asset {asset_id}.", className="text-success"),
                    html.P("Haga clic en 'Visualizar Consumos' para ver los datos actualizados.", className="text-info")
                ])
                
                return success_message, current_data
            except Exception as e:
                error_message = html.Div(f"Error al actualizar lecturas: {str(e)}", className="alert alert-danger")
                return error_message, dash.no_update
                
        except Exception as e:
            import traceback
            error_msg = f"Error al procesar la solicitud: {str(e)}"
            debug_log(f"[ERROR] {error_msg}")
            debug_log(traceback.format_exc())
            return html.Div(error_msg, className="alert alert-danger"), dash.no_update

    # Callback para cerrar el modal de regeneración
    @app.callback(
        Output('regenerate-readings-modal', 'is_open', allow_duplicate=True),
        [Input('cancel-regenerate-readings', 'n_clicks'),
         Input('close-regenerate-readings-modal', 'n_clicks')],
        [State('regenerate-readings-modal', 'is_open')],
        prevent_initial_call=True
    )
    def close_regenerate_readings_modal(cancel_clicks, close_clicks, is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            return is_open
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger_id in ["cancel-regenerate-readings", "close-regenerate-readings-modal"] and is_open:
            return False
        
        return is_open

    # Callback para refrescar los datos después de regenerar
    @app.callback(
        Output("metrics-analyze-button", "n_clicks"),
        [Input("refresh-after-regenerate", "n_clicks")],
        prevent_initial_call=True
    )
    def refresh_after_regenerate(n_clicks):
        if n_clicks:
            # Simular un clic en el botón "Visualizar Consumos"
            return 1
        return dash.no_update
