from dash import Output, Input, html
import pandas as pd
import json
from utils.logging import get_logger

logger = get_logger(__name__)

def register_anomaly_indicator_callbacks(app):
    """Register callbacks for anomaly indicators."""
    
    @app.callback(
        Output("metrics-filter-indicator", "children", allow_duplicate=True),
        [Input("metrics-data-store", "data")],
        prevent_initial_call=True
    )
    def update_filter_indicator(data):
        """
        Actualiza el indicador de filtros y muestra información sobre anomalías corregidas.
        """
        if not data:
            return ""
        
        try:
            # Convertir los datos JSON a DataFrame
            df = pd.DataFrame(json.loads(data))
            
            # Crear el indicador básico con información sobre los datos filtrados
            indicator_elements = [
                html.P(f"Mostrando datos filtrados: {len(df)} registros", className="mb-0")
            ]
            
            # Verificar si hay datos corregidos
            has_corrections = 'is_corrected' in df.columns and df['is_corrected'].any()
            
            # Añadir badge de corrección si hay datos corregidos
            if has_corrections:
                corrected_count = df['is_corrected'].sum()
                indicator_elements.append(
                    html.Div([
                        html.Span([
                            html.I(className="fas fa-magic me-1"),
                            f"{corrected_count} valores corregidos automáticamente"
                        ], className="badge bg-info ms-2")
                    ], className="mt-1")
                )
                
                logger.info(f"Mostrando indicador de {corrected_count} valores corregidos")
            
            return html.Div(indicator_elements, className="metrics-filter-info")
        except Exception as e:
            logger.error(f"Error al actualizar indicador de filtros: {str(e)}")
            return html.Div("Error al procesar datos", className="text-danger") 