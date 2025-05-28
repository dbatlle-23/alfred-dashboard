import dash
from dash import html, dcc, Input, Output, callback, State, dash_table, no_update
import dash_bootstrap_components as dbc
from utils.api_client import (
    get_clients, 
    get_projects_by_client, 
    get_project_assets,
    get_deployment_sensor_passwords,
    update_sensor_password,
    get_asset_devices
)
import pandas as pd
from dash.dash_table.Format import Group
from dash.exceptions import PreventUpdate
from components.sidebar import create_layout
from datetime import datetime, timedelta
import requests
import io
import random
import plotly.express as px
import plotly.graph_objects as go
import base64

dash.register_page(
    __name__,
    path="/access",
    name="Gestión de Accesos"
)

# Load clients at module level
clients = get_clients()

# NFC code configurations
GENERAL_SENSOR_CODES = {
    "102": "202410",
    "121": "30350945",
    "122": "103B0945",
    "123": "205AB844",
}

# Add this after the GENERAL_SENSOR_CODES definition
PAGE_SIZE_OPTIONS = [10, 50, 100, 500]

# Create the content for this page
content = html.Div([
    # Tabs container
    dbc.Tabs([
        # Tab 1: Card Assignment
        dbc.Tab([
            # Selection Panel
            dbc.Card([
                dbc.CardBody([
                    html.H4("Selección de Proyecto", className="card-title mb-4"),
                    dbc.Row([
                        # Client Selection
                        dbc.Col([
                            html.Label("Cliente:", className="fw-bold"),
                            dcc.Dropdown(
                                id="access-dropdown-clientes",
                                placeholder="Selecciona un cliente",
                                options=[{"label": client["name"], "value": client["id"]} for client in clients],
                                className="mb-3"
                            ),
                        ], md=6),
                        
                        # Project Selection
                        dbc.Col([
                            html.Label("Proyecto:", className="fw-bold"),
                            dcc.Dropdown(
                                id="access-dropdown-proyectos",
                                placeholder="Selecciona un proyecto",
                                options=[],
                                className="mb-3"
                            ),
                        ], md=6),
                    ]),
                ])
            ], className="mb-4"),
            
            # UUID Assignment Panel
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H5("Asignación de UUIDs por Slot", className="mb-3"),
                            dbc.Row([
                                # Create a row of slot inputs
                                *[
                                    dbc.Col([
                                        dbc.Form([
                                            dbc.Checkbox(
                                                id=f"slot-check-{i}",
                                                value=False,
                                                persistence=True,
                                                persistence_type="session",
                                                className="mb-2"
                                            ),
                                            dbc.Label(f"Slot {i}:", className="fw-bold"),
                                            dbc.Input(
                                                id=f"slot-uuid-{i}",
                                                type="text",
                                                placeholder="UUID",
                                                className="mb-2",
                                                size="sm"
                                            ),
                                        ])
                                    ], width=2) for i in range(2, 12)
                                ]
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button(
                                        "Seleccionar Todos",
                                        id="select-all-slots-button",
                                        color="secondary",
                                        size="sm",
                                        className="me-2"
                                    ),
                                    dbc.Button(
                                        "Deseleccionar Todos",
                                        id="deselect-all-slots-button",
                                        color="secondary",
                                        size="sm",
                                        className="me-2"
                                    ),
                                    dbc.Button(
                                        "Limpiar UUIDs",
                                        id="clear-uuids-button",
                                        color="warning",
                                        size="sm",
                                        className="me-2"
                                    ),
                                ], className="d-flex"),
                            ]),
                        ], width=12),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "Asignar UUIDs",
                                id="assign-multiple-button",
                                color="success",
                                className="me-2"
                            ),
                            dbc.Button(
                                "Borrar Slots Seleccionados",
                                id="delete-slots-button",
                                color="danger"
                            ),
                        ], className="mt-3 d-flex justify-content-end")
                    ])
                ])
            ], className="mb-4"),
            
            # Assets Table Card
            dbc.Card([
                dbc.CardHeader([
                    dbc.Row([
                        dbc.Col(html.H5("Gestión de Accesos NFC", className="mb-0"), width="auto"),
                        dbc.Col([
                            # Add Select All button
                            dbc.Button(
                                "Seleccionar Todo",
                                id="select-all-button",
                                color="secondary",
                                className="me-2",
                                n_clicks=0
                            ),
                            # Existing refresh button
                            dbc.Button(
                                [html.I(className="fas fa-sync-alt me-2"), "Actualizar Códigos"],
                                id="refresh-nfc-codes-button",
                                color="secondary",
                                className="me-2"
                            ),
                            dbc.Select(
                                id="page-size-select",
                                options=[
                                    {"label": f"{size} filas", "value": int(size)} 
                                    for size in PAGE_SIZE_OPTIONS
                                ] + [{"label": "Todas", "value": -1}],
                                value=10,
                                style={"width": "150px"},
                                className="float-end",
                                persistence=True,
                                persistence_type="session"
                            ),
                        ], className="text-end d-flex justify-content-end align-items-center"),
                    ], align="center", className="mb-3"),
                ]),
                dbc.CardBody([
                    # Status message area
                    html.Div(id="access-status-message", className="mb-3"),
                    
                    # Assets table
                    html.Div(id="access-assets-table"),
                    
                    # Update button
                    dbc.Button(
                        "Actualizar Códigos NFC",
                        id="update-nfc-codes-button",
                        color="primary",
                        className="mt-3",
                        disabled=True
                    ),
                ])
            ], className="mb-4"),
            
        ], label="Asignación de Tarjetas", tab_id="tab-assignment"),
        
        # Tab 2: Access Data
        dbc.Tab([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Análisis de Datos de Acceso", className="mb-4"),
                    
                    # Download Section
                    dbc.Row([
                        dbc.Col([
                            html.H5("Descarga de Datos", className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Site ID:", className="fw-bold"),
                                    dbc.Input(
                                        id="salto-site-id",
                                        type="text",
                                        placeholder="Ingrese el Site ID de SALTO",
                                        className="mb-3"
                                    ),
                                ], md=6),
                                dbc.Col([
                                    html.Label("Año:", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="salto-year-select",
                                        options=[
                                            {"label": str(year), "value": year}
                                            for year in range(2020, datetime.now().year + 1)
                                        ],
                                        value=datetime.now().year,
                                        className="mb-3"
                                    ),
                                ], md=6),
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Token de Acceso:", className="fw-bold"),
                                    dbc.Textarea(
                                        id="salto-bearer-token",
                                        placeholder="Ingrese el token de acceso de SALTO",
                                        className="mb-3",
                                        style={"height": "100px"}
                                    ),
                                ], md=12),
                            ]),
                            dbc.Button(
                                [html.I(className="fas fa-download me-2"), "Descargar Datos"],
                                id="download-salto-data-button",
                                color="primary",
                                className="mb-3"
                            ),
                            dbc.Progress(id="download-progress", className="mb-3"),
                            html.Div(id="download-status", className="mb-3"),
                            dcc.Download(id="download-dataframe"),
                        ], md=12),
                    ], className="mb-4"),
                    
                    # Analysis Section
                    dbc.Row([
                        dbc.Col([
                            html.H5("Análisis de Datos", className="mb-3"),
                            dcc.Upload(
                                id='upload-salto-data',
                                children=html.Div([
                                    'Arrastre y suelte o ',
                                    html.A('seleccione un archivo CSV')
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
                        ], md=12),
                    ]),
                    
                    # Analysis Results
                    html.Div(id="analysis-content", children=[
                        dbc.Row([
                            # Summary Statistics
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H6("Resumen Estadístico", className="mb-3"),
                                        html.Div(id="summary-stats")
                                    ])
                                ])
                            ], md=12, className="mb-4"),
                            
                            # Daily Activity Graph
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H6("Actividad Diaria", className="mb-3"),
                                        dcc.Graph(id="daily-activity-graph")
                                    ])
                                ])
                            ], md=6),
                            
                            # Hourly Distribution
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H6("Distribución por Hora", className="mb-3"),
                                        dcc.Graph(id="hourly-distribution-graph")
                                    ])
                                ])
                            ], md=6),
                        ]),
                        
                        # Detailed Data Table
                        dbc.Row([
                            dbc.Col([
                                html.H6("Datos Detallados", className="mb-3"),
                                dash_table.DataTable(
                                    id='salto-data-table',
                                    page_size=15,
                                    style_table={'overflowX': 'auto'},
                                    style_cell={
                                        'textAlign': 'left',
                                        'padding': '10px'
                                    },
                                    style_header={
                                        'backgroundColor': 'rgb(230, 230, 230)',
                                        'fontWeight': 'bold'
                                    },
                                    filter_action="native",
                                    sort_action="native",
                                    sort_mode="multi"
                                )
                            ], md=12)
                        ])
                    ], style={'display': 'none'})
                ])
            ])
        ], label="Datos de Acceso", tab_id="tab-access-data"),
        
    ], id="access-tabs", active_tab="tab-assignment"),
    
    # Loading component
    dcc.Loading(
        id="loading-access",
        type="circle",
        children=html.Div(id="loading-output-access")
    ),
])

