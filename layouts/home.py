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
                        "Configurar la conexión a la base de datos en ",
                        html.A("Configuración DB", href="/db-config")
                    ]),
                    html.Li([
                        "Explorar las tablas y datos en ",
                        html.A("Explorador BD", href="/database-explorer")
                    ]),
                    html.Li([
                        "Exportar datos específicos en ",
                        html.A("Exportar Datos", href="/data-export") # Assuming this exists or is planned elsewhere
                    ]),
                ]),
            ])
        ])
    ]),

    # --- Export Section ---
    dbc.Card(className="mt-4", children=[
        dbc.CardHeader([
            html.I(className="fas fa-file-export me-2"),
            html.Span("Acciones de Exportación")
        ]),
        dbc.CardBody([
            html.P("Exportar listado de proyectos con información del cliente."),
            html.Div([
                html.Button(
                    [
                        html.I(className="fas fa-file-csv me-2"),
                        "Exportar CSV"
                    ],
                    id="export-projects-button",
                    className="btn btn-success btn-lg me-2"
                ),
                dbc.Spinner(
                    html.Div(id="loading-output"),
                    color="success",
                    type="border",
                    id="loading-export"
                ),
            ], className="d-flex align-items-center")
        ])
    ]),

    # --- Download Component (remains invisible) ---
    dcc.Download(id="download-projects-csv"),
    
    # --- Mensaje de resultado ---
    html.Div(id="export-result-message", className="mt-2")
])

# Función para registrar callbacks con la aplicación principal
def register_callbacks(app):
    """Registra los callbacks de la página de inicio con la aplicación principal."""
    
    @app.callback(
        Output("export-result-message", "children"),
        Output("download-projects-csv", "data"),
        Output("loading-output", "children"),
        Input("export-projects-button", "n_clicks"),
        State("jwt-token-store", "data"),
        prevent_initial_call=True
    )
    def export_projects(n_clicks, token_data):
        """
        Exporta los proyectos y clientes a un archivo CSV
        """
        # Debugging
        print(f"DEBUG - export_projects: Button clicked, n_clicks={n_clicks}")
        logger.info(f"Botón de exportación clickeado. n_clicks={n_clicks}")
        
        # Este valor estará vacío durante la carga, lo que activará el spinner
        loading_output = ""
        
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Verificar si tenemos token
            token = token_data.get('token') if token_data else None
            print(f"DEBUG: Token presente: {bool(token)}")
            
            if not token:
                print("ERROR: No se encontró token JWT")
                return html.Div("No hay sesión activa. Por favor, inicie sesión nuevamente.", className="text-warning"), None, loading_output
            
            # Verificar autenticación
            if not check_authentication(token_data):
                logger.warning("Token JWT no válido o expirado")
                print("ERROR: Token JWT no válido o expirado")
                error_msg = html.Div([
                    html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                    "Su sesión ha expirado. Por favor, inicie sesión nuevamente."
                ], className="text-warning")
                return error_msg, None, loading_output
            
            # Primero, obtener la lista de clientes
            print("DEBUG: Obteniendo lista de clientes")
            clients_data = get_clientes(jwt_token=token)
            if not clients_data:
                logger.error("No se pudieron obtener los datos de clientes")
                print("ERROR: No se pudieron obtener los datos de clientes")
                error_msg = html.Div([
                    html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                    "No se pudieron obtener los datos de clientes. Intente más tarde."
                ], className="text-warning")
                return error_msg, None, loading_output
            
            logger.info(f"Se obtuvieron {len(clients_data)} clientes")
            print(f"DEBUG: Se obtuvieron {len(clients_data)} clientes")
            
            # Lista para almacenar todos los proyectos con sus clientes
            all_projects = []
            
            # Para cada cliente, obtener sus proyectos
            for client in clients_data:
                client_id = client.get('id')
                client_name = client.get('name', client.get('nombre', 'Cliente sin nombre'))
                
                # Registrar datos del cliente para depuración
                print(f"DEBUG: Procesando cliente ID={client_id}, Nombre={client_name}")
                
                if not client_id:
                    logger.warning(f"Cliente sin ID detectado: {client}")
                    continue
                    
                # Obtener proyectos para este cliente específico
                try:
                    client_projects = get_projects(client_id=client_id, jwt_token=token)
                    
                    if not client_projects:
                        logger.info(f"No se encontraron proyectos para el cliente ID={client_id}")
                        continue
                        
                    logger.info(f"Se obtuvieron {len(client_projects)} proyectos para el cliente ID={client_id}")
                    print(f"DEBUG: {len(client_projects)} proyectos para cliente ID={client_id}")
                    
                    # Añadir el nombre del cliente a cada proyecto
                    for project in client_projects:
                        project_name = project.get('name', project.get('nombre', 'Proyecto sin nombre'))
                        
                        # Añadir a la lista de todos los proyectos
                        all_projects.append({
                            'project_name': project_name,
                            'client_name': client_name,
                            'project_id': project.get('id', 'ID desconocido'),
                            'client_id': client_id
                        })
                        
                except Exception as e:
                    logger.error(f"Error al obtener proyectos para cliente ID={client_id}: {str(e)}")
                    print(f"ERROR: Error al obtener proyectos para cliente ID={client_id}: {str(e)}")
                    # Continuar con el siguiente cliente
                    continue
            
            # Verificar si tenemos proyectos
            if not all_projects:
                logger.error("No se pudieron obtener proyectos para ningún cliente")
                error_msg = html.Div([
                    html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                    "No se encontraron proyectos para ningún cliente."
                ], className="text-warning")
                return error_msg, None, loading_output
            
            # Convertir a DataFrame
            projects_df = pd.DataFrame(all_projects)
            
            # Seleccionar y renombrar columnas para el CSV
            export_df = projects_df[['project_name', 'client_name']].copy()
            export_df = export_df.rename(columns={
                'project_name': 'Nombre del Proyecto',
                'client_name': 'Nombre del Cliente'
            })
            
            # Limpiar datos nulos o vacíos
            export_df = export_df.fillna('')
            
            # Generar el CSV
            logger.info(f"Exportando {len(export_df)} proyectos a CSV")
            print(f"DEBUG: Exportando {len(export_df)} proyectos a CSV")
            
            # Mensaje de éxito
            success_msg = html.Div([
                html.I(className="fas fa-check-circle text-success me-2"),
                f"Exportación exitosa: {len(export_df)} proyectos exportados para {len(clients_data)} clientes."
            ], className="text-success")
            
            # Devolver el archivo CSV y actualizar el UI
            return success_msg, dcc.send_data_frame(
                export_df.to_csv, 
                "proyectos_alfred.csv", 
                index=False
            ), loading_output
        
        except Exception as e:
            print(f"ERROR - export_projects: {str(e)}")
            traceback.print_exc()
            
            # Mensaje de error
            message = html.Div([
                html.I(className="fas fa-exclamation-circle text-danger me-2"),
                f"Error durante la exportación: {str(e)}"
            ], className="text-danger")
            
            # No hay datos para descargar en caso de error
            return message, None, loading_output

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

