import json
import pandas as pd
from dash.dependencies import Input, Output, State
from dash import callback_context
from components.metrics.detail_modal import create_calculation_detail_content

def register_modal_callbacks(app):
    """Register callbacks for the calculation detail modal."""
    
    @app.callback(
        [Output("calculation-detail-modal", "is_open"),
         Output("calculation-detail-modal-header", "children"),
         Output("calculation-detail-modal-content", "children")],
        [Input("monthly-summary-table", "active_cell"),
         Input("close-calculation-detail-modal", "n_clicks")],
        [State("monthly-summary-table", "data"),
         State("monthly-summary-calculation-metadata", "data")]
    )
    def toggle_calculation_detail_modal(active_cell, close_clicks, table_data, metadata):
        """
        Abre o cierra el modal de detalles de cálculo y actualiza su contenido.
        
        Args:
            active_cell (dict): Celda activa seleccionada
            close_clicks (int): Número de clics en el botón de cerrar
            table_data (list): Datos de la tabla
            metadata (dict): Metadatos de cálculo
            
        Returns:
            tuple: (is_open, header, content)
        """
        ctx = callback_context
        
        # Valor por defecto para el retorno
        default_return = (False, "", "")
        
        if not ctx.triggered:
            return default_return
        
        # Identificar qué input disparó el callback
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Si se hizo clic en el botón de cerrar
        if trigger_id == "close-calculation-detail-modal":
            return False, "", ""
        
        # Si se seleccionó una celda
        if trigger_id == "monthly-summary-table" and active_cell:
            # Verificar que tenemos los datos necesarios
            if not table_data or not metadata:
                return True, "Error", "No se pudieron cargar los detalles de cálculo."
            
            # Obtener información de la celda seleccionada
            row_idx = active_cell['row']
            col_id = active_cell['column_id']
            
            # Si la columna es 'month', no mostrar modal
            if col_id == 'month':
                return default_return
            
            # Obtener el valor de la celda
            cell_value = table_data[row_idx][col_id]
            month_value = table_data[row_idx]['month']
            
            # Crear título para el modal
            header = f"Detalles de {get_column_display_name(col_id)} - {month_value}"
            
            # Crear contenido del modal
            content = create_calculation_detail_content(
                {
                    'column_id': col_id,
                    'row_index': row_idx,
                    'value': cell_value
                },
                json.loads(metadata) if metadata else {}
            )
            
            return True, header, content
        
        return default_return
    
    @app.callback(
        Output("monthly-summary-calculation-metadata", "data"),
        [Input("metrics-data-store", "data"),
         Input("metrics-monthly-summary-table", "children")],
        [State("metrics-client-filter", "value"),
         State("metrics-project-filter", "value"),
         State("metrics-consumption-tags-filter", "value"),
         State("metrics-date-range", "start_date"),
         State("metrics-date-range", "end_date")]
    )
    def update_calculation_metadata(json_data, summary_table, client_id, project_id, consumption_tags, start_date, end_date):
        """
        Actualiza los metadatos de cálculo cuando cambian los datos o la tabla de resumen.
        
        Args:
            json_data (str): Datos JSON del store
            summary_table (dict): Componente de tabla de resumen
            client_id (str): ID del cliente seleccionado
            project_id (str): ID del proyecto seleccionado
            consumption_tags (list): Etiquetas de consumo seleccionadas
            start_date (str): Fecha de inicio
            end_date (str): Fecha de fin
            
        Returns:
            str: Metadatos de cálculo en formato JSON
        """
        if not json_data:
            return "{}"
        
        try:
            # Convertir JSON a DataFrame
            df = pd.DataFrame(json.loads(json_data))
            
            # Procesar datos según filtros
            from utils.metrics.data_processing import process_metrics_data, generate_calculation_metadata
            
            filtered_df = process_metrics_data(
                df, 
                client_id=client_id, 
                project_id=project_id, 
                consumption_tags=consumption_tags, 
                start_date=start_date, 
                end_date=end_date
            )
            
            if filtered_df.empty:
                return "{}"
            
            # Generar resumen mensual
            from utils.metrics.data_processing import generate_monthly_consumption_summary
            
            monthly_summary = generate_monthly_consumption_summary(filtered_df, start_date, end_date)
            
            if monthly_summary.empty:
                return "{}"
            
            # Generar metadatos de cálculo
            metadata = generate_calculation_metadata(filtered_df, monthly_summary)
            
            # Convertir a JSON
            return json.dumps(metadata)
            
        except Exception as e:
            print(f"[ERROR] Error al generar metadatos de cálculo: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return "{}"

def get_column_display_name(column_id):
    """
    Obtiene el nombre de visualización para una columna.
    
    Args:
        column_id (str): ID de la columna
        
    Returns:
        str: Nombre de visualización
    """
    column_names = {
        'month': 'Mes',
        'total_consumption': 'Consumo Total',
        'average_consumption': 'Consumo Promedio',
        'min_consumption': 'Consumo Mínimo',
        'max_consumption': 'Consumo Máximo',
        'asset_count': 'Número de Activos'
    }
    return column_names.get(column_id, column_id)
