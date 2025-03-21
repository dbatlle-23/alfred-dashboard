from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash
import pandas as pd
from datetime import datetime, timedelta
import json

# Importar constantes
from constants.metrics import ConsumptionTags, CONSUMPTION_TAGS_MAPPING

# Importar configuración
from config.metrics_config import CHART_CONFIG, FILTER_CONFIG

# Importar componentes
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
    create_monthly_readings_by_consumption_type,
    create_consumption_stats_table,
    create_daily_readings_table,
    create_monthly_summary_table
)
from components.metrics.detail_modal import create_calculation_detail_modal
from components.metrics.asset_detail_modal import create_asset_detail_modal

# Importar utilidades
from utils.metrics.data_processing import (
    process_metrics_data,
    aggregate_data_by_project,
    aggregate_data_by_asset,
    aggregate_data_by_consumption_type,
    aggregate_data_by_month_and_asset,
    generate_monthly_readings_by_consumption_type,
    generate_monthly_consumption_summary
)
# Comentar o eliminar importaciones que no existen
# from utils.metrics.error_analysis import analyze_readings_errors
# from utils.metrics.regeneration import regenerate_readings, regenerate_readings_in_bulk
# from utils.metrics.validation import validate_consumption_data
from utils.api import get_clientes, get_projects, get_assets, get_project_assets

# Importar callbacks
from callbacks.metrics import register_callbacks

