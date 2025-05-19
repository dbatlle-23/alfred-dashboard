import dash
from dash import html, dcc, callback_context
import dash_bootstrap_components as dbc
import os
import sys
import traceback
import argparse
import logging

# Configurar logging
from utils.logging import configure_logging
logger = configure_logging()

# Importar manejadores de errores
from utils.error_handlers import handle_exceptions, try_operation

# Importar servicio de autenticación
from utils.auth import auth_service, protect_callbacks

# Importar componentes
from components.sidebar import create_sidebar, register_callbacks as register_sidebar_callbacks
from components.navbar import create_navbar

# Inicializar componentes UI
from components.ui.dialog import Dialog
dialog = Dialog()

# Manejo de errores global para callbacks
def global_callback_error_handler(app):
    """Configura un manejador global de errores para callbacks"""
    # Nota: callback_context_manager no está disponible en esta versión de Dash
    # En su lugar, usamos un enfoque alternativo con un callback global
    
    # Registrar un callback para manejar errores globales
    @app.callback(
        dash.dependencies.Output("global-error-container", "children"),
        [dash.dependencies.Input("url", "pathname")],
        prevent_initial_call=True
    )
    def handle_global_errors(pathname):
        # Este callback se activará cuando cambie la URL
        # Podemos usar esto para limpiar cualquier error previo
        return None

# Inicializar la aplicación
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, 'https://use.fontawesome.com/releases/v5.15.4/css/all.css'],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "favicon", "content": "/assets/favicon.png"}
    ]
)

# Configurar título
app.title = "Alfred Dashboard"

# Configurar manejador global de errores
global_callback_error_handler(app)

# Inicializar componentes UI con la app
dialog.init_callbacks(app)

# Definir el layout principal
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    # Contenedor para mensajes de error global
    html.Div(id="global-error-container"),
    # Contenedor para estado de autenticación (usado por el sistema de auth)
    html.Div(id="global-auth-status", style={"display": "none"}),
    # Store para el token JWT (almacenado en sessionStorage del navegador)
    dcc.Store(id="jwt-token-store", storage_type="session", data={}),
    # Contenedor para el contenido de la página
    html.Div(id="page-content")
])

# Importar callbacks (después de definir app)
from callbacks.db_explorer import register_callbacks
from callbacks.db_config import register_config_callbacks

# Registrar todos los callbacks
try:
    logger.info("Registrando callbacks de explorador de base de datos")
    register_callbacks(app)
    logger.info("Registrando callbacks de configuración de base de datos")
    register_config_callbacks(app)
except Exception as e:
    logger.error(f"Error al registrar callbacks: {str(e)}")
    logger.debug(traceback.format_exc())

# Registrar callbacks de autenticación
from layouts.login import register_callbacks as register_login_callbacks
from components.navbar import register_callbacks as register_navbar_callbacks

# Registrar callbacks de las vistas principales
from layouts.metrics_refactored import register_callbacks as register_metrics_callbacks
from layouts.lock import register_callbacks as register_lock_callbacks
from layouts.spaces import register_callbacks as register_spaces_callbacks
from layouts.api_test import register_callbacks as register_api_test_callbacks
# Importar callbacks para configuración de anomalías
from layouts.anomaly_config import register_callbacks as register_anomaly_config_callbacks
# Importar callbacks para la página de inicio
from layouts.home import register_callbacks as register_home_callbacks
# Importar callbacks para análisis de consumo de agua
from layouts.water_consumption import register_callbacks as register_water_consumption_callbacks
# Importar callbacks para análisis de huella de carbono
from layouts.carbon_footprint import register_callbacks as register_carbon_footprint_callbacks
# Importar callbacks para gestión de cerraduras inteligentes
from layouts.smart_locks import register_callbacks as register_smart_locks_callbacks

try:
    logger.info("Registrando callbacks de autenticación")
    register_login_callbacks(app)
    register_navbar_callbacks(app)
    # Registrar callbacks del sidebar
    register_sidebar_callbacks(app)
    
    # Registrar callbacks de las vistas principales
    logger.info("Registrando callbacks de las vistas principales")
    register_metrics_callbacks(app)
    register_lock_callbacks(app)
    
    # Registrar callbacks para spaces
    register_spaces_callbacks(app)
    
    register_api_test_callbacks(app)
    
    # Registrar callbacks para configuración de anomalías
    register_anomaly_config_callbacks(app)
    
    # Registrar callbacks para la página de inicio
    logger.info("Registrando callbacks de la página de inicio")
    register_home_callbacks(app)
    
    # Registrar callbacks para análisis de consumo de agua
    logger.info("Registrando callbacks para análisis de consumo de agua")
    register_water_consumption_callbacks(app)
    
    # Registrar callbacks para análisis de huella de carbono
    logger.info("Registrando callbacks para análisis de huella de carbono")
    register_carbon_footprint_callbacks(app)
    
    # Registrar callbacks para gestión de cerraduras inteligentes
    logger.info("Registrando callbacks para gestión de cerraduras inteligentes")
    register_smart_locks_callbacks(app)
    
    # Proteger callbacks
    protect_callbacks(app)
except Exception as e:
    logger.error(f"Error al registrar callbacks de autenticación: {str(e)}")
    logger.debug(traceback.format_exc())

