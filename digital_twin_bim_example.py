import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

# Importar el componente de Digital Twin BIM
from components.digital_twin_bim_iframe import create_digital_twin_bim_iframe

# Inicializar la aplicación Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ],
    title="Alfred Smart - Digital Twin"
)

# Definir el layout de la aplicación
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Img(
                    src="/assets/img/AlfredSmart Blue.png",
                    height="50px",
                    style={"marginRight": "15px", "display": "inline-block", "verticalAlign": "middle"}
                ),
                html.H1(
                    "Digital Twin BIM",
                    className="display-4 d-inline",
                    style={"display": "inline-block", "verticalAlign": "middle"}
                )
            ], className="d-flex align-items-center my-4"),
            
            html.Hr(),
            
            # Descripción
            html.Div([
                html.H3("Visualización de Modelos BIM", className="mt-4"),
                html.P("""
                    Este ejemplo muestra cómo integrar un Digital Twin basado en Three.js en una aplicación Dash
                    para visualizar modelos BIM (Building Information Modeling). Puedes cargar modelos GLTF, GLB o IFC
                    desde una URL o seleccionar uno de los modelos de ejemplo.
                """),
                html.P("""
                    Los modelos BIM contienen información detallada sobre la estructura, materiales, sistemas y
                    componentes de un edificio, lo que permite una visualización y análisis más completos que
                    los modelos 3D tradicionales.
                """),
                html.Hr()
            ]),
            
            # Mostrar el Digital Twin BIM
            create_digital_twin_bim_iframe(
                app=app, 
                height=700,
                default_model_url="https://threejs.org/examples/models/gltf/LittlestTokyo.glb"
            )
        ])
    ])
], fluid=True)

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=True) 