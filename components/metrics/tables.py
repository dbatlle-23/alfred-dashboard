import dash_bootstrap_components as dbc
from dash import dash_table, html, dcc
import pandas as pd
from config.metrics_config import TABLE_CONFIG

def create_monthly_readings_table(df, title="Lecturas Mensuales"):
    """
    Create a table for monthly readings.
    
    Args:
        df (pd.DataFrame): DataFrame with monthly readings data
        title (str): Table title
        
    Returns:
        html.Div: Table component
    """
    # Logs para depuración
    print(f"[DEBUG] create_monthly_readings_table - Creando tabla con título: {title}")
    print(f"[DEBUG] create_monthly_readings_table - DataFrame shape: {df.shape if df is not None and not df.empty else 'DataFrame vacío'}")
    
    if df is None or df.empty:
        print(f"[INFO] create_monthly_readings_table - No hay datos disponibles para la tabla")
        return html.Div([
            html.Div([
                dbc.Row([
                    dbc.Col(html.H5(title, className="mb-0"), width="auto"),
                    dbc.Col(width="auto", className="ms-auto")
                ], className="d-flex align-items-center"),
            ], className="mb-3"),
            html.P("No hay datos disponibles", className="text-muted")
        ])
    
    # Create a copy to avoid modifying the original
    table_df = df.copy()
    
    # Logs para depuración - Columnas disponibles
    print(f"[DEBUG] create_monthly_readings_table - Columnas disponibles: {table_df.columns.tolist()}")
    
    # Format numeric columns
    for col in table_df.columns:
        if col not in ['Asset', 'block_number', 'staircase', 'apartment', 'consumption_type'] and not col.endswith('(Consumo)'):
            try:
                # Convert to numeric only if not "Sin Datos"
                mask = table_df[col] != "Sin Datos"
                if mask.any():
                    table_df.loc[mask, col] = pd.to_numeric(table_df.loc[mask, col], errors='coerce')
                    table_df.loc[mask, col] = table_df.loc[mask, col].map('{:.2f}'.format)
            except Exception as e:
                print(f"[ERROR] create_monthly_readings_table - Error al formatear columna {col}: {str(e)}")
        elif col.endswith('(Consumo)'):
            try:
                # Convert to numeric only if not "Sin Datos"
                mask = table_df[col] != "Sin Datos"
                if mask.any():
                    table_df.loc[mask, col] = pd.to_numeric(table_df.loc[mask, col], errors='coerce')
                    table_df.loc[mask, col] = table_df.loc[mask, col].map('{:.2f}'.format)
            except Exception as e:
                print(f"[ERROR] create_monthly_readings_table - Error al formatear columna de consumo {col}: {str(e)}")
    
    # Create conditional styling for consumption columns
    style_data_conditional = [
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)'
        }
    ]
    
    # Add styling for consumption columns
    for col in table_df.columns:
        if col.endswith('(Consumo)'):
            style_data_conditional.append({
                'if': {'column_id': col},
                'backgroundColor': 'rgba(102, 204, 255, 0.2)',
                'fontWeight': 'bold'
            })
    
    # Add styling for metadata columns
    metadata_columns = ['block_number', 'staircase', 'apartment']
    for col in metadata_columns:
        if col in table_df.columns:
            style_data_conditional.append({
                'if': {'column_id': col},
                'backgroundColor': 'rgba(240, 240, 240, 0.5)',
                'fontStyle': 'italic'
            })
    
    # Add styling for consumption type column
    if 'consumption_type' in table_df.columns:
        style_data_conditional.append({
            'if': {'column_id': 'consumption_type'},
            'backgroundColor': 'rgba(255, 230, 153, 0.5)',
            'fontWeight': 'bold'
        })
    
    # Add styling for "Sin Datos" cells
    for col in table_df.columns:
        if col not in ['Asset', 'block_number', 'staircase', 'apartment', 'consumption_type']:
            style_data_conditional.append({
                'if': {
                    'filter_query': '{{{0}}} = "Sin Datos"'.format(col),
                    'column_id': col
                },
                'backgroundColor': 'rgba(240, 240, 240, 0.7)',
                'color': 'rgba(128, 128, 128, 0.7)',
                'fontStyle': 'italic'
            })
    
    # Add styling for clickable cells
    for col in table_df.columns:
        if col not in ['Asset', 'block_number', 'staircase', 'apartment', 'consumption_type']:
            style_data_conditional.append({
                'if': {'column_id': col},
                'cursor': 'pointer'
            })
    
    # Create tooltip data for clickable cells
    tooltip_data = []
    for i in range(len(table_df)):
        row_tooltips = {}
        for col in table_df.columns:
            if col not in ['Asset', 'block_number', 'staircase', 'apartment', 'consumption_type']:
                row_tooltips[col] = {'value': 'Haz clic para ver detalles', 'type': 'markdown'}
        tooltip_data.append(row_tooltips)
    
    # Logs para depuración - Creación de la tabla
    print(f"[DEBUG] create_monthly_readings_table - Creando tabla interactiva con {len(table_df)} filas")
    
    # Create table
    table = dash_table.DataTable(
        id='monthly-readings-table-interactive',
        columns=[{"name": col, "id": col} for col in table_df.columns],
        data=table_df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_data_conditional=style_data_conditional,
        page_size=15,
        page_current=0,
        page_action='native',
        sort_action='native',
        sort_mode='multi',
        filter_action='native',
        filter_options={'case': 'insensitive'},
        export_format='csv',
        cell_selectable=True,
        tooltip_data=tooltip_data,
        tooltip_duration=None,
        virtualization=False,
        persistence=True,
        persistence_type='session',
        persisted_props=['filter_query', 'page_current', 'sort_by'],
    )
    
    # Logs para depuración - Tabla creada
    print(f"[INFO] create_monthly_readings_table - Tabla interactiva creada correctamente con {len(table_df)} filas y {len(table_df.columns)} columnas")
    
    # Crear el encabezado con título y botones de exportación
    header = html.Div([
        dbc.Row([
            dbc.Col(html.H5(title, className="mb-0"), width="auto"),
            dbc.Col(
                dbc.ButtonGroup([
                    dbc.Button(
                        [html.I(className="fas fa-file-export me-2"), "Exportar"],
                        id="export-monthly-readings-btn",
                        color="primary",
                        outline=True,
                        size="sm",
                        className="d-flex align-items-center export-main-btn"
                    ),
                    dbc.DropdownMenu(
                        [
                            dbc.DropdownMenuItem([html.I(className="fas fa-file-csv me-2"), "CSV"], id="export-monthly-readings-csv-btn"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-file-excel me-2"), "Excel"], id="export-monthly-readings-excel-btn"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-file-pdf me-2"), "PDF"], id="export-monthly-readings-pdf-btn"),
                        ],
                        size="sm",
                        group=True,
                        right=True,
                    ),
                ]),
                width="auto",
                className="ms-auto"
            ),
        ], className="d-flex align-items-center"),
    ], className="mb-3")
    
    return html.Div([
        header,
        table
    ])

