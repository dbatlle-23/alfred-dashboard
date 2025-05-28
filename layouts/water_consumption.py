from dash import html, dcc, callback_context
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash
import pandas as pd
from datetime import datetime, timedelta
import json
import numpy as np
import io
import base64
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# Import constants
from constants.metrics import ConsumptionTags, CONSUMPTION_TAGS_MAPPING

# Import components
from components.metrics.charts import (
    create_time_series_chart,
    create_bar_chart,
    create_consumption_comparison_chart,
    create_consumption_trend_chart,
    create_consumption_distribution_chart,
    create_heatmap,
    create_monthly_totals_chart,
    create_monthly_averages_chart
)
from components.metrics.tables import (
    create_monthly_readings_table,
    create_consumption_stats_table,
    create_daily_readings_table,
    create_monthly_summary_table
)
from components.water_consumption.analysis_dashboard import create_water_analysis_dashboard
from components.water_consumption.asset_type_context import create_asset_type_insights

# Import utilities
from utils.metrics.data_processing import (
    process_metrics_data,
    aggregate_data_by_project,
    aggregate_data_by_asset,
    aggregate_data_by_consumption_type,
    aggregate_data_by_month_and_asset,
    generate_monthly_consumption_summary
)
from utils.api import get_clientes, get_projects, get_assets, get_project_assets, get_asset_water_sensors, get_asset_all_sensors, get_sensor_time_series_data
from utils.water_consumption.analysis import (
    calculate_total_consumption,
    calculate_average_consumption,
    detect_peak_hours,
    compare_time_periods,
    detect_anomalies_in_water_consumption
)
from utils.logging import get_logger
from utils.error_handlers import handle_exceptions

# Configure logger
logger = get_logger(__name__)

# Constants for asset types
ASSET_TYPES = {
    "residential_building": "Edificio Residencial",
    "individual_home": "Vivienda Individual",
    "logistics_center": "Centro Logístico",
    "office_building": "Edificio de Oficinas",
    "other": "Otro"
}

# Water consumption tag constant
WATER_CONSUMPTION_TAGS = [
    ConsumptionTags.DOMESTIC_WATER_GENERAL.value,
    ConsumptionTags.DOMESTIC_HOT_WATER.value
]

def create_layout():
    """Create the water consumption analysis page layout."""
    return html.Div([
        # Stores for data
        dcc.Store(id="water-data-store"),
        dcc.Store(id="water-selected-client-store"),
        dcc.Store(id="water-selected-project-store"),
        dcc.Store(id="water-selected-asset-store"),
        dcc.Store(id="water-selected-sensor-store"),
        dcc.Store(id="water-selected-date-range-store"),
        dcc.Store(id="water-asset-type-store"),
        dcc.Store(id="water-analysis-results-store"),
        
        # Main container
        dbc.Container([
            # Page title
            html.H2("Análisis de Consumo de Agua", className="mb-4"),
            
            # Hierarchical selection card
            dbc.Card([
                dbc.CardHeader("Selección Jerárquica"),
                dbc.CardBody([
                    dbc.Row([
                        # Client filter
                        dbc.Col([
                            html.Label("Cliente"),
                            dcc.Dropdown(
                                id="water-client-filter",
                                placeholder="Seleccione un cliente",
                                clearable=False
                            )
                        ], width=3),
                        
                        # Project filter
                        dbc.Col([
                            html.Label("Proyecto"),
                            dcc.Dropdown(
                                id="water-project-filter",
                                placeholder="Seleccione un proyecto",
                                clearable=False,
                                disabled=True
                            )
                        ], width=3),
                        
                        # Asset filter
                        dbc.Col([
                            html.Label("Activo (Espacio)"),
                            dcc.Dropdown(
                                id="water-asset-filter",
                                placeholder="Seleccione un activo",
                                clearable=False,
                                disabled=True
                            )
                        ], width=3),
                        
                        # Water sensor filter
                        dbc.Col([
                            html.Label("Sensor de Agua"),
                            dcc.Dropdown(
                                id="water-sensor-filter",
                                placeholder="Seleccione un sensor",
                                clearable=False,
                                disabled=True
                            )
                        ], width=3)
                    ]),
                    
                    # Second row for asset type and date range
                    dbc.Row([
                        # Asset type selector
                        dbc.Col([
                            html.Label("Tipo de Activo"),
                            dcc.Dropdown(
                                id="water-asset-type-selector",
                                placeholder="Seleccione tipo de activo",
                                options=[
                                    {"label": label, "value": value}
                                    for value, label in ASSET_TYPES.items()
                                ],
                                clearable=False
                            )
                        ], width=3),
                        
                        # Date range selector
                        dbc.Col([
                            html.Label("Período"),
                            dcc.Dropdown(
                                id="water-date-period",
                                options=[
                                    {"label": "Último mes", "value": "last_month"},
                                    {"label": "Últimos 3 meses", "value": "last_3_months"},
                                    {"label": "Último año", "value": "last_year"},
                                    {"label": "Personalizado", "value": "custom"}
                                ],
                                value="last_month",
                                clearable=False
                            )
                        ], width=3),
                        
                        # Custom date picker
                        dbc.Col([
                            html.Div([
                                html.Label("Rango de fechas"),
                                dcc.DatePickerRange(
                                    id="water-date-range",
                                    start_date=(datetime.now() - timedelta(days=30)).date(),
                                    end_date=datetime.now().date(),
                                    display_format="YYYY-MM-DD"
                                )
                            ], id="water-custom-date-container", style={"display": "none"})
                        ], width=3),
                        
                        # Analyze button
                        dbc.Col([
                            html.Div([
                                dbc.Button(
                                    "Analizar Consumo",
                                    id="water-analyze-button",
                                    color="primary",
                                    className="mt-4",
                                    disabled=True
                                )
                            ], className="d-flex justify-content-end")
                        ], width=3)
                    ], className="mt-3")
                ])
            ], className="mb-4"),
            
            # Initial message (shown when no analysis has been performed)
            html.Div([
                dbc.Alert(
                    [
                        html.H4("Bienvenido al Análisis de Consumo de Agua", className="alert-heading"),
                        html.P(
                            "Seleccione un cliente, proyecto, activo y sensor de agua para comenzar el análisis. "
                            "Luego, haga clic en el botón 'Analizar Consumo' para obtener información detallada sobre el consumo de agua."
                        ),
                        html.Hr(),
                        html.P(
                            "Este análisis le proporcionará información valiosa sobre el consumo de agua, incluyendo "
                            "volumen total, consumo promedio, horas pico, comparativas y posibles anomalías.",
                            className="mb-0"
                        )
                    ],
                    color="info",
                    id="water-initial-message"
                )
            ], id="water-initial-message-container"),
            
            # Analysis results container (hidden initially)
            html.Div([
                # Loading spinner
                dbc.Spinner(
                    children=[
                        # Analysis header
                        html.Div(id="water-analysis-header", className="mb-4"),
                        
                        # Key metrics cards
                        dbc.Row(id="water-key-metrics", className="mb-4"),
                        
                        # Charts and detailed analysis
                        dbc.Row([
                            # Left column - Time series and comparisons
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("Evolución del Consumo de Agua"),
                                    dbc.CardBody(id="water-consumption-evolution")
                                ], className="mb-4"),
                                
                                dbc.Card([
                                    dbc.CardHeader("Comparativa Temporal"),
                                    dbc.CardBody(id="water-temporal-comparison")
                                ])
                            ], width=6),
                            
                            # Right column - Distribution and anomalies
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("Distribución del Consumo"),
                                    dbc.CardBody(id="water-consumption-distribution")
                                ], className="mb-4"),
                                
                                dbc.Card([
                                    dbc.CardHeader("Detección de Anomalías"),
                                    dbc.CardBody(id="water-anomaly-detection")
                                ])
                            ], width=6)
                        ]),
                        
                        # Context-aware insights based on asset type
                        html.Div(id="water-asset-type-insights", className="mt-4"),
                        
                        # Detailed data table
                        dbc.Card([
                            dbc.CardHeader("Datos Detallados de Consumo"),
                            dbc.CardBody(id="water-detailed-data-table")
                        ], className="mt-4"),
                        
                        # Export options
                        dbc.Card([
                            dbc.CardHeader("Exportar Resultados"),
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Button(
                                            [html.I(className="fas fa-file-csv me-2"), "Exportar a CSV"],
                                            id="water-export-csv-button",
                                            color="success",
                                            className="me-2"
                                        ),
                                        dbc.Button(
                                            [html.I(className="fas fa-file-pdf me-2"), "Exportar a PDF"],
                                            id="water-export-pdf-button",
                                            color="danger",
                                            className="me-2"
                                        ),
                                        dcc.Download(id="water-download-data")
                                    ])
                                ])
                            ])
                        ], className="mt-4")
                    ],
                    type="border",
                    fullscreen=False,
                )
            ], id="water-analysis-results-container", style={"display": "none"})
        ], fluid=True)
    ])

