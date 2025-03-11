"""
Componentes para la regeneración masiva de lecturas con errores.
"""

import dash_bootstrap_components as dbc
from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import json

def create_bulk_regeneration_modal(error_data=None):
    """
    Crea un modal para la regeneración masiva de lecturas con errores.
    
    Args:
        error_data: Datos de análisis de errores
            {
                'total_errors': número total de errores,
                'errors_by_asset': errores agrupados por asset,
                'errors_by_consumption_type': errores agrupados por tipo de consumo,
                'errors_by_period': errores agrupados por período
            }
        
    Returns:
        dbc.Modal: Modal de regeneración masiva
    """
    print(f"[DEBUG] create_bulk_regeneration_modal - error_data: {error_data}")
    
    # Crear el contenido del modal
    modal_header = dbc.ModalHeader(dbc.ModalTitle("Regeneración masiva de lecturas con errores"))
    
    # Contenido del cuerpo del modal
    modal_body_content = []
    
    # Resumen de errores
    if error_data and error_data.get('total_errors', 0) > 0:
        total_errors = error_data.get('total_errors', 0)
        errors_by_asset = error_data.get('errors_by_asset', {})
        errors_by_consumption_type = error_data.get('errors_by_consumption_type', {})
        errors_by_period = error_data.get('errors_by_period', {})
        
        # Crear resumen
        summary = html.Div([
            html.H5("Resumen de errores encontrados", className="mb-3"),
            html.P(f"Se encontraron {total_errors} errores en total."),
            
            # Desglose por asset
            html.Div([
                html.H6("Errores por asset:"),
                html.Ul([
                    html.Li(f"{asset}: {count} errores") 
                    for asset, count in errors_by_asset.items()
                ])
            ], className="mb-3"),
            
            # Desglose por tipo de consumo
            html.Div([
                html.H6("Errores por tipo de consumo:"),
                html.Ul([
                    html.Li(f"{consumption_type}: {count} errores") 
                    for consumption_type, count in errors_by_consumption_type.items()
                ])
            ], className="mb-3"),
            
            # Desglose por período
            html.Div([
                html.H6("Errores por período:"),
                html.Ul([
                    html.Li(f"{period}: {count} errores") 
                    for period, count in errors_by_period.items()
                ])
            ], className="mb-3")
        ], className="mb-4")
        
        modal_body_content.append(summary)
    else:
        modal_body_content.append(html.Div("No se encontraron errores para regenerar.", className="alert alert-info mb-4"))
    
    # Opciones de regeneración
    modal_body_content.append(html.Div([
        html.H5("Opciones de regeneración", className="mb-3"),
        create_regeneration_options()
    ], className="mb-4"))
    
    # Contenedor para la vista previa
    modal_body_content.append(html.Div(
        html.Div("Haga clic en 'Previsualizar' para ver los elementos que se regenerarán.", className="text-muted"),
        id="bulk-regenerate-preview-container",
        className="mb-4"
    ))
    
    # Contenedor para el progreso
    modal_body_content.append(html.Div(id="bulk-regenerate-progress-container", className="mb-4"))
    
    # Contenedor para los resultados
    modal_body_content.append(html.Div(id="bulk-regenerate-results-container", className="mb-4"))
    
    # Almacenamiento de datos de análisis de errores
    modal_body_content.append(dcc.Store(id="error-analysis-data", data=json.dumps(error_data) if error_data else None))
    
    modal_body = dbc.ModalBody(modal_body_content)
    
    # Pie del modal con botones
    modal_footer = dbc.ModalFooter([
        dbc.Button("Cancelar", id="cancel-bulk-regenerate", className="me-2"),
        dbc.Button("Previsualizar", id="preview-bulk-regenerate", color="info", className="me-2"),
        dbc.Button("Regenerar", id="confirm-bulk-regenerate", color="danger")
    ])
    
    # Crear el modal
    modal = dbc.Modal([
        modal_header,
        modal_body,
        modal_footer
    ], id="bulk-regenerate-modal", size="xl", is_open=False)
    
    return modal

