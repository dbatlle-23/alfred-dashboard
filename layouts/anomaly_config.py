# layouts/anomaly_config.py
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from config.feature_flags import is_feature_enabled, enable_feature, disable_feature
import logging
from utils.logging import get_logger
from datetime import datetime, timedelta

# Configurar logger
logger = get_logger(__name__)

# Layout principal de la página de configuración de anomalías
layout = html.Div([
    dbc.Container([
        # Título de la página
        html.H2("Configuración de Detección de Anomalías", className="mb-4"),
        
        # Descripción
        html.P([
            "Esta página permite configurar el sistema de detección y corrección de anomalías en lecturas de sensores. ",
            "El sistema puede detectar automáticamente reinicios de contadores y aplicar correcciones para mantener la continuidad de los datos."
        ], className="mb-4"),
        
        # Tarjeta de feature flags
        dbc.Card([
            dbc.CardHeader("Feature Flags"),
            dbc.CardBody([
                # Feature flag: Detección de anomalías
                dbc.Row([
                    dbc.Col([
                        html.H5("Detección de Anomalías"),
                        html.P("Habilita la detección automática de anomalías en las lecturas de sensores."),
                    ], width=8),
                    dbc.Col([
                        dbc.Switch(
                            id="switch-anomaly-detection",
                            value=is_feature_enabled("enable_anomaly_detection"),
                            label=["Activado", "Desactivado"],
                            className="mt-2"
                        ),
                    ], width=4, className="text-end"),
                ], className="mb-3"),
                
                # Feature flag: Visualización de anomalías
                dbc.Row([
                    dbc.Col([
                        html.H5("Visualización de Anomalías"),
                        html.P("Muestra gráficos comparativos entre datos originales y corregidos."),
                    ], width=8),
                    dbc.Col([
                        dbc.Switch(
                            id="switch-anomaly-visualization",
                            value=is_feature_enabled("enable_anomaly_visualization"),
                            label=["Activado", "Desactivado"],
                            className="mt-2"
                        ),
                    ], width=4, className="text-end"),
                ], className="mb-3"),
                
                # Feature flag: Corrección de anomalías
                dbc.Row([
                    dbc.Col([
                        html.H5("Corrección de Anomalías"),
                        html.P("Aplica correcciones automáticas a las lecturas con anomalías detectadas."),
                    ], width=8),
                    dbc.Col([
                        dbc.Switch(
                            id="switch-anomaly-correction",
                            value=is_feature_enabled("enable_anomaly_correction"),
                            label=["Activado", "Desactivado"],
                            className="mt-2"
                        ),
                    ], width=4, className="text-end"),
                ]),
            ]),
        ], className="mb-4"),
        
        # Tarjeta de configuración de detección
        dbc.Card([
            dbc.CardHeader("Configuración de Detección"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Umbral de Detección de Reinicios (%)"),
                        dcc.Slider(
                            id="slider-reset-threshold",
                            min=10,
                            max=90,
                            step=5,
                            value=80,
                            marks={i: f"{i}%" for i in range(10, 91, 10)},
                            className="mt-2"
                        ),
                        html.Small(
                            "Un valor más bajo detectará más anomalías pero puede generar falsos positivos.",
                            className="text-muted"
                        ),
                    ], width=12),
                ]),
            ]),
        ], className="mb-4"),
        
        # Tarjeta de prueba
        dbc.Card([
            dbc.CardHeader("Prueba de Detección"),
            dbc.CardBody([
                # Switch para seleccionar entre datos de ejemplo y datos reales
                dbc.Row([
                    dbc.Col([
                        html.H5("Origen de Datos"),
                        html.P("Seleccione si desea usar datos de ejemplo o datos reales para las pruebas."),
                    ], width=8),
                    dbc.Col([
                        dbc.Switch(
                            id="switch-use-real-data",
                            value=False,
                            label=["Datos Reales", "Datos de Ejemplo"],
                            className="mt-2"
                        ),
                    ], width=4, className="text-end"),
                ], className="mb-3"),
                
                # Campos para configurar la prueba
                dbc.Row([
                    dbc.Col([
                        html.Label("Asset ID"),
                        dbc.Input(
                            id="input-asset-id",
                            type="text",
                            placeholder="Ingrese el ID del asset",
                            className="mb-2"
                        ),
                    ], width=6),
                    dbc.Col([
                        html.Label("Tipo de Consumo"),
                        dbc.Select(
                            id="select-consumption-type",
                            options=[
                                {"label": "Agua fría sanitaria", "value": "Agua fría sanitaria"},
                                {"label": "Energía general", "value": "Energía general"},
                                {"label": "Agua caliente sanitaria", "value": "Agua caliente sanitaria"},
                                {"label": "Agua general", "value": "Agua general"},
                                {"label": "Energía térmica frío", "value": "Energía térmica frío"},
                                {"label": "Energía térmica calor", "value": "Energía térmica calor"}
                            ],
                            className="mb-2"
                        ),
                    ], width=6),
                ], className="mb-3"),
                
                # Selector de fechas (visible solo cuando se usan datos reales)
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Fecha de Inicio"),
                            dcc.DatePickerSingle(
                                id="date-picker-start",
                                date=None,
                                display_format="YYYY-MM-DD",
                                placeholder="Seleccione fecha de inicio",
                                className="mb-2"
                            ),
                        ], width=6),
                        dbc.Col([
                            html.Label("Fecha de Fin"),
                            dcc.DatePickerSingle(
                                id="date-picker-end",
                                date=None,
                                display_format="YYYY-MM-DD",
                                placeholder="Seleccione fecha de fin",
                                className="mb-2"
                            ),
                        ], width=6),
                    ]),
                ], id="date-picker-container", style={"display": "none"}),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "Detectar Anomalías",
                            id="btn-detect-anomalies",
                            color="primary",
                            className="me-2",
                            n_clicks=0  # Inicializar n_clicks
                        ),
                        dbc.Button(
                            "Visualizar Comparación",
                            id="btn-visualize-comparison",
                            color="secondary",
                            n_clicks=0  # Inicializar n_clicks
                        ),
                    ], width=12, className="text-end"),
                ]),
                
                # Añadir un div para mostrar el estado de los clics (para depuración)
                html.Div(id="debug-clicks", className="mt-3 small text-muted"),
            ]),
        ], className="mb-4"),
        
        # Contenedor para resultados
        html.Div(id="anomaly-detection-results"),
        
        # Componente para reclasificar anomalías
        html.Div([
            dbc.Card([
                dbc.CardHeader("Reclasificación de Anomalías"),
                dbc.CardBody([
                    html.P("Si se ha detectado un reinicio de contador pero en realidad es un reemplazo de sensor, puede reclasificar la anomalía aquí."),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Fecha de la anomalía"),
                            dcc.DatePickerSingle(
                                id="date-picker-anomaly",
                                date=None,
                                display_format="YYYY-MM-DD",
                                placeholder="Seleccione fecha de la anomalía",
                                className="mb-2"
                            ),
                        ], width=6),
                        dbc.Col([
                            html.Label("Nuevo tipo"),
                            dcc.Dropdown(
                                id="select-anomaly-type",
                                options=[
                                    {"label": "Reinicio de contador", "value": "counter_reset"},
                                    {"label": "Reemplazo de sensor", "value": "sensor_replacement"}
                                ],
                                value="sensor_replacement",
                                clearable=False,
                                className="mb-2"
                            ),
                        ], width=6),
                    ]),
                    dbc.Button(
                        "Reclasificar Anomalía",
                        id="btn-reclassify-anomaly",
                        color="warning",
                        className="mt-2",
                        n_clicks=0
                    ),
                ]),
            ], className="mb-4"),
        ], id="anomaly-reclassification-container", style={"display": "none"}),
        
        # Gráfico de comparación
        html.Div(id="anomaly-comparison-chart"),
        
    ], fluid=True)
])

