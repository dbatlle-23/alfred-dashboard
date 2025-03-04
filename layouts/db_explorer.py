from dash import html, dcc
import dash_bootstrap_components as dbc

# Layout para la página de explorador de base de datos
layout = html.Div([
    html.H2("Explorador de Base de Datos", className="mb-4"),
    
    # Sección de prueba de conexión
    dbc.Card([
        dbc.CardBody([
            html.H5("Conexión a la Base de Datos", className="card-title"),
            html.P("Verifique la conexión a la base de datos antes de cargar las tablas.", className="card-text"),
            dbc.Row([
                dbc.Col([
                    dbc.Button("Probar Conexión", id="db-explorer-test-connection-btn", color="primary", className="me-2"),
                    dbc.Button("Cargar Tablas", id="load-tables-btn", color="success"),
                ], width=12, className="d-flex"),
            ]),
            html.Div([
                html.Br(),
                dbc.Alert(id="db-explorer-connection-status", color="", is_open=False, className="mt-3"),
            ]),
        ]),
    ], className="mb-4"),
    
    # Sección de exploración de tablas
    dbc.Card([
        dbc.CardBody([
            html.H5("Exploración de Tablas", className="card-title"),
            dbc.Row([
                dbc.Col([
                    html.Label("Seleccione una tabla:", className="form-label"),
                    dcc.Dropdown(id="table-dropdown", options=[], placeholder="Seleccione una tabla"),
                ], width=12),
            ], className="mb-3"),
            
            # Información de la tabla seleccionada
            html.Div(id="table-info-container", children=[
                dbc.Tabs([
                    dbc.Tab(label="Estructura", tab_id="structure-tab", children=[
                        html.Div(id="table-structure-container", className="mt-3")
                    ]),
                    dbc.Tab(label="Vista Previa", tab_id="preview-tab", children=[
                        html.Div(id="table-preview-container", className="mt-3")
                    ]),
                ], id="table-tabs", active_tab="structure-tab"),
            ], style={"display": "none"}),
        ]),
    ]),
])