def create_regeneration_options():
    """
    Crea los controles para las opciones de regeneración.
    """
    return html.Div([
        html.H5("Opciones de regeneración"),
        
        # Modo de regeneración
        html.Div([
            html.Label("Modo de regeneración:"),
            dcc.RadioItems(
                id="regeneration-mode",
                options=[
                    {"label": "Todos los errores", "value": "all"},
                    {"label": "Por asset", "value": "by_asset"},
                    {"label": "Por tipo de consumo", "value": "by_consumption_type"},
                    {"label": "Por período", "value": "by_period"},
                    {"label": "Regenerar archivos completos", "value": "complete_files"}
                ],
                value="all",
                className="mb-3"
            )
        ]),
        
        # Filtros adicionales
        html.Div([
            # Filtro por asset
            html.Div([
                html.Label("Filtrar por asset:"),
                dcc.Dropdown(
                    id="filter-asset",
                    placeholder="Seleccione un asset",
                    disabled=True
                )
            ], className="mb-3", id="filter-asset-container"),
            
            # Filtro por tipo de consumo
            html.Div([
                html.Label("Filtrar por tipo de consumo:"),
                dcc.Dropdown(
                    id="filter-consumption-type",
                    placeholder="Seleccione un tipo de consumo",
                    disabled=True
                )
            ], className="mb-3", id="filter-consumption-type-container"),
            
            # Filtro por período
            html.Div([
                html.Label("Filtrar por período:"),
                dcc.Dropdown(
                    id="filter-period",
                    placeholder="Seleccione un período",
                    disabled=True
                )
            ], className="mb-3", id="filter-period-container")
        ]),
        
        # Opciones adicionales
        html.Div([
            html.Label("Opciones adicionales:"),
            dbc.Checkbox(
                id="continue-on-error",
                label="Continuar en caso de error",
                value=True,
                className="mb-2"
            ),
            dbc.Checkbox(
                id="only-errors",
                label="Regenerar solo valores con error (no archivos completos)",
                value=True
            )
        ], className="mb-3")
    ], className="mb-4")

def create_regeneration_preview(preview_data):
    """
    Crea la vista previa de las regeneraciones a realizar.
    
    Args:
        preview_data: Datos para la vista previa
        
    Returns:
        html.Div: Componente de vista previa
    """
    if not preview_data or not preview_data.get('items'):
        return html.Div("No hay elementos para regenerar con los filtros seleccionados.", className="alert alert-warning")
    
    items = preview_data.get('items', [])
    total = len(items)
    
    # Crear tabla de vista previa
    table_header = [
        html.Thead(html.Tr([
            html.Th("Asset ID"),
            html.Th("Tipo de Consumo"),
            html.Th("Período")
        ]))
    ]
    
    # Limitar a 10 filas para la vista previa
    preview_items = items[:10]
    rows = []
    for item in preview_items:
        row = html.Tr([
            html.Td(item['asset_id']),
            html.Td(item['consumption_type']),
            html.Td(item['period'])
        ])
        rows.append(row)
    
    table_body = [html.Tbody(rows)]
    
    # Mostrar mensaje si hay más elementos
    more_items_message = ""
    if total > 10:
        more_items_message = html.P(f"... y {total - 10} elementos más", className="text-muted")
    
    return html.Div([
        html.H5("Vista previa de regeneraciones", className="mb-3"),
        html.P(f"Se regenerarán {total} elementos con los filtros seleccionados."),
        dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True, striped=True, size="sm"),
        more_items_message
    ], className="mt-3")