# Create the layout using the shared layout
layout = create_layout(content)

@callback(
    [Output("access-assets-table", "children"),
     Output("update-nfc-codes-button", "disabled")],
    [Input("access-dropdown-proyectos", "value"),
     Input("page-size-select", "value")]
)
def update_assets_table(project_id, page_size):
    if not project_id:
        return html.P("Seleccione un proyecto para ver sus activos."), True
    
    try:
        # Convert page_size to integer
        page_size = int(page_size) if page_size is not None else 10
        
        # Get project assets
        assets = get_project_assets(project_id)
        if not assets:
            return html.P("No se encontraron activos para este proyecto."), True
        
        # Create list to store rows
        table_rows = []
        devices_found = 0
        
        # First pass: Get basic device information
        for asset in assets:
            asset_devices = get_asset_devices(asset['id'])
            if asset_devices and 'gateways' in asset_devices:
                gateway = asset_devices['gateways'][0]
                gateway_id = gateway.get('uuid')
                
                for device in gateway.get('devices', []):
                    if any(sensor['sensor_type'] == 'NFC_CODE' for sensor in device.get('sensors', [])):
                        devices_found += 1
                        device_id = device['device_id']
                        device_name = device.get('parameters', {}).get('name', '')
                        device_room = device.get('parameters', {}).get('room', '')
                        
                        row = {
                            'id': asset['id'],
                            'alias': f"{asset['alias']} - {device_name} ({device_room})",
                            'gateway_id': gateway_id,
                            'device_id': device_id,
                            'room': device_room,
                            'device_name': device_name
                        }
                        
                        # Initialize slots with empty values
                        for slot in range(2, 12):
                            row[f'slot_{slot}'] = ''
                        
                        table_rows.append(row)
        
        if not table_rows:
            return html.P("No se encontraron dispositivos con sensores NFC."), True
        
        # Create DataFrame
        df = pd.DataFrame(table_rows)
        
        # Second pass: Get current NFC codes (can be refreshed later)
        for row in df.itertuples():
            current_codes = get_deployment_sensor_passwords(row.id)
            device_codes = current_codes.get(row.gateway_id, {})
            
            for slot in range(2, 12):
                df.at[row.Index, f'slot_{slot}'] = device_codes.get(str(slot), '')
        
        # Handle "All" option for page size
        if page_size == -1:
            page_size = len(df)
        
        # Create table
        table = dash_table.DataTable(
            id='assets-nfc-table',
            columns=[
                {"name": "ID", "id": "id"},
                {"name": "Alias", "id": "alias"},
                {"name": "Habitación", "id": "room"},
                {"name": "Dispositivo", "id": "device_name"},
                {"name": "Gateway", "id": "gateway_id"},
                {"name": "Device ID", "id": "device_id"},
            ] + [
                {"name": f"Slot {slot}", "id": f"slot_{slot}"}
                for slot in range(2, 12)
            ],
            data=df.to_dict('records'),
            editable=True,
            row_deletable=False,
            page_size=page_size,
            page_action='native',
            page_current=0,
            style_table={
                'overflowX': 'auto',
                'overflowY': 'auto',
                'maxHeight': '60vh'
            },
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'minWidth': '100px',
                'maxWidth': '300px',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold',
                'position': 'sticky',
                'top': 0,
                'zIndex': 1
            },
            sort_action='native',
            filter_action='native',
            row_selectable='multi',
            selected_rows=[],
            fixed_rows={'headers': True},
            persistence=True,
            persistence_type='session',
            style_data_conditional=[
                {
                    'if': {'column_id': f'slot_{i}'},
                    'backgroundColor': '#e3f2fd'
                } for i in range(2, 12)
            ] + [
                {
                    'if': {'state': 'selected'},
                    'backgroundColor': 'rgba(0, 116, 217, 0.1)',
                    'border': '1px solid rgb(0, 116, 217)'
                }
            ]
        )
        
        return table, False
        
    except Exception as e:
        print(f"Error loading assets: {str(e)}")
        return html.P(f"Error al cargar los activos: {str(e)}"), True