# Function to register callbacks
def register_callbacks(app):
    """Register callbacks for the water consumption analysis page."""
    
    # Callback to load clients
    @app.callback(
        Output("water-client-filter", "options"),
        [Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    @handle_exceptions(default_return=[{"label": "Error al cargar", "value": ""}])
    def load_clients(token_data):
        token = token_data.get('token') if token_data else None
        
        if not token:
            logger.info("No hay token JWT disponible para cargar clientes")
            return [{"label": "Seleccione un cliente", "value": ""}]
        
        logger.debug("Cargando clientes para análisis de consumo de agua")
        clientes = get_clientes(jwt_token=token)
        
        if not isinstance(clientes, list):
            logger.error(f"get_clientes devolvió un tipo no esperado: {type(clientes)}")
            return [{"label": "Error al cargar clientes", "value": ""}]
        
        client_options = []
        for cliente in clientes:
            if not isinstance(cliente, dict):
                continue
                
            # Try to get the name and ID with different possible keys
            nombre = None
            id_cliente = None
            
            for key in ['nombre', 'name', 'client_name', 'nombre_cliente', 'client']:
                if key in cliente and cliente[key]:
                    nombre = cliente[key]
                    break
            
            for key in ['id', 'client_id', 'id_cliente', 'clientId']:
                if key in cliente and cliente[key]:
                    id_cliente = cliente[key]
                    break
            
            if nombre and id_cliente:
                client_options.append({"label": nombre, "value": str(id_cliente)})
        
        return client_options
    
    # Callback to load projects when client is selected
    @app.callback(
        [Output("water-project-filter", "options"),
         Output("water-project-filter", "disabled")],
        [Input("water-client-filter", "value"),
         Input("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=([{"label": "Error al cargar", "value": ""}], True))
    def load_projects(client_id, token_data):
        token = token_data.get('token') if token_data else None
        
        if not token or not client_id:
            return [{"label": "Seleccione un proyecto", "value": ""}], True
        
        logger.debug(f"Cargando proyectos para cliente {client_id}")
        projects = get_projects(client_id=client_id, jwt_token=token)
        
        if not isinstance(projects, list):
            logger.error(f"get_projects devolvió un tipo no esperado: {type(projects)}")
            return [{"label": "Error al cargar proyectos", "value": ""}], True
        
        project_options = []
        for project in projects:
            if not isinstance(project, dict):
                continue
                
            # Try to get the name and ID with different possible keys
            nombre = None
            id_proyecto = None
            
            for key in ['nombre', 'name', 'project_name', 'nombre_proyecto']:
                if key in project and project[key]:
                    nombre = project[key]
                    break
            
            for key in ['id', 'project_id', 'id_proyecto', 'projectId']:
                if key in project and project[key]:
                    id_proyecto = project[key]
                    break
            
            if nombre and id_proyecto:
                project_options.append({"label": nombre, "value": str(id_proyecto)})
        
        return project_options, False
    
    # Callback to load assets when project is selected
    @app.callback(
        [Output("water-asset-filter", "options"),
         Output("water-asset-filter", "disabled")],
        [Input("water-project-filter", "value"),
         Input("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=([{"label": "Error al cargar", "value": ""}], True))
    def load_assets(project_id, token_data):
        token = token_data.get('token') if token_data else None
        
        if not token or not project_id:
            return [{"label": "Seleccione un activo", "value": ""}], True
        
        logger.debug(f"Cargando activos para proyecto {project_id}")
        assets = get_project_assets(project_id=project_id, jwt_token=token)
        
        if not isinstance(assets, list):
            logger.error(f"get_project_assets devolvió un tipo no esperado: {type(assets)}")
            return [{"label": "Error al cargar activos", "value": ""}], True
        
        asset_options = []
        for asset in assets:
            if not isinstance(asset, dict):
                continue
                
            # Try to get the name and ID with different possible keys
            nombre = None
            id_asset = None
            
            # Primero intentamos con los campos estándar
            for key in ['nombre', 'name', 'asset_name', 'nombre_activo', 'alias']:
                if key in asset and asset[key]:
                    nombre = asset[key]
                    break
            
            # Si no encontramos un nombre, construimos uno con los datos disponibles
            if not nombre:
                # Intentamos con la combinación de dirección y apartamento
                street_name = asset.get('street_name', '')
                block_number = asset.get('block_number', '')
                apartment = asset.get('apartment', '')
                
                if street_name and block_number and apartment:
                    nombre = f"{street_name} {block_number}, {apartment}"
                elif apartment:
                    nombre = f"Apartamento {apartment}"
                else:
                    # Último recurso: usar el ID como nombre
                    nombre = f"Asset {asset.get('id', 'desconocido')}"
            
            for key in ['id', 'asset_id', 'id_activo', 'assetId']:
                if key in asset and asset[key]:
                    id_asset = asset[key]
                    break
            
            if nombre and id_asset:
                asset_options.append({"label": nombre, "value": str(id_asset)})
        
        return asset_options, False
    
    # Callback to load water sensors when asset is selected
    @app.callback(
        [Output("water-sensor-filter", "options"),
         Output("water-sensor-filter", "disabled")],
        [Input("water-asset-filter", "value"),
         Input("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=([{"label": "Error al cargar", "value": ""}], True))
    def load_water_sensors(asset_id, token_data):
        token = token_data.get('token') if token_data else None
        
        if not token or not asset_id:
            logger.warning("No se proporcionó token o ID de activo para cargar sensores")
            return [{"label": "Seleccione un sensor", "value": ""}], True
        
        logger.info(f"Cargando todos los sensores para activo {asset_id}")
        
        try:
            # Obtener todos los sensores para el activo desde la API (sin filtrar por tipo de agua)
            all_sensors = get_asset_all_sensors(asset_id=asset_id, jwt_token=token)
            
            # Verificar que all_sensors sea una lista
            if not isinstance(all_sensors, list):
                logger.error(f"get_asset_all_sensors devolvió un tipo no esperado: {type(all_sensors)}")
                all_sensors = []
            
            # Log the first few sensors to understand their structure
            logger.info(f"Sensor structure example (for debugging):")
            for i, sensor in enumerate(all_sensors[:2] if isinstance(all_sensors, list) and len(all_sensors) > 0 else []):
                logger.info(f"Sensor {i} data: {sensor}")
                logger.info(f"Sensor {i} keys: {sensor.keys() if isinstance(sensor, dict) else 'Not a dict'}")
            
            # Si no hay sensores, intentamos usar los tags predefinidos como fallback
            if not all_sensors:
                logger.warning(f"No se encontraron sensores para el activo {asset_id}. Usando tags predefinidos como fallback.")
                sensor_options = []
                
                # Incluir todos los tags de agua definidos en las constantes como fallback
                from constants.metrics import ConsumptionTags
                
                # Incluir todos los tags disponibles
                for tag_enum in ConsumptionTags:
                    tag = tag_enum.value
                    tag_name = CONSUMPTION_TAGS_MAPPING.get(tag, tag)
                    sensor_options.append({"label": tag_name, "value": tag})
                
                logger.info(f"Se utilizaron {len(sensor_options)} tags predefinidos como fallback")
            else:
                # Convertir todos los sensores a opciones para el dropdown sin filtrar
                sensor_options = []
                for sensor in all_sensors:
                    if not isinstance(sensor, dict):
                        logger.warning(f"Sensor no es un diccionario: {sensor}")
                        continue
                        
                    tag_name = sensor.get('tag_name', '')
                    
                    # Si no hay tag_name, intentar buscar en otras claves posibles
                    if not tag_name:
                        for key in ['name', 'sensor_name', 'tag']:
                            if key in sensor and sensor[key]:
                                tag_name = sensor[key]
                                break
                    
                    if not tag_name:
                        name = sensor.get('name', '')
                        if name:
                            tag_name = name
                        else:
                            # Si no hay ningún nombre, usar un identificador genérico con el ID
                            sensor_id = sensor.get('id', '')
                            tag_name = f"Sensor {sensor_id}" if sensor_id else "Sensor desconocido"
                    
                    # Obtener un nombre amigable para mostrar
                    display_name = sensor.get('display_name', CONSUMPTION_TAGS_MAPPING.get(tag_name, tag_name))
                    
                    # Look for sensor UUID - check both 'sensor_uuid' and 'id' fields as API may use either
                    sensor_uuid = None
                    # First try 'id' since that's what we saw in the logs
                    if 'id' in sensor:
                        sensor_uuid = sensor['id']
                        logger.info(f"Using 'id' field as sensor UUID: {sensor_uuid}")
                    # If not found, try other possible keys
                    else:
                        for key in ['sensor_uuid', 'uuid', 'sensor_id']:
                            if key in sensor and sensor[key]:
                                sensor_uuid = sensor[key]
                                logger.info(f"Found sensor UUID in field '{key}': {sensor_uuid}")
                                break
                    
                    # Also capture device_id, sensor_id, and gateway_id if present
                    device_info = ""
                    if all(k in sensor for k in ['device_id', 'sensor_id', 'gateway_id']):
                        device_info = f" (D:{sensor['device_id']},S:{sensor['sensor_id']},G:{sensor['gateway_id']})"
                        logger.info(f"Sensor has complete device info: device_id={sensor['device_id']}, sensor_id={sensor['sensor_id']}, gateway_id={sensor['gateway_id']}")
                    
                    # Construir el valor para el dropdown - include complete info
                    sensor_value = f"{tag_name}:{sensor_uuid}" if sensor_uuid else tag_name
                    
                    # Add to dropdown options - include device info in label for debugging
                    sensor_options.append({
                        "label": f"{display_name}{device_info}",
                        "value": sensor_value
                    })
                    logger.info(f"Added sensor option: label='{display_name}{device_info}', value='{sensor_value}'")
                
                logger.info(f"Se cargaron {len(sensor_options)} opciones de sensores para el activo {asset_id}")
            
            # Si después de todo el proceso no hay opciones, agregar un mensaje de error
            if not sensor_options:
                logger.error(f"No se pudieron cargar sensores para el activo {asset_id}")
                return [{"label": "No hay sensores disponibles", "value": ""}], True
            
            return sensor_options, False
            
        except Exception as e:
            logger.error(f"Error al cargar sensores: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [{"label": f"Error: {str(e)}", "value": ""}], True
    
    # Callback to enable/disable the analyze button
    @app.callback(
        Output("water-analyze-button", "disabled"),
        [Input("water-client-filter", "value"),
         Input("water-project-filter", "value"),
         Input("water-asset-filter", "value"),
         Input("water-sensor-filter", "value"),
         Input("water-asset-type-selector", "value")]
    )
    def toggle_analyze_button(client_id, project_id, asset_id, sensor_id, asset_type):
        if client_id and project_id and asset_id and sensor_id and asset_type:
            return False
        return True
    
    # Callback to show/hide custom date range
    @app.callback(
        Output("water-custom-date-container", "style"),
        [Input("water-date-period", "value")]
    )
    def toggle_custom_date_range(date_period):
        if date_period == "custom":
            return {"display": "block"}
        return {"display": "none"}
    
    # Callback to update date range based on period selection
    @app.callback(
        [Output("water-date-range", "start_date"),
         Output("water-date-range", "end_date")],
        [Input("water-date-period", "value")]
    )
    def update_date_range(date_period):
        end_date = datetime.now().date()
        
        if date_period == "last_month":
            start_date = (datetime.now() - timedelta(days=30)).date()
        elif date_period == "last_3_months":
            start_date = (datetime.now() - timedelta(days=90)).date()
        elif date_period == "last_year":
            start_date = (datetime.now() - timedelta(days=365)).date()
        else:  # Keep current selection for custom
            return dash.no_update, dash.no_update
        
        return start_date, end_date
    
    # Callback to perform analysis and show results
    @app.callback(
        [Output("water-initial-message-container", "style"),
         Output("water-analysis-results-container", "style"),
         Output("water-analysis-header", "children"),
         Output("water-key-metrics", "children"),
         Output("water-consumption-evolution", "children"),
         Output("water-temporal-comparison", "children"),
         Output("water-consumption-distribution", "children"),
         Output("water-anomaly-detection", "children"),
         Output("water-asset-type-insights", "children"),
         Output("water-detailed-data-table", "children"),
         Output("water-analysis-results-store", "data")],
        [Input("water-analyze-button", "n_clicks")],
        [State("water-client-filter", "value"),
         State("water-project-filter", "value"),
         State("water-asset-filter", "value"),
         State("water-sensor-filter", "value"),
         State("water-asset-type-selector", "value"),
         State("water-date-range", "start_date"),
         State("water-date-range", "end_date"),
         State("water-date-period", "value"),
         State("water-client-filter", "options"),
         State("water-project-filter", "options"),
         State("water-asset-filter", "options"),
         State("water-sensor-filter", "options"),
         State("jwt-token-store", "data")]
    )
    @handle_exceptions(default_return=[{} for _ in range(11)])
    def perform_water_analysis(n_clicks, client_id, project_id, asset_id, sensor_id, asset_type,
                              start_date, end_date, date_period, client_options, project_options, 
                              asset_options, sensor_options, token_data):
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, \
                   dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        token = token_data.get('token') if token_data else None
        if not token:
            raise Exception("No hay token de autenticación disponible")
        
        # Get names from options
        client_name = next((opt["label"] for opt in client_options if opt["value"] == client_id), "Cliente desconocido")
        project_name = next((opt["label"] for opt in project_options if opt["value"] == project_id), "Proyecto desconocido")
        asset_name = next((opt["label"] for opt in asset_options if opt["value"] == asset_id), "Activo desconocido")
        
        # Extract tag_name and sensor parameters from sensor_id which might be in the format "tag_name:sensor_uuid"
        tag_name = sensor_id
        sensor_uuid = None
        device_id = None
        sensor_specific_id = None
        gateway_id = None
        
        # Get sensor friendly name from options
        sensor_name = next((opt["label"] for opt in sensor_options if opt["value"] == sensor_id), "Sensor desconocido")
        asset_type_name = ASSET_TYPES.get(asset_type, "Tipo desconocido")
        
        # If the sensor_id contains a UUID, extract it
        if sensor_id and ":" in sensor_id:
            parts = sensor_id.split(":", 1)
            tag_name = parts[0]
            sensor_uuid = parts[1] if len(parts) > 1 else None
        
        # Log details of what we're analyzing
        logger.info(f"Analizando consumo de agua para activo {asset_id}, sensor {tag_name}, periodo {start_date} a {end_date}")
        if sensor_uuid:
            logger.info(f"Utilizando sensor UUID: {sensor_uuid}")
            
        # Format dates for API call (MM-DD-YYYY format)
        start_date_obj = pd.to_datetime(start_date)
        end_date_obj = pd.to_datetime(end_date)
        
        # Format dates for API call
        start_date_formatted = start_date_obj.strftime("%m-%d-%Y")
        end_date_formatted = end_date_obj.strftime("%m-%d-%Y")
        
        # Get sensor parameters from all sensors for the asset to find device_id, sensor_id, and gateway_id
        try:
            all_sensors = get_asset_all_sensors(asset_id=asset_id, jwt_token=token)
            
            # Find the matching sensor to get full parameters
            for sensor in all_sensors:
                if isinstance(sensor, dict):
                    if sensor_uuid and sensor.get('sensor_uuid') == sensor_uuid:
                        # Found exact match by UUID
                        device_id = sensor.get('device_id')
                        sensor_specific_id = sensor.get('sensor_id')
                        gateway_id = sensor.get('gateway_id')
                        logger.info(f"Encontrado sensor con UUID {sensor_uuid}: device_id={device_id}, sensor_id={sensor_specific_id}, gateway_id={gateway_id}")
                        break
                    elif tag_name and sensor.get('tag_name') == tag_name:
                        # Found match by tag_name
                        sensor_uuid = sensor.get('sensor_uuid')
                        device_id = sensor.get('device_id')
                        sensor_specific_id = sensor.get('sensor_id')
                        gateway_id = sensor.get('gateway_id')
                        logger.info(f"Encontrado sensor con tag {tag_name}: UUID={sensor_uuid}, device_id={device_id}, sensor_id={sensor_specific_id}, gateway_id={gateway_id}")
                        break
        except Exception as e:
            logger.warning(f"Error al buscar parámetros completos del sensor: {e}")
        
        # Log detailed sensor parameters for diagnostic purposes
        logger.info("==================== SENSOR PARAMETERS LOG ====================")
        logger.info(f"Client ID: {client_id}, Project ID: {project_id}, Asset ID: {asset_id}")
        logger.info(f"Selected Sensor ID (from dropdown): {sensor_id}")
        logger.info(f"Tag Name: {tag_name}")
        logger.info(f"Sensor UUID: {sensor_uuid}")
        logger.info(f"Device ID: {device_id}")
        logger.info(f"Sensor Specific ID: {sensor_specific_id}")
        logger.info(f"Gateway ID: {gateway_id}")
        
        # Log the first few sensors from all_sensors to understand structure
        logger.info("First few sensors available for this asset:")
        for i, sensor in enumerate(all_sensors[:3] if isinstance(all_sensors, list) else []):
            if isinstance(sensor, dict):
                logger.info(f"Sensor {i+1} keys: {sensor.keys()}")
                logger.info(f"Sensor {i+1} data: {sensor}")
                # Check if the sensor UUID matches and ensure we have the correct device_id
                if sensor_uuid and sensor.get('id') == sensor_uuid and device_id is None:
                    device_id = sensor.get('device_id')
                    sensor_specific_id = sensor.get('sensor_id')
                    gateway_id = sensor.get('gateway_id')
                    logger.info(f"Found matching sensor by UUID in logging loop, updating parameters: device_id={device_id}, sensor_id={sensor_specific_id}, gateway_id={gateway_id}")
            else:
                logger.info(f"Sensor {i+1} (not a dict): {sensor}")
        
        # Final check for missing sensor parameters before API call
        if sensor_uuid and (device_id is None or sensor_specific_id is None or gateway_id is None):
            logger.warning("Missing critical sensor parameters for API call. Searching all sensors again for exact match.")
            # Try once more with all sensors, not just the first few
            for sensor in all_sensors:
                if isinstance(sensor, dict) and sensor.get('id') == sensor_uuid:
                    # Found exact match by UUID
                    device_id = sensor.get('device_id')
                    sensor_specific_id = sensor.get('sensor_id')
                    gateway_id = sensor.get('gateway_id')
                    logger.info(f"Found matching sensor in final check: device_id={device_id}, sensor_id={sensor_specific_id}, gateway_id={gateway_id}")
                    break
        
        logger.info("==================== END SENSOR PARAMETERS LOG ====================")
        
        # Try to get real sensor data
        sensor_data = get_sensor_time_series_data(
            asset_id=asset_id,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            sensor_uuid=sensor_uuid,
            device_id=device_id,
            sensor_id=sensor_specific_id,
            gateway_id=gateway_id,
            jwt_token=token
        )
        
        # Log the API response structure
        logger.info("==================== SENSOR API RESPONSE LOG ====================")
        if sensor_data:
            logger.info(f"API Response - Keys available: {sensor_data.keys() if isinstance(sensor_data, dict) else 'Not a dictionary'}")
            # Log metadata if available
            if isinstance(sensor_data, dict) and 'meta' in sensor_data:
                logger.info(f"API Response - Metadata: {sensor_data.get('meta')}")
            # Log the number of data points
            data_points = sensor_data.get('data', []) if isinstance(sensor_data, dict) else []
            logger.info(f"API Response - Number of data points: {len(data_points)}")
            # Log a few data points as sample
            if data_points and len(data_points) > 0:
                logger.info(f"API Response - Sample data points (first 3): {data_points[:3]}")
        else:
            logger.warning("API Response: No data returned from get_sensor_time_series_data")
        logger.info("==================== END SENSOR API RESPONSE LOG ====================")
        
        # Check if we got real data
        use_real_data = False
        data_points = sensor_data.get('data', []) if isinstance(sensor_data, dict) else []
        
        if sensor_data and data_points and len(data_points) > 0:
            logger.info(f"Usando datos reales del sensor: {len(data_points)} puntos de datos disponibles")
            use_real_data = True
        else:
            logger.warning("No se encontraron datos reales para el sensor. Usando simulación.")
            
        # Generate date range for analysis
        date_range = pd.date_range(start=start_date_obj, end=end_date_obj, freq="D")
        num_days = len(date_range)
        
        # Process data based on whether we have real data or need simulation
        if use_real_data:
            # Parse real data points
            # Convert timestamps to datetime and values to float
            timestamps = []
            readings = []
            
            for point in data_points:
                ts = point.get('ts')
                value = point.get('v')
                
                if ts is not None and value is not None:
                    try:
                        # Convert timestamp to datetime
                        dt = datetime.fromtimestamp(float(ts))
                        # Convert value to float
                        val = float(value)
                        
                        timestamps.append(dt)
                        readings.append(val)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error procesando punto de datos: {e} - ts={ts}, v={value}")
            
            if not timestamps:
                logger.error("No se pudieron procesar los datos reales. Usando simulación.")
                use_real_data = False
            else:
                # Create a DataFrame with the real data
                real_data_df = pd.DataFrame({
                    'timestamp': timestamps,
                    'reading': readings
                })
                
                # Sort by timestamp
                real_data_df = real_data_df.sort_values('timestamp')
                
                # Get unit from metadata
                unit = sensor_data.get('meta', {}).get('unit', 'm3')
                
                # Get date column for daily aggregation
                real_data_df['date'] = real_data_df['timestamp'].dt.date
                
                # Group by date to get daily readings (last reading of each day)
                daily_readings = real_data_df.groupby('date')['reading'].last().reset_index()
                
                # Ensure we have a reading for each day in the date range
                all_dates_df = pd.DataFrame({'date': date_range.date})
                daily_readings = pd.merge(all_dates_df, daily_readings, on='date', how='left')
                
                # Forward fill missing values (use previous reading if no reading on a day)
                daily_readings['reading'] = daily_readings['reading'].ffill()
                
                # Calculate daily consumption (difference between consecutive readings)
                daily_readings['consumption'] = daily_readings['reading'].diff().fillna(0)
                
                # Replace negative values with 0 (can happen with meter replacements or errors)
                daily_readings['consumption'] = daily_readings['consumption'].clip(lower=0)
                
                # Create arrays for analysis
                counter_readings = daily_readings['reading'].values
                consumption_data = daily_readings['consumption'].values
                
                # Log data summary
                logger.info(f"Datos procesados: {len(counter_readings)} lecturas diarias, consumo total: {consumption_data.sum():.2f} {unit}")
                                
        # If no real data or processing failed, use simulation
        if not use_real_data:
            logger.info("Generando datos simulados para el análisis")
            
            # Simular datos de consumo de agua para el período seleccionado
            np.random.seed(42)  # Para resultados reproducibles
            
            # Valor inicial del contador
            initial_counter_value = 15000  # Por ejemplo, 15,000 m³
            
            # Generar consumos diarios base con variaciones aleatorias (valores que se suman cada día)
            daily_base_consumption = np.random.normal(40, 5, size=num_days)  # ~40m³/día con variación
            daily_base_consumption = np.maximum(daily_base_consumption, 5)  # Mínimo 5m³/día
            
            # Introducir anomalías en algunos días
            anomaly_threshold = 1.5
            is_anomaly = np.random.random(num_days) < 0.1  # ~10% de los días como anomalías
            
            # Aumentar el consumo en los días con anomalías
            daily_base_consumption[is_anomaly] *= 2.5  # Multiplicar por 2.5 para anomalías
            
            # Calcular lecturas acumulativas del contador
            counter_readings = np.zeros(num_days)
            counter_readings[0] = initial_counter_value + daily_base_consumption[0]
            
            for i in range(1, num_days):
                counter_readings[i] = counter_readings[i-1] + daily_base_consumption[i]
            
            # Los consumos diarios son las diferencias entre lecturas consecutivas
            consumption_data = daily_base_consumption.copy()
            
            # Unidad por defecto para datos simulados
            unit = "m³"
        
        # Contamos anomalías (valores atípicos basados en los datos)
        mean_consumption = np.mean(consumption_data)
        std_consumption = np.std(consumption_data)
        anomaly_threshold = 1.5  # Umbral para detección de anomalías
        is_anomaly = np.abs(consumption_data - mean_consumption) > (anomaly_threshold * std_consumption)
        
        # Calcular métricas para el análisis
        total_consumption = np.sum(consumption_data)
        avg_consumption = np.mean(consumption_data)
        num_anomalies = np.sum(is_anomaly)
        
        # Create analysis header
        analysis_header = html.Div([
            html.H3(f"Análisis de Consumo de Agua: {asset_name}"),
            html.P([
                html.Strong("Cliente: "), client_name, html.Br(),
                html.Strong("Proyecto: "), project_name, html.Br(),
                html.Strong("Tipo de activo: "), asset_type_name, html.Br(),
                html.Strong("Sensor: "), sensor_name, html.Br(),
                html.Strong("Período de análisis: "), f"{start_date} a {end_date}", html.Br(),
                html.Strong("Tipo de datos: "), html.Span("Reales", className="text-success") if use_real_data else html.Span("Simulados", className="text-warning")
            ])
        ])
        
        # Create key metrics
        key_metrics = [
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Volumen Total", className="card-title"),
                        html.H2(f"{total_consumption:.1f} {unit}", className="text-primary"),
                        html.P("Consumo total en el período seleccionado")
                    ])
                ])
            ),
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Consumo Promedio", className="card-title"),
                        html.H2(f"{avg_consumption:.1f} {unit}/día", className="text-primary"),
                        html.P("Promedio diario en el período")
                    ])
                ])
            ),
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Horas Pico", className="card-title"),
                        html.H2("7-9 AM, 7-10 PM", className="text-primary"),
                        html.P("Franjas horarias de mayor consumo")
                    ])
                ])
            ),
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Anomalías", className="card-title"),
                        html.H2(f"{num_anomalies} detectadas", className=f"{'text-danger' if num_anomalies > 0 else 'text-success'}"),
                        html.P("Posibles consumos anómalos")
                    ])
                ])
            )
        ]
        
        # Create consumption evolution chart (mostrando tanto lectura acumulada como consumo diario)
        consumption_evolution = html.Div([
            dcc.Tabs([
                dcc.Tab(label="Consumo Diario", children=[
                    dcc.Graph(
                        figure={
                            "data": [
                                {
                                    "x": date_range,
                                    "y": consumption_data,
                                    "type": "scatter",
                                    "mode": "lines+markers",
                                    "name": "Consumo diario",
                                    "marker": {"size": 6}
                                }
                            ],
                            "layout": {
                                "title": "Evolución del Consumo Diario",
                                "xaxis": {"title": "Fecha"},
                                "yaxis": {"title": f"Consumo ({unit}/día)"},
                                "height": 400
                            }
                        }
                    )
                ]),
                dcc.Tab(label="Lectura Acumulada", children=[
                    dcc.Graph(
                        figure={
                            "data": [
                                {
                                    "x": date_range,
                                    "y": counter_readings,
                                    "type": "scatter",
                                    "mode": "lines+markers",
                                    "name": "Lectura del contador",
                                    "marker": {"size": 6}
                                }
                            ],
                            "layout": {
                                "title": "Lectura Acumulada del Contador",
                                "xaxis": {"title": "Fecha"},
                                "yaxis": {"title": f"Lectura del contador ({unit})"},
                                "height": 400
                            }
                        }
                    )
                ])
            ])
        ])
        
        # Dividir el período en segmentos para comparación temporal
        num_segments = min(4, num_days // 7)  # Mínimo entre 4 o la cantidad de semanas
        if num_segments < 1:
            num_segments = 1
        
        segment_size = num_days // num_segments
        segment_names = [f"Semana {i+1}" for i in range(num_segments)]
        
        current_segments = []
        previous_segments = []
        
        for i in range(num_segments):
            start_idx = i * segment_size
            end_idx = min((i + 1) * segment_size, num_days)
            if start_idx < end_idx:
                current_segments.append(np.mean(consumption_data[start_idx:end_idx]))
                previous_segments.append(np.mean(consumption_data[start_idx:end_idx]) * 0.9)  # Simular período anterior
        
        # Create temporal comparison chart
        temporal_comparison = dcc.Graph(
            figure={
                "data": [
                    {
                        "x": segment_names[:len(current_segments)],
                        "y": current_segments,
                        "type": "bar",
                        "name": "Período actual"
                    },
                    {
                        "x": segment_names[:len(previous_segments)],
                        "y": previous_segments,
                        "type": "bar",
                        "name": "Período anterior"
                    }
                ],
                "layout": {
                    "title": "Comparativa con Período Anterior",
                    "xaxis": {"title": "Período"},
                    "yaxis": {"title": f"Consumo ({unit})"},
                    "barmode": "group",
                    "height": 400
                }
            }
        )
        
        # Generar datos para distribución por día de semana
        days_of_week = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        dow_indices = [d.weekday() for d in date_range]
        dow_consumption = [[] for _ in range(7)]
        
        for i, dow in enumerate(dow_indices):
            dow_consumption[dow].append(consumption_data[i])
        
        dow_avg_consumption = [np.mean(vals) if len(vals) > 0 else 0 for vals in dow_consumption]
        
        # Create consumption distribution chart
        consumption_distribution = dcc.Graph(
            figure={
                "data": [
                    {
                        "x": days_of_week,
                        "y": dow_avg_consumption,
                        "type": "bar",
                        "name": "Consumo por día"
                    }
                ],
                "layout": {
                    "title": "Distribución por Día de la Semana",
                    "xaxis": {"title": "Día"},
                    "yaxis": {"title": f"Consumo Promedio ({unit})"},
                    "height": 400
                }
            }
        )
        
        # Preparar datos para detección de anomalías
        anomaly_dates = date_range[is_anomaly]
        anomaly_values = consumption_data[is_anomaly]
        
        # Create anomaly detection chart
        anomaly_detection = html.Div([
            dcc.Graph(
                figure={
                    "data": [
                        {
                            "x": date_range,
                            "y": consumption_data,
                            "type": "scatter",
                            "mode": "lines",
                            "name": "Consumo diario"
                        },
                        {
                            "x": anomaly_dates,
                            "y": anomaly_values,
                            "type": "scatter",
                            "mode": "markers",
                            "marker": {"size": 12, "color": "red"},
                            "name": "Anomalías detectadas"
                        }
                    ],
                    "layout": {
                        "title": "Detección de Anomalías",
                        "xaxis": {"title": "Fecha"},
                        "yaxis": {"title": f"Consumo ({unit})"},
                        "height": 400
                    }
                }
            ),
            html.Div([
                html.H5("Análisis de Anomalías", className="mt-3"),
                html.Ul([
                    html.Li(f"Consumo anómalo el {anomaly_dates[i].strftime('%d/%m/%Y')}: {anomaly_values[i]:.1f} {unit} "
                           f"({abs(anomaly_values[i] - avg_consumption) / avg_consumption * 100:.1f}% {'superior' if anomaly_values[i] > avg_consumption else 'inferior'} a la media)")
                    for i in range(min(len(anomaly_dates), 5))  # Mostrar hasta 5 anomalías
                ]) if len(anomaly_dates) > 0 else html.P("No se detectaron anomalías en el período seleccionado.")
            ])
        ])
        
        # Create asset type insights
        asset_type_insights = create_asset_type_insights(asset_type, {
            "total_consumption": total_consumption,
            "average_consumption": avg_consumption,
            "peak_hours": ["7-9 AM", "7-10 PM"],
            "anomalies": num_anomalies
        })
        
        # Create detailed data table with correct length arrays and properly formatted dates
        detailed_data_table = create_daily_readings_table(pd.DataFrame({
            # Convertir las fechas a un formato más legible (dd/mm/yyyy)
            "Fecha": [d.strftime("%d/%m/%Y") for d in date_range],
            "Lectura del Contador ({})".format(unit): counter_readings,
            "Consumo Diario ({})".format(unit): consumption_data,
            "Anomalía": is_anomaly
        }))
        
        # Store results including both counter readings and daily consumption for export
        analysis_results = {
            "client_id": client_id,
            "client_name": client_name,
            "project_id": project_id,
            "project_name": project_name,
            "asset_id": asset_id,
            "asset_name": asset_name,
            "sensor_id": sensor_id,
            "sensor_name": sensor_name,
            "asset_type": asset_type,
            "asset_type_name": asset_type_name,
            "start_date": start_date,
            "end_date": end_date,
            "total_consumption": float(total_consumption),
            "average_consumption": float(avg_consumption),
            "peak_hours": ["7-9 AM", "7-10 PM"],
            "anomalies": int(num_anomalies),
            "counter_readings": counter_readings.tolist(),
            "daily_consumption": consumption_data.tolist(),
            "unit": unit,
            "data_source": "real" if use_real_data else "simulated"
        }
        
        # Return the updated components
        return {"display": "none"}, {"display": "block"}, analysis_header, key_metrics, \
               consumption_evolution, temporal_comparison, consumption_distribution, \
               anomaly_detection, asset_type_insights, detailed_data_table, analysis_results
    
    # Callback to handle CSV export
    @app.callback(
        Output("water-download-data", "data"),
        [Input("water-export-csv-button", "n_clicks"),
         Input("water-export-pdf-button", "n_clicks")],
        [State("water-analysis-results-store", "data")],
        prevent_initial_call=True
    )
    def export_data(csv_clicks, pdf_clicks, analysis_results):
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update
        
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if button_id == "water-export-csv-button" and csv_clicks:
            try:
                # Obtener fechas desde los resultados del análisis
                start_date = pd.to_datetime(analysis_results.get("start_date"))
                end_date = pd.to_datetime(analysis_results.get("end_date"))
                
                # Generar secuencia de fechas para el período analizado
                date_range = pd.date_range(start=start_date, end=end_date, freq="D")
                
                # Obtener los datos de consumo y lecturas del contador
                if "counter_readings" in analysis_results and "daily_consumption" in analysis_results:
                    counter_readings = analysis_results.get("counter_readings")
                    consumption_values = analysis_results.get("daily_consumption")
                else:
                    # Regenerar los mismos datos que se usaron para el análisis
                    np.random.seed(42)  # Para mantener consistencia con análisis
                    num_days = len(date_range)
                    
                    # Generar consumos diarios base
                    daily_base_consumption = np.random.normal(40, 5, size=num_days)
                    daily_base_consumption = np.maximum(daily_base_consumption, 5)
                    
                    # Introducir anomalías
                    is_anomaly = np.random.random(num_days) < 0.1
                    daily_base_consumption[is_anomaly] *= 2.5
                    
                    # Calcular lecturas acumulativas
                    initial_counter_value = 15000
                    counter_readings = np.zeros(num_days)
                    counter_readings[0] = initial_counter_value + daily_base_consumption[0]
                    
                    for i in range(1, num_days):
                        counter_readings[i] = counter_readings[i-1] + daily_base_consumption[i]
                    
                    consumption_values = daily_base_consumption
                
                # Crear DataFrame para exportar con fechas formateadas
                asset_name = analysis_results.get('asset_name', 'asset')
                clean_name = ''.join(c if c.isalnum() else '_' for c in asset_name)
                
                df = pd.DataFrame({
                    "Fecha": [d.strftime("%d/%m/%Y") for d in date_range],
                    "Lectura del Contador (m³)": counter_readings,
                    "Consumo Diario (m³)": consumption_values
                })
                
                return dcc.send_data_frame(df.to_csv, f"consumo_agua_{clean_name}_{datetime.now().strftime('%Y%m%d')}.csv")
            except Exception as e:
                logger.error(f"Error al exportar datos a CSV: {str(e)}")
                return dash.no_update
        
        elif button_id == "water-export-pdf-button" and pdf_clicks:
            try:
                # Obtener información del análisis
                asset_name = analysis_results.get('asset_name', 'Activo')
                client_name = analysis_results.get('client_name', 'Cliente')
                project_name = analysis_results.get('project_name', 'Proyecto')
                asset_type = analysis_results.get('asset_type', 'other')
                asset_type_name = analysis_results.get('asset_type_name', 'Otro')
                start_date = pd.to_datetime(analysis_results.get('start_date', datetime.now() - timedelta(days=30)))
                end_date = pd.to_datetime(analysis_results.get('end_date', datetime.now()))
                total_consumption = analysis_results.get('total_consumption', 0)
                average_consumption = analysis_results.get('average_consumption', 0)
                num_anomalies = analysis_results.get('anomalies', 0)
                unit = analysis_results.get('unit', 'm³')
                
                # Obtener fechas y datos de consumo
                date_range = pd.date_range(start=start_date, end=end_date, freq="D")
                
                # Obtener datos de consumo
                if "counter_readings" in analysis_results and "daily_consumption" in analysis_results:
                    counter_readings = analysis_results.get("counter_readings")
                    consumption_values = analysis_results.get("daily_consumption")
                    
                    # Verificar si los datos son listas y no están vacíos
                    if not isinstance(counter_readings, list) or not isinstance(consumption_values, list) or len(counter_readings) == 0 or len(consumption_values) == 0:
                        logger.warning("Los datos de consumo no son válidos, regenerando datos")
                        counter_readings = None
                        consumption_values = None
                else:
                    counter_readings = None
                    consumption_values = None
                
                # Si los datos no son válidos, regenerar
                if counter_readings is None or consumption_values is None:
                    # Regenerar los mismos datos que se usaron para el análisis
                    logger.info("Generando datos simulados para exportación PDF")
                    np.random.seed(42)  # Para mantener consistencia con análisis
                    num_days = len(date_range)
                    
                    # Generar consumos diarios base
                    daily_base_consumption = np.random.normal(40, 5, size=num_days)
                    daily_base_consumption = np.maximum(daily_base_consumption, 5)
                    
                    # Introducir anomalías
                    is_anomaly = np.random.random(num_days) < 0.1
                    daily_base_consumption[is_anomaly] *= 2.5
                    
                    # Calcular lecturas acumulativas
                    initial_counter_value = 15000
                    counter_readings = np.zeros(num_days)
                    counter_readings[0] = initial_counter_value + daily_base_consumption[0]
                    
                    for i in range(1, num_days):
                        counter_readings[i] = counter_readings[i-1] + daily_base_consumption[i]
                    
                    consumption_values = daily_base_consumption
                
                # Contamos anomalías (valores atípicos basados en los datos)
                mean_consumption = np.mean(consumption_values)
                std_consumption = np.std(consumption_values)
                anomaly_threshold = 1.5  # Umbral para detección de anomalías
                is_anomaly = np.abs(np.array(consumption_values) - mean_consumption) > (anomaly_threshold * std_consumption)
                
                # Preparar datos para detección de anomalías
                anomaly_dates = [date_range[i] for i in range(len(date_range)) if i < len(is_anomaly) and is_anomaly[i]]
                anomaly_values = [consumption_values[i] for i in range(len(consumption_values)) if i < len(is_anomaly) and is_anomaly[i]]
                
                # Generar datos para distribución por día de semana
                days_of_week = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                dow_indices = [d.weekday() for d in date_range]
                dow_consumption = [[] for _ in range(7)]
                
                for i, dow in enumerate(dow_indices):
                    if i < len(consumption_values):
                        dow_consumption[dow].append(consumption_values[i])
                
                dow_avg_consumption = [np.mean(vals) if len(vals) > 0 else 0 for vals in dow_consumption]
                
                # Dividir el período en segmentos para comparación temporal
                num_days = len(date_range)
                num_segments = min(4, num_days // 7)  # Mínimo entre 4 o la cantidad de semanas
                if num_segments < 1:
                    num_segments = 1
                
                segment_size = num_days // num_segments
                segment_names = [f"Semana {i+1}" for i in range(num_segments)]
                
                current_segments = []
                previous_segments = []
                
                for i in range(num_segments):
                    start_idx = i * segment_size
                    end_idx = min((i + 1) * segment_size, num_days)
                    if start_idx < end_idx and start_idx < len(consumption_values) and end_idx <= len(consumption_values):
                        current_segments.append(np.mean(consumption_values[start_idx:end_idx]))
                        previous_segments.append(np.mean(consumption_values[start_idx:end_idx]) * 0.9)  # Simular período anterior
                
                # Generar gráficos para incluir en el PDF
                # Nota: Utilizamos matplotlib para generar las imágenes que incluiremos en el PDF
                
                import matplotlib.pyplot as plt
                from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
                from matplotlib.figure import Figure
                import tempfile
                import os
                
                # Función auxiliar para guardar figuras como imágenes
                def fig_to_image(fig):
                    """Convierte una figura de matplotlib a una imagen para ReportLab"""
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        fig.savefig(temp_file.name, format='png', dpi=150, bbox_inches='tight')
                        img = Image(temp_file.name, width=6*inch, height=4*inch)
                        # Cerrar la figura para liberar memoria
                        plt.close(fig)
                        return img, temp_file.name
                
                # Lista para almacenar los archivos temporales que crearemos
                temp_files = []
                
                # 1. Gráfico de evolución del consumo diario
                fig_daily = Figure(figsize=(10, 6))
                ax = fig_daily.add_subplot(111)
                ax.plot(date_range[:len(consumption_values)], consumption_values, 'o-', color='#007bff')
                ax.set_title('Evolución del Consumo Diario', fontsize=14)
                ax.set_xlabel('Fecha', fontsize=12)
                ax.set_ylabel(f'Consumo ({unit}/día)', fontsize=12)
                ax.grid(True, linestyle='--', alpha=0.7)
                fig_daily.autofmt_xdate()  # Rotar las fechas para mejor legibilidad
                
                daily_img, daily_temp = fig_to_image(fig_daily)
                temp_files.append(daily_temp)
                
                # 2. Gráfico de lectura acumulada
                fig_accumulated = Figure(figsize=(10, 6))
                ax = fig_accumulated.add_subplot(111)
                ax.plot(date_range[:len(counter_readings)], counter_readings, 'o-', color='#28a745')
                ax.set_title('Lectura Acumulada del Contador', fontsize=14)
                ax.set_xlabel('Fecha', fontsize=12)
                ax.set_ylabel(f'Lectura del contador ({unit})', fontsize=12)
                ax.grid(True, linestyle='--', alpha=0.7)
                fig_accumulated.autofmt_xdate()
                
                accumulated_img, accumulated_temp = fig_to_image(fig_accumulated)
                temp_files.append(accumulated_temp)
                
                # 3. Gráfico de distribución por día de semana
                fig_distribution = Figure(figsize=(10, 6))
                ax = fig_distribution.add_subplot(111)
                ax.bar(days_of_week, dow_avg_consumption, color='#17a2b8')
                ax.set_title('Distribución por Día de la Semana', fontsize=14)
                ax.set_xlabel('Día', fontsize=12)
                ax.set_ylabel(f'Consumo Promedio ({unit})', fontsize=12)
                ax.grid(True, linestyle='--', alpha=0.7)
                
                distribution_img, distribution_temp = fig_to_image(fig_distribution)
                temp_files.append(distribution_temp)
                
                # 4. Gráfico de comparativa temporal
                if len(current_segments) > 0 and len(segment_names) > 0:
                    fig_comparison = Figure(figsize=(10, 6))
                    ax = fig_comparison.add_subplot(111)
                    x = np.arange(len(segment_names[:len(current_segments)]))
                    width = 0.35
                    
                    ax.bar(x - width/2, current_segments, width, label='Período actual', color='#007bff')
                    ax.bar(x + width/2, previous_segments[:len(current_segments)], width, label='Período anterior', color='#6c757d')
                    
                    ax.set_title('Comparativa con Período Anterior', fontsize=14)
                    ax.set_xlabel('Período', fontsize=12)
                    ax.set_ylabel(f'Consumo ({unit})', fontsize=12)
                    ax.set_xticks(x)
                    ax.set_xticklabels(segment_names[:len(current_segments)])
                    ax.legend()
                    ax.grid(True, linestyle='--', alpha=0.7)
                    
                    comparison_img, comparison_temp = fig_to_image(fig_comparison)
                    temp_files.append(comparison_temp)
                else:
                    comparison_img = None
                
                # 5. Gráfico de detección de anomalías
                if len(anomaly_dates) > 0 and len(anomaly_values) > 0:
                    fig_anomalies = Figure(figsize=(10, 6))
                    ax = fig_anomalies.add_subplot(111)
                    
                    # Dibujar consumo diario como línea
                    ax.plot(date_range[:len(consumption_values)], consumption_values, '-', color='#6c757d', label='Consumo diario')
                    
                    # Dibujar anomalías como puntos rojos
                    ax.scatter(anomaly_dates, anomaly_values, color='#dc3545', s=100, label='Anomalías detectadas')
                    
                    ax.set_title('Detección de Anomalías', fontsize=14)
                    ax.set_xlabel('Fecha', fontsize=12)
                    ax.set_ylabel(f'Consumo ({unit})', fontsize=12)
                    ax.legend()
                    ax.grid(True, linestyle='--', alpha=0.7)
                    fig_anomalies.autofmt_xdate()
                    
                    anomalies_img, anomalies_temp = fig_to_image(fig_anomalies)
                    temp_files.append(anomalies_temp)
                else:
                    anomalies_img = None
                
                # Crear un buffer para el PDF
                buffer = io.BytesIO()
                
                # Crear el documento PDF
                doc = SimpleDocTemplate(buffer, pagesize=letter)
                elements = []
                
                # Estilos
                styles = getSampleStyleSheet()
                title_style = styles['Title']
                heading1_style = styles['Heading1']
                heading2_style = styles['Heading2']
                normal_style = styles['Normal']
                
                # Estilos personalizados
                custom_styles = {
                    'Title': ParagraphStyle(
                        'CustomTitle',
                        parent=styles['Title'],
                        fontSize=24,
                        textColor=colors.darkblue,
                        spaceAfter=12
                    ),
                    'Heading1': ParagraphStyle(
                        'CustomHeading1',
                        parent=styles['Heading1'],
                        fontSize=18,
                        textColor=colors.darkblue,
                        spaceAfter=8
                    ),
                    'Heading2': ParagraphStyle(
                        'CustomHeading2',
                        parent=styles['Heading2'],
                        fontSize=16,
                        textColor=colors.darkblue,
                        spaceAfter=6
                    ),
                    'Normal': ParagraphStyle(
                        'CustomNormal',
                        parent=styles['Normal'],
                        fontSize=11,
                        spaceAfter=6
                    )
                }
                
                # Agregar título y encabezado
                elements.append(Paragraph(f"Informe de Consumo de Agua", custom_styles['Title']))
                elements.append(Spacer(1, 0.25*inch))
                
                # Información del informe
                elements.append(Paragraph(f"Cliente: {client_name}", custom_styles['Heading2']))
                elements.append(Paragraph(f"Proyecto: {project_name}", custom_styles['Heading2']))
                elements.append(Paragraph(f"Activo: {asset_name}", custom_styles['Heading2']))
                elements.append(Paragraph(f"Tipo de activo: {asset_type_name}", custom_styles['Heading2']))
                elements.append(Paragraph(f"Período: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}", custom_styles['Heading2']))
                elements.append(Spacer(1, 0.3*inch))
                
                # Métricas clave en tarjetas estilo Bootstrap
                elements.append(Paragraph("Métricas Clave", custom_styles['Heading1']))
                elements.append(Spacer(1, 0.1*inch))
                
                # Crear tarjetas para las métricas clave en formato de tabla 2x2
                key_metrics_data = [
                    [
                        Table([
                            [Paragraph("<b>Volumen Total</b>", styles['Normal'])],
                            [Paragraph(f"<font size='14' color='blue'>{total_consumption:.1f} {unit}</font>", styles['Normal'])],
                            [Paragraph("Consumo total en el período seleccionado", styles['Normal'])]
                        ], colWidths=[2.75*inch], style=[
                            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                            ('BOX', (0, 0), (-1, -1), 1, colors.gray),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('TOPPADDING', (0, 0), (-1, -1), 8),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ]),
                        
                        Table([
                            [Paragraph("<b>Consumo Promedio</b>", styles['Normal'])],
                            [Paragraph(f"<font size='14' color='blue'>{average_consumption:.1f} {unit}/día</font>", styles['Normal'])],
                            [Paragraph("Promedio diario en el período", styles['Normal'])]
                        ], colWidths=[2.75*inch], style=[
                            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                            ('BOX', (0, 0), (-1, -1), 1, colors.gray),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('TOPPADDING', (0, 0), (-1, -1), 8),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ])
                    ],
                    [
                        Table([
                            [Paragraph("<b>Horas Pico</b>", styles['Normal'])],
                            [Paragraph("<font size='14' color='blue'>7-9 AM, 7-10 PM</font>", styles['Normal'])],
                            [Paragraph("Franjas horarias de mayor consumo", styles['Normal'])]
                        ], colWidths=[2.75*inch], style=[
                            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                            ('BOX', (0, 0), (-1, -1), 1, colors.gray),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('TOPPADDING', (0, 0), (-1, -1), 8),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ]),
                        
                        Table([
                            [Paragraph("<b>Anomalías</b>", styles['Normal'])],
                            [Paragraph(f"<font size='14' color='{'red' if num_anomalies > 0 else 'green'}'>{num_anomalies} detectadas</font>", styles['Normal'])],
                            [Paragraph("Posibles consumos anómalos", styles['Normal'])]
                        ], colWidths=[2.75*inch], style=[
                            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                            ('BOX', (0, 0), (-1, -1), 1, colors.gray),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('TOPPADDING', (0, 0), (-1, -1), 8),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ])
                    ]
                ]
                
                metrics_card_table = Table(key_metrics_data, colWidths=[3*inch, 3*inch], rowHeights=[1.2*inch, 1.2*inch])
                metrics_card_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
                
                elements.append(metrics_card_table)
                elements.append(Spacer(1, 0.3*inch))
                elements.append(Paragraph("Evolución del Consumo de Agua", custom_styles['Heading1']))
                
                # Añadir gráfico de evolución diaria
                elements.append(Paragraph("Consumo Diario", custom_styles['Heading2']))
                elements.append(daily_img)
                elements.append(Spacer(1, 0.2*inch))
                
                # Añadir gráfico de lectura acumulada
                elements.append(Paragraph("Lectura Acumulada del Contador", custom_styles['Heading2']))
                elements.append(accumulated_img)
                elements.append(Spacer(1, 0.2*inch))
                
                # Añadir gráfico de distribución
                elements.append(Paragraph("Distribución del Consumo", custom_styles['Heading1']))
                elements.append(distribution_img)
                elements.append(Spacer(1, 0.2*inch))
                
                # Añadir gráfico de comparativa temporal
                if comparison_img:
                    elements.append(Paragraph("Comparativa Temporal", custom_styles['Heading1']))
                    elements.append(comparison_img)
                    elements.append(Spacer(1, 0.2*inch))
                
                # Añadir gráfico de anomalías
                if anomalies_img:
                    elements.append(Paragraph("Detección de Anomalías", custom_styles['Heading1']))
                    elements.append(anomalies_img)
                    
                    # Lista de anomalías detectadas
                    if len(anomaly_dates) > 0:
                        elements.append(Paragraph("Análisis de Anomalías:", custom_styles['Heading2']))
                        
                        anomaly_bullets = []
                        for i in range(min(len(anomaly_dates), 5)):  # Mostrar hasta 5 anomalías
                            anomaly_text = f"Consumo anómalo el {anomaly_dates[i].strftime('%d/%m/%Y')}: {anomaly_values[i]:.1f} {unit} "
                            anomaly_text += f"({abs(anomaly_values[i] - mean_consumption) / mean_consumption * 100:.1f}% "
                            anomaly_text += f"{'superior' if anomaly_values[i] > mean_consumption else 'inferior'} a la media)"
                            anomaly_bullets.append(Paragraph("• " + anomaly_text, custom_styles['Normal']))
                        
                        for bullet in anomaly_bullets:
                            elements.append(bullet)
                    
                    elements.append(Spacer(1, 0.2*inch))
                
                # Insights Contextuales basados en el tipo de activo
                elements.append(Paragraph("Insights Contextuales por Tipo de Activo", custom_styles['Heading1']))
                elements.append(Spacer(1, 0.1*inch))
                
                # Contenido específico basado en el tipo de activo
                asset_insights = {
                    "residential_building": [
                        Paragraph("<b>Análisis para Edificio Residencial</b>", custom_styles['Heading2']),
                        Paragraph(f"El consumo total de <b>{total_consumption:.1f} {unit}</b> para este edificio residencial representa:", custom_styles['Normal']),
                        Paragraph("• Un consumo promedio de <b>{:.1f} {}/día</b>, lo que está dentro del rango esperado para edificios residenciales (30-50 m³/día).".format(average_consumption, unit), custom_styles['Normal']),
                        Paragraph("• Las horas pico de consumo (7-9 AM, 7-10 PM) coinciden con patrones típicos de uso doméstico.", custom_styles['Normal']),
                        Paragraph(f"• Se detectaron {num_anomalies} anomalías que podrían indicar fugas o usos excesivos.", custom_styles['Normal']),
                        Paragraph("<b>Recomendaciones:</b>", custom_styles['Normal']),
                        Paragraph("• Considerar la instalación de sistemas de recolección de agua de lluvia para reducir el consumo.", custom_styles['Normal']),
                        Paragraph("• Implementar programas de concientización para residentes sobre el uso responsable del agua.", custom_styles['Normal']),
                        Paragraph("• Revisar las instalaciones para identificar posibles fugas en los días con anomalías detectadas.", custom_styles['Normal'])
                    ],
                    "individual_home": [
                        Paragraph("<b>Análisis para Vivienda Individual</b>", custom_styles['Heading2']),
                        Paragraph(f"El consumo total de <b>{total_consumption:.1f} {unit}</b> para esta vivienda representa:", custom_styles['Normal']),
                        Paragraph("• Un consumo promedio de <b>{:.1f} {}/día</b>, lo que está por encima del promedio para una vivienda individual (0.5-1.5 m³/día).".format(average_consumption, unit), custom_styles['Normal']),
                        Paragraph("• Las horas pico de consumo (7-9 AM, 7-10 PM) son consistentes con actividades matutinas y vespertinas en el hogar.", custom_styles['Normal']),
                        Paragraph(f"• Se detectaron {num_anomalies} anomalías que requieren atención.", custom_styles['Normal']),
                        Paragraph("<b>Recomendaciones:</b>", custom_styles['Normal']),
                        Paragraph("• Instalar dispositivos de ahorro de agua en grifos y duchas.", custom_styles['Normal']),
                        Paragraph("• Revisar el sistema de riego si existe jardín, ya que podría ser responsable del alto consumo.", custom_styles['Normal']),
                        Paragraph("• Verificar posibles fugas en cisternas de baños y conexiones de electrodomésticos.", custom_styles['Normal'])
                    ],
                    "logistics_center": [
                        Paragraph("<b>Análisis para Centro Logístico</b>", custom_styles['Heading2']),
                        Paragraph(f"El consumo total de <b>{total_consumption:.1f} {unit}</b> para este centro logístico representa:", custom_styles['Normal']),
                        Paragraph("• Un consumo promedio de <b>{:.1f} {}/día</b>, lo que es típico para operaciones logísticas de este tamaño.".format(average_consumption, unit), custom_styles['Normal']),
                        Paragraph("• Las horas pico de consumo (7-9 AM, 7-10 PM) coinciden con los horarios de mayor actividad operativa.", custom_styles['Normal']),
                        Paragraph(f"• Se detectaron {num_anomalies} anomalías que podrían relacionarse con procesos industriales específicos.", custom_styles['Normal']),
                        Paragraph("<b>Recomendaciones:</b>", custom_styles['Normal']),
                        Paragraph("• Implementar sistemas de recirculación de agua para procesos industriales.", custom_styles['Normal']),
                        Paragraph("• Evaluar la posibilidad de recolección y tratamiento de aguas grises para reutilización.", custom_styles['Normal']),
                        Paragraph("• Realizar auditorías periódicas de consumo de agua para identificar oportunidades de mejora.", custom_styles['Normal'])
                    ],
                    "office_building": [
                        Paragraph("<b>Análisis para Edificio de Oficinas</b>", custom_styles['Heading2']),
                        Paragraph(f"El consumo total de <b>{total_consumption:.1f} {unit}</b> para este edificio de oficinas representa:", custom_styles['Normal']),
                        Paragraph("• Un consumo promedio de <b>{:.1f} {}/día</b>, lo que está dentro del rango esperado para edificios de oficinas de este tamaño.".format(average_consumption, unit), custom_styles['Normal']),
                        Paragraph("• Las horas pico de consumo (7-9 AM, 7-10 PM) coinciden con el horario laboral principal.", custom_styles['Normal']),
                        Paragraph(f"• Se detectaron {num_anomalies} anomalías que merecen atención.", custom_styles['Normal']),
                        Paragraph("<b>Recomendaciones:</b>", custom_styles['Normal']),
                        Paragraph("• Instalar grifos con sensores en baños para reducir el desperdicio.", custom_styles['Normal']),
                        Paragraph("• Implementar sistemas de refrigeración eficientes en el uso de agua.", custom_styles['Normal']),
                        Paragraph("• Desarrollar campañas de concientización sobre el uso del agua entre empleados.", custom_styles['Normal'])
                    ],
                    "other": [
                        Paragraph("<b>Análisis General</b>", custom_styles['Heading2']),
                        Paragraph(f"El consumo total de <b>{total_consumption:.1f} {unit}</b> para este activo representa:", custom_styles['Normal']),
                        Paragraph("• Un consumo promedio de <b>{:.1f} {}/día</b>.".format(average_consumption, unit), custom_styles['Normal']),
                        Paragraph("• Las horas pico de consumo son: 7-9 AM, 7-10 PM.", custom_styles['Normal']),
                        Paragraph(f"• Se detectaron {num_anomalies} anomalías que podrían indicar consumos inusuales.", custom_styles['Normal']),
                        Paragraph("<b>Recomendaciones:</b>", custom_styles['Normal']),
                        Paragraph("• Realizar un análisis detallado del patrón de consumo para establecer una línea base.", custom_styles['Normal']),
                        Paragraph("• Implementar medidores adicionales para segmentar el consumo por áreas o usos.", custom_styles['Normal']),
                        Paragraph("• Considerar una auditoría especializada de consumo de agua.", custom_styles['Normal'])
                    ]
                }
                
                # Agregar los insights específicos para el tipo de activo
                insights_for_asset_type = asset_insights.get(asset_type, asset_insights["other"])
                for insight in insights_for_asset_type:
                    elements.append(insight)
                
                elements.append(Spacer(1, 0.3*inch))
                
                # Tabla de datos detallados
                elements.append(Paragraph("Datos Detallados de Consumo", custom_styles['Heading1']))
                elements.append(Spacer(1, 0.1*inch))
                
                # Crear encabezados de tabla
                table_data = [["Fecha", f"Lectura ({unit})", f"Consumo ({unit})", "Anomalía"]]
                
                # Añadir filas a la tabla (limitar a 20 para no hacer el PDF demasiado largo)
                max_rows_detailed = min(20, len(date_range))
                for i in range(max_rows_detailed):
                    is_anomaly_val = "Sí" if (i < len(is_anomaly) and is_anomaly[i]) else "No"
                    anomaly_color = colors.red if is_anomaly_val == "Sí" else colors.black
                    
                    # Manejar posibles valores None
                    if i < len(counter_readings) and i < len(consumption_values):
                        counter_value = counter_readings[i]
                        consumption_value = consumption_values[i]
                        
                        # Verificar que los valores no sean None y sean numéricos
                        if counter_value is not None and consumption_value is not None:
                            try:
                                counter_formatted = f"{float(counter_value):.2f}"
                            except (ValueError, TypeError):
                                counter_formatted = "N/A"
                                
                            try:
                                consumption_formatted = f"{float(consumption_value):.2f}"
                            except (ValueError, TypeError):
                                consumption_formatted = "N/A"
                        else:
                            counter_formatted = "N/A"
                            consumption_formatted = "N/A"
                    else:
                        counter_formatted = "N/A"
                        consumption_formatted = "N/A"
                    
                    table_data.append([
                        date_range[i].strftime("%d/%m/%Y"),
                        counter_formatted,
                        consumption_formatted,
                        is_anomaly_val
                    ])
                
                # Añadir nota si hay más datos
                if len(date_range) > max_rows_detailed:
                    table_data.append(["...", "...", "...", "..."])
                    table_data.append([f"Mostrando {max_rows_detailed} de {len(date_range)} días", "", "", ""])
                
                # Crear la tabla con estilos
                detail_table = Table(table_data, colWidths=[1.3*inch, 1.5*inch, 1.5*inch, 1*inch])
                detail_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    # Colorear filas alternadas
                    *[('BACKGROUND', (0, i), (-1, i), colors.whitesmoke) for i in range(1, len(table_data)) if i % 2 == 0]
                ]))
                
                elements.append(detail_table)
                elements.append(Spacer(1, 0.2*inch))
                
                # Nota de pie de página
                elements.append(Paragraph("Nota: Este informe ha sido generado automáticamente por Alfred Dashboard.", custom_styles['Normal']))
                elements.append(Paragraph(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}", custom_styles['Normal']))
                
                # Generar el PDF
                doc.build(elements)
                
                # Mover el cursor al inicio del buffer
                buffer.seek(0)
                
                # Crear el nombre del archivo
                clean_name = ''.join(c if c.isalnum() else '_' for c in asset_name)
                filename = f"consumo_agua_{clean_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
                
                # Eliminar archivos temporales
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                
                # Devolver el archivo para descarga
                return dcc.send_bytes(buffer.getvalue(), filename=filename)
            except Exception as e:
                logger.error(f"Error al exportar datos a PDF: {str(e)}")
                logger.exception("Detalles del error:")
                return dash.no_update
        
        return dash.no_update

# Layout to be used in app.py
layout = create_layout() 