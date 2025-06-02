import dash_bootstrap_components as dbc
from dash import html, dcc
from utils.api import get_clientes, get_projects, get_clientes_fallback, get_projects_fallback
from utils.logging import get_logger
import os

logger = get_logger(__name__)

def create_sidebar():
    """Crea el componente de sidebar"""
    # Crear el sidebar con opciones por defecto
    sidebar = html.Div([
        html.Div([
            # Sección de Navegación
            html.Div([
                html.H5("NAVEGACIÓN", className="sidebar-title"),
                html.Hr(className="my-2"),
                dbc.Nav(
                    [
                        dbc.NavLink(
                            [html.I(className="fas fa-home me-2"), "Inicio"],
                            href="/",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ],
                    vertical=True,
                    pills=True,
                    className="sidebar-nav"
                ),
            ], className="mb-4"),
            
            # Sección de Apps
            html.Div([
                html.H5("APPS", className="sidebar-title"),
                html.Hr(className="my-2"),
                
                # Menú con submenús para Apps
                html.Div([
                    # Metrics App con submenú
                    html.Div([
                        # Botón principal que actúa como cabecera del menú desplegable
                        html.Div([
                            dbc.Button(
                                [html.I(className="fas fa-chart-bar me-2"), "Metrics ", 
                                 html.I(className="fas fa-chevron-down ms-auto")],
                                id="metrics-submenu-button",
                                color="link",
                                className="sidebar-link text-start w-100 py-2 d-flex align-items-center justify-content-between"
                            ),
                        ]),
                        
                        # Contenido desplegable para Metrics
                        dbc.Collapse(
                            dbc.Nav(
                                [
                                    dbc.NavLink(
                                        [html.I(className="fas fa-chart-line me-2"), "Análisis General"],
                                        href="/metrics",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-tint me-2"), "Consumo de Agua"],
                                        href="/water-consumption",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-leaf me-2"), "Huella de Carbono"],
                                        href="/carbon-footprint",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-chart-area me-2"), "Análisis de Agua"],
                                        href="/water-analysis",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-bolt me-2"), "Consumo Eléctrico"],
                                        href="/electricity-consumption",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                ],
                                vertical=True,
                                pills=True,
                                className="sidebar-nav"
                            ),
                            id="metrics-submenu-collapse",
                        ),
                    ], className="mb-3"),
                    
                    # Spaces App
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-building me-2"), "Spaces"],
                            href="/spaces",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ], className="mb-2"),
                    
                    # Lock App
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-lock me-2"), "Lock"],
                            href="/lock",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ], className="mb-2"),
                    
                    # Smart Locks App
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-key me-2"), "Smart Locks"],
                            href="/smart-locks",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ]),
                ], className="sidebar-nav"),
            ], className="mb-4"),
            
            # Sección de Herramientas
            html.Div([
                html.H5("HERRAMIENTAS", className="sidebar-title"),
                html.Hr(className="my-2"),
                
                html.Div([
                    # Exportaciones
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-file-export me-2"), "Exportaciones"],
                            href="/exportaciones",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ], className="mb-2"),
                    
                    # Database con submenú
                    html.Div([
                        # Botón principal que actúa como cabecera del menú desplegable
                        html.Div([
                            dbc.Button(
                                [html.I(className="fas fa-database me-2"), "Database ", 
                                 html.I(className="fas fa-chevron-down ms-auto")],
                                id="db-submenu-button",
                                color="link",
                                className="sidebar-link text-start w-100 py-2 d-flex align-items-center justify-content-between"
                            ),
                        ]),
                        
                        # Contenido desplegable para Database
                        dbc.Collapse(
                            dbc.Nav(
                                [
                                    dbc.NavLink(
                                        [html.I(className="fas fa-table me-2"), "Explorer"],
                                        href="/db-explorer",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-cog me-2"), "Configuración"],
                                        href="/db-config",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-flask me-2"), "API Test"],
                                        href="/api-test",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-sync me-2"), "Bulk Regeneration"],
                                        href="/bulk-regeneration",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                ],
                                vertical=True,
                                pills=True,
                                className="sidebar-nav"
                            ),
                            id="db-submenu-collapse",
                        ),
                    ]),
                ], className="sidebar-nav"),
            ], className="mb-4")
        ], className="sidebar-content"),
        
        # Línea del final del sidebar (placeholder que puede ser eliminado si no se necesita)
        html.Hr(className="my-4"),
        
    ], 
    className="sidebar",
    style={"height": "100vh", "overflow-y": "auto"}
    )
    
    return sidebar

def register_callbacks(app):
    """
    Registra los callbacks para la barra lateral
    
    Args:
        app: Instancia de la aplicación Dash
    """
    from dash.dependencies import Input, Output, State
    
    # Callback para alternar el submenú de métricas
    @app.callback(
        Output("metrics-submenu-collapse", "is_open"),
        [Input("metrics-submenu-button", "n_clicks")],
        [State("metrics-submenu-collapse", "is_open")],
    )
    def toggle_metrics_submenu(n, is_open):
        if n:
            return not is_open
        return is_open
    
    # Callback para alternar el submenú de base de datos
    @app.callback(
        Output("db-submenu-collapse", "is_open"),
        [Input("db-submenu-button", "n_clicks")],
        [State("db-submenu-collapse", "is_open")],
    )
    def toggle_db_submenu(n, is_open):
        if n:
            return not is_open
        return is_open
