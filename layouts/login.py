from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import dash
from utils.auth import auth_service

# Layout para la página de login
layout = html.Div([
    dcc.Location(id="login-url", refresh=True),
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Img(src="/assets/img/logo.svg", className="login-logo mb-4"),
                    html.H2("Iniciar Sesión", className="text-center mb-4"),
                    
                    # Alerta para mensajes de error o éxito
                    html.Div(id="login-alert"),
                    
                    # Formulario de login
                    dbc.Form([
                        html.Div([
                            dbc.Label("Email", html_for="login-email"),
                            dbc.Input(
                                type="email",
                                id="login-email",
                                placeholder="Ingrese su email",
                                className="mb-3"
                            ),
                        ], className="mb-3"),
                        
                        html.Div([
                            dbc.Label("Contraseña", html_for="login-password"),
                            dbc.Input(
                                type="password",
                                id="login-password",
                                placeholder="Ingrese su contraseña",
                                className="mb-3"
                            ),
                        ], className="mb-4"),
                        
                        dbc.Button(
                            "Iniciar Sesión",
                            id="login-button",
                            color="primary",
                            className="w-100 mb-3"
                        ),
                        
                        # Spinner para indicar carga
                        dbc.Spinner(html.Div(id="login-loading"), color="primary", type="grow", size="sm"),
                        
                        # Store para almacenar el estado del login
                        dcc.Store(id="login-state"),
                    ]),
                    
                    html.Hr(className="my-4"),
                    
                    html.P([
                        "¿Problemas para iniciar sesión? ",
                        html.A("Contacte a soporte", href="mailto:soporte@alfredsmartdata.com")
                    ], className="text-center text-muted small")
                    
                ], className="login-form p-4 border rounded shadow-sm bg-white")
            ], width={"size": 6, "offset": 3}, lg={"size": 4, "offset": 4}, md={"size": 6, "offset": 3}, sm={"size": 10, "offset": 1})
        ], className="vh-100 d-flex align-items-center")
    ], fluid=True)
], className="login-page bg-light")

# Callback para manejar el login
def register_callbacks(app):
    @app.callback(
        [
            Output("login-alert", "children"),
            Output("login-loading", "children"),
            Output("login-state", "data"),
            Output("login-url", "pathname")
        ],
        [Input("login-button", "n_clicks")],
        [
            State("login-email", "value"),
            State("login-password", "value")
        ],
        prevent_initial_call=True
    )
    def handle_login(n_clicks, email, password):
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Validar campos
        if not email or not password:
            return dbc.Alert(
                "Por favor, complete todos los campos",
                color="danger",
                dismissable=True
            ), "", {"authenticated": False}, dash.no_update
        
        # Intentar login
        result = auth_service.login(email, password)
        
        if result["success"]:
            # Login exitoso - Forzar recarga completa para asegurar redirección
            from dash import dcc
            import time
            
            # Mostrar mensaje de éxito
            alert = dbc.Alert(
                "Login exitoso. Redirigiendo...",
                color="success",
                dismissable=False
            )
            
            # Pequeña pausa para mostrar el mensaje
            time.sleep(0.5)
            
            # Redireccionar a la página principal
            return alert, "", {"authenticated": True, "timestamp": time.time()}, "/"
        else:
            # Login fallido
            return dbc.Alert(
                result["message"],
                color="danger",
                dismissable=True
            ), "", {"authenticated": False}, dash.no_update 