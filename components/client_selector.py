from dash import html, dcc
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
    # Obtener la lista de clientes para el dropdown
    try:
        clientes = get_clientes()
        
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
                client_options.append({"label": nombre, "value": id_cliente})
            else:
                logger.warning(f"No se pudo extraer nombre o ID del cliente: {cliente}")
        
    except Exception as e:
        logger.error(f"Error al obtener clientes: {str(e)}")
        # Usar opciones por defecto en caso de error
        client_options = [
            {"label": "Ver todos", "value": "all"},
            {"label": "Cliente A", "value": 1},
            {"label": "Cliente B", "value": 2}
        ]
    
    # Crear el selector
    selector = html.Div([
        # Store para mantener el estado de selección
        dcc.Store(id="selected-client-store", data={"client_id": "all", "project_id": "all"}),
        
        # Selector de cliente
        dbc.Row([
            dbc.Col([
                html.Label("Cliente:", className="text-light me-2"),
                dcc.Dropdown(
                    id="client-dropdown",
                    options=client_options,
                    value="all",
                    clearable=False,
                    style={"width": "200px", "display": "inline-block"},
                    className="bg-dark text-white"
                ),
            ], width="auto"),
            
            # Selector de proyecto
            dbc.Col([
                html.Label("Proyecto:", className="text-light me-2"),
                dcc.Dropdown(
                    id="project-dropdown",
                    options=[{"label": "Ver todos", "value": "all"}],
                    value="all",
                    clearable=False,
                    style={"width": "200px", "display": "inline-block"},
                    className="bg-dark text-white"
                ),
            ], width="auto"),
            
            # Indicador visual de selección actual (breadcrumb)
            dbc.Col([
                html.Div(id="selection-breadcrumb", className="text-light ms-3"),
            ], width="auto", className="d-flex align-items-center"),
        ], className="g-0 align-items-center"),
    ], className="client-selector me-auto")
    
    return selector

def register_callbacks(app):
    """
    Registra los callbacks para el selector de cliente/proyecto
    
    Args:
        app: Instancia de la aplicación Dash
    """
    from dash.dependencies import Input, Output, State
    import dash
    
    # Callback para actualizar las opciones del dropdown de proyectos cuando cambia el cliente
    @app.callback(
        [Output("project-dropdown", "options"), Output("project-dropdown", "value")],
        [Input("client-dropdown", "value")],
        prevent_initial_call=False
    )
    def update_project_options(client_id):
        # Si se selecciona "Ver todos", mostrar solo la opción "Ver todos"
        if client_id == "all":
            return [{"label": "Ver todos", "value": "all"}], "all"
        
        try:
            logger.debug(f"Actualizando opciones de proyectos para cliente: {client_id}")
            
            # Obtener proyectos filtrados por cliente
            projects = get_projects(client_id)
            
            # Verificar que projects sea una lista
            if not isinstance(projects, list):
                logger.error(f"get_projects devolvió un tipo no esperado: {type(projects)}")
                projects = get_projects_fallback(client_id)
            
            # Registrar información sobre los proyectos obtenidos
            logger.debug(f"Se obtuvieron {len(projects)} proyectos para el cliente {client_id}")
            if len(projects) > 0:
                logger.debug(f"Primer proyecto: {projects[0]}")
                # Mostrar todas las claves disponibles en el primer proyecto
                if isinstance(projects[0], dict):
                    logger.debug(f"Claves disponibles en el primer proyecto: {projects[0].keys()}")
            
            # Crear opciones para el dropdown
            project_options = [{"label": "Ver todos", "value": "all"}]
            
            # Extender con los proyectos de la API, manejando la estructura correcta
            for project in projects:
                if not isinstance(project, dict):
                    logger.warning(f"Proyecto no es un diccionario: {project}")
                    continue
                
                # Obtener el nombre y el ID según la estructura de la API
                nombre = project.get("name")
                id_proyecto = project.get("id")
                
                # Si tenemos tanto nombre como ID, añadir a las opciones
                if nombre and id_proyecto is not None:
                    project_options.append({"label": nombre, "value": id_proyecto})
                    logger.debug(f"Añadido proyecto: {nombre} (ID: {id_proyecto})")
                else:
                    logger.warning(f"No se pudo extraer nombre o ID del proyecto: {project}")
            
            # Registrar las opciones generadas
            logger.debug(f"Opciones de proyectos generadas: {len(project_options) - 1} proyectos")
            
            # Si no hay proyectos (solo la opción "Ver todos"), usar fallback
            if len(project_options) <= 1:
                logger.warning(f"No se encontraron proyectos para el cliente {client_id}, usando fallback")
                fallback_projects = get_projects_fallback(client_id)
                
                for project in fallback_projects:
                    project_options.append({
                        "label": project.get("name", f"Proyecto {project['id']}"),
                        "value": project["id"]
                    })
                    logger.debug(f"Añadido proyecto de fallback: {project.get('name')} (ID: {project['id']})")
            
            return project_options, "all"
        except Exception as e:
            logger.error(f"Error al obtener proyectos: {str(e)}")
            # En caso de error, devolver opciones por defecto
            fallback_options = [{"label": "Ver todos", "value": "all"}]
            
            # Añadir algunos proyectos de fallback
            fallback_projects = get_projects_fallback(client_id)
            for project in fallback_projects:
                fallback_options.append({
                    "label": project.get("name", f"Proyecto {project['id']}"),
                    "value": project["id"]
                })
            
            return fallback_options, "all"
    
    # Callback para actualizar el store con la selección actual
    @app.callback(
        Output("selected-client-store", "data"),
        [Input("client-dropdown", "value"), Input("project-dropdown", "value")],
        prevent_initial_call=False
    )
    def update_selection_store(client_id, project_id):
        return {"client_id": client_id, "project_id": project_id}
    
    # Callback para actualizar el breadcrumb con la selección actual
    @app.callback(
        Output("selection-breadcrumb", "children"),
        [Input("selected-client-store", "data")],
        prevent_initial_call=False
    )
    def update_breadcrumb(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        
        # Si ambos son "Ver todos", no mostrar breadcrumb
        if client_id == "all" and project_id == "all":
            return ""
        
        # Obtener nombre del cliente
        client_name = "Todos los clientes"
        if client_id != "all":
            try:
                clientes = get_clientes()
                client_match = next((c for c in clientes if str(c.get("id", "")) == str(client_id)), None)
                if client_match:
                    # Intentar obtener el nombre con diferentes claves posibles
                    for key in ['nombre', 'name', 'client_name', 'nombre_cliente', 'client']:
                        if key in client_match:
                            client_name = client_match[key]
                            break
            except Exception as e:
                logger.error(f"Error al obtener nombre del cliente: {str(e)}")
        
        # Obtener nombre del proyecto
        project_name = "Todos los proyectos"
        if project_id != "all":
            try:
                projects = get_projects(client_id if client_id != "all" else None)
                project_match = next((p for p in projects if str(p.get("id", "")) == str(project_id)), None)
                if project_match:
                    # Intentar obtener el nombre con diferentes claves posibles
                    for key in ['nombre', 'name', 'project_name', 'nombre_proyecto', 'project']:
                        if key in project_match:
                            project_name = project_match[key]
                            break
            except Exception as e:
                logger.error(f"Error al obtener nombre del proyecto: {str(e)}")
        
        # Crear breadcrumb
        if project_id == "all":
            return html.Span([
                html.I(className="fas fa-filter me-2"),
                f"Filtrando: {client_name}"
            ])
        else:
            return html.Span([
                html.I(className="fas fa-filter me-2"),
                f"Filtrando: {client_name} / {project_name}"
            ])