def create_monthly_readings_by_consumption_type(tables_dict):
    """
    Create tables for monthly readings by consumption type.
    
    Args:
        tables_dict (dict): Dictionary of DataFrames with monthly readings by consumption type
        
    Returns:
        html.Div: Component with tables
    """
    if not tables_dict:
        return html.Div([
            html.H5("Lecturas Mensuales por Tipo de Consumo"),
            html.P("No hay datos disponibles", className="text-muted")
        ])
    
    tables = []
    for consumption_type, df in tables_dict.items():
        tables.append(
            create_monthly_readings_table(df, f"Lecturas Mensuales - {consumption_type}")
        )
    
    return html.Div([
        html.H5("Lecturas Mensuales por Tipo de Consumo", className="mb-4"),
        html.Div(tables, className="mt-3")
    ])

def create_consumption_stats_table(stats_df, title="Estadísticas de Consumo"):
    """
    Create a table for consumption statistics.
    
    Args:
        stats_df (pd.DataFrame): DataFrame with consumption statistics
        title (str): Table title
        
    Returns:
        html.Div: Table component
    """
    if stats_df is None or stats_df.empty:
        return html.Div([
            html.H5(title),
            html.P("No hay datos disponibles", className="text-muted")
        ])
    
    # Format numeric columns
    for col in stats_df.columns:
        if col != 'Estadística':
            try:
                stats_df[col] = pd.to_numeric(stats_df[col], errors='coerce')
                stats_df[col] = stats_df[col].map('{:.2f}'.format)
            except:
                pass
    
    # Create table
    table = dash_table.DataTable(
        id='consumption-stats-table',
        columns=[{"name": col, "id": col} for col in stats_df.columns],
        data=stats_df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ]
    )
    
    return html.Div([
        html.H5(title),
        table
    ])

