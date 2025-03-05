from dash import html, dcc, callback_context
import dash_bootstrap_components as dbc
from utils.auth import auth_service
from components.client_selector import create_client_selector
from utils.logging import get_logger

logger = get_logger(__name__)

def create_navbar():
    """
    Crea la barra de navegación superior con opciones de usuario y logout
    
    Returns:
        Un componente de barra de navegación de Dash Bootstrap
    """
    # Botón de logout
    logout_button = dbc.Button(
        [html.I(className="fas fa-sign-out-alt me-2"), "Cerrar Sesión"],
        id="logout-button",
        color="light",
        outline=True,
        size="sm",
        className="ms-2"
    )
    
    # Dropdown de usuario
    user_dropdown = dbc.DropdownMenu(
        [
            dbc.DropdownMenuItem([
                html.I(className="fas fa-user me-2"),
                html.Span(id="user-type-display")
            ], header=True),
            dbc.DropdownMenuItem(divider=True),
            dbc.DropdownMenuItem("Perfil", href="#"),
            dbc.DropdownMenuItem("Configuración", href="#"),
            dbc.DropdownMenuItem(divider=True),
            dbc.DropdownMenuItem(logout_button, className="p-0")
        ],
        label=html.Span([
            html.I(className="fas fa-user-circle me-2"),
            "Usuario"
        ]),
        nav=True,
        align_end=True,
    )
    
    # Crear el selector de cliente/proyecto
    client_selector = create_client_selector()
    
    # Crear la barra de navegación
    navbar = dbc.Navbar(
        dbc.Container(
            [
                # Logo y nombre de la aplicación
                html.A(
                    dbc.Row(
                        [
                            dbc.Col(html.Img(src="/assets/img/logo.svg", height="30px")),
                            dbc.Col(dbc.NavbarBrand("Alfred Dashboard", className="ms-2")),
                        ],
                        align="center",
                        className="g-0",
                    ),
                    href="/",
                    style={"textDecoration": "none"},
                ),
                
                # Selector de cliente/proyecto (nuevo)
                client_selector,
                
                # Elementos a la derecha
                dbc.NavbarToggler(id="navbar-toggler"),
                dbc.Collapse(
                    dbc.Nav(
                        [user_dropdown],
                        className="ms-auto",
                        navbar=True,
                    ),
                    id="navbar-collapse",
                    navbar=True,
                ),
                
                # Store para el estado de logout
                dcc.Store(id="logout-state"),
                
                # Location para redireccionar después del logout
                dcc.Location(id="logout-url", refresh=True),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        className="mb-4",
    )
    
    return navbar

def register_callbacks(app):
    """
    Registra los callbacks para la barra de navegación
    
    Args:
        app: Instancia de la aplicación Dash
    """
    from dash.dependencies import Input, Output, State
    import dash
    
    # Importar y registrar callbacks del selector de cliente/proyecto
    from components.client_selector import register_callbacks as register_client_selector_callbacks
    register_client_selector_callbacks(app)
    
    # Callback para actualizar la información del usuario en la barra de navegación
    @app.callback(
        Output("user-type-display", "children"),
        [Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    def update_user_info(token_data):
        if not token_data or 'token' not in token_data:
            return "Tipo: Usuario"
        
        # Obtener datos del usuario desde el token JWT
        try:
            user_data = auth_service.get_user_data_from_token(token_data['token'])
            user_type = user_data.get('user_type', 'Usuario')
            
            return f"Tipo: {user_type}"
        except Exception as e:
            logger.error(f"Error al obtener datos del usuario: {str(e)}")
            return "Tipo: Usuario"
    
    # Callback para manejar el logout
    @app.callback(
        [Output("logout-state", "data"), 
         Output("jwt-token-store", "data", allow_duplicate=True),
         Output("logout-url", "pathname")],
        [Input("logout-button", "n_clicks")],
        [State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def handle_logout(n_clicks, token_data):
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update
        
        # Limpiar el token JWT del store (solo en esta pestaña)
        # No es necesario llamar a auth_service.logout() ya que no almacenamos el token en el servidor
        
        # Redireccionar a la página de login
        return {"logged_out": True}, {}, "/login"
    
    # Callback para alternar el colapso de la barra de navegación en dispositivos móviles
    @app.callback(
        Output("navbar-collapse", "is_open"),
        [Input("navbar-toggler", "n_clicks")],
        [State("navbar-collapse", "is_open")],
    )
    def toggle_navbar_collapse(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return is_open 