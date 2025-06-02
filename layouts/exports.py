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

# Initialize the logger
logger = get_logger(__name__)

# Initialize the authentication service
auth_service = AuthService()

def check_authentication(token_data):
    """Verificar si el usuario está autenticado"""
    if not token_data:
        return False
    
    token = token_data.get('token')
    if not token:
        return False
    
    try:
        return auth_service.is_authenticated(token)
    except Exception as e:
        logger.error(f"Error verificando autenticación: {e}")
        return False

# Layout para la página de exportaciones
layout = html.Div([
    # Store para datos de exportación
    dcc.Store(id="export-data-store", data={}),
    
    html.H2("Centro de Exportaciones", className="mb-4"),
    
    # Tarjeta de bienvenida
    dbc.Card([
        dbc.CardBody([
            html.H5("Gestión de Exportaciones de Datos", className="card-title"),
            html.P(
                "Desde aquí puedes exportar todos los datos disponibles en el sistema Alfred Dashboard. "
                "Selecciona el tipo de exportación que necesites y configura los parámetros según tus requisitos.",
                className="card-text"
            ),
            html.Div([
                html.P("Tipos de exportación disponibles:", className="mt-3 mb-2 fw-bold"),
                html.Ul([
                    html.Li("Proyectos y Clientes - Listado completo con información detallada"),
                    html.Li("Métricas y Consumos - Datos de análisis energético y medioambiental"),
                    html.Li("Espacios y Reservas - Información de gestión de espacios"),
                    html.Li("Accesos y Cerraduras - Logs de seguridad y control de acceso"),
                ], className="text-muted"),
            ])
        ])
    ], className="mb-4"),

    # Sección de Exportación de Proyectos y Clientes
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-building me-2"),
            html.Span("Exportación de Proyectos y Clientes")
        ]),
        dbc.CardBody([
            html.P("Exporta un listado completo de proyectos con información detallada del cliente.", className="mb-3"),
            
            # Opciones de filtrado
            dbc.Row([
                dbc.Col([
                    html.Label("Cliente (Opcional)", className="form-label"),
                    dcc.Dropdown(
                        id="export-client-filter",
                        placeholder="Todos los clientes",
                        clearable=True,
                        className="mb-3"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Formato de exportación", className="form-label"),
                    dcc.Dropdown(
                        id="export-format-dropdown",
                        options=[
                            {"label": "CSV", "value": "csv"},
                            {"label": "Excel", "value": "excel"},
                            {"label": "JSON", "value": "json"}
                        ],
                        value="csv",
                        clearable=False,
                        className="mb-3"
                    )
                ], width=6)
            ]),
            
            # Opciones adicionales
            dbc.Row([
                dbc.Col([
                    dbc.Checklist(
                        options=[
                            {"label": "Incluir proyectos archivados", "value": "archived"},
                            {"label": "Incluir datos de contacto", "value": "contacts"},
                            {"label": "Incluir métricas básicas", "value": "metrics"}
                        ],
                        value=["contacts"],
                        id="export-options-checklist",
                        className="mb-3"
                    )
                ], width=12)
            ]),
            
            # Botones de acción
            html.Div([
                dbc.Button(
                    [
                        html.I(className="fas fa-download me-2"),
                        "Exportar Datos"
                    ],
                    id="export-projects-button",
                    color="primary",
                    size="lg",
                    className="me-2"
                ),
                dbc.Button(
                    [
                        html.I(className="fas fa-eye me-2"),
                        "Vista Previa"
                    ],
                    id="preview-export-button",
                    color="outline-secondary",
                    size="lg"
                ),
                dbc.Spinner(
                    html.Div(id="loading-export-output"),
                    color="primary",
                    type="border",
                    id="loading-export-spinner"
                ),
            ], className="d-flex align-items-center")
        ])
    ], className="mb-4"),

    # Sección de Exportaciones Avanzadas
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-cogs me-2"),
            html.Span("Exportaciones Avanzadas")
        ]),
        dbc.CardBody([
            html.P("Próximamente disponibles:", className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-chart-line fa-2x text-primary mb-2"),
                            html.H6("Métricas", className="card-title"),
                            html.P("Exportar datos de consumo y análisis", className="card-text small"),
                            dbc.Button("Próximamente", color="outline-primary", size="sm", disabled=True)
                        ], className="text-center")
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-building fa-2x text-success mb-2"),
                            html.H6("Espacios", className="card-title"),
                            html.P("Exportar datos de reservas y ocupación", className="card-text small"),
                            dbc.Button("Próximamente", color="outline-success", size="sm", disabled=True)
                        ], className="text-center")
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-lock fa-2x text-warning mb-2"),
                            html.H6("Accesos", className="card-title"),
                            html.P("Exportar logs de cerraduras y accesos", className="card-text small"),
                            dbc.Button("Próximamente", color="outline-warning", size="sm", disabled=True)
                        ], className="text-center")
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-database fa-2x text-info mb-2"),
                            html.H6("Base de Datos", className="card-title"),
                            html.P("Exportar esquemas y configuraciones", className="card-text small"),
                            dbc.Button("Próximamente", color="outline-info", size="sm", disabled=True)
                        ], className="text-center")
                    ])
                ], width=3)
            ])
        ])
    ], className="mb-4"),

    # Sección de Historial de Exportaciones
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-history me-2"),
            html.Span("Historial de Exportaciones")
        ]),
        dbc.CardBody([
            html.Div(id="export-history-container", children=[
                html.P("No hay exportaciones recientes.", className="text-muted text-center py-4")
            ])
        ])
    ], className="mb-4"),

    # Componentes ocultos
    dcc.Download(id="download-export-file"),
    
    # Mensaje de resultado
    html.Div(id="export-result-message", className="mt-3"),
    
    # Modal para vista previa
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Vista Previa de Datos")),
        dbc.ModalBody([
            html.Div(id="preview-content")
        ]),
        dbc.ModalFooter([
            dbc.Button("Cerrar", id="close-preview-modal", className="ms-auto", n_clicks=0)
        ])
    ], id="preview-modal", is_open=False, size="xl")
])

