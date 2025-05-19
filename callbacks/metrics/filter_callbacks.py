from dash import Output, Input, State, callback_context
import dash
import json
import pandas as pd
import time
import dash_bootstrap_components as dbc
from constants.metrics import CONSUMPTION_TAGS_MAPPING

from utils.api import get_clientes, get_projects, get_assets, get_project_assets, extract_list_from_response

def register_filter_callbacks(app):
    """Register callbacks for filters."""
    
    @app.callback(
        Output("metrics-client-filter", "options"),
        [Input("url", "pathname"),
         Input("jwt-token-store", "data")]
    )
    def load_client_options(pathname, token_data):
        """Load client options for the dropdown."""
        if pathname != "/metrics":
            return dash.no_update
        
        try:
            # Obtener el token JWT directamente del store
            token = token_data.get('token') if token_data else None
            
            if not token:
                print("[ERROR METRICS] load_client_options - No se encontró token JWT")
                return []
            
            # Obtener la lista de clientes usando el token
            clientes = get_clientes(jwt_token=token)
            
            if clientes and isinstance(clientes, list):
                # Verificar si son datos reales o fallback
                is_fallback = any("FALLBACK" in str(client.get('nombre', '')) for client in clientes[:5])
                
                if is_fallback:
                    print("[WARN METRICS] load_client_options - Se obtuvieron datos de fallback, intentando obtener datos reales")
                    
                    # Intentar hacer una solicitud directa a la API
                    from utils.auth import auth_service
                    endpoint = "clients"
                    response = auth_service.make_api_request(token, "GET", endpoint)
                    
                    if isinstance(response, dict) and "error" not in response:
                        # Extraer clientes de la respuesta
                        clientes = extract_list_from_response(response, lambda: [], "clients")
                
                # Crear las opciones para el dropdown
                options = []
                for client in clientes:
                    if isinstance(client, dict) and "id" in client:
                        # Buscar el nombre en diferentes claves posibles
                        client_name = None
                        for key in ['nombre', 'name', 'client_name', 'nombre_cliente']:
                            if key in client and client[key]:
                                client_name = client[key]
                                break
                        
                        if not client_name:
                            client_name = f"Cliente {client['id']}"
                        
                        options.append({"label": client_name, "value": client['id']})
                
                print(f"[INFO METRICS] load_client_options - Se cargaron {len(options)} clientes")
                return options
            
            print("[WARN METRICS] load_client_options - No se obtuvieron clientes")
            return []
        except Exception as e:
            print(f"[ERROR METRICS] load_client_options: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
    
    @app.callback(
        [Output("metrics-project-filter", "disabled"),
         Output("metrics-consumption-tags-filter", "disabled"),
         Output("metrics-selected-client-store", "data")],
        [Input("metrics-client-filter", "value")]
    )
    def update_project_state(client_id):
        """Update project filter state based on client selection."""
        if not client_id:
            return True, True, None
        
        return False, False, {"client_id": client_id}
    
    @app.callback(
        Output("metrics-selected-consumption-tags-store", "data"),
        [Input("metrics-consumption-tags-filter", "value")]
    )
    def update_consumption_tags_store(consumption_tags):
        """Store selected consumption tags."""
        return {"consumption_tags": consumption_tags} if consumption_tags else None
    
    @app.callback(
        [Output("metrics-analyze-button", "disabled"),
         Output("metrics-update-readings-button", "disabled"),
         Output("metrics-refresh-button", "disabled")],
        [Input("metrics-client-filter", "value"),
         Input("metrics-project-filter", "value"),
         Input("metrics-consumption-tags-filter", "value")]
    )
    def update_buttons_state(client_id, project_id, consumption_tags):
        """Update buttons state based on selections."""
        # El botón de visualizar consumos se habilita cuando hay un cliente seleccionado y al menos un tipo de consumo
        if not client_id or not consumption_tags:
            return True, True, True
        
        # El botón de actualizar lecturas se habilita solo cuando hay un proyecto específico seleccionado
        update_disabled = not project_id or project_id == "all"
        
        # El botón de refresh sigue la misma lógica que el de visualizar
        return False, update_disabled, False
    
    @app.callback(
        [Output("metrics-project-filter", "options"),
         Output("metrics-project-filter", "value")],
        [Input("metrics-selected-client-store", "data"),
         Input("url", "pathname")],
        [State("jwt-token-store", "data")]
    )
    def update_project_options(client_selection, pathname, token_data):
        """Update project options based on selected client."""
        if pathname != "/metrics" or not client_selection:
            return [], None
        
        client_id = client_selection.get("client_id")
        if not client_id:
            return [], None
        
        try:
            # Obtener el token JWT
            token = token_data.get('token') if token_data else None
            
            if not token:
                print("[ERROR METRICS] update_project_options - No se encontró token JWT")
                return [], None
            
            # Obtener proyectos para el cliente seleccionado
            projects = get_projects(client_id=client_id, jwt_token=token)
            
            if projects and isinstance(projects, list):
                # Crear opciones para el dropdown
                options = [{"label": "Todos los proyectos", "value": "all"}]
                
                for project in projects:
                    if isinstance(project, dict) and "id" in project:
                        # Buscar el nombre en diferentes claves posibles
                        project_name = None
                        for key in ['nombre', 'name', 'project_name', 'nombre_proyecto']:
                            if key in project and project[key]:
                                project_name = project[key]
                                break
                        
                        if not project_name:
                            project_name = f"Proyecto {project['id']}"
                        
                        options.append({"label": project_name, "value": project['id']})
                
                print(f"[INFO METRICS] update_project_options - Se cargaron {len(options)-1} proyectos")
                return options, "all"
            
            print("[WARN METRICS] update_project_options - No se obtuvieron proyectos")
            return [], None
        except Exception as e:
            print(f"[ERROR METRICS] update_project_options: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return [], None
    
    @app.callback(
        [Output("metrics-custom-date-container", "style"),
         Output("metrics-date-range", "start_date"),
         Output("metrics-date-range", "end_date")],
        [Input("metrics-date-period", "value")]
    )
    def update_date_range(period):
        """Update date range based on selected period."""
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        
        if period == "last_month":
            start_date = today - timedelta(days=30)
            return {"display": "none"}, start_date, today
        elif period == "last_3_months":
            start_date = today - timedelta(days=90)
            return {"display": "none"}, start_date, today
        elif period == "last_year":
            start_date = today - timedelta(days=365)
            return {"display": "none"}, start_date, today
        elif period == "custom":
            return {"display": "block"}, dash.no_update, dash.no_update
        
        return {"display": "none"}, today - timedelta(days=30), today
    
    @app.callback(
        [Output("metrics-asset-filter", "options"),
         Output("metrics-asset-filter", "value")],
        [Input("metrics-project-filter", "value"),
         Input("metrics-selected-client-store", "data"),
         Input("metrics-data-store", "data")],
        [State("jwt-token-store", "data")]
    )
    def update_asset_options(project_id, client_selection, json_data, token_data):
        """Update asset options based on selected project."""
        # Solo actualizar cuando hay datos cargados
        if not client_selection:
            return [{"label": "Todos", "value": "all"}], "all"
                
        try:
            # Obtener el ID del cliente seleccionado
            client_id = client_selection.get("client_id")
            
            if not client_id:
                return [{"label": "Todos", "value": "all"}], "all"
            
            # Obtener el token JWT directamente del store
            token = token_data.get('token') if token_data else None
            
            if not token:
                print("[ERROR METRICS] update_asset_options - No se encontró token JWT")
                return [{"label": "Todos", "value": "all"}], "all"
            
            # Si no se ha seleccionado un proyecto específico, mostrar todos los assets del cliente
            if not project_id or project_id == "all":
                try:
                    # Intentar obtener assets para el cliente seleccionado
                    assets = get_assets(client_id=client_id, jwt_token=token)
                    if assets:
                        # Crear las opciones para el dropdown
                        options = [{"label": "Todos", "value": "all"}]
                        options.extend([
                            {"label": a.get("name", f"Asset {a['id']}"), "value": a['id']} 
                            for a in assets if isinstance(a, dict) and "id" in a
                        ])
                    
                        print(f"[INFO METRICS] update_asset_options - Se cargaron {len(options)-1} assets para el cliente {client_id}")
                        return options, "all"
                    else:
                        print(f"[WARNING METRICS] update_asset_options - No se encontraron assets para el cliente {client_id}")
                except Exception as e:
                    print(f"[ERROR METRICS] Error al cargar assets para el cliente {client_id}: {str(e)}")
            else:
                # Si se ha seleccionado un proyecto específico, obtener los assets de ese proyecto
                try:
                    # Intentar obtener assets para el proyecto seleccionado
                    assets = get_project_assets(project_id, jwt_token=token)
                    if assets:
                        # Crear las opciones para el dropdown
                        options = [{"label": "Todos", "value": "all"}]
                        options.extend([
                            {"label": a.get("name", f"Asset {a['id']}"), "value": a['id']} 
                            for a in assets if isinstance(a, dict) and "id" in a
                        ])
                        
                        print(f"[INFO METRICS] update_asset_options - Se cargaron {len(options)-1} assets para el proyecto {project_id}")
                        return options, "all"
                    else:
                        print(f"[WARNING METRICS] update_asset_options - No se encontraron assets para el proyecto {project_id}")
                except Exception as e:
                    print(f"[ERROR METRICS] Error al cargar assets para el proyecto {project_id}: {str(e)}")
            
            # Fallback: retornar siempre la opción "Todos" si algo falla
            return [{"label": "Todos", "value": "all"}], "all"
        
        except Exception as e:
            print(f"[ERROR METRICS] update_asset_options global catch: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return [{"label": "Todos", "value": "all"}], "all"

    @app.callback(
        Output("metrics-refresh-data-store", "data"),
        [Input("metrics-refresh-button", "n_clicks")],
        prevent_initial_call=True
    )
    def handle_refresh_button(n_clicks):
        """Handle refresh button click."""
        if n_clicks:
            # Trigger data refresh by updating the store with a timestamp
            return {"timestamp": time.time()}
        return dash.no_update

    @app.callback(
        Output("metrics-refresh-data-store", "data", allow_duplicate=True),
        [Input("metrics-data-store", "data")],
        [State("metrics-refresh-data-store", "data")],  # Add state to check if already auto-triggered
        prevent_initial_call=True
    )
    def auto_refresh_on_empty_data(json_data, current_refresh_data):
        """Trigger auto-refresh if data is initially empty or invalid."""
        # Evita el refresh si ya se activó manualmente o automáticamente
        if current_refresh_data and current_refresh_data.get("auto_triggered"):
            return dash.no_update
            
        data = json.loads(json_data) if json_data else None
        # Verifica si los datos están vacíos o si hay una estructura de error común
        if not data or (isinstance(data, dict) and data.get("error")):
            print("[INFO METRICS] auto_refresh_on_empty_data - Datos vacíos o con error, iniciando refresco automático.")
            return {"timestamp": time.time(), "auto_triggered": True} 
        
        return dash.no_update

    # Callback to manage the KPI selector (Dropdown) in the title area
    @app.callback(
        [Output("metrics-kpi-title-selector-container", "children"),
         Output("metrics-kpi-selected-type-store", "data")],
        [Input("metrics-consumption-tags-filter", "value")]
    )
    def update_kpi_selector(selected_tags):
        """
        Update the KPI card title area: Show H5 title if single type,
        or H5 title + Dropdown if multiple types are selected.
        Store the currently active type for KPI display.
        """
        from dash import dcc, html
        import dash_bootstrap_components as dbc
        from constants.metrics import CONSUMPTION_TAGS_MAPPING

        default_title = html.H5("Indicadores Principales", className="mb-0")

        if selected_tags and len(selected_tags) > 1:
            # Multiple tags selected: Show Title + Dropdown
            options = [
                {"label": CONSUMPTION_TAGS_MAPPING.get(tag, tag), "value": tag}
                for tag in selected_tags
            ]
            # Default to the first selected tag
            active_tag = selected_tags[0] 
            
            kpi_selector = dcc.Dropdown(
                id="metrics-kpi-dropdown-selector",
                options=options,
                value=active_tag,
                clearable=False,
                style={'width': '250px', 'min-width': '200px'}
            )
            
            # Combine Title and Dropdown using Row/Col for better alignment
            title_with_selector = dbc.Row([
                dbc.Col(html.H5("Indicadores:", className="mb-0 me-2"), width="auto", align="center"), 
                dbc.Col(kpi_selector, width="auto")
            ], align="center", className="g-2")

            # Return the combined layout and the active tag for the store
            return title_with_selector, {"active_tag": active_tag}
        
        elif selected_tags and len(selected_tags) == 1:
            # Single tag selected: Show specific title, store the single tag
            active_tag = selected_tags[0]
            type_name = CONSUMPTION_TAGS_MAPPING.get(active_tag, active_tag)
            title = html.H5(f"Indicadores Principales: {type_name}", className="mb-0")
            # Return the specific title and the active tag for the store
            return title, {"active_tag": active_tag}
        
        else:
            # No tags selected or invalid selection: Show default title, store None
            return default_title, None

    # Callback to update the store when the Dropdown value changes
    @app.callback(
        Output("metrics-kpi-selected-type-store", "data", allow_duplicate=True),
        [Input("metrics-kpi-dropdown-selector", "value")],
        prevent_initial_call=True
    )
    def update_kpi_store_from_dropdown(active_tag):
        """Update the store when the user selects a different option in the dropdown."""
        if active_tag:
            return {"active_tag": active_tag}
        return dash.no_update

    # --- Callbacks for Monthly Summary Section Selector ---

    @app.callback(
        [Output("metrics-monthly-summary-selector-container", "children"),
         Output("metrics-monthly-summary-selected-type-store", "data")],
        [Input("metrics-consumption-tags-filter", "value")]
    )
    def update_monthly_summary_selector(selected_tags):
        """
        Show a dropdown selector in the Monthly Summary header only when multiple 
        consumption types are selected. Store the currently active type for this section.
        """
        from dash import dcc, html
        from constants.metrics import CONSUMPTION_TAGS_MAPPING

        if selected_tags and len(selected_tags) > 1:
            # Multiple tags selected: Show Dropdown
            options = [
                {"label": CONSUMPTION_TAGS_MAPPING.get(tag, tag), "value": tag}
                for tag in selected_tags
            ]
            active_tag = selected_tags[0] # Default to the first selected tag
            
            summary_selector = dcc.Dropdown(
                id="metrics-monthly-summary-dropdown-selector", # New ID
                options=options,
                value=active_tag,
                clearable=False,
                placeholder="Seleccione tipo...",
                style={'width': '250px', 'min-width': '200px'} 
            )
            # Return the selector and the active tag for the store
            return summary_selector, {"active_tag": active_tag}
        
        elif selected_tags and len(selected_tags) == 1:
            # Single tag selected: No selector needed, store the single tag
            active_tag = selected_tags[0]
            type_name = CONSUMPTION_TAGS_MAPPING.get(active_tag, active_tag)
            # Optionally, display the selected type name if desired (e.g., in a disabled input or text)
            # For now, just return None for the container children
            return None, {"active_tag": active_tag}
        
        else:
            # No tags selected: No selector, store None
            return None, None

    @app.callback(
        Output("metrics-monthly-summary-selected-type-store", "data", allow_duplicate=True),
        [Input("metrics-monthly-summary-dropdown-selector", "value")], 
        prevent_initial_call=True
    )
    def update_summary_store_from_dropdown(active_tag):
        """Update the monthly summary store when the user selects a different option."""
        if active_tag:
            return {"active_tag": active_tag}
        return dash.no_update

    # --- End Callbacks for Monthly Summary Section Selector ---