def create_daily_readings_table(df, title="Lecturas Diarias"):
    """
    Create a table for daily readings.
    
    Args:
        df (pd.DataFrame): DataFrame with daily readings data
        title (str): Table title
        
    Returns:
        html.Div: Table component
    """
    if df is None or df.empty:
        return html.Div([
            html.H5(title),
            html.P("No hay datos disponibles", className="text-muted")
        ])
    
    # Format date column
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    
    # Format numeric columns
    for col in df.columns:
        if col not in ['date', 'asset_id', 'consumption_type']:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].map('{:.2f}'.format)
            except:
                pass
    
    # Create table
    table = dash_table.DataTable(
        id='daily-readings-table',
        columns=[{"name": col, "id": col} for col in df.columns],
        data=df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ],
        page_size=15,
        sort_action='native',
        filter_action='native'
    )
    
    return html.Div([
        html.H5(title),
        table
    ])

def create_monthly_summary_table(df, title="Resumen Mensual de Consumos"):
    """
    Create a table for monthly consumption summary.
    
    Args:
        df (pd.DataFrame): DataFrame with monthly summary data
        title (str): Table title
        
    Returns:
        html.Div: Table component
    """
    print("=====================================================")
    print("DEBUGGING MONTHLY SUMMARY TABLE - FUNCTION CALLED")
    print("=====================================================")
    print(f"[DEBUG] create_monthly_summary_table - DataFrame type: {type(df)}")
    print(f"[DEBUG] create_monthly_summary_table - DataFrame shape: {df.shape if df is not None and not df.empty else 'Empty or None'}")
    print(f"[DEBUG] create_monthly_summary_table - DataFrame columns: {df.columns.tolist() if df is not None and not df.empty else 'Empty or None'}")
    
    if df is None or df.empty:
        print(f"[DEBUG] create_monthly_summary_table - DataFrame is empty or None")
        return html.Div([
            html.Div([
                dbc.Row([
                    dbc.Col(html.H5(title if title != "Resumen Mensual de Consumos" else "Resumen Mensual de Consumos", className="mb-0"), width="auto"),
                ], className="d-flex align-items-center"),
            ], className="mb-3"),
            html.Div([
                html.I(className="fas fa-info-circle me-2"),
                html.Span("No hay datos disponibles.")
            ], className="alert alert-info")
        ])
    
    # Create a copy to avoid modifying the original
    table_df = df.copy()
    
    # Format numeric columns
    numeric_columns = ['total_consumption', 'average_consumption', 'min_consumption', 'max_consumption']
    for col in table_df.columns:
        if col in numeric_columns:
            try:
                table_df[col] = pd.to_numeric(table_df[col], errors='coerce')
                table_df[col] = table_df[col].map('{:.2f}'.format)
            except:
                pass
    
    # Create conditional styling
    style_data_conditional = [
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)'
        },
        {
            'if': {'state': 'selected'},
            'backgroundColor': 'rgba(0, 116, 217, 0.3)',
            'border': '1px solid blue'
        }
    ]
    
    # Create tooltip data to indicate clickable cells
    tooltip_data = [
        {
            column: {'value': 'Haz clic para ver detalles', 'type': 'markdown'}
            for column in table_df.columns if column != 'month'
        }
        for _ in range(len(table_df))
    ]
    
    # Create the table with cell selection enabled
    table = dash_table.DataTable(
        id='metrics-monthly-summary-table',
        columns=[
            {"name": "Mes", "id": "month"},
            {"name": "Consumo Total", "id": "total_consumption"},
            {"name": "Consumo Promedio", "id": "average_consumption"},
            {"name": "Consumo Mínimo", "id": "min_consumption"},
            {"name": "Consumo Máximo", "id": "max_consumption"},
            {"name": "Número de Activos", "id": "asset_count"}
        ],
        data=table_df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'center',
            'padding': '10px',
            'minWidth': '100px'
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold',
            'textAlign': 'center'
        },
        style_data_conditional=style_data_conditional,
        page_size=10,
        sort_action='native',
        filter_action='native',
        export_format='csv',
        # Habilitar selección de celdas
        cell_selectable=True,
        # Añadir tooltips
        tooltip_data=tooltip_data,
        tooltip_duration=None
    )
    
    return html.Div([
        html.H5(title, className="mb-3"),
        table
    ])

