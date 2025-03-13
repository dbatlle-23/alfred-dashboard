import dash_html_components as html
from dash import html, dcc, dash, callback_context
from dash.dependencies import Input, Output, State
import json
import time
import base64
import os
from urllib.parse import quote

def create_digital_twin_bim_iframe(app, height=600, width="100%", default_model_url=None):
    """
    Crea un componente IFrame que muestra un Digital Twin BIM creado con Three.js
    
    Args:
        app (dash.Dash): La aplicación Dash
        height (int): Altura del IFrame en píxeles
        width (str): Ancho del IFrame, puede ser en píxeles o porcentaje
        default_model_url (str, optional): URL del modelo BIM por defecto
        
    Returns:
        dash_html_components.Div: Un contenedor con el IFrame del Digital Twin BIM
    """
    # Crear un ID único para el IFrame
    iframe_id = "digital-twin-bim-iframe"
    
    # Crear un componente Store para almacenar la URL del modelo
    store_id = "digital-twin-bim-store"
    
    # Crear un componente Store para almacenar información del modelo cargado desde el PC
    upload_store_id = "digital-twin-bim-upload-store"
    
    # Crear el layout
    layout = html.Div([
        html.H2("Alfred Smart - Digital Twin", className="mt-4"),
        html.P("Visualizador de modelos BIM integrado con Three.js"),
        
        # Componentes Store para almacenar datos
        dcc.Store(id=store_id, data=default_model_url),
        dcc.Store(id=upload_store_id, data=None),
        
        # Tabs para diferentes métodos de carga
        dcc.Tabs([
            # Tab para cargar desde URL
            dcc.Tab(label="Cargar desde URL", children=[
                html.Div([
                    html.Label("URL del modelo BIM (GLTF, GLB o IFC):"),
                    dcc.Input(
                        id="model-url-input",
                        type="text",
                        placeholder="Introduce la URL del modelo BIM",
                        value=default_model_url or "",
                        style={"width": "70%", "marginRight": "10px"}
                    ),
                    html.Button("Cargar Modelo", id="load-model-button", className="btn btn-primary")
                ], style={"marginBottom": "15px", "marginTop": "15px"}),
                
                # Ejemplos de modelos predefinidos
                html.Div([
                    html.Label("O selecciona un modelo de ejemplo:"),
                    dcc.Dropdown(
                        id="model-examples-dropdown",
                        options=[
                            {"label": "Tokyo (GLTF)", "value": "https://threejs.org/examples/models/gltf/LittlestTokyo.glb"},
                            {"label": "Edificio de Oficinas (GLTF)", "value": "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/OfficeBuilding/glTF/OfficeBuilding.gltf"},
                            {"label": "Sala de Conferencias (GLTF)", "value": "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/RecursiveSkeletons/glTF/RecursiveSkeletons.gltf"}
                        ],
                        placeholder="Selecciona un modelo de ejemplo",
                        style={"width": "100%"}
                    )
                ], style={"marginBottom": "15px"})
            ], style={"padding": "15px"}),
            
            # Tab para cargar desde PC
            dcc.Tab(label="Cargar desde PC", children=[
                html.Div([
                    html.Label("Selecciona un archivo de modelo BIM (GLTF, GLB o IFC):"),
                    dcc.Upload(
                        id="upload-model",
                        children=html.Div([
                            'Arrastra y suelta o ',
                            html.A('selecciona un archivo')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px 0'
                        },
                        multiple=False
                    ),
                    html.Div(id="upload-status")
                ], style={"marginBottom": "15px", "marginTop": "15px"})
            ], style={"padding": "15px"})
        ]),
        
        # IFrame para mostrar el modelo BIM
        html.Div([
            html.Iframe(
                id=iframe_id,
                src="/assets/digital_twin_bim.html",
                style={
                    'height': f"{height}px",
                    'width': width,
                    'border': 'none',
                    'borderRadius': '5px',
                    'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
                    'backgroundColor': '#333333'
                }
            )
        ], style={
            'padding': '10px',
            'marginBottom': '20px',
            'marginTop': '20px'
        }),
        
        # Información sobre el modelo cargado
        html.Div(id="model-info-output")
    ])
    
    # Callback para cargar modelo desde la URL introducida
    @app.callback(
        Output(store_id, "data"),
        [Input("load-model-button", "n_clicks"), Input("model-examples-dropdown", "value")],
        [State("model-url-input", "value")],
        prevent_initial_call=True
    )
    def update_model_url(n_clicks, dropdown_value, input_value):
        ctx = callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "load-model-button" and input_value:
            return input_value
        elif trigger_id == "model-examples-dropdown" and dropdown_value:
            return dropdown_value
        
        return dash.no_update
    
    # Callback para actualizar el valor del input cuando se selecciona un modelo de ejemplo
    @app.callback(
        Output("model-url-input", "value"),
        Input("model-examples-dropdown", "value"),
        prevent_initial_call=True
    )
    def update_input_from_dropdown(value):
        if value:
            return value
        return dash.no_update
    
    # Callback para procesar el archivo subido
    @app.callback(
        [Output(upload_store_id, "data"), Output("upload-status", "children")],
        Input("upload-model", "contents"),
        State("upload-model", "filename"),
        prevent_initial_call=True
    )
    def process_upload(contents, filename):
        if contents is None:
            return dash.no_update, dash.no_update
        
        # Verificar la extensión del archivo
        file_extension = filename.split('.')[-1].lower()
        if file_extension not in ['gltf', 'glb', 'ifc']:
            return None, html.Div([
                html.P(f"Error: Formato de archivo no soportado. Por favor, sube un archivo GLTF, GLB o IFC.", 
                       style={"color": "red"})
            ])
        
        # Crear directorio para archivos subidos si no existe
        upload_dir = os.path.join('assets', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Guardar el archivo
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Generar un nombre de archivo único para evitar colisiones
        timestamp = int(time.time())
        safe_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        with open(file_path, 'wb') as f:
            f.write(decoded)
        
        # Crear URL relativa para el archivo
        relative_path = f"/assets/uploads/{safe_filename}"
        
        return relative_path, html.Div([
            html.P(f"Archivo cargado: {filename}", style={"color": "green"}),
            html.P("Haz clic en el visor para cargar el modelo.")
        ])
    
    # Callback para enviar la URL del modelo al IFrame
    @app.callback(
        Output(iframe_id, "src"),
        [Input(store_id, "data"), Input(upload_store_id, "data")],
        prevent_initial_call=True
    )
    def update_iframe(model_url, upload_url):
        ctx = callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == store_id and model_url:
            # URL externa
            return f"/assets/digital_twin_bim.html?model={quote(model_url)}&t={int(time.time())}"
        elif trigger_id == upload_store_id and upload_url:
            # Archivo subido
            return f"/assets/digital_twin_bim.html?model={upload_url}&t={int(time.time())}"
        
        return "/assets/digital_twin_bim.html"
    
    # Callback para mostrar información sobre el modelo cargado
    @app.callback(
        Output("model-info-output", "children"),
        [Input(store_id, "data"), Input(upload_store_id, "data")],
        prevent_initial_call=True
    )
    def update_model_info(model_url, upload_url):
        ctx = callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == store_id and model_url:
            url = model_url
            source = "URL externa"
        elif trigger_id == upload_store_id and upload_url:
            url = upload_url
            source = "Archivo local"
        else:
            return html.Div()
        
        file_name = url.split("/")[-1]
        file_extension = file_name.split(".")[-1].lower()
        
        return html.Div([
            html.Hr(),
            html.H4("Información del Modelo"),
            html.P(f"Nombre del archivo: {file_name}"),
            html.P(f"Tipo de archivo: {file_extension.upper()}"),
            html.P(f"Fuente: {source}"),
            html.P(f"Ruta: {url}")
        ])
    
    return layout 