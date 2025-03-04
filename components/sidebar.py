import dash_bootstrap_components as dbc
from dash import html

def create_sidebar():
    """Crea el componente de sidebar"""
    return html.Div(
        [
            html.H2("Alfred Dashboard", className="display-6"),
            html.Hr(),
            
            # Sección Inicio
            dbc.Nav(
                [
                    dbc.NavLink([html.I(className="fas fa-home me-2"), "Inicio"], href="/", active="exact"),
                ],
                vertical=True,
                pills=True,
                className="mb-3"
            ),
            
            # Sección Apps
            html.P("Apps", className="lead mb-1"),
            dbc.Nav(
                [
                    dbc.NavLink([html.I(className="fas fa-chart-line me-2"), "Metrics"], href="/metrics", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-lock me-2"), "Lock"], href="/lock", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-th-large me-2"), "Spaces"], href="/spaces", active="exact"),
                ],
                vertical=True,
                pills=True,
                className="mb-3"
            ),
            
            # Sección Configuración
            html.P("Configuración", className="lead mb-1"),
            dbc.Nav(
                [
                    dbc.NavLink([html.I(className="fas fa-cog me-2"), "Configuración DB"], href="/db-config", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-database me-2"), "Explorador BD"], href="/database-explorer", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-file-export me-2"), "Exportar Datos"], href="/data-export", active="exact"),
                ],
                vertical=True,
                pills=True,
                className="mb-3"
            ),
            
            # Sección Desarrollo (opcional, puedes eliminarla si no la necesitas)
            html.Hr(),
            html.P("Desarrollo", className="lead mb-1"),
            dbc.Nav(
                [
                    dbc.NavLink([html.I(className="fas fa-palette me-2"), "Componentes UI"], href="/ui-demo", active="exact"),
                ],
                vertical=True,
                pills=True,
            ),
        ],
        className="sidebar",
    )
