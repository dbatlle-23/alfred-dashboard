import dash_bootstrap_components as dbc
from dash import html, dcc
from utils.api import get_clientes, get_projects, get_clientes_fallback, get_projects_fallback
from utils.logging import get_logger
import os

logger = get_logger(__name__)

def create_sidebar():
    """Crea el componente de sidebar"""
    # Crear el sidebar con opciones por defecto
    sidebar = html.Div([
        html.Div([
            # Sección de Filtros
            html.Div([
                html.H5("FILTROS", className="sidebar-title"),
                html.Hr(className="my-2"),
                
                # Filtro de cliente
                html.Div([
                    html.Label("Cliente", className="filter-label"),
                    dcc.Dropdown(
                        id="sidebar-client-dropdown",
                        options=[{"label": "Cargando...", "value": "all"}],
                        value="all",
                        clearable=False,
                        className="sidebar-dropdown"
                    )
                ], className="sidebar-filter"),
                
                # Filtro de proyecto
                html.Div([
                    html.Label("Proyecto", className="filter-label"),
                    dcc.Dropdown(
                        id="sidebar-project-dropdown",
                        options=[{"label": "Cargando...", "value": "all"}],
                        value="all",
                        clearable=False,
                        className="sidebar-dropdown"
                    )
                ], className="sidebar-filter"),
                
                # Botón para aplicar filtros
                html.Div([
                    dbc.Button(
                        "Aplicar Filtros",
                        id="apply-filters-button",
                        color="primary",
                        className="w-100 mt-2"
                    )
                ]),
            ], className="mb-4"),
            
            # Sección de Navegación
            html.Div([
                html.H5("NAVEGACIÓN", className="sidebar-title"),
                html.Hr(className="my-2"),
                dbc.Nav(
                    [
                        dbc.NavLink(
                            [html.I(className="fas fa-home me-2"), "Inicio"],
                            href="/",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ],
                    vertical=True,
                    pills=True,
                    className="sidebar-nav"
                ),
            ], className="mb-4"),
            
            # Sección de Visualizaciones con submenús
            html.Div([
                html.H5("VISUALIZACIONES", className="sidebar-title"),
                html.Hr(className="my-2"),
                
                html.Div([
                    # Enlace directo a Home
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-home me-2"), "Home"],
                            href="/",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ]),
                    
                    # Enlace directo a Spaces
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-building me-2"), "Spaces"],
                            href="/spaces",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ]),
                    
                    # Enlace a Cerraduras
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-lock me-2"), "Lock"],
                            href="/lock",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ]),
                    
                    # Enlace a Gestión de Cerraduras Inteligentes
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-key me-2"), "Cerraduras Inteligentes"],
                            href="/smart-locks",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ]),
                    
                    # Metrics App con submenú
                    html.Div([
                        # Botón principal que actúa como cabecera del menú desplegable
                        html.Div([
                            dbc.Button(
                                [html.I(className="fas fa-chart-bar me-2"), "Metrics ", 
                                 html.I(className="fas fa-chevron-down ms-auto")],
                                id="metrics-submenu-button",
                                color="link",
                                className="sidebar-link text-start w-100 py-2 d-flex align-items-center justify-content-between"
                            ),
                        ]),
                        
                        # Contenido desplegable para Metrics
                        dbc.Collapse(
                            dbc.Nav(
                                [
                                    dbc.NavLink(
                                        [html.I(className="fas fa-chart-line me-2"), "Análisis General"],
                                        href="/metrics",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-tint me-2"), "Consumo de Agua"],
                                        href="/water-consumption",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-leaf me-2"), "Huella de Carbono"],
                                        href="/carbon-footprint",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-chart-area me-2"), "Análisis de Agua"],
                                        href="/water-analysis",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-bolt me-2"), "Consumo Eléctrico"],
                                        href="/electricity-consumption",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                ],
                                vertical=True,
                                pills=True,
                                className="sidebar-nav"
                            ),
                            id="metrics-submenu-collapse",
                        ),
                    ]),
                ], className="sidebar-nav"),
            ], className="mb-4"),
            
            # Sección de Apps
            html.Div([
                html.H5("APPS", className="sidebar-title"),
                html.Hr(className="my-2"),
                
                # Menú con submenús para Apps
                html.Div([
                    # Spaces App
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-building me-2"), "Spaces"],
                            href="/spaces",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ]),
                    
                    # Lock App
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-lock me-2"), "Lock"],
                            href="/lock",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ]),
                    
                    # Metrics App con submenú
                    html.Div([
                        # Botón principal que actúa como cabecera del menú desplegable
                        html.Div([
                            dbc.Button(
                                [html.I(className="fas fa-chart-bar me-2"), "Metrics ", 
                                 html.I(className="fas fa-chevron-down ms-auto")],
                                id="metrics-submenu-button",
                                color="link",
                                className="sidebar-link text-start w-100 py-2 d-flex align-items-center justify-content-between"
                            ),
                        ]),
                        
                        # Contenido desplegable para Metrics
                        dbc.Collapse(
                            dbc.Nav(
                                [
                                    dbc.NavLink(
                                        [html.I(className="fas fa-chart-line me-2"), "Análisis General"],
                                        href="/metrics",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-tint me-2"), "Consumo de Agua"],
                                        href="/water-consumption",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-leaf me-2"), "Huella de Carbono"],
                                        href="/carbon-footprint",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-chart-area me-2"), "Análisis de Agua"],
                                        href="/water-analysis",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-bolt me-2"), "Consumo Eléctrico"],
                                        href="/electricity-consumption",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                ],
                                vertical=True,
                                pills=True,
                                className="sidebar-nav"
                            ),
                            id="metrics-submenu-collapse",
                        ),
                    ]),
                ], className="sidebar-nav"),
            ], className="mb-4"),
            
            # Sección de Configuración con submenús
            html.Div([
                html.H5("CONFIGURACIÓN", className="sidebar-title"),
                html.Hr(className="my-2"),
                
                html.Div([
                    # Base de Datos con submenú
                    html.Div([
                        # Botón principal
                        html.Div([
                            dbc.Button(
                                [html.I(className="fas fa-database me-2"), "Base de Datos ", 
                                 html.I(className="fas fa-chevron-down ms-auto")],
                                id="db-submenu-button",
                                color="link",
                                className="sidebar-link text-start w-100 py-2 d-flex align-items-center justify-content-between"
                            ),
                        ]),
                        
                        # Contenido desplegable para Base de Datos
                        dbc.Collapse(
                            dbc.Nav(
                                [
                                    dbc.NavLink(
                                        [html.I(className="fas fa-table me-2"), "Explorador DB"],
                                        href="/db-explorer",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                    dbc.NavLink(
                                        [html.I(className="fas fa-cog me-2"), "Configuración DB"],
                                        href="/db-config",
                                        active="exact",
                                        className="sidebar-link ms-3 ps-2"
                                    ),
                                ],
                                vertical=True,
                                pills=True,
                                className="sidebar-nav"
                            ),
                            id="db-submenu-collapse",
                        ),
                    ]),
                    
                    # Test API
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-flask me-2"), "Test API"],
                            href="/api-test",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ]),
                    
                    # Configuración de Anomalías
                    html.Div([
                        dbc.NavLink(
                            [html.I(className="fas fa-exclamation-triangle me-2"), "Config. Anomalías"],
                            href="/anomaly-config",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ]),
                ], className="sidebar-nav"),
            ], className="mb-4"),
            
            # Sección de Developer
            html.Div([
                html.H5("DEVELOPER", className="sidebar-title"),
                html.Hr(className="my-2"),
                dbc.Nav(
                    [
                        dbc.NavLink(
                            [html.I(className="fas fa-palette me-2"), "Demo UI"],
                            href="/ui-demo",
                            active="exact",
                            className="sidebar-link"
                        ),
                    ],
                    vertical=True,
                    pills=True,
                    className="sidebar-nav"
                ),
            ]),
            
            # Versión en la parte inferior
            html.Div([
                html.Hr(className="my-3"),
                html.P("v1.0.0", className="text-muted text-center small")
            ], className="mt-auto pt-4"),
            
        ], className="sidebar-content"),
        
        # Store para la selección de cliente/proyecto
        dcc.Store(id="selected-client-store", data={"client_id": "all", "project_id": "all"})
    ], className="sidebar", style={"font-family": "Inter, system-ui, Avenir, Helvetica, Arial, sans-serif"})
    
    return sidebar

