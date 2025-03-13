# layouts/anomaly_config.py
import dash_bootstrap_components as dbc
from dash import html, dcc
from config.feature_flags import is_feature_enabled, enable_feature, disable_feature

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
                
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "Detectar Anomalías",
                            id="btn-detect-anomalies",
                            color="primary",
                            className="me-2"
                        ),
                        dbc.Button(
                            "Visualizar Comparación",
                            id="btn-visualize-comparison",
                            color="secondary"
                        ),
                    ], width=12, className="text-end"),
                ]),
            ]),
        ], className="mb-4"),
        
        # Contenedor para resultados
        html.Div(id="anomaly-detection-results"),
        
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
    from datetime import datetime, timedelta
    
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
    
    # Callback para detectar anomalías
    @app.callback(
        Output("anomaly-detection-results", "children"),
        Input("btn-detect-anomalies", "n_clicks"),
        [State("input-asset-id", "value"),
         State("select-consumption-type", "value"),
         State("slider-reset-threshold", "value")],
        prevent_initial_call=True
    )
    def detect_anomalies(n_clicks, asset_id, consumption_type, threshold):
        if not n_clicks or not asset_id or not consumption_type:
            return html.Div()
        
        # Crear datos de ejemplo para demostración
        # En un entorno real, estos datos vendrían de la base de datos o archivos
        dates = [datetime.now() - timedelta(days=i) for i in range(10)]
        dates.reverse()  # Ordenar cronológicamente
        
        # Simular un reinicio de contador
        data = pd.DataFrame({
            'date': dates,
            'consumption': [100, 110, 120, 130, 140, 50, 60, 70, 80, 90],  # Reinicio después del día 5
            'asset_id': [asset_id] * 10,
            'consumption_type': [consumption_type] * 10
        })
        
        # Configurar el umbral de detección según el valor del slider
        # El slider va de 10 a 90, donde 10 significa que se detecta una caída del 10% o más
        # y 90 significa que se detecta una caída del 90% o más
        detection_threshold = threshold / 100.0
        
        # Crear detector con umbral personalizado
        from utils.anomaly.detector import AnomalyDetector
        detector = AnomalyDetector()
        
        # Modificar la lógica de detección para usar el umbral configurado
        anomalies = []
        for i in range(1, len(data)):
            current = data.iloc[i]
            previous = data.iloc[i-1]
            
            # Calcular la caída relativa
            current_value = current['consumption']
            previous_value = previous['consumption']
            
            # Detectar si el valor actual es menor que el valor anterior * umbral
            # Ejemplo: si umbral=0.8, detecta caídas mayores al 20%
            if current_value < previous_value * (1 - detection_threshold):
                anomalies.append({
                    'type': 'counter_reset',
                    'date': current['date'],
                    'previous_value': previous_value,
                    'current_value': current_value,
                    'asset_id': asset_id,
                    'consumption_type': consumption_type,
                    'offset': previous_value - current_value
                })
        
        # Verificar si se detectaron anomalías
        if anomalies:
            anomaly_count = len(anomalies)
            
            return dbc.Alert([
                html.H4("Anomalías Detectadas", className="alert-heading"),
                html.P(f"Se detectaron {anomaly_count} lecturas con anomalías en el asset {asset_id}."),
                html.Hr(),
                html.P([
                    f"Tipo: {anomalies[0]['type']}, ",
                    f"Fecha: {anomalies[0]['date'].strftime('%Y-%m-%d')}, ",
                    f"Valor anterior: {anomalies[0]['previous_value']}, ",
                    f"Valor actual: {anomalies[0]['current_value']}, ",
                    f"Offset aplicado: {anomalies[0]['offset']}"
                ]),
                html.P(
                    "Haga clic en 'Visualizar Comparación' para ver los datos originales y corregidos.",
                    className="mb-0"
                )
            ], color="warning", className="mt-3")
        else:
            return dbc.Alert([
                html.H4("No se detectaron anomalías", className="alert-heading"),
                html.P(f"No se encontraron anomalías en las lecturas del asset {asset_id} con el umbral actual ({threshold}%)."),
                html.P("Pruebe a reducir el umbral de detección para identificar anomalías más sutiles.")
            ], color="success", className="mt-3")
    
    # Callback para visualizar la comparación
    @app.callback(
        Output("anomaly-comparison-chart", "children"),
        Input("btn-visualize-comparison", "n_clicks"),
        [State("input-asset-id", "value"),
         State("select-consumption-type", "value"),
         State("slider-reset-threshold", "value")],
        prevent_initial_call=True
    )
    def visualize_comparison(n_clicks, asset_id, consumption_type, threshold):
        if not n_clicks or not asset_id or not consumption_type:
            return html.Div()
        
        # Crear datos de ejemplo para demostración
        dates = [datetime.now() - timedelta(days=i) for i in range(10)]
        dates.reverse()  # Ordenar cronológicamente
        
        # Simular un reinicio de contador
        original_data = pd.DataFrame({
            'date': dates,
            'consumption': [100, 110, 120, 130, 140, 50, 60, 70, 80, 90],  # Reinicio después del día 5
            'asset_id': [asset_id] * 10,
            'consumption_type': [consumption_type] * 10
        })
        
        # Configurar el umbral de detección según el valor del slider
        detection_threshold = threshold / 100.0
        
        # Crear detector con umbral personalizado
        from utils.anomaly.detector import AnomalyDetector
        detector = AnomalyDetector()
        
        # Detectar anomalías usando el mismo método que en detect_anomalies
        anomalies = []
        for i in range(1, len(original_data)):
            current = original_data.iloc[i]
            previous = original_data.iloc[i-1]
            
            current_value = current['consumption']
            previous_value = previous['consumption']
            
            if current_value < previous_value * (1 - detection_threshold):
                anomalies.append({
                    'type': 'counter_reset',
                    'date': current['date'],
                    'previous_value': previous_value,
                    'current_value': current_value,
                    'asset_id': asset_id,
                    'consumption_type': consumption_type,
                    'offset': previous_value - current_value
                })
        
        # Crear datos corregidos
        corrected_data = original_data.copy()
        corrected_data['corrected_value'] = original_data['consumption'].copy()
        corrected_data['is_corrected'] = False
        
        # Aplicar correcciones si se detectaron anomalías
        if anomalies:
            # Ordenar anomalías por fecha
            anomalies = sorted(anomalies, key=lambda x: x['date'])
            
            # Aplicar correcciones para cada anomalía
            for anomaly in anomalies:
                # Encontrar el índice de la fecha de la anomalía
                idx = corrected_data[corrected_data['date'] == anomaly['date']].index
                
                if len(idx) > 0:
                    # Obtener el offset
                    offset = anomaly['offset']
                    
                    # Aplicar el offset a todas las lecturas posteriores
                    corrected_data.loc[idx[0]:, 'corrected_value'] = \
                        corrected_data.loc[idx[0]:, 'consumption'] + offset
                    
                    # Marcar como corregidas
                    corrected_data.loc[idx[0]:, 'is_corrected'] = True
        
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