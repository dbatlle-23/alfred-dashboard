import dash_bootstrap_components as dbc
import dash.html as html
from dash import dcc
from dash import Output, Input, State, callback_context
import pandas as pd
import json
from datetime import datetime, timedelta

from components.metrics.tables import create_daily_readings_table

def create_calculation_detail_modal():
    """
    Crea el componente modal para mostrar detalles de cálculo.
    
    Returns:
        dbc.Modal: Componente modal para detalles de cálculo
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(id="calculation-detail-modal-header"),
            dbc.ModalBody(id="calculation-detail-modal-content"),
            dbc.ModalFooter(
                dbc.Button("Cerrar", id="close-calculation-detail-modal", className="ml-auto")
            ),
        ],
        id="calculation-detail-modal",
        size="lg",
    )

def create_calculation_detail_content(cell_data, metadata):
    """
    Crea el contenido del modal con detalles de cálculo.
    
    Args:
        cell_data (dict): Datos de la celda seleccionada
        metadata (dict): Metadatos del cálculo
        
    Returns:
        html.Div: Contenido del modal
    """
    # Extraer información relevante
    column_id = cell_data.get('column_id', '')
    row_index = cell_data.get('row_index', 0)
    value = cell_data.get('value', '')
    
    # Obtener metadatos específicos para esta celda
    cell_metadata = metadata.get(column_id, {}).get(str(row_index), {})
    
    # Crear componentes para el modal
    components = [
        html.H5(f"Detalles de cálculo para: {value}", className="mb-4"),
        
        # Información básica
        html.Div([
            html.H6("Información básica", className="mb-3"),
            dbc.Row([
                dbc.Col(html.Strong("Columna:"), width=3),
                dbc.Col(html.Span(get_column_display_name(column_id)), width=9)
            ], className="mb-2"),
            dbc.Row([
                dbc.Col(html.Strong("Período:"), width=3),
                dbc.Col(html.Span(cell_metadata.get('period', 'No disponible')), width=9)
            ], className="mb-2"),
            dbc.Row([
                dbc.Col(html.Strong("Última actualización:"), width=3),
                dbc.Col(html.Span(cell_metadata.get('last_updated', 'No disponible')), width=9)
            ], className="mb-4"),
        ], className="p-3 border rounded mb-4"),
        
        # Método de cálculo
        html.Div([
            html.H6("Método de cálculo", className="mb-3"),
            dbc.Row([
                dbc.Col(html.Strong("Fórmula:"), width=3),
                dbc.Col(html.Span(cell_metadata.get('formula', 'No disponible')), width=9)
            ], className="mb-2"),
            dbc.Row([
                dbc.Col(html.Strong("Descripción:"), width=3),
                dbc.Col(html.Span(cell_metadata.get('description', 'No disponible')), width=9)
            ], className="mb-2"),
        ], className="p-3 border rounded mb-4"),
        
        # Datos de origen
        html.Div([
            html.H6("Datos de origen", className="mb-3"),
            dbc.Row([
                dbc.Col(html.Strong("Fuente de datos:"), width=3),
                dbc.Col(html.Span(cell_metadata.get('data_source', 'No disponible')), width=9)
            ], className="mb-2"),
            dbc.Row([
                dbc.Col(html.Strong("Número de registros:"), width=3),
                dbc.Col(html.Span(str(cell_metadata.get('record_count', 'No disponible'))), width=9)
            ], className="mb-2"),
            dbc.Row([
                dbc.Col(html.Strong("Activos incluidos:"), width=3),
                dbc.Col(html.Span(cell_metadata.get('assets_included', 'No disponible')), width=9)
            ], className="mb-2"),
        ], className="p-3 border rounded mb-4"),
    ]
    
    # Si hay información adicional específica para cada tipo de columna
    if column_id == 'total_consumption':
        components.append(create_total_consumption_details(cell_metadata))
    elif column_id == 'average_consumption':
        components.append(create_average_consumption_details(cell_metadata))
    elif column_id == 'min_consumption':
        components.append(create_min_consumption_details(cell_metadata))
    elif column_id == 'max_consumption':
        components.append(create_max_consumption_details(cell_metadata))
    
    return html.Div(components)

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

def create_total_consumption_details(metadata):
    """
    Crea detalles específicos para el consumo total.
    
    Args:
        metadata (dict): Metadatos del cálculo
        
    Returns:
        html.Div: Componente con detalles específicos
    """
    return html.Div([
        html.H6("Detalles específicos - Consumo Total", className="mb-3"),
        dbc.Row([
            dbc.Col(html.Strong("Método de agregación:"), width=3),
            dbc.Col(html.Span("Suma de todos los consumos registrados en el período"), width=9)
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(html.Strong("Unidad de medida:"), width=3),
            dbc.Col(html.Span(metadata.get('unit', 'No disponible')), width=9)
        ], className="mb-2"),
    ], className="p-3 border rounded mb-4")

def create_average_consumption_details(metadata):
    """
    Detalles para consumo promedio.
    
    Args:
        metadata (dict): Metadatos del cálculo
        
    Returns:
        html.Div: Componente con detalles específicos
    """
    return html.Div([
        html.H6("Detalles específicos - Consumo Promedio", className="mb-3"),
        dbc.Row([
            dbc.Col(html.Strong("Método de cálculo:"), width=3),
            dbc.Col(html.Span("Promedio de consumos de todos los activos en el período"), width=9)
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(html.Strong("Unidad de medida:"), width=3),
            dbc.Col(html.Span(metadata.get('unit', 'No disponible')), width=9)
        ], className="mb-2"),
    ], className="p-3 border rounded mb-4")

def create_min_consumption_details(metadata):
    """
    Detalles para consumo mínimo.
    
    Args:
        metadata (dict): Metadatos del cálculo
        
    Returns:
        html.Div: Componente con detalles específicos
    """
    return html.Div([
        html.H6("Detalles específicos - Consumo Mínimo", className="mb-3"),
        dbc.Row([
            dbc.Col(html.Strong("Activo con consumo mínimo:"), width=3),
            dbc.Col(html.Span(metadata.get('min_asset', 'No disponible')), width=9)
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(html.Strong("Unidad de medida:"), width=3),
            dbc.Col(html.Span(metadata.get('unit', 'No disponible')), width=9)
        ], className="mb-2"),
    ], className="p-3 border rounded mb-4")

def create_max_consumption_details(metadata):
    """
    Detalles para consumo máximo.
    
    Args:
        metadata (dict): Metadatos del cálculo
        
    Returns:
        html.Div: Componente con detalles específicos
    """
    return html.Div([
        html.H6("Detalles específicos - Consumo Máximo", className="mb-3"),
        dbc.Row([
            dbc.Col(html.Strong("Activo con consumo máximo:"), width=3),
            dbc.Col(html.Span(metadata.get('max_asset', 'No disponible')), width=9)
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(html.Strong("Unidad de medida:"), width=3),
            dbc.Col(html.Span(metadata.get('unit', 'No disponible')), width=9)
        ], className="mb-2"),
    ], className="p-3 border rounded mb-4")

def create_asset_detail_modal():
    """
    Create a reusable modal component for displaying asset details.
    
    Returns:
        dbc.Modal: Modal component for asset details
    """
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="asset-detail-modal-title")),
        dbc.ModalBody(id="asset-detail-modal-body"),
        dbc.ModalFooter([
            dbc.Button(
                [html.I(className="fas fa-file-export me-2"), "Exportar"],
                id="export-asset-detail-btn",
                color="primary",
                outline=True,
                size="sm",
                className="me-2"
            ),
            dbc.Button(
                "Cerrar", 
                id="close-asset-detail-modal", 
                className="ms-auto"
            )
        ])
    ], id="asset-detail-modal", size="xl")

def create_asset_detail_content(asset_id, month, detail_data, asset_metadata=None):
    """
    Create the content for the asset detail modal.
    
    Args:
        asset_id (str): ID of the asset
        month (str): Month in 'YYYY-MM' format
        detail_data (pd.DataFrame): DataFrame with detailed data
        asset_metadata (dict, optional): Additional metadata about the asset
        
    Returns:
        html.Div: Content for the modal body
    """
    # Crear el título con información del asset
    asset_name = asset_metadata.get('name', asset_id) if asset_metadata else asset_id
    
    # Crear sección de metadatos
    metadata_section = html.Div([
        html.H6("Información del Asset"),
        dbc.Row([
            dbc.Col([
                html.Strong("ID: "),
                html.Span(asset_id)
            ], width=4),
            dbc.Col([
                html.Strong("Nombre: "),
                html.Span(asset_name)
            ], width=4),
            dbc.Col([
                html.Strong("Mes: "),
                html.Span(month)
            ], width=4)
        ]),
        # Añadir más metadatos si están disponibles
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Strong("Bloque: "),
                    html.Span(asset_metadata.get('block_number', 'N/A'))
                ], width=4),
                dbc.Col([
                    html.Strong("Escalera: "),
                    html.Span(asset_metadata.get('staircase', 'N/A'))
                ], width=4),
                dbc.Col([
                    html.Strong("Apartamento: "),
                    html.Span(asset_metadata.get('apartment', 'N/A'))
                ], width=4)
            ])
        ]) if asset_metadata else html.Div(),
        html.Hr()
    ])
    
    # Crear tabla de datos o mensaje si no hay datos
    if detail_data is not None and not detail_data.empty:
        data_section = create_daily_readings_table(
            detail_data,
            f"Lecturas Diarias - {month}"
        )
    else:
        data_section = html.Div([
            html.I(className="fas fa-info-circle me-2"),
            "No hay datos detallados disponibles para este asset y mes."
        ], className="alert alert-info")
    
    # Combinar todo en un contenedor
    return html.Div([
        metadata_section,
        data_section,
        # Añadir store para datos de exportación
        dcc.Store(id="asset-detail-export-data")
    ])

def register_detail_modal_callbacks(app):
    """
    Register callbacks for the asset detail modal.
    
    Args:
        app: Dash application instance
    """
    @app.callback(
        Output("asset-detail-modal", "is_open"),
        [Input("close-asset-detail-modal", "n_clicks"),
         Input("show-asset-detail-trigger", "data")],
        [State("asset-detail-modal", "is_open")]
    )
    def toggle_asset_detail_modal(close_clicks, show_data, is_open):
        """Toggle the asset detail modal."""
        ctx = callback_context
        if not ctx.triggered:
            return is_open
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "close-asset-detail-modal":
            return False
        elif trigger_id == "show-asset-detail-trigger" and show_data:
            return True
        
        return is_open
    
    @app.callback(
        Output("asset-detail-export-data", "data"),
        [Input("export-asset-detail-btn", "n_clicks")],
        [State("asset-detail-modal-body", "children"),
         State("asset-detail-modal-title", "children")]
    )
    def prepare_asset_detail_export(n_clicks, modal_body, modal_title):
        """Prepare data for export when export button is clicked."""
        if not n_clicks:
            return None
        
        # Aquí se implementaría la lógica para preparar los datos para exportación
        # Por ahora, solo devolvemos un objeto vacío para que el callback funcione
        return {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")} 