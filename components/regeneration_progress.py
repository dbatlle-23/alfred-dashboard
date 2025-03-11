"""
Componente para mostrar el progreso de la regeneración de lecturas.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go

def create_progress_bar(progress_value, success_count=0, failed_count=0, total_count=0):
    """
    Crea una barra de progreso con información sobre éxitos y fallos.
    
    Args:
        progress_value: Valor del progreso (0-100)
        success_count: Número de regeneraciones exitosas
        failed_count: Número de regeneraciones fallidas
        total_count: Número total de regeneraciones
        
    Returns:
        dbc.Card: Componente de barra de progreso
    """
    # Asegurar que el progreso esté entre 0 y 100
    progress_value = max(0, min(100, progress_value))
    
    # Calcular el color de la barra de progreso
    if failed_count == 0:
        bar_color = "success"
    elif failed_count < success_count:
        bar_color = "warning"
    else:
        bar_color = "danger"
    
    return dbc.Card(
        dbc.CardBody([
            html.H5("Progreso de la regeneración", className="card-title"),
            html.Div([
                dbc.Progress(
                    value=progress_value,
                    color=bar_color,
                    striped=True,
                    animated=True,
                    style={"height": "20px"}
                ),
                html.Div(
                    f"{progress_value:.1f}%",
                    style={
                        "position": "absolute",
                        "top": "0",
                        "left": "50%",
                        "transform": "translateX(-50%)",
                        "color": "white" if progress_value > 30 else "black",
                        "fontWeight": "bold",
                        "lineHeight": "20px"
                    }
                )
            ], style={"position": "relative"}),
            html.Div([
                html.Span(f"Procesados: {success_count + failed_count} de {total_count}", className="me-3"),
                html.Span([
                    html.I(className="fas fa-check-circle text-success me-1"),
                    f"Éxitos: {success_count}"
                ], className="me-3"),
                html.Span([
                    html.I(className="fas fa-times-circle text-danger me-1"),
                    f"Fallos: {failed_count}"
                ])
            ], className="mt-2 d-flex justify-content-center")
        ]),
        className="mb-3"
    )

def create_progress_chart(success_count, failed_count):
    """
    Crea un gráfico de pastel que muestra la proporción de éxitos y fallos.
    
    Args:
        success_count: Número de regeneraciones exitosas
        failed_count: Número de regeneraciones fallidas
        
    Returns:
        dcc.Graph: Componente de gráfico
    """
    total = success_count + failed_count
    if total == 0:
        # Si no hay datos, mostrar un gráfico vacío
        return html.Div("No hay datos para mostrar", className="text-center py-3")
    
    # Crear el gráfico de pastel
    fig = go.Figure(data=[
        go.Pie(
            labels=['Éxitos', 'Fallos'],
            values=[success_count, failed_count],
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
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

def create_regeneration_progress_component(progress_data=None):
    """
    Crea un componente completo para mostrar el progreso de la regeneración.
    
    Args:
        progress_data: Datos del progreso de la regeneración
            {
                'total': número total de regeneraciones,
                'processed': número de regeneraciones procesadas,
                'success': número de regeneraciones exitosas,
                'failed': número de regeneraciones fallidas,
                'status': estado de la regeneración ('in_progress', 'completed', etc.)
            }
        
    Returns:
        html.Div: Componente de progreso
    """
    if progress_data is None or progress_data.get('total', 0) == 0:
        return html.Div(
            dbc.Alert("No hay datos de progreso disponibles", color="info"),
            id="regeneration-progress-container"
        )
    
    total = progress_data.get('total', 0)
    processed = progress_data.get('processed', 0)
    success = progress_data.get('success', 0)
    failed = progress_data.get('failed', 0)
    status = progress_data.get('status', 'unknown')
    
    # Calcular el porcentaje de progreso
    progress_percent = (processed / total * 100) if total > 0 else 0
    
    # Crear el componente de progreso
    progress_component = html.Div([
        create_progress_bar(
            progress_value=progress_percent,
            success_count=success,
            failed_count=failed,
            total_count=total
        ),
        
        # Mostrar el gráfico solo si hay datos procesados
        html.Div(
            create_progress_chart(success, failed) if processed > 0 else None,
            className="mt-3"
        ),
        
        # Mostrar mensaje de estado
        html.Div([
            html.I(
                className={
                    'in_progress': "fas fa-spinner fa-spin me-2",
                    'completed': "fas fa-check-circle me-2 text-success",
                    'failed': "fas fa-exclamation-circle me-2 text-danger"
                }.get(status, "fas fa-info-circle me-2")
            ),
            {
                'in_progress': "Regeneración en progreso...",
                'completed': "Regeneración completada",
                'failed': "Regeneración fallida"
            }.get(status, f"Estado: {status}")
        ], className="text-center mt-3 fs-5"),
        
        # Intervalo para actualizar el progreso si está en curso
        dcc.Interval(
            id='regeneration-progress-interval',
            interval=2000,  # 2 segundos
            disabled=status != 'in_progress'
        )
    ], id="regeneration-progress-container")
    
    return progress_component 