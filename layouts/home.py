from dash import html, dcc, Input, Output, State, callback, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import dash
import traceback
import time
from utils.api import get_clientes, get_projects
from utils.auth import AuthService
from utils.logging import get_logger
# --- Placeholder Imports --- 
# TODO: Replace these comments with actual imports from your project structure
# from utils.api_client import fetch_clients, fetch_projects 
# from utils.logging import get_logger # Optional: If you want to log errors

# Initialize the logger
logger = get_logger(__name__)

# Initialize the authentication service
auth_service = AuthService()

# Layout para la página de inicio
layout = html.Div([
    html.H2("Dashboard Alfred", className="mb-4"),
    
    # --- Welcome Card ---
    dbc.Card([
        dbc.CardBody([
            html.H5("Bienvenido al Dashboard de Alfred", className="card-title"),
            html.P(
                "Esta aplicación te permite explorar y gestionar la base de datos de Alfred. "
                "Utiliza el menú lateral para navegar entre las diferentes secciones.",
                className="card-text"
            ),
            html.Div([
                html.P("Para comenzar, puedes:", className="mt-3"),
                html.Ul([
                    html.Li([
                        "Ver las métricas y análisis en ",
                        html.A("Metrics", href="/metrics")
                    ]),
                    html.Li([
                        "Gestionar espacios y reservas en ",
                        html.A("Spaces", href="/spaces")
                    ]),
                    html.Li([
                        "Controlar accesos en ",
                        html.A("Lock", href="/lock")
                    ]),
                    html.Li([
                        "Configurar la base de datos en ",
                        html.A("Configuración DB", href="/db-config")
                    ]),
                    html.Li([
                        "Explorar las tablas y datos en ",
                        html.A("Explorador BD", href="/db-explorer")
                    ]),
                    html.Li([
                        "Exportar datos en ",
                        html.A("Exportaciones", href="/exportaciones")
                    ]),
                ]),
            ])
        ])
    ], className="mb-4"),

    # --- Quick Access Cards ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.I(className="fas fa-chart-line fa-3x text-primary mb-3"),
                    html.H5("Metrics", className="card-title"),
                    html.P("Analiza consumos energéticos y medioambientales", className="card-text"),
                    dbc.Button("Ir a Metrics", color="primary", href="/metrics", external_link=True)
                ], className="text-center")
            ], className="h-100")
        ], md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.I(className="fas fa-building fa-3x text-success mb-3"),
                    html.H5("Spaces", className="card-title"),
                    html.P("Gestiona espacios comunes y reservas", className="card-text"),
                    dbc.Button("Ir a Spaces", color="success", href="/spaces", external_link=True)
                ], className="text-center")
            ], className="h-100")
        ], md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.I(className="fas fa-file-export fa-3x text-info mb-3"),
                    html.H5("Exportaciones", className="card-title"),
                    html.P("Exporta datos y genera reportes", className="card-text"),
                    dbc.Button("Ir a Exportaciones", color="info", href="/exportaciones", external_link=True)
                ], className="text-center")
            ], className="h-100")
        ], md=4)
    ], className="mb-4"),

    # --- System Status ---
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-info-circle me-2"),
            html.Span("Estado del Sistema")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-check-circle text-success fa-2x"),
                        html.H6("Sistema Operativo", className="mt-2"),
                        html.P("Todos los servicios funcionando correctamente", className="text-muted small")
                    ], className="text-center")
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-database text-primary fa-2x"),
                        html.H6("Base de Datos", className="mt-2"),
                        html.P("Conexión estable", className="text-muted small")
                    ], className="text-center")
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-shield-alt text-warning fa-2x"),
                        html.H6("Seguridad", className="mt-2"),
                        html.P("Autenticación activa", className="text-muted small")
                    ], className="text-center")
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-clock text-info fa-2x"),
                        html.H6("Última Actualización", className="mt-2"),
                        html.P("Hace 5 minutos", className="text-muted small")
                    ], className="text-center")
                ], md=3)
            ])
        ])
    ])
])

# Función para registrar callbacks (simplificada)
def register_callbacks(app):
    """Registra los callbacks de la página de inicio con la aplicación principal."""
    # Ya no necesitamos callbacks de exportación aquí
    pass

def fetch_clients(token):
    """Obtiene la lista de clientes usando la API
    
    Args:
        token: Token JWT para autenticación
        
    Returns:
        list: Lista de clientes o None si hay un error
    """
    try:
        logger.info("Obteniendo lista de clientes...")
        clients = get_clientes(jwt_token=token)
        logger.info(f"Se obtuvieron {len(clients) if clients else 0} clientes")
        return clients
    except Exception as e:
        logger.error(f"Error al obtener clientes: {str(e)}", exc_info=True)
        return None

def fetch_projects(token):
    """Obtiene la lista de proyectos usando la API
    
    Args:
        token: Token JWT para autenticación
        
    Returns:
        list: Lista de proyectos o None si hay un error
    """
    try:
        logger.info("Obteniendo lista de proyectos...")
        projects = get_projects(jwt_token=token)
        logger.info(f"Se obtuvieron {len(projects) if projects else 0} proyectos")
        # Imprimir algunos campos clave para depuración
        if projects and len(projects) > 0:
            sample_project = projects[0]
            logger.info(f"Ejemplo de proyecto: id={sample_project.get('id', 'N/A')}, "
                       f"name={sample_project.get('name', 'N/A')}, "
                       f"client_id={sample_project.get('client_id', 'N/A')}")
        return projects
    except Exception as e:
        logger.error(f"Error al obtener proyectos: {str(e)}", exc_info=True)
        return None

def check_authentication(token_data):
    """Verifica si el token de autenticación es válido
    
    Args:
        token_data: Datos de token JWT
        
    Returns:
        bool: True si el token es válido, False en caso contrario
    """
    try:
        token = token_data.get('token') if token_data else None
        is_valid = auth_service.is_authenticated(token)
        logger.info(f"Verificación de token: {'válido' if is_valid else 'inválido'}")
        return is_valid
    except Exception as e:
        logger.error(f"Error al verificar autenticación: {str(e)}", exc_info=True)
        return False

