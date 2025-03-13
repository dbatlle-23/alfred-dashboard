import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

# Importar los componentes de Digital Twin
from components.digital_twin_iframe import create_digital_twin_iframe
from components.digital_twin_direct import create_digital_twin_direct

# Inicializar la aplicación Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)

# Definir el layout de la aplicación
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Integración de Digital Twin con Three.js en Dash", className="text-center my-4"),
            html.Hr(),
            
            # Tabs para cambiar entre los dos métodos
            dcc.Tabs(id='tabs', value='tab-iframe', children=[
                dcc.Tab(label='Método IFrame', value='tab-iframe'),
                dcc.Tab(label='Método Directo', value='tab-direct'),
            ]),
            
            # Contenido de las tabs
            html.Div(id='tabs-content')
        ])
    ])
], fluid=True)

# Callback para cambiar entre tabs
@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value')
)
def render_content(tab):
    if tab == 'tab-iframe':
        return html.Div([
            html.Div([
                html.H3("Método IFrame", className="mt-4"),
                html.P("""
                    Este método utiliza un componente IFrame de Dash para cargar un archivo HTML 
                    independiente que contiene el código de Three.js. El archivo HTML se encuentra 
                    en la carpeta 'assets' y se carga automáticamente.
                """),
                html.H4("Ventajas:"),
                html.Ul([
                    html.Li("Separación clara entre el código de Dash y el código de Three.js"),
                    html.Li("Fácil de implementar y mantener"),
                    html.Li("Evita conflictos entre las bibliotecas JavaScript"),
                    html.Li("El archivo HTML puede ser desarrollado y probado de forma independiente")
                ]),
                html.H4("Desventajas:"),
                html.Ul([
                    html.Li("Comunicación limitada entre Dash y Three.js"),
                    html.Li("Puede haber problemas de rendimiento al cargar el IFrame"),
                    html.Li("Dificultad para pasar datos dinámicos desde Dash al modelo 3D")
                ])
            ], className="mb-4"),
            
            # Mostrar el Digital Twin con IFrame
            create_digital_twin_iframe(height=500)
        ])
    elif tab == 'tab-direct':
        return html.Div([
            html.Div([
                html.H3("Método Directo", className="mt-4"),
                html.P("""
                    Este método carga Three.js directamente en la página de Dash y utiliza un 
                    archivo JavaScript en la carpeta 'assets' para inicializar y controlar el 
                    modelo 3D. Dash carga automáticamente todos los archivos JavaScript y CSS 
                    de la carpeta 'assets'.
                """),
                html.H4("Ventajas:"),
                html.Ul([
                    html.Li("Mejor integración con Dash y sus componentes"),
                    html.Li("Posibilidad de comunicación bidireccional entre Dash y Three.js"),
                    html.Li("Mejor rendimiento al evitar el uso de IFrames"),
                    html.Li("Facilidad para actualizar el modelo 3D con datos dinámicos")
                ]),
                html.H4("Desventajas:"),
                html.Ul([
                    html.Li("Mayor complejidad en la implementación"),
                    html.Li("Posibles conflictos con otras bibliotecas JavaScript"),
                    html.Li("Requiere conocimientos más avanzados de JavaScript y Three.js")
                ])
            ], className="mb-4"),
            
            # Mostrar el Digital Twin con incrustación directa
            create_digital_twin_direct(height=500)
        ])

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=True) 