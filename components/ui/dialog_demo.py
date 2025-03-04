from dash import html, dcc
import dash_bootstrap_components as dbc
import uuid

from components.ui import (
    create_dialog,
    create_dialog_header,
    create_dialog_footer,
    create_dialog_title,
    create_dialog_description,
    create_button,
    create_input,
    create_checkbox
)

def create_login_dialog():
    """
    Crea un diálogo de inicio de sesión similar al ejemplo de React.
    
    Returns:
        Un componente de diálogo de inicio de sesión
    """
    # Generar IDs únicos para los componentes
    dialog_id = str(uuid.uuid4())
    email_id = f"email-{dialog_id}"
    password_id = f"password-{dialog_id}"
    remember_id = f"remember-{dialog_id}"
    
    # Crear el contenido del diálogo
    dialog_content = html.Div([
        # Icono circular (usando FontAwesome en lugar de SVG)
        html.Div(
            html.I(className="fas fa-user-circle fa-2x text-secondary"),
            className="d-flex justify-content-center align-items-center rounded-circle border border-secondary",
            style={"width": "44px", "height": "44px"}
        ),
        
        # Encabezado del diálogo
        create_dialog_header([
            create_dialog_title("Welcome back", className="text-center"),
            create_dialog_description(
                "Enter your credentials to login to your account.",
                className="text-center text-muted"
            )
        ]),
        
        # Formulario
        html.Form([
            html.Div([
                html.Div([
                    create_input(
                        id=email_id,
                        type="email",
                        label="Email",
                        placeholder="hi@yourcompany.com",
                        required=True
                    )
                ], className="mb-3"),
                
                html.Div([
                    create_input(
                        id=password_id,
                        type="password",
                        label="Password",
                        placeholder="Enter your password",
                        required=True
                    )
                ], className="mb-3")
            ], className="mb-4"),
            
            html.Div([
                html.Div([
                    create_checkbox(
                        id=remember_id,
                        label="Remember me",
                        className="text-muted"
                    )
                ], className="d-inline-block"),
                
                html.A(
                    "Forgot password?",
                    href="#",
                    className="text-decoration-underline ms-auto small"
                )
            ], className="d-flex justify-content-between align-items-center mb-3"),
            
            create_button(
                "Sign in",
                color="primary",
                className="w-100 mb-3"
            ),
            
            # Separador "Or"
            html.Div([
                html.Span("Or", className="text-muted small px-2")
            ], className="d-flex align-items-center text-center mb-3",
               style={"position": "relative"},
               **{
                   "data-content": "",
                   "data-before": {"style": "flex: 1; height: 1px; background: #dee2e6;"},
                   "data-after": {"style": "flex: 1; height: 1px; background: #dee2e6;"}
               }),
            
            create_button(
                "Login with Google",
                color="light",
                outline=True,
                className="w-100"
            )
        ], className="mt-3")
    ], className="d-flex flex-column align-items-center")
    
    # Crear el botón de activación
    trigger = create_button("Sign in", color="light", outline=True)
    
    # Crear el diálogo
    return create_dialog(
        dialog_id=dialog_id,
        trigger=trigger,
        content=dialog_content,
        size="md",
        centered=True,
        scrollable=True
    )

# Ejemplo de uso
def get_dialog_demo():
    """
    Obtiene un ejemplo de uso del componente de diálogo.
    
    Returns:
        Un componente de demostración del diálogo
    """
    return html.Div([
        html.H3("Dialog Component Demo", className="mb-4"),
        html.P("Click the button below to open the login dialog:", className="mb-3"),
        create_login_dialog()
    ], className="p-4") 