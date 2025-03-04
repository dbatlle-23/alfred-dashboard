import dash_bootstrap_components as dbc
from dash import html, dcc
from utils.api import get_clientes, get_projects, get_clientes_fallback, get_projects_fallback
from utils.logging import get_logger

logger = get_logger(__name__)

def create_sidebar():
    """Crea el componente de sidebar"""
    # Obtener la lista de clientes para el filtro
    try:
        clientes = get_clientes()
        
        # Verificar que clientes sea una lista
        if not isinstance(clientes, list):
            logger.error(f"get_clientes devolvió un tipo no esperado: {type(clientes)}")
            clientes = get_clientes_fallback()
        
        # Crear opciones para el filtro de clientes
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
    
    return html.Div(
        [
            html.H2("Alfred Dashboard", className="display-6"),
            html.Hr(),
            
            # Filtros de Cliente/Proyecto
            html.Div([
                html.P("Filtros", className="lead mb-2"),
                
                # Filtro de Cliente
                html.Label("Cliente:", className="mb-1"),
                dcc.Dropdown(
                    id="sidebar-client-dropdown",
                    options=client_options,
                    value="all",
                    clearable=False,
                    className="mb-3"
                ),
                
                # Filtro de Proyecto
                html.Label("Proyecto:", className="mb-1"),
                dcc.Dropdown(
                    id="sidebar-project-dropdown",
                    options=[{"label": "Ver todos", "value": "all"}],
                    value="all",
                    clearable=False,
                    className="mb-3"
                ),
                
                # Botón para aplicar filtros
                dbc.Button(
                    [html.I(className="fas fa-filter me-2"), "Aplicar Filtros"],
                    id="apply-filters-button",
                    color="primary",
                    className="w-100 mb-3"
                ),
            ], className="mb-4"),
            
            html.Hr(),
            
            # Sección Inicio
            dbc.Nav(
                [
                    dbc.NavLink([html.I(className="fas fa-home me-2"), "Inicio"], href="/", active="exact"),
                ],
                vertical=True,
                pills=True,
                className="mb-3"
            ),
            
            # Sección Apps
            html.P("Apps", className="lead mb-1"),
            dbc.Nav(
                [
                    dbc.NavLink([html.I(className="fas fa-chart-line me-2"), "Metrics"], href="/metrics", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-lock me-2"), "Lock"], href="/lock", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-th-large me-2"), "Spaces"], href="/spaces", active="exact"),
                ],
                vertical=True,
                pills=True,
                className="mb-3"
            ),
            
            # Sección Configuración
            html.P("Configuración", className="lead mb-1"),
            dbc.Nav(
                [
                    dbc.NavLink([html.I(className="fas fa-cog me-2"), "Configuración DB"], href="/db-config", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-database me-2"), "Explorador BD"], href="/database-explorer", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-file-export me-2"), "Exportar Datos"], href="/data-export", active="exact"),
                    dbc.NavLink([html.I(className="fas fa-plug me-2"), "Prueba de API"], href="/api-test", active="exact"),
                ],
                vertical=True,
                pills=True,
                className="mb-3"
            ),
            
            # Sección Desarrollo (opcional, puedes eliminarla si no la necesitas)
            html.Hr(),
            html.P("Desarrollo", className="lead mb-1"),
            dbc.Nav(
                [
                    dbc.NavLink([html.I(className="fas fa-palette me-2"), "Componentes UI"], href="/ui-demo", active="exact"),
                ],
                vertical=True,
                pills=True,
            ),
        ],
        className="sidebar",
    )

def register_callbacks(app):
    """
    Registra los callbacks para el sidebar
    
    Args:
        app: Instancia de la aplicación Dash
    """
    from dash.dependencies import Input, Output, State
    import dash
    
    # Callback para sincronizar los filtros del sidebar con los de la barra superior
    @app.callback(
        [Output("sidebar-client-dropdown", "value"), Output("sidebar-project-dropdown", "value")],
        [Input("selected-client-store", "data")],
        prevent_initial_call=False
    )
    def sync_sidebar_filters(selection_data):
        client_id = selection_data.get("client_id", "all")
        project_id = selection_data.get("project_id", "all")
        return client_id, project_id
    
    # Callback para actualizar las opciones del dropdown de proyectos en el sidebar
    @app.callback(
        Output("sidebar-project-dropdown", "options"),
        [Input("sidebar-client-dropdown", "value")],
        prevent_initial_call=False
    )
    def update_sidebar_project_options(client_id):
        # Si se selecciona "Ver todos", mostrar solo la opción "Ver todos"
        if client_id == "all":
            return [{"label": "Ver todos", "value": "all"}]
        
        try:
            logger.debug(f"Actualizando opciones de proyectos en sidebar para cliente: {client_id}")
            
            # Obtener proyectos filtrados por cliente
            projects = get_projects(client_id)
            
            # Verificar que projects sea una lista
            if not isinstance(projects, list):
                logger.error(f"get_projects devolvió un tipo no esperado: {type(projects)}")
                projects = get_projects_fallback(client_id)
            
            # Registrar información sobre los proyectos obtenidos
            logger.debug(f"Se obtuvieron {len(projects)} proyectos para el cliente {client_id} (sidebar)")
            if len(projects) > 0:
                logger.debug(f"Primer proyecto (sidebar): {projects[0]}")
                # Mostrar todas las claves disponibles en el primer proyecto
                if isinstance(projects[0], dict):
                    logger.debug(f"Claves disponibles en el primer proyecto (sidebar): {projects[0].keys()}")
            
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
                    logger.debug(f"Añadido proyecto (sidebar): {nombre} (ID: {id_proyecto})")
                else:
                    logger.warning(f"No se pudo extraer nombre o ID del proyecto (sidebar): {project}")
            
            # Registrar las opciones generadas
            logger.debug(f"Opciones de proyectos generadas en sidebar: {len(project_options) - 1} proyectos")
            
            # Si no hay proyectos (solo la opción "Ver todos"), usar fallback
            if len(project_options) <= 1:
                logger.warning(f"No se encontraron proyectos para el cliente {client_id} en sidebar, usando fallback")
                fallback_projects = get_projects_fallback(client_id)
                
                for project in fallback_projects:
                    project_options.append({
                        "label": project.get("name", f"Proyecto {project['id']}"),
                        "value": project["id"]
                    })
                    logger.debug(f"Añadido proyecto de fallback (sidebar): {project.get('name')} (ID: {project['id']})")
            
            return project_options
        except Exception as e:
            logger.error(f"Error al obtener proyectos para sidebar: {str(e)}")
            # En caso de error, devolver opciones por defecto
            fallback_options = [{"label": "Ver todos", "value": "all"}]
            
            # Añadir algunos proyectos de fallback
            fallback_projects = get_projects_fallback(client_id)
            for project in fallback_projects:
                fallback_options.append({
                    "label": project.get("name", f"Proyecto {project['id']}"),
                    "value": project["id"]
                })
            
            return fallback_options
    
    # Callback para aplicar los filtros del sidebar
    @app.callback(
        Output("selected-client-store", "data", allow_duplicate=True),
        [Input("apply-filters-button", "n_clicks")],
        [State("sidebar-client-dropdown", "value"), State("sidebar-project-dropdown", "value")],
        prevent_initial_call=True
    )
    def apply_sidebar_filters(n_clicks, client_id, project_id):
        if n_clicks:
            return {"client_id": client_id, "project_id": project_id}
        return dash.no_update