# Callback to load projects based on selected client
@callback(
    Output("access-dropdown-proyectos", "options"),
    Input("access-dropdown-clientes", "value")
)
def cargar_proyectos(cliente_id):
    if not cliente_id:
        return []
    try:
        print(f"Loading projects for client_id: {cliente_id}")
        proyectos = get_projects_by_client(cliente_id)
        options = [{"label": proyecto["name"], "value": proyecto["id"]} for proyecto in proyectos]
        print(f"Loaded projects: {options}")
        return options
    except Exception as e:
        print(f"Error loading projects: {str(e)}")
        return []

# Clear projects when client changes
@callback(
    Output("access-dropdown-proyectos", "value"),
    Input("access-dropdown-clientes", "value")
)
def clear_project_selection(_):
    return None

# Add callback to enable/disable UIDD assignment button
@callback(
    Output("assign-uidd-button", "disabled"),
    [Input("uidd-input", "value"),
     Input("access-dropdown-proyectos", "value")]
)
def toggle_assign_button(uidd, project_id):
    return not (uidd and project_id)

# Add callback for slot selection buttons
@callback(
    [Output(f"slot-check-{i}", "value") for i in range(2, 12)],
    [Input("select-all-slots-button", "n_clicks"),
     Input("deselect-all-slots-button", "n_clicks")],
    prevent_initial_call=True
)
def handle_slot_selection(select_clicks, deselect_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [no_update] * 10
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == "select-all-slots-button":
        return [True] * 10
    elif trigger_id == "deselect-all-slots-button":
        return [False] * 10
    return [no_update] * 10

@callback(
    [Output(f"slot-uuid-{i}", "value") for i in range(2, 12)],
    Input("clear-uuids-button", "n_clicks"),
    prevent_initial_call=True
)
def clear_uuids(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return [""] * 10

# Update the handle_updates callback to work with individual slot inputs
@callback(
    [Output("assets-nfc-table", "data", allow_duplicate=True),
     Output("access-status-message", "children", allow_duplicate=True)],
    [Input("assign-multiple-button", "n_clicks"),
     Input("delete-slots-button", "n_clicks")],
    [State(f"slot-check-{i}", "value") for i in range(2, 12)] +
    [State(f"slot-uuid-{i}", "value") for i in range(2, 12)] +
    [State("assets-nfc-table", "data"),
     State("assets-nfc-table", "selected_rows"),
     State("assets-nfc-table", "derived_virtual_selected_rows")],
    prevent_initial_call=True
)
def handle_slot_updates(assign_clicks, delete_clicks, *args):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update
    
    # Split args into checks, uuids, and table data
    slot_checks = [check if check is not None else False for check in args[:10]]
    slot_uuids = args[10:20]
    table_data = args[20]
    selected_rows = args[21]
    derived_selected_rows = args[22]
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if not table_data:
        return no_update, no_update
    
    rows_to_process = derived_selected_rows if derived_selected_rows is not None else selected_rows
    new_data = table_data.copy()
    success_count = 0
    error_count = 0
    
    if trigger_id == "assign-multiple-button":
        # Debug prints
        print("Slot checks:", slot_checks)
        print("Slot UUIDs:", slot_uuids)
        print("Selected rows:", selected_rows)
        print("Derived selected rows:", derived_selected_rows)
        
        # Collect slots that are checked and have UUIDs
        selected_slots_with_uuids = []
        for slot_idx, (checked, uuid) in enumerate(zip(slot_checks, slot_uuids), 2):
            uuid_str = str(uuid).strip() if uuid is not None else ""
            if checked and uuid_str:
                selected_slots_with_uuids.append((slot_idx, uuid_str))
                print(f"Added slot {slot_idx} with UUID {uuid_str}")
        
        print(f"Selected slots with UUIDs: {selected_slots_with_uuids}")
        
        if not selected_slots_with_uuids:
            return no_update, dbc.Alert(
                "Por favor, seleccione al menos un slot y asigne un UUID",
                color="warning",
                dismissable=True
            )
        
        # Update row selection logic
        if not rows_to_process:
            # If no rows are selected, use all rows
            rows_to_update = list(range(len(table_data)))
            print(f"No rows selected, using all rows: {rows_to_update}")
        else:
            rows_to_update = rows_to_process
            print(f"Using selected rows: {rows_to_update}")
        
        # Process updates one row at a time
        for row_idx in rows_to_update:
            row = new_data[row_idx]
            gateway_id = row['gateway_id']
            device_id = row['device_id']
            print(f"Processing row {row_idx} - Gateway: {gateway_id}, Device: {device_id}")
            
            # Process one slot at a time
            for slot_idx, uuid in selected_slots_with_uuids:
                try:
                    print(f"Updating slot {slot_idx} with UUID {uuid}")
                    # Add a small delay between requests
                    import time
                    time.sleep(0.5)  # 500ms delay
                    
                    if update_sensor_password(gateway_id, device_id, str(slot_idx), uuid):
                        row[f'slot_{slot_idx}'] = uuid
                        success_count += 1
                        print(f"Success updating slot {slot_idx}")
                    else:
                        error_count += 1
                        print(f"Failed updating slot {slot_idx}")
                except Exception as e:
                    print(f"Error updating slot {slot_idx}: {str(e)}")
                    error_count += 1
        
        status_message = f"Asignación de UUIDs completada. Éxitos: {success_count}, Errores: {error_count}"
        return new_data, dbc.Alert(
            status_message,
            color="success" if error_count == 0 else "warning",
            dismissable=True
        )
    
    elif trigger_id == "delete-slots-button":
        # Similar to existing delete code but using slot_checks
        if not any(slot_checks):
            return no_update, dbc.Alert(
                "Por favor, seleccione al menos un slot para borrar",
                color="warning",
                dismissable=True
            )
        
        rows_to_update = rows_to_process if rows_to_process else ([0] if len(table_data) == 1 else [])
        
        for row_idx in rows_to_update:
            row = new_data[row_idx]
            gateway_id = row['gateway_id']
            device_id = row['device_id']
            
            for slot_idx, checked in enumerate(slot_checks, 2):
                if checked:
                    if update_sensor_password(gateway_id, device_id, str(slot_idx), ""):
                        row[f'slot_{slot_idx}'] = ""
                        success_count += 1
                    else:
                        error_count += 1
        
        status_message = f"Borrado de slots completado. Éxitos: {success_count}, Errores: {error_count}"
    
    return new_data, dbc.Alert(status_message, color="success" if error_count == 0 else "warning", dismissable=True)

# Add new callback for Select All functionality
@callback(
    [Output("assets-nfc-table", "selected_rows"),
     Output("select-all-button", "children")],
    [Input("select-all-button", "n_clicks")],
    [State("assets-nfc-table", "data"),
     State("assets-nfc-table", "selected_rows")],
    prevent_initial_call=True
)
def toggle_select_all(n_clicks, data, current_selection):
    if not data:
        return [], "Seleccionar Todo"
    
    # If no rows are currently selected or only some rows are selected, select all
    if not current_selection or len(current_selection) < len(data):
        return list(range(len(data))), "Deseleccionar Todo"
    # If all rows are selected, deselect all
    else:
        return [], "Seleccionar Todo" 

# Add a callback to handle tab changes if needed
@callback(
    Output("loading-output-access", "children"),
    Input("access-tabs", "active_tab")
)
def handle_tab_switch(active_tab):
    if active_tab == "tab-assignment":
        return ""
    elif active_tab == "tab-access-data":
        return ""
    return ""

# Add this function to handle SALTO API requests
def download_salto_entries(site_id, start_date, end_date, bearer_token):
    """Download entries from SALTO API for a specific date range"""
    url = f'https://connect.my-clay.com/v1.1/sites/{site_id}/entries/export'
    
    params = {
        'export_file_name': 'entries.csv',
        'from_date': start_date.strftime('%Y-%m-%dT00:00:00.000Z'),
        'to_date': end_date.strftime('%Y-%m-%dT23:59:59.999Z')
    }
    
    # First, make the OPTIONS request
    options_headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'access-control-request-headers': 'authorization,clp-disable-odata-v3-conversion,x-datadog-origin,x-datadog-parent-id,x-datadog-sampling-priority,x-datadog-trace-id',
        'access-control-request-method': 'GET',
        'origin': 'https://app.saltoks.com',
        'referer': 'https://app.saltoks.com/',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
    }
    
    try:
        # Make OPTIONS request
        options_response = requests.options(url, params=params, headers=options_headers)
        # 204 is a successful response for OPTIONS
        if options_response.status_code not in [200, 204]:
            raise Exception(f"Error en la solicitud OPTIONS: {options_response.status_code}")
        
        # Then make the GET request
        get_headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'authorization': f'Bearer {bearer_token}',
            'clp-disable-odata-v3-conversion': 'true',
            'origin': 'https://app.saltoks.com',
            'referer': 'https://app.saltoks.com/',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'x-datadog-origin': 'rum',
            'x-datadog-sampling-priority': '1',
            'x-datadog-parent-id': str(random.randint(1000000000000000000, 9999999999999999999)),
            'x-datadog-trace-id': str(random.randint(1000000000000000000, 9999999999999999999))
        }
        
        response = requests.get(url, params=params, headers=get_headers)
        
        if response.status_code == 401:
            raise Exception("El token de acceso es inválido o ha expirado. Por favor, obtenga un nuevo token.")
        
        if response.status_code == 200:
            try:
                df = pd.read_csv(io.StringIO(response.text))
                return df
            except Exception as e:
                print(f"Error parsing CSV: {e}")
                print(f"Response content: {response.text[:200]}...")
                return None
        else:
            error_msg = f"Error en la respuesta de SALTO (código {response.status_code})"
            if response.text:
                error_msg += f": {response.text}"
            raise Exception(error_msg)
            
    except Exception as e:
        raise Exception(f"Error al descargar datos: {str(e)}")