# Callback para cambiar el contenido de la página
@app.callback(
    dash.dependencies.Output("page-content", "children"),
    [dash.dependencies.Input("url", "pathname")],
    [dash.dependencies.State("jwt-token-store", "data")]
)
@handle_exceptions(default_return=html.Div("Ha ocurrido un error al cargar la página", className="alert alert-danger"))
def display_page(pathname, token_data):
    # Importar layouts aquí para evitar importaciones circulares
    from layouts.home import layout as home_layout
    from layouts.db_config import layout as db_config_layout
    from layouts.db_explorer import layout as db_explorer_layout
    from layouts.ui_demo import layout as ui_demo_layout
    from layouts.login import layout as login_layout
    from layouts.metrics_refactored import layout as metrics_layout
    from layouts.lock import layout as lock_layout
    from layouts.spaces import layout as spaces_layout
    from layouts.api_test import layout as api_test_layout
    # Importar layout para configuración de anomalías
    from layouts.anomaly_config import layout as anomaly_config_layout
    # Importar layout para análisis de consumo de agua
    from layouts.water_consumption import layout as water_consumption_layout
    # Importar layout para análisis de huella de carbono
    from layouts.carbon_footprint import layout as carbon_footprint_layout
    # Importar layout para gestión de cerraduras inteligentes
    from layouts.smart_locks import layout as smart_locks_layout
    
    logger.info(f"Navegando a la ruta: {pathname}")
    
    # Si la ruta es /login, mostrar la página de login
    if pathname == "/login":
        return login_layout
    
    # Obtener el token JWT del store
    token = token_data.get('token') if token_data else None
    
    # Verificar autenticación para todas las demás rutas
    if not token or not auth_service.is_authenticated(token):
        logger.info("Usuario no autenticado, redirigiendo a login")
        # Usar dcc.Location para forzar la redirección a /login
        return html.Div([
            dcc.Location(id="redirect-to-login", pathname="/login"),
            html.Div("Redirigiendo a la página de login...")
        ])
    
    try:
        logger.info("Creando layout principal")
        
        # Determinar qué contenido mostrar
        logger.info(f"Determinando contenido para la ruta: {pathname}")
        if pathname == "/database-explorer":
            content = db_explorer_layout
        elif pathname == "/db-config":
            content = db_config_layout
        elif pathname == "/ui-demo":
            content = ui_demo_layout
        elif pathname == "/metrics":
            content = metrics_layout
        elif pathname == "/lock":
            content = lock_layout
        elif pathname == "/spaces":
            content = spaces_layout
        elif pathname == "/api-test":
            logger.info("Cargando layout de API test")
            content = api_test_layout
        elif pathname == "/anomaly-config":
            logger.info("Cargando layout de configuración de anomalías")
            content = anomaly_config_layout
        elif pathname == "/water-consumption":
            logger.info("Cargando layout de análisis de consumo de agua")
            content = water_consumption_layout
        elif pathname == "/carbon-footprint":
            logger.info("Cargando layout de análisis de huella de carbono")
            content = carbon_footprint_layout
        elif pathname == "/smart-locks":
            content = smart_locks_layout
        else:
            content = home_layout
        
        # Crear el layout principal con navbar y sidebar
        main_layout = html.Div([
            # Navbar
            create_navbar(),
            
            # Contenido principal con sidebar
            dbc.Container([
                dbc.Row([
                    # Sidebar
                    dbc.Col(create_sidebar(), width=2, className="sidebar-container"),
                    # Contenido de la página
                    dbc.Col(
                        content,  # Colocar el contenido directamente aquí
                        width=10, 
                        className="content-container"
                    ),
                ])
            ], fluid=True)
        ])
        
        return main_layout
    except Exception as e:
        logger.error(f"Error en display_page: {str(e)}")
        logger.exception("Detalles del error:")
        return html.Div(f"Ha ocurrido un error al cargar la página: {str(e)}", className="alert alert-danger")

# Crear carpetas necesarias
os.makedirs("data/analyzed_data", exist_ok=True)

# Ejecutar la aplicación
if __name__ == "__main__":
    try:
        # Parsear argumentos de línea de comandos
        parser = argparse.ArgumentParser(description='Alfred Dashboard')
        parser.add_argument('--port', type=int, default=8050, help='Puerto para ejecutar la aplicación')
        parser.add_argument('--host', type=str, default='0.0.0.0', help='Host para ejecutar la aplicación')
        parser.add_argument('--debug', action='store_true', help='Ejecutar en modo debug')
        args = parser.parse_args()
        
        # Asegurarse de que existe el directorio de configuración
        os.makedirs("config", exist_ok=True)
        
        logger.info("Iniciando la aplicación Alfred Dashboard")
        
        # Obtener host y puerto del entorno (útil para Docker) o de los argumentos
        host = os.getenv('HOST', args.host)
        port = int(os.getenv('PORT', args.port))
        debug = os.getenv('DASH_DEBUG', 'false').lower() == 'true' or args.debug
        
        # Información adicional de inicio
        logger.info(f"Ejecutando en: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
        logger.info(f"Modo debug: {'activado' if debug else 'desactivado'}")
        
        # Iniciar servidor
        app.run_server(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.critical(f"Error fatal al iniciar la aplicación: {str(e)}")
        logger.exception("Detalles del error:")
        # En caso de error fatal, salir con código de error
        sys.exit(1)
