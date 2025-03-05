from dash import html, dcc, callback_context
import dash_bootstrap_components as dbc
from utils.api import get_clientes, get_projects, get_clientes_fallback, get_projects_fallback
from utils.logging import get_logger

logger = get_logger(__name__)

def create_client_selector():
    """
    Crea un selector de cliente/proyecto para la barra superior
    
    Returns:
        Un componente de selección de cliente/proyecto
    """
    # Crear el componente de selección
    selector = html.Div([
        dbc.Row([
            # Selector de cliente
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("Cliente:"),
                    dbc.Select(
                        id="client-selector",
                        options=[{"label": "Cargando...", "value": "all"}],
                        value="all",
                        className="client-select"
                    )
                ], size="sm")
            ], width="auto"),
            
            # Selector de proyecto
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("Proyecto:"),
                    dbc.Select(
                        id="project-selector",
                        options=[{"label": "Cargando...", "value": "all"}],
                        value="all",
                        className="project-select"
                    )
                ], size="sm")
            ], width="auto")
        ], className="g-2 align-items-center")
    ], className="ms-auto me-3 client-selector-container")
    
    return selector

def register_callbacks(app):
    """
    Registra los callbacks para el selector de cliente/proyecto
    
    Args:
        app: Instancia de la aplicación Dash
    """
    from dash.dependencies import Input, Output, State
    import dash
    
    # Callback para cargar la lista de clientes
    @app.callback(
        Output("client-selector", "options"),
        [Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    def load_clients(token_data):
        try:
            # Obtener el token JWT del store
            token = token_data.get('token') if token_data else None
            
            # Si no hay token, mostrar opciones por defecto
            if not token:
                logger.info("No hay token JWT disponible para cargar clientes (comportamiento normal durante inicialización)")
                return [{"label": "Ver todos", "value": "all"}]
            
            # Log para depuración - verificar que tenemos un token
            logger.debug(f"Token JWT disponible para cargar clientes: {token[:10]}...")
            
            # Obtener la lista de clientes
            logger.debug("Llamando a get_clientes con el token JWT")
            clientes = get_clientes(jwt_token=token)
            
            # Log para depuración - verificar qué devolvió get_clientes
            logger.debug(f"get_clientes devolvió: {type(clientes)}, longitud: {len(clientes) if isinstance(clientes, list) else 'no es lista'}")
            
            # Verificar que clientes sea una lista
            if not isinstance(clientes, list):
                logger.error(f"get_clientes devolvió un tipo no esperado: {type(clientes)}")
                clientes = get_clientes_fallback()
            
            # Opciones para el dropdown de clientes
            client_options = [{"label": "Ver todos", "value": "all"}]
            
            # Extender con los clientes de la API, manejando diferentes estructuras posibles
            for cliente in clientes:
                if not isinstance(cliente, dict):
                    logger.warning(f"Cliente no es un diccionario: {cliente}")
                    continue
                    
                # Intentar obtener el nombre y el ID con diferentes claves posibles
                nombre = None
                id_cliente = None
                
                # Posibles claves para el nombre
                for key in ['nombre', 'name', 'client_name', 'nombre_cliente', 'client']:
                    if key in cliente:
                        nombre = cliente[key]
                        break
                
                # Posibles claves para el ID
                for key in ['id', 'client_id', 'id_cliente', 'clientId']:
                    if key in cliente:
                        id_cliente = cliente[key]
                        break
                
                # Si tenemos tanto nombre como ID, añadir a las opciones
                if nombre and id_cliente is not None:
                    client_options.append({"label": nombre, "value": str(id_cliente)})
            
            return client_options
        except Exception as e:
            logger.error(f"Error al cargar clientes: {str(e)}")
            return [{"label": "Error al cargar", "value": "all"}]
    
    # Callback para cargar la lista de proyectos cuando cambia el cliente seleccionado
    @app.callback(
        Output("project-selector", "options"),
        [Input("client-selector", "value"),
         Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    def load_projects(client_id, token_data):
        try:
            # Obtener el token JWT del store
            token = token_data.get('token') if token_data else None
            
            # Si no hay token, mostrar opciones por defecto
            if not token:
                logger.info("No hay token JWT disponible para cargar proyectos (comportamiento normal durante inicialización)")
                return [{"label": "Ver todos", "value": "all"}]
            
            # Obtener la lista de proyectos para el cliente seleccionado
            projects = get_projects(client_id=client_id, jwt_token=token)
            
            # Verificar que projects sea una lista
            if not isinstance(projects, list):
                logger.error(f"get_projects devolvió un tipo no esperado: {type(projects)}")
                projects = get_projects_fallback(client_id)
            
            # Opciones para el dropdown de proyectos
            project_options = [{"label": "Ver todos", "value": "all"}]
            
            # Extender con los proyectos de la API
            for project in projects:
                if not isinstance(project, dict):
                    logger.warning(f"Proyecto no es un diccionario: {project}")
                    continue
                
                # Intentar obtener el nombre y el ID con diferentes claves posibles
                nombre = None
                id_proyecto = None
                
                # Posibles claves para el nombre
                for key in ['nombre', 'name', 'project_name', 'nombre_proyecto']:
                    if key in project:
                        nombre = project[key]
                        break
                
                # Posibles claves para el ID
                for key in ['id', 'project_id', 'id_proyecto', 'projectId']:
                    if key in project:
                        id_proyecto = project[key]
                        break
                
                # Si tenemos tanto nombre como ID, añadir a las opciones
                if nombre and id_proyecto is not None:
                    project_options.append({"label": nombre, "value": str(id_proyecto)})
            
            return project_options
        except Exception as e:
            logger.error(f"Error al cargar proyectos: {str(e)}")
            return [{"label": "Error al cargar", "value": "all"}]
    
    # Callback para actualizar el store global cuando cambia la selección
    @app.callback(
        Output("global-client-selection", "data"),
        [Input("client-selector", "value"),
         Input("project-selector", "value")],
        prevent_initial_call=False
    )
    def update_selection(client_id, project_id):
        return {
            "client_id": client_id,
            "project_id": project_id
        }