# Update the callback for download functionality
@callback(
    [Output("download-dataframe", "data"),
     Output("download-status", "children"),
     Output("download-progress", "value", allow_duplicate=True),
     Output("download-progress", "label", allow_duplicate=True)],
    Input("download-salto-data-button", "n_clicks"),
    [State("salto-site-id", "value"),
     State("salto-year-select", "value"),
     State("salto-bearer-token", "value")],
    prevent_initial_call=True
)
def download_yearly_data(n_clicks, site_id, year, bearer_token):
    if not n_clicks or not site_id or not year or not bearer_token:
        raise PreventUpdate
    
    try:
        # Validate bearer token format
        if not bearer_token.strip().startswith("eyJ"):
            return (None, "Error: El token de acceso no tiene el formato correcto. Debe comenzar con 'eyJ'", 0, "Error")
        
        all_data = []
        total_months = 12
        
        # Try first month to validate credentials
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 1, 31)
        try:
            test_data = download_salto_entries(site_id, start_date, end_date, bearer_token)
            if test_data is not None:
                all_data.append(test_data)
        except Exception as e:
            return (None, str(e), 0, "Error")
        
        # If we get here, token is valid, continue with remaining months
        for month in range(2, 13):
            try:
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year, month, 31)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(days=1)
                
                monthly_data = download_salto_entries(site_id, start_date, end_date, bearer_token)
                if monthly_data is not None and not monthly_data.empty:
                    all_data.append(monthly_data)
            except Exception as e:
                print(f"Error en mes {month}: {str(e)}")
                continue
        
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            return (
                dcc.send_data_frame(
                    final_df.to_csv,
                    f"salto_data_{year}.csv",
                    index=False
                ),
                f"Descarga completada para el año {year}. Total registros: {len(final_df)}",
                100,
                "100%"
            )
        else:
            return (None, "No se encontraron datos para el período seleccionado", 0, "Error")
            
    except Exception as e:
        return (None, f"Error: {str(e)}", 0, "Error")

