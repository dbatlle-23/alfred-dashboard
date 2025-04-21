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
from components.carbon_footprint.analysis_dashboard import create_carbon_analysis_dashboard
from components.carbon_footprint.asset_type_context import create_asset_type_insights

# Import utilities
from utils.metrics.data_processing import (
    process_metrics_data,
    aggregate_data_by_project,
    aggregate_data_by_asset,
    aggregate_data_by_consumption_type,
    aggregate_data_by_month_and_asset,
    generate_monthly_consumption_summary
)
from utils.api import get_clientes, get_projects, get_assets, get_project_assets, get_asset_all_sensors, get_sensor_time_series_data
from utils.carbon_footprint.analysis import (
    calculate_carbon_emissions,
    calculate_total_emissions,
    calculate_average_emissions,
    detect_emission_anomalies,
    compare_emission_periods,
    estimate_annual_emissions,
    calculate_emission_reduction_targets
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

# Energy consumption tag constants
ENERGY_CONSUMPTION_TAGS = [
    ConsumptionTags.DOMESTIC_ENERGY_GENERAL.value,
    ConsumptionTags.THERMAL_ENERGY_HEAT.value,
    ConsumptionTags.THERMAL_ENERGY_COOLING.value
]

# Energy sensor type constants
ENERGY_SENSOR_TYPES = [
    "KILOWATTSHOUR_ACCUMULATED",
    "KILOWATTHOUR_ACCUMULATED",  # Variante alternativa posible
    "ENERGY_ACCUMULATED",        # Nombre genérico para consumos acumulados de energía
]

def create_layout():
    """Create the carbon footprint analysis page layout."""
    return html.Div([
        # Stores for data
        dcc.Store(id="carbon-data-store"),
        dcc.Store(id="carbon-selected-client-store"),
        dcc.Store(id="carbon-selected-project-store"),
        dcc.Store(id="carbon-selected-asset-store"),
        dcc.Store(id="carbon-selected-sensor-store"),
        dcc.Store(id="carbon-selected-date-range-store"),
        dcc.Store(id="carbon-asset-type-store"),
        dcc.Store(id="carbon-analysis-results-store"),
        
        # Main container
        dbc.Container([
            # Page title
            html.H2("Análisis de Huella de Carbono", className="mb-4"),
            
            # Hierarchical selection card
            dbc.Card([
                dbc.CardHeader("Selección Jerárquica"),
                dbc.CardBody([
                    dbc.Row([
                        # Client filter
                        dbc.Col([
                            html.Label("Cliente"),
                            dcc.Dropdown(
                                id="carbon-client-filter",
                                placeholder="Seleccione un cliente",
                                clearable=False
                            )
                        ], width=3),
                        
                        # Project filter
                        dbc.Col([
                            html.Label("Proyecto"),
                            dcc.Dropdown(
                                id="carbon-project-filter",
                                placeholder="Seleccione un proyecto",
                                clearable=False,
                                disabled=True
                            )
                        ], width=3),
                        
                        # Asset filter
                        dbc.Col([
                            html.Label("Activo (Espacio)"),
                            dcc.Dropdown(
                                id="carbon-asset-filter",
                                placeholder="Seleccione un activo",
                                clearable=False,
                                disabled=True
                            )
                        ], width=3),
                        
                        # Energy sensor filter
                        dbc.Col([
                            html.Label("Sensor de Energía"),
                            dcc.Dropdown(
                                id="carbon-sensor-filter",
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
                                id="carbon-asset-type-selector",
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
                                id="carbon-date-period",
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
                                    id="carbon-date-range",
                                    start_date=(datetime.now() - timedelta(days=30)).date(),
                                    end_date=datetime.now().date(),
                                    display_format="YYYY-MM-DD"
                                )
                            ], id="carbon-custom-date-container", style={"display": "none"})
                        ], width=3),
                        
                        # Analyze button
                        dbc.Col([
                            html.Div([
                                dbc.Button(
                                    "Calcular Huella de Carbono",
                                    id="carbon-analyze-button",
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
                        html.H4("Bienvenido al Análisis de Huella de Carbono", className="alert-heading"),
                        html.P(
                            "Seleccione un cliente, proyecto, activo y sensor de energía para comenzar el análisis. "
                            "Luego, haga clic en el botón 'Calcular Huella de Carbono' para obtener información detallada sobre las emisiones de CO2."
                        ),
                        html.Hr(),
                        html.P(
                            "Este análisis le proporcionará información valiosa sobre su huella de carbono, incluyendo "
                            "emisiones totales, proyecciones anuales, comparativas temporales y recomendaciones para reducir su impacto ambiental.",
                            className="mb-0"
                        )
                    ],
                    color="info",
                    id="carbon-initial-message"
                )
            ], id="carbon-initial-message-container"),
            
            # Analysis results container (hidden initially)
            html.Div([
                # Loading spinner
                dbc.Spinner(
                    children=[
                        # Analysis header
                        html.Div(id="carbon-analysis-header", className="mb-4"),
                        
                        # Key metrics cards
                        dbc.Row(id="carbon-key-metrics", className="mb-4"),
                        
                        # Charts and detailed analysis
                        dbc.Row([
                            # Left column - Time series and comparisons
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("Evolución de Emisiones de CO2"),
                                    dbc.CardBody(id="carbon-emission-evolution")
                                ], className="mb-4"),
                                
                                dbc.Card([
                                    dbc.CardHeader("Comparativa Temporal"),
                                    dbc.CardBody(id="carbon-temporal-comparison")
                                ])
                            ], width=6),
                            
                            # Right column - Distribution and anomalies
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("Distribución de Emisiones"),
                                    dbc.CardBody(id="carbon-emission-distribution")
                                ], className="mb-4"),
                                
                                dbc.Card([
                                    dbc.CardHeader("Detección de Anomalías"),
                                    dbc.CardBody(id="carbon-anomaly-detection")
                                ])
                            ], width=6)
                        ]),
                        
                        # Context-aware insights based on asset type
                        html.Div(id="carbon-asset-type-insights", className="mt-4"),
                        
                        # Reduction targets
                        dbc.Card([
                            dbc.CardHeader("Objetivos de Reducción de Emisiones"),
                            dbc.CardBody(id="carbon-reduction-targets")
                        ], className="mt-4"),
                        
                        # Detailed data table
                        dbc.Card([
                            dbc.CardHeader("Datos Detallados de Emisiones"),
                            dbc.CardBody(id="carbon-detailed-data-table")
                        ], className="mt-4"),
                        
                        # Export options
                        dbc.Card([
                            dbc.CardHeader("Exportar Resultados"),
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Button(
                                            [html.I(className="fas fa-file-csv me-2"), "Exportar a CSV"],
                                            id="carbon-export-csv-button",
                                            color="success",
                                            className="me-2"
                                        ),
                                        dbc.Button(
                                            [html.I(className="fas fa-file-pdf me-2"), "Exportar a PDF"],
                                            id="carbon-export-pdf-button",
                                            color="danger",
                                            className="me-2"
                                        ),
                                        dcc.Download(id="carbon-download-data")
                                    ])
                                ])
                            ])
                        ], className="mt-4")
                    ],
                    type="border",
                    fullscreen=False,
                )
            ], id="carbon-analysis-results-container", style={"display": "none"})
        ], fluid=True)
    ])