def create_progress_component(progress_data):
    """
    Crea un componente para mostrar el progreso de la regeneración.
    
    Args:
        progress_data: Datos de progreso
        
    Returns:
        html.Div: Componente de progreso
    """
    if not progress_data:
        return html.Div()
    
    total = progress_data.get('total', 0)
    processed = progress_data.get('processed', 0)
    success = progress_data.get('success', 0)
    failed = progress_data.get('failed', 0)
    
    if total == 0:
        percentage = 0
    else:
        percentage = int((processed / total) * 100)
    
    return html.Div([
        html.H5("Progreso de regeneración", className="mb-3"),
        dbc.Progress(value=percentage, striped=True, animated=True, color="primary", className="mb-2"),
        html.P(f"Procesando {processed} de {total} elementos ({percentage}%)", className="text-center"),
        html.Div([
            html.Span(f"Éxitos: {success}", className="text-success me-3"),
            html.Span(f"Fallos: {failed}", className="text-danger")
        ], className="text-center")
    ], className="mt-3")

def create_results_summary(results):
    """
    Crea un resumen de los resultados de la regeneración.
    
    Args:
        results: Resultados de la regeneración
        
    Returns:
        html.Div: Componente de resumen de resultados
    """
    if not results:
        return html.Div("No hay resultados disponibles.", className="alert alert-warning")
    
    total = results.get('total', 0)
    success = results.get('success', 0)
    failed = results.get('failed', 0)
    details = results.get('details', [])
    
    # Calcular porcentajes
    success_percent = (success / total * 100) if total > 0 else 0
    failed_percent = (failed / total * 100) if total > 0 else 0
    
    # Crear gráfico de pastel
    fig = go.Figure(data=[
        go.Pie(
            labels=['Éxitos', 'Fallos'],
            values=[success, failed],
            hole=.3,
            marker_colors=['#28a745', '#dc3545'],
            textinfo='value+percent',
            insidetextorientation='radial'
        )
    ])
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=250,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    # Crear tabla de fallos
    failed_items = [item for item in details if item.get('status') == 'failed']
    
    if failed_items:
        table_header = [
            html.Thead(html.Tr([
                html.Th("Asset ID"),
                html.Th("Tipo de Consumo"),
                html.Th("Período"),
                html.Th("Razón")
            ]))
        ]
        
        # Limitar a 10 filas para la vista
        preview_items = failed_items[:10]
        rows = []
        for item in preview_items:
            row = html.Tr([
                html.Td(item.get('asset_id', '')),
                html.Td(item.get('consumption_type', '')),
                html.Td(item.get('period', '')),
                html.Td(item.get('reason', 'Desconocido'))
            ])
            rows.append(row)
        
        table_body = [html.Tbody(rows)]
        
        # Mostrar mensaje si hay más elementos
        more_items_message = ""
        if len(failed_items) > 10:
            more_items_message = html.P(f"... y {len(failed_items) - 10} fallos más", className="text-muted")
        
        failed_table = html.Div([
            html.H6("Detalles de fallos:"),
            dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True, striped=True, size="sm"),
            more_items_message
        ])
    else:
        failed_table = html.Div()
    
    return html.Div([
        html.H5("Resultados de la regeneración", className="mb-3"),
        html.Div([
            html.Div([
                html.P([
                    html.Strong("Total procesado: "), f"{total} elementos"
                ]),
                html.P([
                    html.Strong("Éxitos: "), f"{success} ({success_percent:.1f}%)",
                    html.I(className="fas fa-check-circle text-success ms-2")
                ]),
                html.P([
                    html.Strong("Fallos: "), f"{failed} ({failed_percent:.1f}%)",
                    html.I(className="fas fa-times-circle text-danger ms-2")
                ])
            ], className="col-md-6"),
            html.Div([
                dcc.Graph(figure=fig, config={'displayModeBar': False})
            ], className="col-md-6")
        ], className="row"),
        failed_table,
        html.Div([
            dbc.Button("Cerrar", id="close-results", className="me-2"),
            dbc.Button("Regenerar fallidos", id="regenerate-failed", color="warning", className="me-2"),
            dbc.Button("Exportar resultados", id="export-results", color="info")
        ], className="mt-3 d-flex justify-content-end")
    ], className="mt-3") 