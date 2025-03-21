import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, callback_context
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
from dash.exceptions import PreventUpdate
from utils.logging import get_logger
from utils.error_handlers import handle_exceptions

# Configurar logger
logger = get_logger(__name__)

def create_asset_detail_modal():
    """
    Crea un modal para mostrar detalles de un asset específico.
    
    Returns:
        dbc.Modal: Componente modal con estructura para mostrar detalles de asset.
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(id="asset-detail-modal-title"),
                close_button=True,
                className="bg-primary text-white"
            ),
            html.Div(id="update-readings-status", className="px-4 pt-3"),
            dbc.ModalBody(id="asset-detail-modal-body", className="p-4"),
            dbc.ModalFooter([
                dbc.Button(
                    [html.I(className="fas fa-sync-alt me-2"), "Actualizar Lecturas"], 
                    id="update-asset-readings-btn", 
                    className="me-auto", 
                    color="primary",
                    n_clicks=0
                ),
                dbc.Button(
                    "Cerrar", id="close-asset-detail-modal", className="ms-auto", n_clicks=0
                )
            ]),
            dcc.Store(id="selected-asset-info", storage_type="memory"),
            dcc.Store(id="update-readings-state", storage_type="memory"),
        ],
        id="asset-detail-modal",
        size="xl",
        is_open=False,
        backdrop="static",
        scrollable=True,
        centered=True,
    )

def create_asset_detail_content(asset_id, month, detail_data, asset_metadata):
    """
    Crea el contenido del modal de detalles de asset.
    
    Args:
        asset_id (str): ID del asset seleccionado.
        month (str): Mes seleccionado en formato 'YYYY-MM'.
        detail_data (pd.DataFrame): DataFrame con los datos detallados del asset.
        asset_metadata (dict): Diccionario con metadatos del asset.
    
    Returns:
        html.Div: Contenido del modal con información detallada del asset.
    """
    # Si no hay datos, mostrar mensaje
    if detail_data is None or detail_data.empty:
        return html.Div([
            html.Div([
                html.H5("Información del Asset", className="card-title"),
                html.Div([
                    html.Strong("ID: "), html.Span(str(asset_id)),
                    html.Br(),
                    html.Strong("Bloque: "), html.Span(str(asset_metadata.get('block_number', 'N/A'))),
                    html.Br(),
                    html.Strong("Escalera: "), html.Span(str(asset_metadata.get('staircase', 'N/A'))),
                    html.Br(),
                    html.Strong("Apartamento: "), html.Span(str(asset_metadata.get('apartment', 'N/A'))),
                ], className="mb-3"),
            ], className="card-body"),
            html.Div([
                html.I(className="fas fa-info-circle me-2"),
                html.Span("No hay datos disponibles para este asset en el mes seleccionado.")
            ], className="alert alert-info")
        ], className="card")
    
    # Preparar datos para visualización
    try:
        # Convertir columna de fecha a datetime si existe y asegurar que sea serializable
        if 'date' in detail_data.columns:
            detail_data['date'] = pd.to_datetime(detail_data['date'])
            # Convertir fechas a strings para evitar problemas de serialización
            detail_data['date'] = detail_data['date'].dt.strftime('%Y-%m-%d')
            detail_data = detail_data.sort_values('date')
        
        # Identificar columnas numéricas para gráficos
        numeric_cols = detail_data.select_dtypes(include=[np.number]).columns.tolist()
        date_col = 'date' if 'date' in detail_data.columns else None
        
        # Crear contenido del modal
        content = []
        
        # Sección de información del asset
        content.append(html.Div([
            html.H5("Información del Asset", className="card-title"),
            html.Div([
                html.Strong("ID: "), html.Span(str(asset_id)),
                html.Br(),
                html.Strong("Bloque: "), html.Span(str(asset_metadata.get('block_number', 'N/A'))),
                html.Br(),
                html.Strong("Escalera: "), html.Span(str(asset_metadata.get('staircase', 'N/A'))),
                html.Br(),
                html.Strong("Apartamento: "), html.Span(str(asset_metadata.get('apartment', 'N/A'))),
            ], className="mb-3"),
        ], className="card-body border-bottom"))
        
        # Sección de gráficos (si hay datos numéricos y fechas)
        if date_col and numeric_cols:
            # Seleccionar hasta 3 columnas numéricas para mostrar en gráficos, excluyendo 'timestamp'
            plot_cols = [col for col in numeric_cols if col.lower() != 'timestamp'][:3]
            
            # Mantener un registro de las columnas ya visualizadas para evitar duplicados
            visualized_columns = set()
            
            # Crear gráfico de línea para cada columna numérica
            for col in plot_cols:
                # Evitar duplicar gráficos para la misma columna o sus derivados
                base_col = col.split('_')[0].lower()  # Nombre base de la columna, sin sufijos
                if base_col in visualized_columns:
                    continue
                
                # Añadir esta columna a las ya visualizadas
                visualized_columns.add(base_col)
                
                # Asegurarse de que los datos son serializables
                plot_data = detail_data.copy()
                
                # Convertir a tipos serializables si es necesario
                if pd.api.types.is_datetime64_any_dtype(plot_data[date_col]):
                    plot_data[date_col] = plot_data[date_col].astype(str)
                
                # Calcular el consumo del periodo (diferencia entre lecturas consecutivas)
                if col == 'value' or col.lower() == 'consumption' or col.lower().startswith('consumo'):
                    # Ordenar por fecha para asegurar cálculos correctos
                    plot_data = plot_data.sort_values(by=date_col)
                    
                    # Calcular diferencia entre lecturas consecutivas (consumo del periodo)
                    period_consumption_col = f"{col}_periodo"
                    plot_data[period_consumption_col] = plot_data[col].astype(float).diff()
                    
                    # Reemplazar valores negativos (pueden ocurrir por reinicios de contador) con 0 o NaN
                    plot_data.loc[plot_data[period_consumption_col] < 0, period_consumption_col] = 0
                    
                    # Eliminar el primer valor que será NaN debido al diff()
                    plot_data = plot_data.dropna(subset=[period_consumption_col])
                    
                    # Crear gráfico con el consumo del periodo
                    fig = px.bar(
                        plot_data, 
                        x=date_col, 
                        y=period_consumption_col,
                        title=f"Consumo por periodo ({col})",
                        labels={period_consumption_col: f"Consumo por periodo", date_col: "Fecha"},
                        template="plotly_white"
                    )
                    
                    # Personalizar el gráfico de barras para mejor visualización
                    fig.update_traces(
                        marker_color='rgb(55, 83, 109)',
                        marker_line_color='rgb(8,48,107)',
                        marker_line_width=1
                    )
                else:
                    # Para otras columnas, mostrar el valor directo
                    fig = px.line(
                        plot_data, 
                        x=date_col, 
                        y=col,
                        title=f"Evolución de {col}",
                        labels={col: col, date_col: "Fecha"},
                        template="plotly_white"
                    )
                
                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=300,
                    hovermode="x unified"
                )
                content.append(html.Div([
                    dcc.Graph(figure=fig)
                ], className="mb-4"))
        
        # Sección de tabla de datos
        # Asegurarse de que todos los datos son serializables
        table_data = detail_data.copy()
        for col in table_data.columns:
            if pd.api.types.is_datetime64_any_dtype(table_data[col]):
                table_data[col] = table_data[col].astype(str)
            elif pd.api.types.is_period_dtype(table_data[col]):
                table_data[col] = table_data[col].astype(str)
        
        content.append(html.Div([
            html.H5("Datos Detallados", className="mb-3"),
            dash_table.DataTable(
                data=table_data.to_dict('records'),
                columns=[{"name": i, "id": i} for i in table_data.columns],
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '8px',
                    'minWidth': '100px',
                    'maxWidth': '300px',
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
                sort_action="native",
                filter_action="native",
                export_format="csv",
            )
        ], className="mt-3"))
        
        return html.Div(content)
    
    except Exception as e:
        import traceback
        print(f"[ERROR] create_asset_detail_content - Error al crear contenido: {str(e)}")
        print(traceback.format_exc())
        
        return html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error al procesar datos: {str(e)}"
            ], className="alert alert-danger")
        ])

def register_asset_detail_modal_callbacks(app):
    """
    Registra los callbacks necesarios para el modal de detalles de asset.
    
    Args:
        app (dash.Dash): Aplicación Dash.
    """
    from dash.dependencies import Input, Output, State
    from dash.exceptions import PreventUpdate
    
    @app.callback(
        [Output("asset-detail-modal", "is_open"),
         Output("selected-asset-info", "data"),
         Output("update-readings-status", "children")],
        [Input("show-asset-detail-trigger", "data"),
         Input("close-asset-detail-modal", "n_clicks")],
        [State("asset-detail-modal", "is_open")]
    )
    def toggle_asset_detail_modal(trigger_data, close_clicks, is_open):
        """Toggle the asset detail modal."""
        ctx = callback_context
        
        # Logs para depuración
        logger.debug(f"toggle_asset_detail_modal - Contexto de callback: {ctx.triggered}")
        logger.debug(f"toggle_asset_detail_modal - Datos de trigger: {trigger_data}")
        logger.debug(f"toggle_asset_detail_modal - Estado actual del modal: {is_open}")
        
        if not ctx.triggered:
            return is_open, {}, None
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        logger.debug(f"toggle_asset_detail_modal - ID del trigger: {trigger_id}")
        
        if trigger_id == "show-asset-detail-trigger" and trigger_data:
            logger.info(f"toggle_asset_detail_modal - Abriendo modal para asset: {trigger_data.get('asset_id', 'N/A')}, mes: {trigger_data.get('month', 'N/A')}")
            # Devolver True para abrir el modal, los datos del asset para el Store, y None para el estado de actualización
            return True, trigger_data, None
        elif trigger_id == "close-asset-detail-modal":
            logger.info(f"toggle_asset_detail_modal - Cerrando modal")
            # Devolver False para cerrar el modal, un diccionario vacío para el Store, y None para el estado de actualización
            return False, {}, None
        
        return is_open, {}, None
    
    # Callback para iniciar la actualización de lecturas (Solución directa unificada)
    @app.callback(
        [Output("update-readings-status", "children", allow_duplicate=True),
         Output("update-readings-state", "data"),
         Output("asset-detail-modal-body", "children", allow_duplicate=True)],
        [Input("update-asset-readings-btn", "n_clicks")],
        [State("selected-asset-info", "data"),
         State("jwt-token-store", "data"),
         State("asset-detail-modal-body", "children")],
        prevent_initial_call=True
    )
    @handle_exceptions(default_return=(
        dbc.Alert(
            [html.I(className="fas fa-exclamation-triangle me-2"), "Ha ocurrido un error al actualizar las lecturas."],
            color="danger",
            dismissable=True
        ),
        None,  # No cambios en el estado
        None   # Mantener el contenido actual del modal
    ))
    def update_asset_readings(n_clicks, asset_info, token_data, current_content):
        """
        Actualiza las lecturas del asset en un solo paso.
        Esta función realiza todo el proceso que antes estaba dividido en dos etapas.
        """
        import dash_bootstrap_components as dbc
        from dash import html
        from utils.api import get_daily_readings_for_tag_monthly, get_daily_readings_for_tag, ensure_project_folder_exists
        import os
        import pandas as pd
        import re
        
        # Logs de inicialización
        print(f"[CONSOLE-DEBUG] update_asset_readings - Callback activado con n_clicks={n_clicks}")
        logger.critical(f"[CRITICAL] update_asset_readings - Callback activado con n_clicks={n_clicks}")
        
        # Verificar contexto del callback
        ctx = callback_context
        if not ctx.triggered:
            logger.warning("[WARNING] update_asset_readings - No se detectó un trigger para el callback")
            raise PreventUpdate
            
        logger.debug(f"[DEBUG] update_asset_readings - Trigger detectado: {ctx.triggered[0]['prop_id']}")
        
        # Verificar que tenemos la información necesaria
        if not asset_info or 'asset_id' not in asset_info:
            logger.warning("[ERROR] update_asset_readings - No se encontró asset_id en la información del asset")
            return dbc.Alert(
                [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    "No se pudo obtener información del asset para actualizar lecturas.",
                    html.Br(),
                    html.Small(f"Asset info: {asset_info}")
                ],
                color="danger",
                dismissable=True
            ), {"status": "error"}, current_content
        
        # Obtener información del asset
        asset_id = asset_info.get('asset_id')
        project_id = asset_info.get('project_id')
        month = asset_info.get('month')
        asset_metadata = asset_info.get('metadata', {})
        tags = asset_info.get('tags', [])
        token = token_data.get('token') if token_data else None
        
        # Depuración: Registrar la información clave del asset
        logger.info(f"[INFO] update_asset_readings - Iniciando actualización para asset_id={asset_id}, project_id={project_id}")
        logger.debug(f"[DEBUG] update_asset_readings - Tags detectados: {tags}")
        logger.debug(f"[DEBUG] update_asset_readings - Contenido completo de asset_info: {asset_info}")
        
        # Mostrar mensaje de carga con botón de cancelación
        loading_message = html.Div([
            dbc.Alert(
                [
                    dbc.Spinner(size="sm", color="primary", spinner_class_name="me-2"),
                    "Actualizando lecturas del asset...",
                ],
                color="info",
                className="mb-2"
            ),
            html.Div(
                dbc.Button(
                    "Cerrar", 
                    id="close-asset-detail-modal", 
                    color="secondary", 
                    size="sm",
                    className="mt-1"
                ),
                className="text-end"
            )
        ])
        
        # Intentar actualizar las lecturas
        try:
            # Asegurar que existe la carpeta del proyecto
            if not project_id:
                logger.warning("[WARNING] update_asset_readings - No se encontró project_id en la información del asset, intentando determinar proyecto a partir del sistema de archivos")
                
                # Primero intentar encontrar el project_id buscando archivos existentes para este asset
                from utils.data_loader import get_project_for_asset
                
                found_project_id = get_project_for_asset(asset_id)
                if found_project_id:
                    project_id = found_project_id
                    logger.info(f"[INFO] update_asset_readings - Se encontró project_id={project_id} para el asset {asset_id} en archivos existentes")
                else:
                    logger.warning("[WARNING] update_asset_readings - No se encontró project_id en archivos existentes, intentando obtenerlo de la API")
                    
                    # Como segunda opción, intentar obtener el project_id desde la API
                    try:
                        from utils.api import get_assets
                        assets = get_assets(token=token)
                        matching_asset = next((a for a in assets if a.get('id') == asset_id), None)
                        
                        if matching_asset and 'project_id' in matching_asset:
                            project_id = matching_asset['project_id']
                            logger.info(f"[INFO] update_asset_readings - Se obtuvo project_id={project_id} desde la API para el asset {asset_id}")
                        else:
                            # Si no se puede obtener el project_id, usar el project_id del primer asset como fallback
                            if assets and len(assets) > 0 and 'project_id' in assets[0]:
                                project_id = assets[0]['project_id']
                                logger.warning(f"[WARNING] update_asset_readings - No se encontró el asset en la API, usando project_id={project_id} del primer asset como alternativa")
                            else:
                                # Si no hay assets o no tienen project_id, usar "general" como último recurso
                                project_id = "general"
                                logger.warning("[WARNING] update_asset_readings - No se pudo obtener un project_id válido, usando carpeta 'general' como último recurso")
                    except Exception as e:
                        logger.error(f"[ERROR] update_asset_readings - Error al intentar obtener project_id: {str(e)}")
                        project_id = "general"  # Fallback a una carpeta general solo como último recurso
                
            # Validar que el project_id no sea "general" si hay otra manera de obtener un ID de proyecto válido
            if project_id == "general":
                logger.warning("[WARNING] update_asset_readings - Se está usando 'general' como project_id, lo que no coincide con la estructura esperada de directorios")
                
            logger.debug(f"[DEBUG] update_asset_readings - Asegurando carpeta para el proyecto {project_id}")
            project_folder = ensure_project_folder_exists(project_id)
            logger.debug(f"[DEBUG] update_asset_readings - Carpeta del proyecto: {project_folder}")
            
            # Validar el formato del mes
            if not month or not re.match(r'^\d{4}-\d{2}$', month):
                logger.error(f"[ERROR] update_asset_readings - Formato de mes inválido: {month}")
                return dbc.Alert(
                    [
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        f"Formato de mes inválido: {month}. Debe tener el formato YYYY-MM."
                    ],
                    color="danger",
                    dismissable=True
                ), {"status": "error", "reason": "invalid_month_format"}, current_content
            
            # Si no tenemos tags específicos, usar una lista predefinida de tags comunes
            if not tags or not isinstance(tags, list) or len(tags) == 0:
                logger.info("[INFO] update_asset_readings - No se encontraron tags específicos, obteniendo sensores automáticamente")
                # Intentar obtener los sensores disponibles para el asset
                from utils.api import get_sensors_with_tags
                available_sensors = get_sensors_with_tags(asset_id, token)
                
                if available_sensors and len(available_sensors) > 0:
                    logger.info(f"[INFO] update_asset_readings - Se encontraron {len(available_sensors)} sensores disponibles")
                    tags = available_sensors
                else:
                    logger.warning("[WARNING] update_asset_readings - No se encontraron sensores disponibles, usando tags predefinidos")
                    # Usar tags predefinidos como fallback (estos serán procesados como strings y se buscará un sensor que coincida)
                    tags = [
                        "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER",
                        "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT",
                        "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL",
                        "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL"
                    ]
            
            # Actualizar lecturas para cada tag
            results = []
            logger.info(f"[INFO] update_asset_readings - Iniciando actualización para {len(tags)} tags")
            
            for i, tag in enumerate(tags):
                logger.debug(f"[DEBUG] update_asset_readings - Procesando tag {i+1}/{len(tags)}: {tag}")
                # Llamar a la función para actualizar lecturas
                try:
                    # Formatear el tag correctamente según su tipo
                    if isinstance(tag, dict) and 'device_id' in tag and 'sensor_id' in tag and 'gateway_id' in tag:
                        # Si el tag ya es un diccionario con los parámetros del sensor, usarlo directamente
                        logger.debug(f"[DEBUG] update_asset_readings - Tag {i+1} ya es un diccionario, usando directamente: {tag}")
                        sensor_params = tag.copy()  # Crear una copia para no modificar el original
                        # Asegurar que el tag tenga un tag_name
                        if 'tag_name' not in sensor_params:
                            sensor_params['tag_name'] = f"{sensor_params.get('device_id')}_{sensor_params.get('sensor_id')}_{sensor_params.get('gateway_id')}"
                    elif isinstance(tag, str):
                        # Si el tag es un string, buscar el sensor correspondiente
                        logger.debug(f"[DEBUG] update_asset_readings - Tag {i+1} es un string, buscando sensor para: {tag}")
                        from utils.api import get_sensors_with_tags
                        sensors = get_sensors_with_tags(asset_id, token)
                        sensor = next((s for s in sensors if s.get("tag_name") == tag), None)
                        
                        if sensor:
                            logger.debug(f"[DEBUG] update_asset_readings - Sensor encontrado para tag {tag}: {sensor}")
                            sensor_params = {
                                'device_id': sensor.get('device_id'),
                                'sensor_id': sensor.get('sensor_id'),
                                'gateway_id': sensor.get('gateway_id'),
                                'tag_name': tag  # Usar el nombre del tag original
                            }
                        else:
                            logger.warning(f"[WARNING] update_asset_readings - No se encontró sensor para tag {tag}")
                            results.append({
                                "tag": tag,
                                "status": "error",
                                "reason": "sensor_not_found"
                            })
                            continue
                    else:
                        # Si el tag tiene otro formato, registrar error y continuar
                        logger.warning(f"[WARNING] update_asset_readings - Formato de tag no reconocido: {tag}")
                        results.append({
                            "tag": str(tag),
                            "status": "error",
                            "reason": "invalid_tag_format"
                        })
                        continue
                    
                    # Usar la función actualizada para obtener los datos del mes específico
                    logger.debug(f"[DEBUG] update_asset_readings - Llamando a get_daily_readings_for_tag_monthly con sensor_params: {sensor_params}")
                    
                    # Si el mes solicitado es el mes actual, mencionar que se limitará hasta el día de hoy
                    from datetime import datetime
                    current_date = datetime.now()
                    try:
                        year, month_num = month.split('-')
                        year = int(year)
                        month_num = int(month_num)
                        
                        if year == current_date.year and month_num == current_date.month:
                            logger.info(f"[INFO] update_asset_readings - Mes actual detectado ({month}), los datos se limitarán hasta el día de hoy ({current_date.strftime('%Y-%m-%d')})")
                    except Exception as e:
                        logger.warning(f"[WARNING] update_asset_readings - Error al validar el formato del mes: {e}")
                    
                    result = get_daily_readings_for_tag_monthly(asset_id, sensor_params, month, project_folder, token)
                    
                    logger.debug(f"[DEBUG] update_asset_readings - Resultado para tag {tag}: {type(result)}, Filas: {len(result) if result is not None and not isinstance(result, bool) and not result.empty else 'N/A'}")
                    
                    # Guardar resultado
                    if result is not None and not isinstance(result, bool) and not result.empty:
                        tag_name = tag.get('tag_name', str(tag)) if isinstance(tag, dict) else str(tag)
                        results.append({
                            "tag": tag_name,
                            "status": "success",
                            "rows": len(result)
                        })
                        logger.info(f"[INFO] update_asset_readings - Tag {tag_name} actualizado con éxito: {len(result)} filas")
                    else:
                        tag_name = tag.get('tag_name', str(tag)) if isinstance(tag, dict) else str(tag)
                        results.append({
                            "tag": tag_name,
                            "status": "error",
                            "rows": 0,
                            "reason": "no_data_returned"
                        })
                        logger.warning(f"[WARNING] update_asset_readings - Error al actualizar tag {tag_name}, result: {result}")
                except Exception as e:
                    import traceback
                    tag_name = tag.get('tag_name', str(tag)) if isinstance(tag, dict) else str(tag)
                    logger.error(f"[ERROR] update_asset_readings - Excepción al procesar tag {tag_name}: {str(e)}")
                    logger.error(f"[ERROR] update_asset_readings - Traceback: {traceback.format_exc()}")
                    results.append({
                        "tag": tag_name,
                        "status": "error",
                        "rows": 0,
                        "error": str(e)
                    })
            
            # Crear mensaje de resultado
            success_count = sum(1 for r in results if r["status"] == "success")
            total_tags = len(tags)
            
            logger.info(f"[INFO] update_asset_readings - Resultados finales: {success_count} exitosos de {total_tags} tags")
            
            if success_count > 0:
                # Crear mensaje de éxito
                success_message = dbc.Alert(
                    [
                        html.I(className="fas fa-check-circle me-2"),
                        f"Lecturas actualizadas con éxito para {success_count} de {total_tags} tags."
                    ],
                    color="success",
                    dismissable=True
                )
                
                # Recargar los datos del asset para mostrar los datos actualizados
                try:
                    # Obtener los datos actualizados del asset
                    from utils.data_loader import load_asset_detail_data
                    
                    logger.debug(f"[DEBUG] update_asset_readings - Recargando datos para asset_id={asset_id}, project_id={project_id}, month={month}")
                    # Cargar los datos actualizados con todos los parámetros necesarios
                    updated_data = load_asset_detail_data(
                        project_id=project_id,
                        asset_id=asset_id,
                        consumption_tags=tags,
                        month=month,
                        jwt_token=token
                    )
                    
                    # Validar que se obtuvieron datos
                    if updated_data is None or updated_data.empty:
                        logger.warning(f"[WARNING] update_asset_readings - No se pudieron cargar datos actualizados para asset_id={asset_id}, project_id={project_id}, month={month}")
                        # Intentar con una ruta de archivo específica para depuración
                        file_name = f"daily_readings_{asset_id}__*.csv"
                        file_path = os.path.join(project_folder, file_name)
                        logger.debug(f"[DEBUG] update_asset_readings - Buscando archivos que coincidan con: {file_path}")
                        
                        import glob
                        matching_files = glob.glob(file_path)
                        logger.debug(f"[DEBUG] update_asset_readings - Archivos encontrados: {matching_files}")
                        
                        # Si aún no hay datos, mostrar la información pero mantener el contenido actual
                        success_message_with_warning = dbc.Alert(
                            [
                                html.I(className="fas fa-check-circle me-2"),
                                f"Lecturas actualizadas con éxito para {success_count} de {total_tags} tags, pero no se pudieron cargar los datos actualizados.",
                                html.Br(),
                                html.Small(f"Intente cerrar y volver a abrir el detalle del asset para ver los cambios.")
                            ],
                            color="warning",
                            dismissable=True
                        )
                        return success_message_with_warning, {"status": "success", "updated": False}, current_content
                    
                    logger.debug(f"[DEBUG] update_asset_readings - Datos recargados: {type(updated_data)}, Filas: {len(updated_data) if updated_data is not None and not updated_data.empty else 'N/A'}")
                    
                    # Verificar contenido de los datos para depuración
                    if not updated_data.empty:
                        logger.debug(f"[DEBUG] update_asset_readings - Columnas en datos actualizados: {updated_data.columns.tolist()}")
                        logger.debug(f"[DEBUG] update_asset_readings - Primeras filas de datos actualizados: {updated_data.head(3).to_dict()}")
                    
                    # Recrear el contenido del modal con los datos actualizados
                    logger.debug("[DEBUG] update_asset_readings - Recreando contenido del modal")
                    updated_content = create_asset_detail_content(asset_id, month, updated_data, asset_metadata)
                    
                    logger.info("[INFO] update_asset_readings - Actualización completada con éxito")
                    return success_message, {"status": "success", "updated": True}, updated_content
                except Exception as e:
                    logger.error(f"[ERROR] update_asset_readings - Error al recargar datos: {str(e)}")
                    import traceback
                    logger.error(f"[ERROR] update_asset_readings - Traceback: {traceback.format_exc()}")
                    # Si hay un error al recargar los datos, mostrar el mensaje de éxito
                    # pero mantener el contenido actual
                    return success_message, {"status": "success", "updated": False}, current_content
            else:
                # Crear mensaje de error
                logger.warning("[WARNING] update_asset_readings - No se pudo actualizar ningún tag")
                error_message = dbc.Alert(
                    [
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        "No se pudieron actualizar las lecturas para ningún tag."
                    ],
                    color="danger",
                    dismissable=True
                )
                return error_message, {"status": "error", "reason": "no_tags_updated"}, current_content
                
        except Exception as e:
            import traceback
            logger.error(f"[ERROR] update_asset_readings - Error al actualizar lecturas: {str(e)}")
            logger.error(f"[ERROR] update_asset_readings - Traceback: {traceback.format_exc()}")
            
            # Crear mensaje de error
            error_message = dbc.Alert(
                [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"Error al actualizar lecturas: {str(e)}"
                ],
                color="danger",
                dismissable=True
            )
            return error_message, {"status": "error", "reason": str(e)}, current_content
    
    # Callback de prueba para verificar que la estructura de callbacks funciona
    @app.callback(
        Output("asset-detail-modal-title", "children", allow_duplicate=True),
        [Input("close-asset-detail-modal", "n_clicks")],
        [State("asset-detail-modal-title", "children")],
        prevent_initial_call=True
    )
    def test_callback_structure(n_clicks, current_title):
        """
        Callback de prueba para verificar que la estructura de callbacks funciona.
        Este callback no hace nada importante, solo imprime mensajes de depuración
        para confirmar que los callbacks están funcionando correctamente.
        """
        print("[CONSOLE-TEST] Callback de prueba activado. Esto confirma que los callbacks del modal funcionan.")
        logger.critical("[CRITICAL-TEST] Callback de prueba activado. Esto confirma que los callbacks del modal funcionan.")
        
        # No cambiamos realmente el título, solo verificamos que el callback se activa
        return current_title 