# Función para registrar callbacks
def register_callbacks(app):
    """
    Registra los callbacks para la página de configuración de anomalías
    
    Args:
        app: Instancia de la aplicación Dash
    """
    from dash.dependencies import Input, Output, State
    from utils.adapters.anomaly_adapter import AnomalyAdapter
    from components.metrics.anomaly.comparison_chart import create_anomaly_comparison_chart
    import pandas as pd
    import json
    import traceback
    
    # Callback para actualizar el feature flag de detección de anomalías
    @app.callback(
        Output("switch-anomaly-detection", "value"),
        Input("switch-anomaly-detection", "value")
    )
    def update_anomaly_detection_flag(value):
        if value:
            enable_feature("enable_anomaly_detection")
        else:
            disable_feature("enable_anomaly_detection")
        return value
    
    # Callback para actualizar el feature flag de visualización de anomalías
    @app.callback(
        Output("switch-anomaly-visualization", "value"),
        Input("switch-anomaly-visualization", "value")
    )
    def update_anomaly_visualization_flag(value):
        if value:
            enable_feature("enable_anomaly_visualization")
        else:
            disable_feature("enable_anomaly_visualization")
        return value
    
    # Callback para actualizar el feature flag de corrección de anomalías
    @app.callback(
        Output("switch-anomaly-correction", "value"),
        Input("switch-anomaly-correction", "value")
    )
    def update_anomaly_correction_flag(value):
        if value:
            enable_feature("enable_anomaly_correction")
        else:
            disable_feature("enable_anomaly_correction")
        return value
    
    # Callback para mostrar/ocultar el selector de fechas según el origen de datos
    @app.callback(
        Output("date-picker-container", "style"),
        Input("switch-use-real-data", "value")
    )
    def toggle_date_picker(use_real_data):
        if use_real_data:
            return {"display": "block"}
        else:
            return {"display": "none"}
    
    # Callback para depurar los clics en los botones
    @app.callback(
        Output("debug-clicks", "children"),
        [Input("btn-detect-anomalies", "n_clicks"),
         Input("btn-visualize-comparison", "n_clicks")],
        prevent_initial_call=True
    )
    def debug_button_clicks(detect_clicks, visualize_clicks):
        """Callback para depurar los clics en los botones"""
        from dash import callback_context
        
        # Determinar qué botón se hizo clic
        ctx = callback_context
        if not ctx.triggered:
            button_id = "No se ha hecho clic en ningún botón"
        else:
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        logger.info(f"Botón clicado: {button_id}, detect_clicks={detect_clicks}, visualize_clicks={visualize_clicks}")
        
        return f"Botón clicado: {button_id}, Detectar: {detect_clicks}, Visualizar: {visualize_clicks}"
    
    # Función para obtener datos reales
    def get_real_data(asset_id, consumption_type, start_date=None, end_date=None, jwt_token=None):
        try:
            # Importar las funciones necesarias
            from utils.api import get_sensors_with_tags, get_sensor_value_for_date
            import logging
            import os
            import glob
            
            # Configurar logger
            logger = logging.getLogger(__name__)
            
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
                logger.warning(f"No se pudo mapear el tipo de consumo: '{consumption_type}' a un tag de consumo.")
                return None
            
            # Primero intentar cargar datos desde archivos CSV locales
            logger.info(f"Buscando archivos CSV locales para el asset {asset_id} con tag {consumption_tag}")
            
            # Buscar en la carpeta de datos analizados
            analyzed_data_folder = os.path.join("data", "analyzed_data")
            matching_files = []
            
            if os.path.exists(analyzed_data_folder):
                # Buscar en todas las carpetas de proyectos
                for project_folder in os.listdir(analyzed_data_folder):
                    project_path = os.path.join(analyzed_data_folder, project_folder)
                    if os.path.isdir(project_path):
                        # Buscar archivos que coincidan con el patrón
                        for filename in os.listdir(project_path):
                            if filename.startswith(f"daily_readings_{asset_id}__") and consumption_tag in filename and filename.endswith(".csv"):
                                file_path = os.path.join(project_path, filename)
                                matching_files.append({
                                    "project_id": project_folder,
                                    "filename": filename,
                                    "full_path": file_path
                                })
            
            # Si encontramos archivos CSV, cargar los datos
            if matching_files:
                logger.info(f"Se encontraron {len(matching_files)} archivos CSV para el asset {asset_id}")
                
                # Usar el primer archivo encontrado
                file_path = matching_files[0]["full_path"]
                logger.info(f"Cargando datos desde {file_path}")
                
                try:
                    # Cargar el archivo CSV
                    csv_data = pd.read_csv(file_path)
                    
                    # Convertir la columna de fecha a datetime
                    if 'date' in csv_data.columns:
                        csv_data['date'] = pd.to_datetime(csv_data['date'])
                    
                    # Filtrar por fechas si se proporcionan
                    if start_date and end_date:
                        # Convertir fechas a objetos datetime si son strings
                        if isinstance(start_date, str):
                            start_date = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d")
                        if isinstance(end_date, str):
                            end_date = datetime.strptime(end_date.split("T")[0], "%Y-%m-%d")
                        
                        # Filtrar por rango de fechas
                        csv_data = csv_data[(csv_data['date'] >= start_date) & (csv_data['date'] <= end_date)]
                    
                    # Verificar si hay datos después del filtrado
                    if csv_data.empty:
                        logger.warning(f"No hay datos en el rango de fechas seleccionado en el archivo CSV")
                    else:
                        # Convertir los valores a numéricos
                        if 'value' in csv_data.columns:
                            # Filtrar solo valores numéricos
                            csv_data = csv_data[csv_data['value'] != 'Error']
                            csv_data = csv_data[csv_data['value'] != 'Sin datos disponibles']
                            
                            try:
                                # Convertir a numérico
                                csv_data['consumption'] = pd.to_numeric(csv_data['value'], errors='coerce')
                                
                                # Eliminar filas con valores NaN
                                csv_data = csv_data.dropna(subset=['consumption'])
                                
                                # Añadir columnas necesarias
                                csv_data['asset_id'] = asset_id
                                csv_data['consumption_type'] = consumption_type
                                
                                # Seleccionar solo las columnas necesarias
                                result_df = csv_data[['date', 'consumption', 'asset_id', 'consumption_type']]
                                
                                logger.info(f"Se cargaron {len(result_df)} lecturas válidas desde el archivo CSV")
                                return result_df
                            except Exception as e:
                                logger.error(f"Error al convertir valores a numéricos: {str(e)}")
                
                except Exception as e:
                    logger.error(f"Error al cargar datos desde el archivo CSV: {str(e)}")
            
            # Si no se encontraron archivos CSV o hubo un error al cargarlos, intentar con la API
            logger.info(f"No se encontraron datos locales válidos, intentando obtener datos desde la API")
            
            # Verificar si tenemos un token JWT válido
            if not jwt_token:
                logger.error("No se proporcionó un token JWT para obtener datos reales")
                return None
                
            # Obtener los sensores asociados al asset
            logger.info(f"Obteniendo sensores para el asset {asset_id} con tag {consumption_tag}")
            sensors = get_sensors_with_tags(asset_id, jwt_token)
            
            if not sensors:
                logger.warning(f"No se encontraron sensores para el asset {asset_id}")
                return None
            
            # Filtrar los sensores por el tag de consumo
            matching_sensors = []
            for sensor in sensors:
                tag_name = sensor.get("tag_name", "")
                if consumption_tag in tag_name:
                    matching_sensors.append(sensor)
            
            if not matching_sensors:
                logger.warning(f"No se encontraron sensores para el tag {consumption_tag}")
                return None
            
            # Generar fechas para obtener datos
            if start_date and end_date:
                # Convertir fechas a objetos datetime si son strings
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d")
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date.split("T")[0], "%Y-%m-%d")
                
                # Generar lista de fechas entre start_date y end_date
                delta = end_date - start_date
                dates = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
            else:
                # Si no se proporcionan fechas, usar los últimos 30 días
                current_date = datetime.now()
                dates = [current_date - timedelta(days=i) for i in range(30)]
                dates.reverse()  # Ordenar cronológicamente
            
            # Obtener lecturas para cada sensor y fecha
            readings = []
            
            # Usar el primer sensor que coincida con el tag
            sensor = matching_sensors[0]
            device_id = sensor.get("device_id")
            sensor_id = sensor.get("sensor_id")
            gateway_id = sensor.get("gateway_id")
            tag_name = sensor.get("tag_name")
            
            logger.info(f"Obteniendo lecturas para el sensor: device_id={device_id}, sensor_id={sensor_id}, gateway_id={gateway_id}")
            
            for date in dates:
                try:
                    # Formatear fecha para la API (MM-DD-YYYY)
                    formatted_date_api = date.strftime("%m-%d-%Y")
                    
                    # Obtener lectura para esta fecha
                    value, timestamp = get_sensor_value_for_date(
                        asset_id=asset_id,
                        device_id=device_id,
                        sensor_id=sensor_id,
                        gateway_id=gateway_id,
                        date=formatted_date_api,
                        token=jwt_token
                    )
                    
                    # Si se obtuvo un valor válido, añadirlo a las lecturas
                    if value != "Sin datos disponibles" and value != "Error":
                        try:
                            # Convertir valor a número
                            numeric_value = float(value)
                            
                            # Añadir lectura
                            readings.append({
                                'date': date,
                                'consumption': numeric_value,
                                'asset_id': asset_id,
                                'consumption_type': consumption_type
                            })
                        except (ValueError, TypeError):
                            logger.warning(f"No se pudo convertir el valor '{value}' a número para la fecha {date}")
                    
                except Exception as e:
                    logger.error(f"Error al obtener lectura para la fecha {date}: {str(e)}")
            
            # Crear DataFrame con las lecturas
            if readings:
                df = pd.DataFrame(readings)
                logger.info(f"Se obtuvieron {len(readings)} lecturas válidas desde la API para el asset {asset_id}")
                return df
            else:
                logger.warning("No se obtuvieron lecturas válidas desde la API")
                return None
            
        except Exception as e:
            import traceback
            logger.error(f"Error al obtener datos reales: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    # Callback para detectar anomalías
    @app.callback(
        Output("anomaly-detection-results", "children"),
        Input("btn-detect-anomalies", "n_clicks"),
        [State("input-asset-id", "value"),
         State("select-consumption-type", "value"),
         State("slider-reset-threshold", "value"),
         State("switch-use-real-data", "value"),
         State("date-picker-start", "date"),
         State("date-picker-end", "date"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def detect_anomalies(n_clicks, asset_id, consumption_type, threshold, use_real_data, start_date, end_date, token_data):
        logger.info(f"Callback detect_anomalies ejecutado: n_clicks={n_clicks}, asset_id={asset_id}, consumption_type={consumption_type}")
        
        if not n_clicks or not asset_id or not consumption_type:
            logger.warning("Callback detect_anomalies: Faltan parámetros requeridos")
            return html.Div()
        
        try:
            # Configurar el umbral de detección según el valor del slider
            detection_threshold = threshold / 100.0
            logger.info(f"Umbral de detección configurado: {detection_threshold} (slider: {threshold}%)")
            
            # Obtener el token JWT si está disponible
            jwt_token = None
            if token_data and "token" in token_data:
                jwt_token = token_data["token"]
                logger.debug(f"Token JWT obtenido: {jwt_token[:10]}...")
            else:
                logger.warning("No se encontró token JWT en token_data")
            
            # Obtener datos según la fuente seleccionada
            if use_real_data:
                logger.info("Usando datos reales para la detección de anomalías")
                # Verificar si tenemos un token JWT válido
                if not jwt_token:
                    logger.error("No hay token JWT válido para obtener datos reales")
                    return dbc.Alert([
                        html.H4("Error de autenticación", className="alert-heading"),
                        html.P("No se pudo obtener un token JWT válido para consultar datos reales."),
                        html.P("Por favor, inicie sesión nuevamente o pruebe con datos de ejemplo desactivando la opción 'Datos Reales'.")
                    ], color="danger", className="mt-3")
                    
                # Obtener datos reales
                data = get_real_data(asset_id, consumption_type, start_date, end_date, jwt_token)
                
                if data is None or data.empty:
                    logger.error(f"No se pudieron obtener datos reales para asset_id={asset_id}, consumption_type={consumption_type}")
                    return dbc.Alert([
                        html.H4("Error al obtener datos reales", className="alert-heading"),
                        html.P(f"No se pudieron obtener datos reales para el asset {asset_id} y tipo de consumo {consumption_type}."),
                        html.P("Verifique que el asset y el tipo de consumo sean correctos y que existan datos para el período seleccionado."),
                        html.P("También puede probar con datos de ejemplo desactivando la opción 'Datos Reales'.")
                    ], color="danger", className="mt-3")
            else:
                logger.info("Usando datos de ejemplo para la detección de anomalías")
                # Crear datos de ejemplo para demostración
                current_date = datetime.now()
                dates = [current_date - timedelta(days=i) for i in range(10)]
                dates.reverse()  # Ordenar cronológicamente
                
                # Simular un reinicio de contador
                data = pd.DataFrame({
                    'date': dates,
                    'consumption': [100, 110, 120, 130, 140, 50, 60, 70, 80, 90],  # Reinicio después del día 5
                    'asset_id': [asset_id] * 10,
                    'consumption_type': [consumption_type] * 10
                })
                logger.debug(f"Datos de ejemplo creados: {len(data)} registros")
            
            # Crear detector con umbral personalizado y repositorio
            from utils.anomaly.detector import AnomalyDetector
            from utils.repositories.reading_repository import ReadingRepository
            
            repository = ReadingRepository()
            detector = AnomalyDetector(repository)
            logger.debug("Detector de anomalías creado")
            
            # Detectar anomalías con la opción de detectar reemplazos de sensores
            # Esto permitirá que el detector identifique automáticamente posibles reemplazos de sensores
            anomalies = detector.detect_counter_resets(data, detect_sensor_replacements=True)
            
            # Verificar si se detectaron anomalías
            if anomalies:
                anomaly_count = len(anomalies)
                logger.info(f"Se detectaron {anomaly_count} anomalías")
                
                # Crear mensaje con información sobre las anomalías detectadas
                anomaly_info = []
                for i, anomaly in enumerate(anomalies):
                    anomaly_type = anomaly['type']
                    anomaly_date = anomaly['date']
                    if isinstance(anomaly_date, str):
                        anomaly_date = datetime.fromisoformat(anomaly_date.replace('Z', '+00:00'))
                    
                    anomaly_info.append(html.P([
                        f"Tipo: {anomaly_type}, ",
                        f"Fecha: {anomaly_date.strftime('%Y-%m-%d')}, ",
                        f"Valor anterior: {anomaly['previous_value']}, ",
                        f"Valor actual: {anomaly['current_value']}, ",
                        f"Offset aplicado: {anomaly['offset']}"
                    ]))
                
                return dbc.Alert([
                    html.H4("Anomalías Detectadas", className="alert-heading"),
                    html.P(f"Se detectaron {anomaly_count} lecturas con anomalías en el asset {asset_id}."),
                    html.Hr(),
                    *anomaly_info,
                    html.P(
                        "Haga clic en 'Visualizar Comparación' para ver los datos originales y corregidos.",
                        className="mb-0"
                    )
                ], color="warning", className="mt-3")
            else:
                logger.info("No se detectaron anomalías")
                return dbc.Alert([
                    html.H4("No se detectaron anomalías", className="alert-heading"),
                    html.P(f"No se encontraron anomalías en las lecturas del asset {asset_id} con el umbral actual ({threshold}%)."),
                    html.P("Pruebe a reducir el umbral de detección para identificar anomalías más sutiles.")
                ], color="success", className="mt-3")
        except Exception as e:
            logger.error(f"Error en detect_anomalies: {str(e)}")
            logger.error(traceback.format_exc())
            return dbc.Alert([
                html.H4("Error en la detección de anomalías", className="alert-heading"),
                html.P(f"Se produjo un error al procesar los datos: {str(e)}"),
                html.Pre(traceback.format_exc(), className="small text-muted")
            ], color="danger", className="mt-3")
    
    # Callback para visualizar la comparación
    @app.callback(
        Output("anomaly-comparison-chart", "children"),
        Input("btn-visualize-comparison", "n_clicks"),
        [State("input-asset-id", "value"),
         State("select-consumption-type", "value"),
         State("slider-reset-threshold", "value"),
         State("switch-use-real-data", "value"),
         State("date-picker-start", "date"),
         State("date-picker-end", "date"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def visualize_comparison(n_clicks, asset_id, consumption_type, threshold, use_real_data, start_date, end_date, token_data):
        logger.info(f"Callback visualize_comparison ejecutado: n_clicks={n_clicks}, asset_id={asset_id}, consumption_type={consumption_type}")
        
        if not n_clicks or not asset_id or not consumption_type:
            logger.warning("Callback visualize_comparison: Faltan parámetros requeridos")
            return html.Div()
        
        try:
            # Configurar el umbral de detección según el valor del slider
            detection_threshold = threshold / 100.0
            logger.info(f"Umbral de detección configurado: {detection_threshold} (slider: {threshold}%)")
            
            # Obtener el token JWT si está disponible
            jwt_token = None
            if token_data and "token" in token_data:
                jwt_token = token_data["token"]
                logger.debug(f"Token JWT obtenido: {jwt_token[:10]}...")
            else:
                logger.warning("No se encontró token JWT en token_data")
            
            # Obtener datos según la fuente seleccionada
            if use_real_data:
                logger.info("Usando datos reales para la visualización de comparación")
                # Verificar si tenemos un token JWT válido
                if not jwt_token:
                    logger.error("No hay token JWT válido para obtener datos reales")
                    return dbc.Alert([
                        html.H4("Error de autenticación", className="alert-heading"),
                        html.P("No se pudo obtener un token JWT válido para consultar datos reales."),
                        html.P("Por favor, inicie sesión nuevamente o pruebe con datos de ejemplo desactivando la opción 'Datos Reales'.")
                    ], color="danger", className="mt-3")
                    
                # Obtener datos reales
                original_data = get_real_data(asset_id, consumption_type, start_date, end_date, jwt_token)
                
                if original_data is None or original_data.empty:
                    logger.error(f"No se pudieron obtener datos reales para asset_id={asset_id}, consumption_type={consumption_type}")
                    return dbc.Alert([
                        html.H4("Error al obtener datos reales", className="alert-heading"),
                        html.P(f"No se pudieron obtener datos reales para el asset {asset_id} y tipo de consumo {consumption_type}."),
                        html.P("Verifique que el asset y el tipo de consumo sean correctos y que existan datos para el período seleccionado."),
                        html.P("También puede probar con datos de ejemplo desactivando la opción 'Datos Reales'.")
                    ], color="danger", className="mt-3")
            else:
                logger.info("Usando datos de ejemplo para la visualización de comparación")
                # Crear datos de ejemplo para demostración
                current_date = datetime.now()
                dates = [current_date - timedelta(days=i) for i in range(10)]
                dates.reverse()  # Ordenar cronológicamente
                
                # Simular un reinicio de contador
                original_data = pd.DataFrame({
                    'date': dates,
                    'consumption': [100, 110, 120, 130, 140, 50, 60, 70, 80, 90],  # Reinicio después del día 5
                    'asset_id': [asset_id] * 10,
                    'consumption_type': [consumption_type] * 10
                })
                logger.debug(f"Datos de ejemplo creados: {len(original_data)} registros")
            
            # Obtener anomalías desde el repositorio en lugar de detectarlas nuevamente
            # Esto asegura que se usen las anomalías reclasificadas
            from utils.repositories.reading_repository import ReadingRepository
            repository = ReadingRepository()
            anomalies = repository.get_anomalies(
                asset_id=asset_id,
                consumption_type=consumption_type,
                start_date=start_date,
                end_date=end_date
            )
            
            # Si no hay anomalías en el repositorio, detectarlas
            if not anomalies:
                logger.info("No se encontraron anomalías en el repositorio, detectando nuevas anomalías")
                from utils.anomaly.detector import AnomalyDetector
                detector = AnomalyDetector(repository)
                
                # Detectar anomalías con la opción de detectar reemplazos de sensores
                anomalies = detector.detect_counter_resets(original_data, detect_sensor_replacements=True)
            else:
                logger.info(f"Se encontraron {len(anomalies)} anomalías en el repositorio")
                # Imprimir información de las anomalías para depuración
                for i, anomaly in enumerate(anomalies):
                    logger.debug(f"Anomalía {i+1}: tipo={anomaly['type']}, fecha={anomaly['date']}")
            
            # Crear datos corregidos
            corrected_data = original_data.copy()
            corrected_data['corrected_value'] = original_data['consumption'].copy()
            corrected_data['is_corrected'] = False
            
            # Aplicar correcciones usando el corrector
            from utils.anomaly.corrector import AnomalyCorrector
            corrector = AnomalyCorrector()
            corrected_data = corrector.correct_counter_resets(corrected_data, anomalies)
            
            # Crear resultado
            result = {
                'original': original_data,
                'corrected': corrected_data,
                'anomalies': anomalies
            }
            
            # Crear gráfico de comparación
            return html.Div([
                html.H4("Comparación de Datos Originales vs. Corregidos", className="mt-4 mb-3"),
                create_anomaly_comparison_chart(result)
            ], className="mt-3")
        except Exception as e:
            logger.error(f"Error en visualize_comparison: {str(e)}")
            logger.error(traceback.format_exc())
            return dbc.Alert([
                html.H4("Error en la visualización de comparación", className="alert-heading"),
                html.P(f"Se produjo un error al procesar los datos: {str(e)}"),
                html.Pre(traceback.format_exc(), className="small text-muted")
            ], color="danger", className="mt-3")
    
    # Añadir callback para mostrar/ocultar el contenedor de reclasificación
    @app.callback(
        Output("anomaly-reclassification-container", "style"),
        Input("anomaly-detection-results", "children")
    )
    def toggle_reclassification_container(results):
        if results:
            return {"display": "block"}
        return {"display": "none"}
    
    # Callback para reclasificar anomalías
    @app.callback(
        [Output("anomaly-detection-results", "children", allow_duplicate=True),
         Output("anomaly-comparison-chart", "children", allow_duplicate=True)],
        Input("btn-reclassify-anomaly", "n_clicks"),
        [State("input-asset-id", "value"),
         State("select-consumption-type", "value"),
         State("date-picker-anomaly", "date"),
         State("select-anomaly-type", "value"),
         State("switch-use-real-data", "value"),
         State("date-picker-start", "date"),
         State("date-picker-end", "date"),
         State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def reclassify_anomaly(n_clicks, asset_id, consumption_type, anomaly_date, new_type, use_real_data, start_date, end_date, token_data):
        if not n_clicks or not asset_id or not consumption_type or not anomaly_date:
            return dash.no_update, dash.no_update
        
        logger.info(f"Reclasificando anomalía: asset_id={asset_id}, consumption_type={consumption_type}, fecha={anomaly_date}, nuevo_tipo={new_type}")
        
        try:
            # Crear instancia del detector
            from utils.anomaly.detector import AnomalyDetector
            from utils.repositories.reading_repository import ReadingRepository
            
            repository = ReadingRepository()
            detector = AnomalyDetector(repository)
            
            # Obtener anomalías para el asset y tipo de consumo
            anomalies = repository.get_anomalies(
                asset_id=asset_id,
                consumption_type=consumption_type
            )
            
            # Buscar la anomalía por fecha
            try:
                if isinstance(anomaly_date, str):
                    anomaly_datetime = datetime.fromisoformat(anomaly_date.replace('Z', '+00:00'))
                else:
                    anomaly_datetime = anomaly_date
            except ValueError:
                # Intentar otro formato común
                try:
                    anomaly_datetime = datetime.strptime(anomaly_date.split('T')[0], '%Y-%m-%d')
                except ValueError:
                    logger.error(f"No se pudo convertir la fecha de anomalía: {anomaly_date}")
                    return dbc.Alert(
                        f"Error al procesar la fecha de anomalía: {anomaly_date}. Formato no válido.",
                        color="danger",
                        className="mt-3"
                    ), dash.no_update
            
            target_anomaly = None
            for anomaly in anomalies:
                anomaly_date = anomaly['date']
                if isinstance(anomaly_date, str):
                    anomaly_date = datetime.fromisoformat(anomaly_date.replace('Z', '+00:00'))
                
                # Comparar solo la fecha (ignorar la hora)
                if (anomaly_date.year == anomaly_datetime.year and 
                    anomaly_date.month == anomaly_datetime.month and 
                    anomaly_date.day == anomaly_datetime.day):
                    target_anomaly = anomaly
                    break
            
            if not target_anomaly:
                return dbc.Alert(
                    f"No se encontró ninguna anomalía para el asset {asset_id} en la fecha {anomaly_date}",
                    color="warning",
                    className="mt-3"
                ), dash.no_update
            
            # Reclasificar la anomalía
            updated_anomaly = detector.reclassify_anomaly(target_anomaly, new_type)
            logger.info(f"Anomalía reclasificada: {updated_anomaly}")
            
            # Mensaje de éxito
            success_message = dbc.Alert([
                html.H4("Anomalía reclasificada correctamente", className="alert-heading"),
                html.P(f"La anomalía del {anomaly_date} ha sido reclasificada como '{new_type}'."),
                html.P("Se ha actualizado la visualización con la nueva clasificación.")
            ], color="success", className="mt-3")
            
            # Actualizar la visualización con la nueva clasificación
            # Obtener datos según la fuente seleccionada
            if use_real_data:
                # Obtener el token JWT si está disponible
                jwt_token = None
                if token_data and "token" in token_data:
                    jwt_token = token_data["token"]
                
                # Obtener datos reales
                original_data = get_real_data(asset_id, consumption_type, start_date, end_date, jwt_token)
                
                if original_data is None or original_data.empty:
                    return success_message, dash.no_update
            else:
                # Crear datos de ejemplo para demostración
                current_date = datetime.now()
                dates = [current_date - timedelta(days=i) for i in range(10)]
                dates.reverse()  # Ordenar cronológicamente
                
                # Simular un reinicio de contador
                original_data = pd.DataFrame({
                    'date': dates,
                    'consumption': [100, 110, 120, 130, 140, 50, 60, 70, 80, 90],  # Reinicio después del día 5
                    'asset_id': [asset_id] * 10,
                    'consumption_type': [consumption_type] * 10
                })
            
            # Obtener anomalías actualizadas desde el repositorio
            updated_anomalies = repository.get_anomalies(
                asset_id=asset_id,
                consumption_type=consumption_type,
                start_date=start_date,
                end_date=end_date
            )
            
            # Crear datos corregidos
            corrected_data = original_data.copy()
            corrected_data['corrected_value'] = original_data['consumption'].copy()
            corrected_data['is_corrected'] = False
            
            # Aplicar correcciones usando el corrector
            from utils.anomaly.corrector import AnomalyCorrector
            corrector = AnomalyCorrector()
            corrected_data = corrector.correct_counter_resets(corrected_data, updated_anomalies)
            
            # Crear resultado
            result = {
                'original': original_data,
                'corrected': corrected_data,
                'anomalies': updated_anomalies
            }
            
            # Crear gráfico de comparación actualizado
            updated_chart = html.Div([
                html.H4("Comparación de Datos Originales vs. Corregidos (Actualizado)", className="mt-4 mb-3"),
                create_anomaly_comparison_chart(result)
            ], className="mt-3")
            
            return success_message, updated_chart
            
        except Exception as e:
            logger.error(f"Error al reclasificar anomalía: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            error_message = dbc.Alert([
                html.H4("Error al reclasificar anomalía", className="alert-heading"),
                html.P(f"Se produjo un error: {str(e)}")
            ], color="danger", className="mt-3")
            return error_message, dash.no_update 