# Función para registrar callbacks
def register_callbacks(app):
    """Registra los callbacks de la página de exportaciones con la aplicación principal."""
    
    # Callback para cargar clientes en el filtro
    @app.callback(
        Output("export-client-filter", "options"),
        [Input("jwt-token-store", "data")],
        prevent_initial_call=False
    )
    def load_export_clients(token_data):
        try:
            token = token_data.get('token') if token_data else None
            if not token:
                return [{"label": "Todos los clientes", "value": "all"}]
            
            clientes = get_clientes(jwt_token=token)
            client_options = [{"label": "Todos los clientes", "value": "all"}]
            
            for cliente in clientes:
                if isinstance(cliente, dict):
                    nombre = None
                    id_cliente = None
                    
                    for key in ['nombre', 'name', 'client_name']:
                        if key in cliente:
                            nombre = cliente[key]
                            break
                    
                    for key in ['id', 'client_id', 'id_cliente']:
                        if key in cliente:
                            id_cliente = cliente[key]
                            break
                    
                    if nombre and id_cliente is not None:
                        client_options.append({"label": nombre, "value": str(id_cliente)})
            
            return client_options
        except Exception as e:
            logger.error(f"Error cargando clientes para exportación: {e}")
            return [{"label": "Error al cargar", "value": "all"}]
    
    # Callback principal de exportación
    @app.callback(
        Output("export-result-message", "children"),
        Output("download-export-file", "data"),
        Output("loading-export-output", "children"),
        Input("export-projects-button", "n_clicks"),
        State("jwt-token-store", "data"),
        State("export-client-filter", "value"),
        State("export-format-dropdown", "value"),
        State("export-options-checklist", "value"),
        prevent_initial_call=True
    )
    def export_projects(n_clicks, token_data, client_filter, export_format, export_options):
        """Exporta los proyectos y clientes según los filtros seleccionados"""
        logger.info(f"Exportación iniciada. n_clicks={n_clicks}")
        
        loading_output = ""
        
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Verificar autenticación
            token = token_data.get('token') if token_data else None
            if not token:
                return html.Div("No hay sesión activa. Por favor, inicie sesión nuevamente.", className="alert alert-warning"), None, loading_output
            
            if not check_authentication(token_data):
                logger.warning("Token JWT no válido o expirado")
                error_msg = html.Div([
                    html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                    "Su sesión ha expirado. Por favor, inicie sesión nuevamente."
                ], className="alert alert-warning")
                return error_msg, None, loading_output
            
            # Obtener datos de clientes
            logger.info("Obteniendo datos de clientes")
            clients_data = get_clientes(jwt_token=token)
            if not clients_data:
                logger.error("No se pudieron obtener los datos de clientes")
                error_msg = html.Div([
                    html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                    "No se pudieron obtener los datos de clientes. Intente más tarde."
                ], className="alert alert-warning")
                return error_msg, None, loading_output
            
            logger.info(f"Se obtuvieron {len(clients_data)} clientes")
            
            # Lista para todos los proyectos
            all_projects = []
            
            # Filtrar clientes si es necesario
            clients_to_process = clients_data
            if client_filter and client_filter != "all":
                clients_to_process = [c for c in clients_data if str(c.get("id", c.get("client_id", ""))) == str(client_filter)]
            
            # Obtener proyectos para cada cliente
            for cliente in clients_to_process:
                client_id = cliente.get("id", cliente.get("client_id"))
                client_name = cliente.get("nombre", cliente.get("name", f"Cliente {client_id}"))
                
                try:
                    logger.info(f"Obteniendo proyectos para cliente {client_name} (ID: {client_id})")
                    projects = get_projects(client_id=client_id, jwt_token=token)
                    
                    if projects:
                        for project in projects:
                            project_data = {
                                "cliente_id": client_id,
                                "cliente_nombre": client_name,
                                "proyecto_id": project.get("id"),
                                "proyecto_nombre": project.get("name"),
                                "proyecto_descripcion": project.get("description", ""),
                                "fecha_creacion": project.get("created_at", ""),
                                "estado": project.get("status", "Activo")
                            }
                            
                            # Agregar datos opcionales según checklist
                            if "contacts" in (export_options or []):
                                project_data.update({
                                    "contacto_principal": cliente.get("contact_email", ""),
                                    "telefono": cliente.get("phone", ""),
                                    "direccion": cliente.get("address", "")
                                })
                            
                            if "metrics" in (export_options or []):
                                # Aquí podrías agregar métricas básicas
                                project_data.update({
                                    "num_dispositivos": project.get("device_count", 0),
                                    "ultimo_acceso": project.get("last_access", ""),
                                })
                            
                            all_projects.append(project_data)
                    
                except Exception as e:
                    logger.error(f"Error obteniendo proyectos para cliente {client_id}: {e}")
                    continue
            
            if not all_projects:
                logger.warning("No se encontraron proyectos para exportar")
                warning_msg = html.Div([
                    html.I(className="fas fa-info-circle text-info me-2"),
                    "No se encontraron proyectos para exportar con los filtros seleccionados."
                ], className="alert alert-info")
                return warning_msg, None, loading_output
            
            # Crear DataFrame
            export_df = pd.DataFrame(all_projects)
            
            # Generar nombre de archivo
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if client_filter and client_filter != "all":
                client_name = next((c.get("nombre", c.get("name", "")) for c in clients_data if str(c.get("id", c.get("client_id", ""))) == str(client_filter)), "cliente")
                filename = f"proyectos_{client_name}_{timestamp}"
            else:
                filename = f"proyectos_alfred_{timestamp}"
            
            # Mensaje de éxito
            success_msg = html.Div([
                html.I(className="fas fa-check-circle text-success me-2"),
                f"✅ Exportación completada exitosamente. {len(all_projects)} proyectos exportados."
            ], className="alert alert-success")
            
            # Exportar según formato seleccionado
            if export_format == "csv":
                return success_msg, dcc.send_data_frame(export_df.to_csv, f"{filename}.csv", index=False), loading_output
            elif export_format == "excel":
                return success_msg, dcc.send_data_frame(export_df.to_excel, f"{filename}.xlsx", index=False), loading_output
            elif export_format == "json":
                return success_msg, dcc.send_data_frame(export_df.to_json, f"{filename}.json", orient="records", indent=2), loading_output
            else:
                return success_msg, dcc.send_data_frame(export_df.to_csv, f"{filename}.csv", index=False), loading_output
        
        except Exception as e:
            logger.error(f"Error durante la exportación: {str(e)}")
            traceback.print_exc()
            
            error_msg = html.Div([
                html.I(className="fas fa-exclamation-circle text-danger me-2"),
                f"Error durante la exportación: {str(e)}"
            ], className="alert alert-danger")
            
            return error_msg, None, loading_output
    
    # Callback para vista previa
    @app.callback(
        Output("preview-modal", "is_open"),
        Output("preview-content", "children"),
        [Input("preview-export-button", "n_clicks"), Input("close-preview-modal", "n_clicks")],
        [State("preview-modal", "is_open"), State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def toggle_preview_modal(preview_clicks, close_clicks, is_open, token_data):
        """Toggle preview modal and show data preview"""
        ctx = dash.callback_context
        if not ctx.triggered:
            return False, ""
        
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if button_id == "close-preview-modal":
            return False, ""
        
        if button_id == "preview-export-button":
            try:
                token = token_data.get('token') if token_data else None
                if not token:
                    return True, html.Div("Error: No hay sesión activa", className="alert alert-warning")
                
                # Obtener una muestra de datos
                clients_data = get_clientes(jwt_token=token)
                if clients_data and len(clients_data) > 0:
                    # Mostrar los primeros 5 clientes como preview
                    preview_data = []
                    for i, cliente in enumerate(clients_data[:5]):
                        preview_data.append({
                            "Cliente": cliente.get("nombre", cliente.get("name", "N/A")),
                            "ID": cliente.get("id", cliente.get("client_id", "N/A")),
                            "Email": cliente.get("contact_email", "N/A"),
                        })
                    
                    df_preview = pd.DataFrame(preview_data)
                    
                    table = dbc.Table.from_dataframe(
                        df_preview, 
                        striped=True, 
                        bordered=True, 
                        hover=True,
                        size="sm",
                        className="mb-0"
                    )
                    
                    return True, html.Div([
                        html.P(f"Vista previa de los primeros {len(preview_data)} registros:", className="mb-3"),
                        table,
                        html.P(f"Total de clientes disponibles: {len(clients_data)}", className="mt-3 text-muted")
                    ])
                else:
                    return True, html.Div("No hay datos disponibles para mostrar", className="alert alert-info")
                    
            except Exception as e:
                return True, html.Div(f"Error generando vista previa: {str(e)}", className="alert alert-danger")
        
        return not is_open, "" 