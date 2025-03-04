from dash import html, dcc
import dash_bootstrap_components as dbc

from components.ui.dialog_demo import get_dialog_demo
from components.ui import (
    create_button,
    create_input,
    create_checkbox
)

# Layout para la página de demostración de componentes UI
layout = html.Div([
    html.H2("Componentes UI", className="mb-4"),
    
    dbc.Card([
        dbc.CardBody([
            html.H3("Diálogo", className="card-title mb-4"),
            html.P(
                "El componente de diálogo es equivalente al componente Dialog de Radix UI en React.",
                className="card-text mb-4"
            ),
            get_dialog_demo()
        ])
    ], className="mb-4"),
    
    dbc.Card([
        dbc.CardBody([
            html.H3("Botones", className="card-title mb-4"),
            html.P(
                "Ejemplos de botones personalizados.",
                className="card-text mb-4"
            ),
            html.Div([
                create_button("Primary", color="primary", className="me-2"),
                create_button("Secondary", color="secondary", className="me-2"),
                create_button("Success", color="success", className="me-2"),
                create_button("Danger", color="danger", className="me-2"),
                create_button("Warning", color="warning", className="me-2"),
                create_button("Info", color="info", className="me-2"),
                create_button("Light", color="light", className="me-2"),
                create_button("Dark", color="dark", className="me-2"),
                create_button("Link", color="link", className="me-2"),
            ], className="mb-4"),
            
            html.H4("Botones Outline", className="mb-3"),
            html.Div([
                create_button("Primary", color="primary", outline=True, className="me-2"),
                create_button("Secondary", color="secondary", outline=True, className="me-2"),
                create_button("Success", color="success", outline=True, className="me-2"),
                create_button("Danger", color="danger", outline=True, className="me-2"),
                create_button("Warning", color="warning", outline=True, className="me-2"),
                create_button("Info", color="info", outline=True, className="me-2"),
                create_button("Light", color="light", outline=True, className="me-2"),
                create_button("Dark", color="dark", outline=True, className="me-2"),
            ], className="mb-4"),
            
            html.H4("Tamaños de Botones", className="mb-3"),
            html.Div([
                create_button("Small", color="primary", size="sm", className="me-2"),
                create_button("Default", color="primary", className="me-2"),
                create_button("Large", color="primary", size="lg", className="me-2"),
            ], className="mb-4"),
        ])
    ], className="mb-4"),
    
    dbc.Card([
        dbc.CardBody([
            html.H3("Inputs", className="card-title mb-4"),
            html.P(
                "Ejemplos de inputs personalizados.",
                className="card-text mb-4"
            ),
            html.Div([
                create_input(
                    label="Text Input",
                    placeholder="Enter text",
                    help_text="This is a standard text input",
                    className="mb-3"
                ),
                create_input(
                    type="email",
                    label="Email Input",
                    placeholder="Enter email",
                    help_text="This is an email input",
                    className="mb-3"
                ),
                create_input(
                    type="password",
                    label="Password Input",
                    placeholder="Enter password",
                    help_text="This is a password input",
                    className="mb-3"
                ),
                create_input(
                    type="number",
                    label="Number Input",
                    placeholder="Enter number",
                    help_text="This is a number input",
                    min=0,
                    max=100,
                    step=1,
                    className="mb-3"
                ),
            ], className="mb-4"),
            
            html.H4("Checkbox", className="mb-3"),
            html.Div([
                create_checkbox(
                    label="Default Checkbox",
                    className="mb-2"
                ),
                create_checkbox(
                    label="Checked Checkbox",
                    value=True,
                    className="mb-2"
                ),
                create_checkbox(
                    label="Disabled Checkbox",
                    disabled=True,
                    className="mb-2"
                ),
            ], className="mb-4"),
        ])
    ], className="mb-4"),
]) 