def register_callbacks(app):
    """
    Registra los callbacks para el sidebar
    
    Args:
        app: Instancia de la aplicación Dash
    """
    from dash.dependencies import Input, Output, State
    import dash
    
    # Callback para cargar la lista de clientes en el sidebar
    @app.callback(
        Output("sidebar-client-dropdown", "options"),
        [Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    def load_sidebar_clients(token_data):
        try:
            # Obtener el token JWT del store
            token = token_data.get('token') if token_data else None
            
            # Si no hay token, mostrar opciones por defecto
            if not token:
                logger.info("No hay token JWT disponible para cargar clientes en sidebar (comportamiento normal durante inicialización)")
                return [{"label": "Ver todos", "value": "all"}]
            
            # Log para depuración - verificar que tenemos un token
            logger.debug(f"Token JWT disponible para cargar clientes en sidebar: {token[:10]}...")
            
            # Obtener la lista de clientes
            logger.debug("Llamando a get_clientes con el token JWT desde sidebar")
            clientes = get_clientes(jwt_token=token)
            
            # Log para depuración - verificar qué devolvió get_clientes
            logger.debug(f"get_clientes devolvió para sidebar: {type(clientes)}, longitud: {len(clientes) if isinstance(clientes, list) else 'no es lista'}")
            
            # Verificar que clientes sea una lista
            if not isinstance(clientes, list):
                logger.error(f"get_clientes devolvió un tipo no esperado para sidebar: {type(clientes)}")
                clientes = get_clientes_fallback()
            
            # Opciones para el dropdown de clientes
            client_options = [{"label": "Ver todos", "value": "all"}]
            
            # Extender con los clientes de la API, manejando diferentes estructuras posibles
            for cliente in clientes:
                if not isinstance(cliente, dict):
                    logger.warning(f"Cliente no es un diccionario (sidebar): {cliente}")
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
            logger.error(f"Error al cargar clientes en sidebar: {str(e)}")
            return [{"label": "Error al cargar", "value": "all"}]
    
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
        [Input("sidebar-client-dropdown", "value"),
         Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    def update_sidebar_project_options(client_id, token_data):
        # Si se selecciona "Ver todos", mostrar solo la opción "Ver todos"
        if client_id == "all":
            return [{"label": "Ver todos", "value": "all"}]
        
        try:
            # Obtener el token JWT del store
            token = token_data.get('token') if token_data else None
            
            # Si no hay token, mostrar opciones por defecto
            if not token:
                logger.info("No hay token JWT disponible para cargar proyectos en sidebar (comportamiento normal durante inicialización)")
                return [{"label": "Ver todos", "value": "all"}]
                
            logger.debug(f"Actualizando opciones de proyectos en sidebar para cliente: {client_id}")
            
            # Obtener proyectos filtrados por cliente
            projects = get_projects(client_id=client_id, jwt_token=token)
            
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
            selection = {"client_id": client_id, "project_id": project_id}
            if os.environ.get('DASH_DEBUG') == 'true':
                print(f"[DEBUG SIDEBAR] Aplicando filtros: {selection}")
            return selection
        return dash.no_update
    
    # Callbacks para controlar los submenús desplegables
    @app.callback(
        Output("metrics-submenu-collapse", "is_open"),
        [Input("metrics-submenu-button", "n_clicks")],
        [State("metrics-submenu-collapse", "is_open")],
    )
    def toggle_metrics_submenu(n, is_open):
        if n:
            return not is_open
        return is_open
    
    @app.callback(
        Output("db-submenu-collapse", "is_open"),
        [Input("db-submenu-button", "n_clicks")],
        [State("db-submenu-collapse", "is_open")],
    )
    def toggle_db_submenu(n, is_open):
        if n:
            return not is_open
        return is_open