# Función para crear el layout de la página de métricas
def create_layout():
    """Create the metrics page layout."""
    return html.Div([
        # Stores para datos
        dcc.Store(id="metrics-data-store"),
        dcc.Store(id="metrics-selected-client-store"),
        dcc.Store(id="metrics-selected-consumption-tags-store"),
        dcc.Store(id="error-analysis-data"),
        dcc.Store(id="filtered-errors-data"),
        dcc.Store(id="regenerate-readings-data"),
        dcc.Store(id="update-asset-readings-data"),
        dcc.Store(id="refresh-data-store"),
        dcc.Store(id="file-selector-data"),
        dcc.Store(id="delete-file-data"),
        dcc.Store(id="error-diagnosis-data"),
        dcc.Store(id="complete-consumption-data"),
        dcc.Store(id="realtime-reading-data"),
        dcc.Store(id="store-monthly-readings-data"),
        dcc.Store(id="show-asset-detail-trigger"),
        dcc.Store(id="monthly-readings-complete-data"),
        dcc.Store(id="monthly-readings-table-debug"),
        
        # Contenedor principal
        dbc.Container([
            # Título de la página
            html.H2("Visualización de Consumos", className="mb-4"),
            
            # Filtros
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        # Filtro de cliente
                        dbc.Col([
                            html.Label("Cliente"),
                            dcc.Dropdown(
                                id="metrics-client-filter",
                                placeholder="Seleccione un cliente",
                                clearable=False
                            )
                        ], width=3),
                        
                        # Filtro de proyecto
                        dbc.Col([
                            html.Label("Proyecto"),
                            dcc.Dropdown(
                                id="metrics-project-filter",
                                placeholder="Seleccione un proyecto",
                                clearable=False,
                                disabled=True
                            )
                        ], width=3),
                        
                        # Filtro de tipo de consumo
                        dbc.Col([
                            html.Label("Tipo de Consumo"),
                            dcc.Dropdown(
                                id="metrics-consumption-tags-filter",
                                placeholder="Seleccione tipos de consumo",
                                multi=True,
                                disabled=True,
                                options=[
                                    {"label": CONSUMPTION_TAGS_MAPPING.get(tag.value, tag.value), "value": tag.value}
                                    for tag in ConsumptionTags
                                ]
                            )
                        ], width=3),
                        
                        # Botones de acción
                        dbc.Col([
                            html.Div([
                                dbc.Button(
                                    "Visualizar Consumos",
                                    id="metrics-analyze-button",
                                    color="primary",
                                    className="me-2",
                                    disabled=True
                                ),
                                dbc.Button(
                                    "Actualizar Lecturas",
                                    id="metrics-update-readings-button",
                                    color="secondary",
                                    disabled=True
                                )
                            ], className="d-flex justify-content-end")
                        ], width=3)
                    ]),
                    
                    # Segunda fila de filtros
                    dbc.Row([
                        # Filtro de activo
                        dbc.Col([
                            html.Label("Activo"),
                            dcc.Dropdown(
                                id="metrics-asset-filter",
                                placeholder="Seleccione un activo",
                                clearable=False,
                                options=[{"label": "Todos", "value": "all"}],
                                value="all"
                            )
                        ], width=3),
                        
                        # Filtro de período
                        dbc.Col([
                            html.Label("Período"),
                            dcc.Dropdown(
                                id="metrics-date-period",
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
                        
                        # Selector de fechas personalizado
                        dbc.Col([
                            html.Div([
                                html.Label("Rango de fechas"),
                                dcc.DatePickerRange(
                                    id="metrics-date-range",
                                    start_date=(datetime.now() - timedelta(days=30)).date(),
                                    end_date=datetime.now().date(),
                                    display_format="YYYY-MM-DD"
                                )
                            ], id="metrics-custom-date-container", style={"display": "none"})
                        ], width=6)
                    ], className="mt-3")
                ])
            ], className="mb-4"),
            
            # Mensaje inicial
            html.Div([
                html.Div([
                    html.H4("Seleccione un cliente, proyecto y tipo de consumo para visualizar los datos", className="text-center text-muted"),
                    html.P("Utilice los filtros superiores para seleccionar los datos que desea visualizar", className="text-center text-muted")
                ], className="p-5")
            ], id="metrics-initial-message"),
            
            # Mensaje de carga
            html.Div([
                dbc.Spinner(size="lg"),
                html.H4("Cargando datos...", className="text-center mt-3")
            ], id="metrics-data-loading-message", style={"display": "none"}),
            
            # Resultado de actualización de lecturas
            html.Div(id="metrics-update-readings-result", className="mt-3"),
            
            # Contenedor de visualización
            html.Div([
                # Indicador de filtros aplicados
                html.Div(id="metrics-filter-indicator", className="mb-3"),
                
                # Tarjeta de métricas principales
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            # Consumo total del periodo
                            dbc.Col([
                                html.H5("Consumo Total del Periodo"),
                                html.Div([
                                    html.Span(id="metrics-total-period-consumption", className="h3 me-2"),
                                    html.Span(id="metrics-total-period-consumption-unit", className="text-muted")
                                ])
                            ], width=4),
                            
                            # Promedio mensual
                            dbc.Col([
                                html.H5("Promedio Mensual"),
                                html.Div([
                                    html.Span(id="metrics-monthly-average", className="h3 me-2"),
                                    html.Span(id="metrics-monthly-average-unit", className="text-muted")
                                ])
                            ], width=4),
                            
                            # Tendencia
                            dbc.Col([
                                html.H5("Tendencia"),
                                html.Div([
                                    html.Span(id="metrics-trend", className="h3 me-2"),
                                    html.Span(id="metrics-trend-period", className="text-muted")
                                ])
                            ], width=4)
                        ]),
                        html.Hr(),
                        dbc.Row([
                            # Último mes
                            dbc.Col([
                                html.H5("Último Mes"),
                                html.Div([
                                    html.Span(id="metrics-last-month-consumption", className="h3 me-2"),
                                    html.Span(id="metrics-last-month-name", className="text-muted d-block"),
                                    html.Span(id="metrics-last-month-consumption-unit", className="text-muted")
                                ])
                            ], width=4),
                            
                            # Máximo mensual
                            dbc.Col([
                                html.H5("Máximo Mensual"),
                                html.Div([
                                    html.Span(id="metrics-max-month-consumption", className="h3 me-2"),
                                    html.Span(id="metrics-max-month-name", className="text-muted d-block"),
                                    html.Span(id="metrics-max-month-consumption-unit", className="text-muted")
                                ])
                            ], width=4),
                            
                            # Mínimo mensual
                            dbc.Col([
                                html.H5("Mínimo Mensual"),
                                html.Div([
                                    html.Span(id="metrics-min-month-consumption", className="h3 me-2"),
                                    html.Span(id="metrics-min-month-name", className="text-muted d-block"),
                                    html.Span(id="metrics-min-month-consumption-unit", className="text-muted")
                                ])
                            ], width=4)
                        ])
                    ])
                ], className="mb-4"),
                
                # Resumen Mensual de Consumos
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col(html.H5("Resumen Mensual de Consumos", className="mb-0"), width="auto"),
                            dbc.Col(
                                dbc.ButtonGroup([
                                    dbc.Button(
                                        [html.I(className="fas fa-file-export me-2"), "Exportar"],
                                        id="export-monthly-data-btn",
                                        color="primary",
                                        outline=True,
                                        size="sm",
                                        className="d-flex align-items-center export-main-btn"
                                    ),
                                    dbc.DropdownMenu(
                                        [
                                            dbc.DropdownMenuItem([html.I(className="fas fa-file-csv me-2"), "CSV"], id="export-csv-btn"),
                                            dbc.DropdownMenuItem([html.I(className="fas fa-file-excel me-2"), "Excel"], id="export-excel-btn"),
                                            dbc.DropdownMenuItem([html.I(className="fas fa-file-pdf me-2"), "PDF"], id="export-pdf-btn"),
                                            dbc.DropdownMenuItem(divider=True),
                                            dbc.DropdownMenuItem([html.I(className="fas fa-chart-bar me-2"), "Imagen PNG"], id="export-png-btn"),
                                        ],
                                        size="sm",
                                        group=True,
                                        right=True,
                                    ),
                                ]),
                                width="auto",
                                className="ms-auto"
                            ),
                        ], className="d-flex align-items-center"),
                    ]),
                    dbc.CardBody([
                        # Alerta para errores de exportación
                        html.Div(id="export-error-container", className="mb-3"),
                        
                        dbc.Row([
                            # Gráfico de totales mensuales
                            dbc.Col([
                                html.H5("Total de Consumo por Mes", className="chart-title"),
                                dcc.Graph(
                                    id="metrics-monthly-totals-chart",
                                    config={'displayModeBar': True},
                                    className="dash-graph"
                                )
                            ], width=6, className="chart-container"),
                            
                            # Gráfico de promedios mensuales
                            dbc.Col([
                                html.H5("Promedio de Consumo por Mes", className="chart-title"),
                                dcc.Graph(
                                    id="metrics-monthly-averages-chart",
                                    config={'displayModeBar': True},
                                    className="dash-graph"
                                )
                            ], width=6, className="chart-container")
                        ]),
                        
                        # Tabla de resumen mensual
                        dbc.Row([
                            dbc.Col([
                                html.H5("Tabla de Resumen Mensual", className="mt-4"),
                                html.Div(id="metrics-monthly-summary-table")
                            ], width=12)
                        ]),
                        
                        # Componente para descargar archivos
                        dcc.Download(id="download-monthly-data"),
                        
                        # Toast para notificaciones de éxito
                        dbc.Toast(
                            id="export-notification",
                            header="Exportación",
                            is_open=False,
                            dismissable=True,
                            duration=4000,
                            icon="success",
                            style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 1000},
                        ),
                        
                        # Toast para notificaciones de error
                        dbc.Toast(
                            id="export-error-notification",
                            header="Error de Exportación",
                            is_open=False,
                            dismissable=True,
                            duration=6000,
                            icon="danger",
                            style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 1000},
                        ),
                    ])
                ], className="mb-4"),
                
                # Tablas de lecturas mensuales
                dbc.Card([
                    dbc.CardHeader("Lecturas Mensuales"),
                    dbc.CardBody([
                        # Alerta para errores de exportación
                        html.Div(id="monthly-readings-error-container", className="mb-3"),
                        
                        html.Div(id="metrics-monthly-readings-table"),
                        
                        # Componente para descargar archivos
                        dcc.Download(id="download-monthly-readings"),
                        
                        # Toast para notificaciones de éxito
                        dbc.Toast(
                            id="monthly-readings-export-notification",
                            header="Exportación",
                            is_open=False,
                            dismissable=True,
                            duration=4000,
                            icon="success",
                            style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 1000},
                        ),
                        
                        # Toast para notificaciones de error
                        dbc.Toast(
                            id="monthly-readings-export-error-notification",
                            header="Error de Exportación",
                            is_open=False,
                            dismissable=True,
                            duration=6000,
                            icon="danger",
                            style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 1000},
                        ),
                    ])
                ], className="mb-4"),
                
                # Tablas de lecturas mensuales por tipo de consumo
                dbc.Card([
                    dbc.CardHeader("Lecturas Mensuales por Tipo de Consumo"),
                    dbc.CardBody([
                        html.Div(id="metrics-monthly-readings-by-consumption-type")
                    ])
                ], className="mb-4"),
                
                # Botón para regeneración masiva
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "Regenerar Lecturas en Lote",
                            id="bulk-regenerate-readings-btn",
                            color="warning",
                            className="me-2"
                        )
                    ], width=12, className="d-flex justify-content-end")
                ], className="mb-4")
            ], id="metrics-visualization-container", style={"display": "none"}),
            
            # Modales
            # Modal de detalle de consumo
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Detalle de Consumo")),
                dbc.ModalBody(id="consumption-detail-modal-body"),
                dbc.ModalFooter(
                    dbc.Button("Cerrar", id="close-consumption-detail-modal", className="ms-auto")
                )
            ], id="consumption-detail-modal", size="xl"),
            
            # Modal de actualización de lecturas
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Actualizar Lecturas")),
                dbc.ModalBody(id="update-asset-readings-modal-body"),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="close-update-asset-readings-modal", className="me-2"),
                    dbc.Button("Confirmar", id="confirm-update-asset-readings", color="primary")
                ])
            ], id="update-asset-readings-modal", size="lg"),
            
            # Modal de regeneración de lecturas
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Regenerar Lecturas")),
                dbc.ModalBody(id="regenerate-readings-modal-body"),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="cancel-regenerate-readings", className="me-2"),
                    dbc.Button("Confirmar", id="confirm-regenerate-readings", color="primary")
                ])
            ], id="regenerate-readings-modal", size="lg"),
            
            # Modal de confirmación de eliminación de archivo
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Confirmar Eliminación")),
                dbc.ModalBody(id="delete-file-confirm-body"),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="cancel-delete-file", className="me-2"),
                    dbc.Button("Eliminar", id="confirm-delete-file", color="danger")
                ])
            ], id="delete-file-confirm-modal", size="md"),
            
            # Modal de confirmación de regeneración masiva
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Confirmar Regeneración Masiva")),
                dbc.ModalBody(id="confirm-regeneration-body"),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="cancel-confirmation", className="me-2"),
                    dbc.Button("Proceder", id="proceed-regeneration", color="primary")
                ])
            ], id="confirm-regeneration-modal", size="lg"),
            
            # Modal de regeneración masiva
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Regeneración Masiva de Lecturas")),
                dbc.ModalBody(id="bulk-regenerate-modal-body"),
                dbc.ModalFooter([
                    dbc.Button("Cerrar", id="cancel-bulk-regenerate", className="me-2"),
                    dbc.Button("Cerrar Resultados", id="close-results", className="me-2", style={"display": "none"}),
                    dbc.Button("Confirmar", id="confirm-bulk-regenerate", color="primary")
                ])
            ], id="bulk-regenerate-modal", size="xl"),
            
            # Intervalo para actualizar progreso de regeneración
            dcc.Interval(
                id="regeneration-progress-interval",
                interval=2000,  # 2 segundos
                n_intervals=0,
                disabled=True
            ),
            
            # Modal para detalles de cálculo
            create_calculation_detail_modal(),
            
            # Modal de detalle de asset
            create_asset_detail_modal()
        ], fluid=True)
    ])

# Registrar callbacks
def register_metrics_callbacks(app):
    """Register all callbacks for the metrics page."""
    register_callbacks(app)

# Layout
layout = create_layout() 