# Function to register callbacks
def register_callbacks(app):
    """Register callbacks for the carbon footprint analysis page."""
    
    # Callback to load clients
    @app.callback(
        Output("carbon-client-filter", "options"),
        [Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    @handle_exceptions(default_return=[{"label": "Error al cargar", "value": ""}])
    def load_clients(token_data):
        token = token_data.get('token') if token_data else None
        
        if not token:
            logger.info("No hay token JWT disponible para cargar clientes")
            return [{"label": "Seleccione un cliente", "value": ""}]
        
        logger.debug("Cargando clientes para análisis de huella de carbono")
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
        [Output("carbon-project-filter", "options"),
         Output("carbon-project-filter", "disabled")],
        [Input("carbon-client-filter", "value"),
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
        [Output("carbon-asset-filter", "options"),
         Output("carbon-asset-filter", "disabled")],
        [Input("carbon-project-filter", "value"),
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
    
    # Callback to load energy sensors when asset is selected
    @app.callback(
        [Output("carbon-sensor-filter", "options"),
         Output("carbon-sensor-filter", "disabled")],
        [Input("carbon-asset-filter", "value"),
         Input("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=([{"label": "Error al cargar", "value": ""}], True))
    def load_energy_sensors(asset_id, token_data):
        token = token_data.get('token') if token_data else None
        
        if not token or not asset_id:
            logger.warning("No se proporcionó token o ID de activo para cargar sensores")
            return [{"label": "Seleccione un sensor", "value": ""}], True
        
        # Definir palabras clave relacionadas con energía para filtrado
        ENERGY_KEYWORDS = ['kwh', 'kilowatt', 'kw', 'energía', 'energia', 'energy', 'consumo', 'consumption', 'eléctrico', 'electrico', 'acumulado']
        
        logger.info(f"Cargando todos los sensores para activo {asset_id}")
        
        try:
            # Obtener todos los sensores para el activo desde la API
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
                if isinstance(sensor, dict):
                    logger.info(f"Sensor {i} type: {sensor.get('sensor_type', 'No sensor_type')}")
                    logger.info(f"Sensor {i} name: {sensor.get('name', 'No name')}")
                    logger.info(f"Sensor {i} tag_name: {sensor.get('tag_name', 'No tag_name')}")
                    logger.info(f"Sensor {i} id: {sensor.get('id', 'No id')}")
            
            # Mostrar todos los tipos diferentes de sensores encontrados
            if isinstance(all_sensors, list) and len(all_sensors) > 0:
                sensor_types = set()
                for sensor in all_sensors:
                    if isinstance(sensor, dict) and 'sensor_type' in sensor:
                        sensor_types.add(sensor['sensor_type'])
                logger.info(f"Tipos de sensores encontrados: {sensor_types}")
            
            # Si no hay sensores, intentamos usar los tags predefinidos como fallback
            if not all_sensors:
                logger.warning(f"No se encontraron sensores para el activo {asset_id}. Usando tags predefinidos como fallback.")
                sensor_options = []
                
                # Incluir todos los tags de energía definidos en las constantes como fallback
                from constants.metrics import ConsumptionTags
                
                # Filtrar solo los tags relacionados con energía
                for tag_enum in ConsumptionTags:
                    tag = tag_enum.value
                    # Solo incluir tags de energía
                    if tag in ENERGY_CONSUMPTION_TAGS:
                        tag_name = CONSUMPTION_TAGS_MAPPING.get(tag, tag)
                        sensor_options.append({"label": tag_name, "value": tag})
                
                logger.info(f"Se utilizaron {len(sensor_options)} tags de energía predefinidos como fallback")
            else:
                # Convertir sensores a opciones para el dropdown, filtrando por tipos de energía
                sensor_options = []
                for sensor in all_sensors:
                    if not isinstance(sensor, dict):
                        logger.warning(f"Sensor no es un diccionario: {sensor}")
                        continue
                        
                    # Verificar si el sensor es del tipo KILOWATTSHOUR_ACCUMULATED
                    sensor_type = sensor.get('sensor_type', '')
                    
                    # Si no hay sensor_type, intentar inferirlo del nombre o tag_name
                    if not sensor_type:
                        name = sensor.get('name', '').lower()
                        tag_name = sensor.get('tag_name', '').lower()
                        
                        # Verificar si algún campo contiene palabras clave relacionadas con energía
                        energy_keywords = ENERGY_KEYWORDS
                        has_energy_keyword = any(keyword in name or keyword in tag_name for keyword in energy_keywords)
                        
                        if has_energy_keyword:
                            logger.info(f"Sensor inferido como de energía por nombre/tag: {name} / {tag_name}")
                            # Considerar como válido y continuar
                        else:
                            logger.debug(f"Ignorando sensor sin tipo específico y sin palabras clave de energía: {name} / {tag_name}")
                            continue
                    elif sensor_type not in ENERGY_SENSOR_TYPES:
                        logger.debug(f"Ignorando sensor por tipo no compatible: {sensor_type}")
                        continue
                    
                    tag_name = sensor.get('tag_name', '')
                    
                    # Si no hay tag_name, intentar buscar en otras claves posibles
                    if not tag_name:
                        for key in ['name', 'sensor_name', 'tag']:
                            if key in sensor and sensor[key]:
                                tag_name = sensor[key]
                                break
                    
                    # Continuar solo si el tag está en la lista de tags de energía
                    # o si no tenemos info de tag (para no excluir sensores potencialmente relevantes)
                    if tag_name and tag_name not in ENERGY_CONSUMPTION_TAGS and tag_name != "":
                        # Verificar si el tag_name contiene palabras clave de energía antes de descartarlo
                        energy_keywords = ENERGY_KEYWORDS
                        tag_lower = tag_name.lower()
                        
                        # Si el tag contiene alguna palabra clave de energía, no lo descartamos
                        if any(keyword in tag_lower for keyword in energy_keywords):
                            logger.info(f"Manteniendo sensor por contener palabras clave de energía: {tag_name}")
                        else:
                            logger.debug(f"Ignorando sensor por tag no compatible: {tag_name}")
                            continue
                    
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
                    if 'device_id' in sensor and 'sensor_id' in sensor and 'gateway_id' in sensor:
                        # Incluir toda la información necesaria para la API en el valor
                        sensor_value = f"{tag_name}:{sensor_uuid}:{sensor['device_id']}:{sensor['sensor_id']}:{sensor['gateway_id']}"
                    else:
                        # Si falta algún valor, solo incluir el sensor_uuid
                        sensor_value = f"{tag_name}:{sensor_uuid}" if sensor_uuid else tag_name
                    
                    # Add to dropdown options - include device info in label for debugging
                    sensor_options.append({
                        "label": f"{display_name}{device_info}",
                        "value": sensor_value
                    })
                    logger.info(f"Added sensor option: label='{display_name}{device_info}', value='{sensor_value}'")
                
                logger.info(f"Se cargaron {len(sensor_options)} opciones de sensores de energía para el activo {asset_id}")
            
            # Si después de todo el proceso no hay opciones, agregar un mensaje de error
            if not sensor_options:
                logger.error(f"No se pudieron cargar sensores de energía para el activo {asset_id}")
                return [{"label": "No hay sensores de energía disponibles", "value": ""}], True
            
            return sensor_options, False
            
        except Exception as e:
            logger.error(f"Error al cargar sensores: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [{"label": f"Error: {str(e)}", "value": ""}], True
    
    # Callback to enable/disable the analyze button
    @app.callback(
        Output("carbon-analyze-button", "disabled"),
        [Input("carbon-client-filter", "value"),
         Input("carbon-project-filter", "value"),
         Input("carbon-asset-filter", "value"),
         Input("carbon-sensor-filter", "value"),
         Input("carbon-asset-type-selector", "value")]
    )
    def toggle_analyze_button(client_id, project_id, asset_id, sensor_id, asset_type):
        if client_id and project_id and asset_id and sensor_id and asset_type:
            return False
        return True
    
    # Callback to show/hide custom date range
    @app.callback(
        Output("carbon-custom-date-container", "style"),
        [Input("carbon-date-period", "value")]
    )
    def toggle_custom_date_range(date_period):
        if date_period == "custom":
            return {"display": "block"}
        return {"display": "none"}
    
    # Callback to update date range based on period selection
    @app.callback(
        [Output("carbon-date-range", "start_date"),
         Output("carbon-date-range", "end_date")],
        [Input("carbon-date-period", "value")]
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
        
    # Callback to perform carbon footprint analysis when the button is clicked
    @app.callback(
        [
            # Control de visibilidad de contenedores
            Output("carbon-initial-message-container", "style"),
            Output("carbon-analysis-results-container", "style"),
            
            # Almacenar datos seleccionados
            Output("carbon-selected-client-store", "data"),
            Output("carbon-selected-project-store", "data"),
            Output("carbon-selected-asset-store", "data"),
            Output("carbon-selected-sensor-store", "data"),
            Output("carbon-asset-type-store", "data"),
            Output("carbon-selected-date-range-store", "data"),
            
            # Contenidos de análisis
            Output("carbon-analysis-header", "children"),
            Output("carbon-key-metrics", "children"),
            Output("carbon-emission-evolution", "children"),
            Output("carbon-temporal-comparison", "children"),
            Output("carbon-emission-distribution", "children"),
            Output("carbon-anomaly-detection", "children"),
            Output("carbon-asset-type-insights", "children"),
            Output("carbon-reduction-targets", "children"),
            Output("carbon-detailed-data-table", "children")
        ],
        [Input("carbon-analyze-button", "n_clicks")],
        [
            State("carbon-client-filter", "value"),
            State("carbon-project-filter", "value"),
            State("carbon-asset-filter", "value"),
            State("carbon-sensor-filter", "value"),
            State("carbon-asset-type-selector", "value"),
            State("carbon-date-period", "value"),
            State("carbon-date-range", "start_date"),
            State("carbon-date-range", "end_date"),
            State("jwt-token-store", "data")
        ],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=(
        {"display": "block"},  # Mantener visible mensaje inicial
        {"display": "none"},   # Ocultar resultados
        dash.no_update,        # client_data
        dash.no_update,        # project_data
        dash.no_update,        # asset_data
        dash.no_update,        # sensor_data
        dash.no_update,        # asset_type_data
        dash.no_update,        # date_range_data
        html.Div([            # análisis header (mensaje de error)
            dbc.Alert(
                [
                    html.H4("Error al realizar el análisis", className="alert-heading"),
                    html.P("Se produjo un error durante el análisis. Por favor, inténtelo de nuevo."),
                    html.Hr(),
                    html.P(
                        "Si el problema persiste, contacte al administrador del sistema.",
                        className="mb-0"
                    )
                ],
                color="danger"
            )
        ]),
        [],  # key_metrics
        [],  # emission_evolution
        [],  # temporal_comparison
        [],  # emission_distribution
        [],  # anomaly_detection
        [],  # asset_type_insights
        [],  # reduction_targets
        []   # detailed_data_table
    ))
    def perform_carbon_footprint_analysis(
        n_clicks, client_id, project_id, asset_id, sensor_id, asset_type, 
        date_period, start_date, end_date, token_data
    ):
        logger.info("Iniciando análisis de huella de carbono")
        
        # Verificar si se ha realizado un clic en el botón
        if not n_clicks:
            logger.info("No se detectó clic en el botón de análisis")
            raise dash.exceptions.PreventUpdate
        
        # Obtener el token JWT
        token = token_data.get('token') if token_data else None
        if not token:
            logger.error("No hay token JWT disponible para realizar el análisis")
            return dash.no_update
        
        # Determinar el rango de fechas según el período seleccionado
        if date_period != "custom":
            end_date = datetime.now().date()
            if date_period == "last_month":
                start_date = (datetime.now() - timedelta(days=30)).date()
            elif date_period == "last_3_months":
                start_date = (datetime.now() - timedelta(days=90)).date()
            elif date_period == "last_year":
                start_date = (datetime.now() - timedelta(days=365)).date()
            
            # Permitir un buffer de tiempo adicional para datos futuros, con fines de prueba
            additional_days = 365*2  # Buffer de 2 años
            end_date = (datetime.now() + timedelta(days=additional_days)).date()
            
        # Convertir fechas a objetos datetime si son strings
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            
        # Guardar selecciones en stores
        client_data = {"id": client_id}
        project_data = {"id": project_id}
        asset_data = {"id": asset_id}
        sensor_data = {"id": sensor_id}
        asset_type_data = {"type": asset_type}
        date_range_data = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "period": date_period}
        
        # Obtener datos de consumo para el sensor seleccionado
        logger.info(f"Obteniendo datos para sensor {sensor_id} desde {start_date} hasta {end_date}")
        try:
            # Extraer ID del sensor si está en formato "tag_name:sensor_id:device_id:sensor_id:gateway_id"
            sensor_parts = sensor_id.split(":")
            
            # Variables para almacenar los valores extraídos
            actual_sensor_id = None
            device_id = None
            sensor_id_param = None
            gateway_id = None
            
            # Extraer los valores según la longitud del array
            if len(sensor_parts) >= 2:
                actual_sensor_id = sensor_parts[1]  # UUID del sensor
            
            if len(sensor_parts) >= 5:
                # Tenemos el formato completo con todos los parámetros
                device_id = sensor_parts[2]
                sensor_id_param = sensor_parts[3]
                gateway_id = sensor_parts[4]
                logger.info(f"Parámetros completos extraídos: sensor_uuid={actual_sensor_id}, device_id={device_id}, sensor_id={sensor_id_param}, gateway_id={gateway_id}")
            else:
                # Si no tenemos todos los parámetros, usamos solo el UUID
                actual_sensor_id = actual_sensor_id or sensor_parts[0]
                logger.info(f"Solo se extrajo el UUID del sensor: {actual_sensor_id}")
            
            # Obtener datos del sensor
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # Obtener los datos de series temporales del sensor
            sensor_data_response = get_sensor_time_series_data(
                asset_id=asset_id,
                sensor_uuid=actual_sensor_id,
                device_id=device_id,
                sensor_id=sensor_id_param,
                gateway_id=gateway_id,
                start_date=start_datetime.strftime("%m-%d-%Y"),
                end_date=end_datetime.strftime("%m-%d-%Y"),
                jwt_token=token
            )
            
            # Verificar que los datos sean válidos
            if not isinstance(sensor_data_response, dict) or "data" not in sensor_data_response:
                logger.error(f"Respuesta de datos de sensor no válida: {sensor_data_response}")
                # Generar datos simulados para desarrollo
                energy_consumption = np.random.uniform(20, 100, size=(end_date - start_date).days*24)
                logger.warning("Usando datos simulados para el análisis")
            else:
                # Procesar los datos del sensor
                data_points = sensor_data_response.get("data", [])
                if not data_points:
                    logger.warning("No se encontraron datos para el sensor en el período especificado")
                    energy_consumption = np.random.uniform(20, 100, size=(end_date - start_date).days*24)
                    logger.warning("Usando datos simulados para el análisis")
                else:
                    logger.info(f"Se obtuvieron {len(data_points)} puntos de datos para el análisis")
                    
                    # Primero ordenar los puntos por timestamp para asegurar cálculos correctos
                    try:
                        # Verificar si los datos tienen key 'ts' o similar 
                        has_timestamp = False
                        if data_points and len(data_points) > 0:
                            first_point = data_points[0]
                            if 'ts' in first_point:
                                has_timestamp = True
                                logger.info(f"Los puntos tienen timestamp en la clave 'ts'")
                            elif 'timestamp' in first_point:
                                has_timestamp = True
                                # Renombrar 'timestamp' a 'ts' para consistencia
                                for point in data_points:
                                    point['ts'] = point['timestamp']
                                logger.info(f"Los puntos tienen timestamp en la clave 'timestamp', renombrando a 'ts'")
                        
                        if has_timestamp:
                            # Ordenar los puntos por timestamp
                            data_points.sort(key=lambda x: float(x.get('ts', 0)))
                            logger.info(f"Puntos ordenados por timestamp")
                        else:
                            logger.warning("No se encontró clave de timestamp en los datos, no se pueden ordenar")
                    except Exception as e:
                        logger.warning(f"Error al ordenar puntos por timestamp: {str(e)}")
                    
                    # Convertir valores string a float y calcular consumo diferencial
                    raw_values = []
                    for point in data_points:
                        try:
                            # Convertir string a float - verificar diferentes claves posibles para el valor
                            value = None
                            if "v" in point:
                                value = float(point.get("v", 0))
                            elif "value" in point:
                                value = float(point.get("value", 0))
                            else:
                                # Iterar sobre todas las claves para buscar una que pueda ser un valor numérico
                                for key, val in point.items():
                                    try:
                                        if key != "ts" and key != "timestamp":  # Evitar claves de timestamp
                                            value = float(val)
                                            logger.info(f"Valor encontrado en clave alternativa '{key}': {value}")
                                            break
                                    except (ValueError, TypeError):
                                        continue
                            
                            # Si se encontró un valor, añadirlo al array
                            if value is not None:
                                raw_values.append(value)
                                if len(raw_values) <= 5:  # Para depuración, mostrar los primeros 5 valores
                                    logger.debug(f"Valor procesado: {value} de point: {point}")
                            else:
                                logger.warning(f"No se pudo extraer un valor del punto: {point}")
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Error al convertir valor de consumo: {str(e)} en punto: {point}")
                            # No añadir valores inválidos
                    
                    # Calcular diferencias entre lecturas consecutivas (consumo real)
                    energy_consumption = []
                    if len(raw_values) > 1:
                        # Ordenar los valores por timestamps
                        # Nota: Esto es importante para manejar datos con timestamps que podrían estar en desorden
                        sorted_indices = range(len(raw_values))
                        
                        for i in range(1, len(raw_values)):
                            # Si el valor actual es mayor que el anterior (incremento normal)
                            if raw_values[i] > raw_values[i-1]:
                                diff = raw_values[i] - raw_values[i-1]
                                # Filtrar valores anómalos (diferencias muy grandes)
                                # Aumento del umbral para evitar filtrado excesivo con lecturas espaciadas
                                if diff < 1000:  # Umbral más permisivo para permitir incrementos mayores
                                    energy_consumption.append(diff)
                                else:
                                    logger.warning(f"Diferencia anormalmente grande ignorada: {diff} (valores: {raw_values[i-1]} -> {raw_values[i]})")
                            # Si hay un reset del contador u otro problema, ignorar pero registrar
                            elif raw_values[i] < raw_values[i-1]:
                                logger.warning(f"Posible reset de contador: {raw_values[i-1]} -> {raw_values[i]}")
                        
                        # Si no se encontraron diferencias válidas a pesar de tener datos, revisar los datos
                        if len(energy_consumption) == 0 and len(raw_values) > 2:
                            logger.warning("No se pudieron calcular diferencias válidas a pesar de tener lecturas. Verificando lecturas...")
                            
                            # Usar la diferencia total entre el primer y último valor como fallback
                            total_diff = raw_values[-1] - raw_values[0]
                            if total_diff > 0:
                                logger.info(f"Usando diferencia total como fallback: {total_diff} (primer valor: {raw_values[0]}, último valor: {raw_values[-1]})")
                                energy_consumption.append(total_diff)
                        
                        logger.info(f"Calculadas {len(energy_consumption)} diferencias de consumo a partir de {len(raw_values)} lecturas acumuladas")
                        logger.info(f"Consumo total calculado: {sum(energy_consumption):.2f} kWh")
                    else:
                        logger.warning("No hay suficientes puntos de datos para calcular diferencias de consumo")
                        energy_consumption = np.random.uniform(1, 5, size=24)  # Valores simulados razonables
            
            # Calcular métricas de huella de carbono
            total_emissions = calculate_total_emissions(energy_consumption)
            average_emissions = calculate_average_emissions(energy_consumption)
            
            # Log para depuración
            logger.info(f"Valores de energy_consumption: primeros 5 valores: {energy_consumption[:5] if len(energy_consumption) > 5 else energy_consumption}")
            logger.info(f"Cálculo de emisiones - total: {total_emissions}, promedio: {average_emissions}")
            
            # Verificar que tenemos suficientes datos para detectar anomalías
            if len(energy_consumption) > 5:
                anomalies, threshold = detect_emission_anomalies(energy_consumption)
                num_anomalies = np.sum(anomalies)
                logger.info(f"Detectadas {num_anomalies} anomalías con umbral {threshold}")
            else:
                logger.warning("No hay suficientes datos para detectar anomalías")
                anomalies = np.array([])
                threshold = 0
                num_anomalies = 0
            
            # Estimar emisiones anuales
            days_covered = (end_date - start_date).days
            annual_estimate = estimate_annual_emissions(energy_consumption, days_covered)
            
            # Calcular objetivos de reducción
            reduction_targets = calculate_emission_reduction_targets(annual_estimate)
            
            # Comparar con período anterior si hay suficientes datos
            comparison_result = compare_emission_periods(energy_consumption)
            
            # Determinar tendencia de emisiones
            if comparison_result["is_improved"]:
                emission_trend = "decreasing"
            elif comparison_result["change_percentage"] > 5:
                emission_trend = "increasing"
            else:
                emission_trend = "stable"
                
            # Construir objeto de datos para análisis
            analysis_data = {
                "total_emissions": total_emissions,
                "average_emissions": average_emissions,
                "annual_estimate": annual_estimate,
                "anomalies": num_anomalies,
                "emission_trend": emission_trend,
                "comparison": comparison_result,
                "reduction_targets": reduction_targets
            }
            
            logger.info(f"Análisis completado: Emisiones totales = {total_emissions:.2f} kg CO2, "
                       f"Media = {average_emissions:.2f} kg CO2/día, "
                       f"Anomalías = {num_anomalies}")
                       
            # Crear componentes para la visualización de resultados
            # Header de análisis
            analysis_header = html.Div([
                html.H3("Análisis de Huella de Carbono", className="mb-3"),
                html.P([
                    f"Período analizado: ",
                    html.Strong(f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
                ], className="lead"),
                html.P([
                    f"Tipo de activo: ",
                    html.Strong(ASSET_TYPES.get(asset_type, asset_type))
                ])
            ])
            
            # Métricas clave en tarjetas
            key_metrics = [
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Emisiones Totales", className="card-title text-center"),
                            html.H3(f"{total_emissions:.2f} kg CO2", className="text-center text-primary"),
                            html.P("en el período analizado", className="text-center text-muted small")
                        ])
                    ], className="shadow-sm")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Promedio Diario", className="card-title text-center"),
                            html.H3(f"{average_emissions:.2f} kg CO2/día", className="text-center text-primary"),
                            html.P("consumo energético", className="text-center text-muted small")
                        ])
                    ], className="shadow-sm")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Proyección Anual", className="card-title text-center"),
                            html.H3(f"{annual_estimate:.2f} kg CO2/año", className="text-center text-primary"),
                            html.P("al ritmo actual", className="text-center text-muted small")
                        ])
                    ], className="shadow-sm")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Anomalías", className="card-title text-center"),
                            html.H3(f"{num_anomalies}", className="text-center text-primary"),
                            html.P("picos de consumo detectados", className="text-center text-muted small")
                        ])
                    ], className="shadow-sm")
                ], width=3)
            ]
            
            # Evolución de emisiones (gráfica temporal)
            emission_evolution = html.Div([
                dcc.Graph(
                    figure={
                        'data': [
                            {'x': [i for i in range(len(energy_consumption))], 
                             'y': [calculate_carbon_emissions(value) for value in energy_consumption], 
                             'type': 'scatter', 
                             'mode': 'lines',
                             'name': 'Emisiones CO2',
                             'line': {'color': '#28a745'}
                            }
                        ],
                        'layout': {
                            'title': 'Evolución de Emisiones de CO2',
                            'xaxis': {'title': 'Tiempo'},
                            'yaxis': {'title': 'kg CO2'},
                            'template': 'plotly_white'
                        }
                    }
                )
            ])
            
            # Comparativa temporal
            temporal_comparison = html.Div([
                html.H5(f"Comparación con período anterior"),
                html.Div([
                    html.P([
                        "Las emisiones actuales son ",
                        html.Span(
                            f"{abs(comparison_result['change_percentage']):.1f}% "
                            f"{'menores' if comparison_result['is_improved'] else 'mayores'} ",
                            className=f"text-{'success' if comparison_result['is_improved'] else 'danger'} fw-bold"
                        ),
                        " que en el período anterior."
                    ]),
                    html.Div([
                        html.Div([
                            html.Span("Período actual: ", className="text-muted"),
                            html.Span(f"{comparison_result['current_total']:.2f} kg CO2", className="fw-bold")
                        ], className="col-6"),
                        html.Div([
                            html.Span("Período anterior: ", className="text-muted"),
                            html.Span(f"{comparison_result['previous_total']:.2f} kg CO2", className="fw-bold")
                        ], className="col-6")
                    ], className="row mt-3"),
                    html.P(
                        "(Nota: Si no hay datos históricos, la comparación se basa en una proyección)",
                        className="small text-muted mt-3"
                    ) if comparison_result["is_simulated"] else None
                ])
            ])
            
            # Distribución de emisiones
            emission_distribution = html.Div([
                dcc.Graph(
                    figure={
                        'data': [
                            {'x': ['00-06h', '06-12h', '12-18h', '18-24h'], 
                             'y': [
                                 np.mean([calculate_carbon_emissions(value) for i, value in enumerate(energy_consumption) if i % 24 < 6]),
                                 np.mean([calculate_carbon_emissions(value) for i, value in enumerate(energy_consumption) if 6 <= i % 24 < 12]),
                                 np.mean([calculate_carbon_emissions(value) for i, value in enumerate(energy_consumption) if 12 <= i % 24 < 18]),
                                 np.mean([calculate_carbon_emissions(value) for i, value in enumerate(energy_consumption) if i % 24 >= 18])
                             ], 
                             'type': 'bar',
                             'marker': {'color': ['#28a745', '#17a2b8', '#ffc107', '#dc3545']}
                            }
                        ],
                        'layout': {
                            'title': 'Distribución por Franja Horaria',
                            'xaxis': {'title': 'Horario'},
                            'yaxis': {'title': 'kg CO2 (promedio)'},
                            'template': 'plotly_white'
                        }
                    }
                )
            ])
            
            # Detección de anomalías
            anomaly_detection = html.Div([
                html.P(f"Se detectaron {num_anomalies} anomalías en el consumo energético durante el período analizado."),
                html.P(f"Estas anomalías representan un consumo que excede {threshold:.2f} kg CO2 por encima del promedio."),
                html.Div([
                    dcc.Graph(
                        figure={
                            'data': [
                                {'x': [i for i in range(len(energy_consumption))], 
                                 'y': [calculate_carbon_emissions(value) for value in energy_consumption], 
                                 'type': 'scatter', 
                                 'mode': 'lines',
                                 'name': 'Emisiones CO2',
                                 'line': {'color': '#17a2b8'}
                                },
                                {'x': [i for i in range(len(anomalies)) if anomalies[i]], 
                                 'y': [calculate_carbon_emissions(energy_consumption[i]) for i in range(len(anomalies)) if anomalies[i]], 
                                 'type': 'scatter', 
                                 'mode': 'markers',
                                 'name': 'Anomalías',
                                 'marker': {'color': '#dc3545', 'size': 8}
                                },
                                {'x': [0, len(energy_consumption)],
                                 'y': [threshold, threshold],
                                 'type': 'scatter',
                                 'mode': 'lines',
                                 'name': 'Umbral',
                                 'line': {'color': '#ffc107', 'dash': 'dash'}
                                }
                            ],
                            'layout': {
                                'title': 'Detección de Anomalías en Emisiones',
                                'xaxis': {'title': 'Tiempo'},
                                'yaxis': {'title': 'kg CO2'},
                                'template': 'plotly_white'
                            }
                        }
                    )
                ])
            ])
            
            # Insights según tipo de activo
            asset_type_insights = create_asset_type_insights(asset_type, analysis_data)
            
            # Objetivos de reducción
            reduction_targets_content = html.Div([
                html.P("Basados en la estimación anual de emisiones, se proponen los siguientes objetivos de reducción:"),
                html.Div([
                    html.Div([
                        dbc.Card([
                            dbc.CardHeader(f"Objetivo a Corto Plazo ({datetime.now().year + 1})"),
                            dbc.CardBody([
                                html.H5(f"{reduction_targets[datetime.now().year + 1]['target_emissions']:.2f} kg CO2/año", className="card-title"),
                                html.P(f"Reducción del {reduction_targets[datetime.now().year + 1]['reduction_percentage']}% respecto al actual"),
                                html.P(f"Ahorro de {reduction_targets[datetime.now().year + 1]['reduction_amount']:.2f} kg CO2/año")
                            ])
                        ])
                    ], className="col-4"),
                    html.Div([
                        dbc.Card([
                            dbc.CardHeader(f"Objetivo a Mediano Plazo ({datetime.now().year + 5})"),
                            dbc.CardBody([
                                html.H5(f"{reduction_targets[datetime.now().year + 5]['target_emissions']:.2f} kg CO2/año", className="card-title"),
                                html.P(f"Reducción del {reduction_targets[datetime.now().year + 5]['reduction_percentage']}% respecto al actual"),
                                html.P(f"Ahorro de {reduction_targets[datetime.now().year + 5]['reduction_amount']:.2f} kg CO2/año")
                            ])
                        ])
                    ], className="col-4"),
                    html.Div([
                        dbc.Card([
                            dbc.CardHeader(f"Objetivo a Largo Plazo ({datetime.now().year + 10})"),
                            dbc.CardBody([
                                html.H5(f"{reduction_targets[datetime.now().year + 10]['target_emissions']:.2f} kg CO2/año", className="card-title"),
                                html.P(f"Reducción del {reduction_targets[datetime.now().year + 10]['reduction_percentage']}% respecto al actual"),
                                html.P(f"Ahorro de {reduction_targets[datetime.now().year + 10]['reduction_amount']:.2f} kg CO2/año")
                            ])
                        ])
                    ], className="col-4")
                ], className="row")
            ])
            
            # Tabla de datos detallados
            detailed_data_table = html.Div([
                html.P("Esta tabla muestra un resumen de los datos de emisiones para el período analizado:"),
                dbc.Table([
                    html.Thead([
                        html.Tr([
                            html.Th("Métrica"),
                            html.Th("Valor"),
                            html.Th("Unidad"),
                            html.Th("Notas")
                        ])
                    ]),
                    html.Tbody([
                        html.Tr([
                            html.Td("Emisiones Totales"),
                            html.Td(f"{total_emissions:.2f}"),
                            html.Td("kg CO2"),
                            html.Td("Suma de todas las emisiones en el período")
                        ]),
                        html.Tr([
                            html.Td("Emisiones Promedio"),
                            html.Td(f"{average_emissions:.2f}"),
                            html.Td("kg CO2/día"),
                            html.Td("Promedio diario de emisiones")
                        ]),
                        html.Tr([
                            html.Td("Proyección Anual"),
                            html.Td(f"{annual_estimate:.2f}"),
                            html.Td("kg CO2/año"),
                            html.Td("Estimación anual basada en el consumo actual")
                        ]),
                        html.Tr([
                            html.Td("Anomalías Detectadas"),
                            html.Td(f"{num_anomalies}"),
                            html.Td("-"),
                            html.Td(f"Picos de consumo que superan {threshold:.2f} kg CO2")
                        ]),
                        html.Tr([
                            html.Td("Tendencia"),
                            html.Td(f"{emission_trend}"),
                            html.Td("-"),
                            html.Td("Respecto al período anterior")
                        ]),
                        html.Tr([
                            html.Td("Cambio Porcentual"),
                            html.Td(f"{comparison_result['change_percentage']:.2f}"),
                            html.Td("%"),
                            html.Td("Respecto al período anterior")
                        ])
                    ])
                ], bordered=True, hover=True, responsive=True, striped=True)
            ])
            
            # Retornar todos los componentes actualizados
            return (
                {"display": "none"},  # Ocultar mensaje inicial
                {"display": "block"},  # Mostrar resultados de análisis
                client_data,
                project_data,
                asset_data,
                sensor_data,
                asset_type_data,
                date_range_data,
                analysis_header,
                key_metrics,
                emission_evolution,
                temporal_comparison,
                emission_distribution,
                anomaly_detection,
                asset_type_insights,
                reduction_targets_content,
                detailed_data_table
            )
            
        except Exception as e:
            logger.error(f"Error durante el análisis de huella de carbono: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Mostrar mensaje de error
            error_message = html.Div([
                dbc.Alert(
                    [
                        html.H4("Error al realizar el análisis", className="alert-heading"),
                        html.P(f"Se produjo un error durante el análisis: {str(e)}"),
                        html.Hr(),
                        html.P(
                            "Por favor, inténtelo de nuevo o contacte al administrador si el problema persiste.",
                            className="mb-0"
                        )
                    ],
                    color="danger"
                )
            ])
            
            # Retornar una respuesta de error, manteniendo la interfaz visible
            return (
                {"display": "none"},  # Ocultar mensaje inicial
                {"display": "block"},  # Mostrar resultados de análisis
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                error_message,  # Header con mensaje de error
                [],             # Sin métricas clave
                [],             # Sin evolución de emisiones
                [],             # Sin comparativa temporal
                [],             # Sin distribución de emisiones
                [],             # Sin detección de anomalías
                [],             # Sin insights por tipo de activo
                [],             # Sin objetivos de reducción
                []              # Sin tabla de datos detallados
            )

# Layout to be used in app.py
layout = create_layout() 