# Add callback for progress updates
@callback(
    [Output("download-progress", "value", allow_duplicate=True),
     Output("download-progress", "label", allow_duplicate=True),
     Output("download-interval", "disabled")],
    [Input("download-interval", "n_intervals"),
     Input("download-salto-data-button", "n_clicks")],
    [State("download-progress", "value")],
    prevent_initial_call=True
)
def update_progress(n_intervals, n_clicks, current_value):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger == "download-salto-data-button":
        return 0, "0%", False
    
    if current_value is None:
        current_value = 0
    
    if current_value >= 100:
        return 100, "100%", True
    
    new_value = min(current_value + 8.33, 100)  # Increment by ~1/12 (for 12 months)
    return new_value, f"{new_value:.0f}%", False

# Add callback to handle file upload and analysis
@callback(
    [Output("analysis-content", "style"),
     Output("summary-stats", "children"),
     Output("daily-activity-graph", "figure"),
     Output("hourly-distribution-graph", "figure"),
     Output("salto-data-table", "data"),
     Output("salto-data-table", "columns")],
    Input("upload-salto-data", "contents"),
    State("upload-salto-data", "filename")
)
def update_analysis(contents, filename):
    if contents is None:
        raise PreventUpdate
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        # Read the CSV file with semicolon separator
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep=';')
        print("Columns in CSV:", df.columns.tolist())
        
        # Convert SALTO timestamp format with American date format (MM/DD/YYYY)
        df['datetime'] = pd.to_datetime(df['Local Time'], format='%m/%d/%Y %H:%M:%S')
        df['hour'] = df['datetime'].dt.hour
        df['date'] = df['datetime'].dt.date
        
        # Summary statistics
        total_records = len(df)
        unique_dates = df['date'].nunique()
        avg_daily = total_records / unique_dates if unique_dates > 0 else 0
        
        # User statistics
        unique_users = df['User First Name'].nunique()
        unique_doors = df['Lock Name'].nunique()
        
        # Add event category statistics
        event_stats = df['Event Category'].value_counts()
        
        summary = dbc.ListGroup([
            dbc.ListGroupItem(f"Total de registros: {total_records:,}"),
            dbc.ListGroupItem(f"Días únicos: {unique_dates}"),
            dbc.ListGroupItem(f"Promedio diario: {avg_daily:.1f}"),
            dbc.ListGroupItem(f"Usuarios únicos: {unique_users}"),
            dbc.ListGroupItem(f"Puertas únicas: {unique_doors}"),
            dbc.ListGroupItem("Tipos de eventos:", className="fw-bold"),
            *[dbc.ListGroupItem(f"{cat}: {count:,}") for cat, count in event_stats.items()]
        ])
        
        # Daily activity graph
        daily_counts = df.groupby('date').size().reset_index(name='count')
        daily_fig = px.line(daily_counts, x='date', y='count',
                          title='Actividad Diaria',
                          labels={'count': 'Número de Eventos', 'date': 'Fecha'})
        daily_fig.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Número de Eventos",
            hovermode='x unified'
        )
        
        # Hourly distribution graph
        hourly_counts = df.groupby('hour').size().reset_index(name='count')
        hourly_fig = px.bar(hourly_counts, x='hour', y='count',
                          title='Distribución por Hora',
                          labels={'count': 'Número de Eventos', 'hour': 'Hora'})
        hourly_fig.update_layout(
            xaxis_title="Hora del día",
            yaxis_title="Número de Eventos",
            xaxis=dict(tickmode='linear', tick0=0, dtick=1),
            bargap=0.2
        )
        
        # Door activity analysis
        door_counts = df.groupby('Lock Name').size().reset_index(name='count')
        door_counts = door_counts.sort_values('count', ascending=False)
        
        # Add top doors to summary
        top_doors = door_counts.head(5).to_dict('records')
        summary.children.append(
            dbc.ListGroupItem("Puertas más utilizadas:", className="fw-bold")
        )
        for door in top_doors:
            summary.children.append(
                dbc.ListGroupItem(f"{door['Lock Name']}: {door['count']:,} eventos")
            )
        
        # Prepare table data with formatted datetime
        df['Time'] = df['datetime'].dt.strftime('%d/%m/%Y %H:%M:%S')
        
        # Reorder columns for better visualization
        column_order = [
            'Time', 'Event Category', 'Event Detail', 'Lock Name', 
            'User First Name', 'User Last Name', 'Access By', 'Access Detail'
        ]
        remaining_columns = [col for col in df.columns if col not in column_order + ['datetime', 'hour', 'date']]
        final_columns = column_order + remaining_columns
        
        table_data = df[final_columns].to_dict('records')
        columns = [{"name": i, "id": i} for i in final_columns]
        
        return (
            {'display': 'block'},
            summary,
            daily_fig,
            hourly_fig,
            table_data,
            columns
        )
        
    except Exception as e:
        print(f"Error processing file: {e}")
        print(f"DataFrame columns: {df.columns if 'df' in locals() else 'No DataFrame'}")
        raise PreventUpdate