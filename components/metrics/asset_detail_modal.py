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
            dcc.Interval(id="update-readings-interval", interval=500, max_intervals=1, disabled=True),
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
    
    # Callback para iniciar la actualización de lecturas (Etapa 1)
    @app.callback(
        [Output("update-readings-status", "children", allow_duplicate=True),
         Output("update-readings-interval", "disabled"),
         Output("update-readings-state", "data")],
        [Input("update-asset-readings-btn", "n_clicks")],
        [State("selected-asset-info", "data"),
         State("jwt-token-store", "data")]
    )
    def start_update_readings(n_clicks, asset_info, token_data):
        """
        Inicia el proceso de actualización de lecturas mostrando un mensaje de carga
        y activando el intervalo para la segunda etapa.
        """
        import dash_bootstrap_components as dbc
        from dash import html
        
        # Verificar contexto del callback
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]["prop_id"] != "update-asset-readings-btn.n_clicks":
            raise PreventUpdate
        
        # Si el botón no ha sido clickeado, no hacer nada
        if n_clicks is None or n_clicks == 0:
            raise PreventUpdate
        
        # Verificar que tenemos la información necesaria
        if not asset_info or 'asset_id' not in asset_info:
            return dbc.Alert(
                "No se pudo obtener información del asset para actualizar lecturas.",
                color="danger"
            ), True, {}
        
        # Mostrar mensaje de carga con botón de cancelación
        loading_message = html.Div([
            dbc.Alert(
                [
                    dbc.Spinner(size="sm", color="primary", className="me-2"),
                    "Actualizando lecturas del asset...",
                ],
                color="info",
                className="mb-2"
            ),
            html.Div(
                dbc.Button(
                    "Cancelar actualización", 
                    id="cancel-update-readings-btn", 
                    color="secondary", 
                    size="sm",
                    className="mt-1"
                ),
                className="text-end"
            )
        ])
        
        # Preparar datos para la segunda etapa
        update_state = {
            "asset_id": asset_info.get("asset_id"),
            "project_id": asset_info.get("project_id"),
            "month": asset_info.get("month"),
            "metadata": asset_info.get("metadata", {}),
            "tags": asset_info.get("tags", []),
            "token": token_data.get("token") if token_data else None
        }
        
        # Activar el intervalo para la segunda etapa
        return loading_message, False, update_state
    
    # Callback para procesar la actualización de lecturas (Etapa 2)
    @app.callback(
        [Output("update-readings-status", "children", allow_duplicate=True),
         Output("asset-detail-modal-body", "children"),
         Output("update-readings-interval", "disabled", allow_duplicate=True)],
        [Input("update-readings-interval", "n_intervals")],
        [State("update-readings-state", "data"),
         State("asset-detail-modal-body", "children")]
    )
    @handle_exceptions(default_return=(
        dbc.Alert(
            [html.I(className="fas fa-exclamation-triangle me-2"), "Ha ocurrido un error al actualizar las lecturas."],
            color="danger",
            dismissable=True
        ),
        None,  # Mantener el contenido actual del modal
        True    # Desactivar el intervalo
    ))
    def process_update_readings(n_intervals, update_state, current_content):
        """
        Procesa la actualización de lecturas cuando se activa el intervalo.
        Esta es la segunda etapa del patrón de dos etapas.
        """
        from utils.api import get_daily_readings_for_tag, ensure_project_folder_exists
        import dash_bootstrap_components as dbc
        import os
        import pandas as pd
        
        # Verificar si el intervalo se ha activado
        if n_intervals is None or n_intervals < 1:
            raise PreventUpdate
        
        # Verificar que tenemos los datos necesarios
        if not update_state or 'asset_id' not in update_state:
            return dbc.Alert(
                "No se pudo obtener información del asset para actualizar lecturas.",
                color="danger"
            ), current_content, True
        
        # Obtener información del asset
        asset_id = update_state.get('asset_id')
        project_id = update_state.get('project_id')
        month = update_state.get('month')
        token = update_state.get('token')
        
        # Intentar actualizar las lecturas
        try:
            # Asegurar que existe la carpeta del proyecto
            if not project_id:
                return dbc.Alert(
                    "No se pudo determinar el proyecto al que pertenece este asset.",
                    color="danger"
                ), current_content, True
            
            project_folder = ensure_project_folder_exists(project_id)
            
            # Determinar los tags disponibles para este asset
            tags = update_state.get('tags', [])
            
            # Si no tenemos tags específicos, usar una lista predefinida de tags comunes
            if not tags:
                tags = [
                    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER",
                    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT",
                    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL",
                    "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL"
                ]
            
            # Actualizar lecturas para cada tag
            results = []
            for tag in tags:
                # Llamar a la función para actualizar lecturas
                result = get_daily_readings_for_tag(asset_id, tag, project_folder, token)
                
                # Guardar resultado
                if result is not None and not result.empty:
                    results.append({
                        "tag": tag,
                        "status": "success",
                        "rows": len(result)
                    })
                else:
                    results.append({
                        "tag": tag,
                        "status": "error",
                        "rows": 0
                    })
            
            # Crear mensaje de éxito
            success_count = sum(1 for r in results if r["status"] == "success")
            total_tags = len(tags)
            
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
                    # Esta función dependerá de cómo se obtienen los datos en tu aplicación
                    # Aquí asumimos que hay una función load_asset_detail_data que obtiene los datos
                    from utils.data_loader import load_asset_detail_data
                    
                    # Cargar los datos actualizados
                    updated_data = load_asset_detail_data(asset_id, month)
                    
                    # Obtener los metadatos del asset
                    asset_metadata = update_state.get('metadata', {})
                    
                    # Recrear el contenido del modal con los datos actualizados
                    updated_content = create_asset_detail_content(asset_id, month, updated_data, asset_metadata)
                    
                    return success_message, updated_content, True
                except Exception as e:
                    logger.error(f"process_update_readings - Error al recargar datos: {str(e)}")
                    # Si hay un error al recargar los datos, mostrar el mensaje de éxito
                    # pero mantener el contenido actual
                    return success_message, current_content, True
            else:
                # Crear mensaje de error
                error_message = dbc.Alert(
                    [
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        "No se pudieron actualizar las lecturas para ningún tag."
                    ],
                    color="danger",
                    dismissable=True
                )
                return error_message, current_content, True
                
        except Exception as e:
            import traceback
            logger.error(f"process_update_readings - Error al actualizar lecturas: {str(e)}")
            logger.debug(traceback.format_exc())
            
            # Crear mensaje de error
            error_message = dbc.Alert(
                [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"Error al actualizar lecturas: {str(e)}"
                ],
                color="danger",
                dismissable=True
            )
            return error_message, current_content, True
    
    # Callback para cancelar la actualización de lecturas
    @app.callback(
        [Output("update-readings-status", "children", allow_duplicate=True),
         Output("update-readings-interval", "disabled", allow_duplicate=True)],
        [Input("cancel-update-readings-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def cancel_update_readings(n_clicks):
        """
        Cancela la actualización de lecturas cuando se hace clic en el botón de cancelación.
        """
        import dash_bootstrap_components as dbc
        from dash import html
        
        # Verificar contexto del callback
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]["prop_id"] != "cancel-update-readings-btn.n_clicks":
            raise PreventUpdate
        
        # Si el botón no ha sido clickeado, no hacer nada
        if n_clicks is None or n_clicks == 0:
            raise PreventUpdate
        
        # Mostrar mensaje de cancelación
        cancel_message = dbc.Alert(
            [
                html.I(className="fas fa-info-circle me-2"),
                "Actualización de lecturas cancelada."
            ],
            color="warning",
            dismissable=True
        )
        
        # Desactivar el intervalo para evitar que se ejecute la segunda etapa
        return cancel_message, True 