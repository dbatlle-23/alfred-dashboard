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
    print("=====================================================")
    print("DEBUGGING CREATE MONTHLY READINGS TABLE - FUNCTION CALLED")
    print("=====================================================")
    
    # Logs para depuración
    print(f"[DEBUG] create_monthly_readings_table - Creando tabla con título: {title}")
    print(f"[DEBUG] create_monthly_readings_table - DataFrame shape: {df.shape if df is not None and not df.empty else 'DataFrame vacío'}")
    
    # Check if df is None or empty
    if df is None:
        print(f"[WARNING] create_monthly_readings_table - DataFrame is None")
        return html.Div([
            html.Div([
                dbc.Row([
                    dbc.Col(html.H5(title, className="mb-0"), width="auto"),
                    dbc.Col(width="auto", className="ms-auto")
                ], className="d-flex align-items-center"),
            ], className="mb-3"),
            html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                html.Span("Error: DataFrame is None")
            ], className="alert alert-warning")
        ])
    
    if df.empty:
        print(f"[INFO] create_monthly_readings_table - No hay datos disponibles para la tabla")
        return html.Div([
            html.Div([
                dbc.Row([
                    dbc.Col(html.H5(title, className="mb-0"), width="auto"),
                    dbc.Col(width="auto", className="ms-auto")
                ], className="d-flex align-items-center"),
            ], className="mb-3"),
            html.Div([
                html.I(className="fas fa-info-circle me-2"),
                html.Span("No hay datos disponibles para mostrar.")
            ], className="alert alert-info")
        ])
    
    try:
        # Create a copy to avoid modifying the original
        table_df = df.copy()
        
        # Logs para depuración - Columnas disponibles
        print(f"[DEBUG] create_monthly_readings_table - Columnas disponibles: {table_df.columns.tolist()}")
        
        # Ensure required columns exist
        required_columns = ['Asset']
        missing_columns = [col for col in required_columns if col not in table_df.columns]
        if missing_columns:
            print(f"[ERROR] create_monthly_readings_table - Missing required columns: {missing_columns}")
            return html.Div([
                html.Div([
                    dbc.Row([
                        dbc.Col(html.H5(title, className="mb-0"), width="auto"),
                        dbc.Col(width="auto", className="ms-auto")
                    ], className="d-flex align-items-center"),
                ], className="mb-3"),
                html.Div([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    html.Span(f"Error: Faltan columnas requeridas: {', '.join(missing_columns)}")
                ], className="alert alert-danger")
            ])
        
        # Detect month-consumption columns (format: 'YYYY-MM (consumption_type)')
        month_columns = []
        consumption_types = set()
        
        import re
        month_pattern = re.compile(r'(\d{4}-\d{2}) \((.*?)\)')
        
        for col in table_df.columns:
            match = month_pattern.match(str(col))
            if match:
                month = match.group(1)
                consumption_type = match.group(2)
                month_columns.append(col)
                consumption_types.add(consumption_type)
        
        print(f"[DEBUG] create_monthly_readings_table - Detected {len(month_columns)} month columns")
        print(f"[DEBUG] create_monthly_readings_table - Detected consumption types: {consumption_types}")
        
        # Format numeric columns
        for col in table_df.columns:
            if col not in ['Asset', 'block_number', 'staircase', 'apartment']:
                try:
                    # Convert to numeric only if not "Sin Datos"
                    mask = table_df[col] != "Sin Datos"
                    if mask.any():
                        table_df.loc[mask, col] = pd.to_numeric(table_df.loc[mask, col], errors='coerce')
                        table_df.loc[mask, col] = table_df.loc[mask, col].map('{:.2f}'.format)
                        print(f"[DEBUG] create_monthly_readings_table - Formatted column {col}")
                except Exception as e:
                    print(f"[ERROR] create_monthly_readings_table - Error al formatear columna {col}: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
        
        # Create conditional styling for consumption columns
        style_data_conditional = [
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ]
        
        # Add styling for metadata columns
        metadata_columns = ['block_number', 'staircase', 'apartment']
        for col in metadata_columns:
            if col in table_df.columns:
                style_data_conditional.append({
                    'if': {'column_id': col},
                    'backgroundColor': 'rgba(240, 240, 240, 0.5)',
                    'fontStyle': 'italic'
                })
        
        # Create color palette for consumption types
        import random
            
        # Define some nice pastel colors for different consumption types
        color_palette = [
            'rgba(255, 204, 204, 0.3)',  # Light red
            'rgba(204, 255, 204, 0.3)',  # Light green
            'rgba(204, 204, 255, 0.3)',  # Light blue
            'rgba(255, 255, 204, 0.3)',  # Light yellow
            'rgba(255, 204, 255, 0.3)',  # Light magenta
            'rgba(204, 255, 255, 0.3)',  # Light cyan
            'rgba(255, 229, 204, 0.3)',  # Light orange
            'rgba(229, 204, 255, 0.3)',  # Light purple
            'rgba(204, 229, 255, 0.3)',  # Light blue/cyan
            'rgba(229, 255, 204, 0.3)'   # Light yellow/green
        ]
        
        # Make sure we have enough colors
        while len(color_palette) < len(consumption_types):
            r = random.randint(150, 255)
            g = random.randint(150, 255)
            b = random.randint(150, 255)
            color_palette.append(f'rgba({r}, {g}, {b}, 0.3)')
        
        # Map consumption types to colors
        consumption_type_colors = {}
        for i, consumption_type in enumerate(sorted(consumption_types)):
            if consumption_type != 'Sin Datos' and consumption_type != '':
                consumption_type_colors[consumption_type] = color_palette[i % len(color_palette)]
        
        # Add styling for month-consumption columns
        for col in month_columns:
            match = month_pattern.match(str(col))
            if match:
                month = match.group(1)
                consumption_type = match.group(2)
                
                if consumption_type in consumption_type_colors:
                    color = consumption_type_colors[consumption_type]
                    
                    # Add styling for column header
                    style_data_conditional.append({
                        'if': {'column_id': col},
                        'backgroundColor': color
                    })
                    
                    # Style header
                    style_data_conditional.append({
                        'if': {'column_id': col},
                        'backgroundColor': color
                    })
        
        # Add styling for "Sin Datos" cells
        for col in table_df.columns:
            if col not in ['Asset', 'block_number', 'staircase', 'apartment']:
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
        for col in month_columns:
            style_data_conditional.append({
                'if': {'column_id': col},
                'cursor': 'pointer'
            })
        
        # Create tooltip data for clickable cells
        try:
            tooltip_data = []
            for i in range(len(table_df)):
                row_tooltips = {}
                for col in month_columns:
                    asset_id = table_df.iloc[i]['Asset']
                    match = month_pattern.match(str(col))
                    if match:
                        month = match.group(1)
                        consumption_type = match.group(2)
                        tooltip_text = f"Asset: {asset_id}\nMes: {month}\nTipo: {consumption_type}\nHaz clic para ver detalles"
                        row_tooltips[col] = {'value': tooltip_text, 'type': 'markdown'}
                tooltip_data.append(row_tooltips)
            print(f"[DEBUG] create_monthly_readings_table - Created tooltip data for {len(tooltip_data)} rows")
        except Exception as e:
            print(f"[ERROR] create_monthly_readings_table - Error creating tooltip data: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Create empty tooltip data as fallback
            tooltip_data = []
        
        # Create a data dictionary for the table
        try:
            table_records = table_df.to_dict('records')
            print(f"[DEBUG] create_monthly_readings_table - Created table records dictionary with {len(table_records)} items")
        except Exception as e:
            print(f"[ERROR] create_monthly_readings_table - Error creating table records: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Return error message if we can't create records
            return html.Div([
                html.Div([
                    dbc.Row([
                        dbc.Col(html.H5(title, className="mb-0"), width="auto"),
                        dbc.Col(width="auto", className="ms-auto")
                    ], className="d-flex align-items-center"),
                ], className="mb-3"),
                html.Div([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    html.Span(f"Error creating table data: {str(e)}")
                ], className="alert alert-danger")
            ])
        
        # Create column definitions for the table
        # Group month columns by month with a merged header
        months_by_name = {}
        for col in month_columns:
            match = month_pattern.match(str(col))
            if match:
                month = match.group(1)
                if month not in months_by_name:
                    months_by_name[month] = []
                months_by_name[month].append(col)
        
        # Create column definitions with header groups
        table_columns = []
        
        # Add metadata columns
        for col in ['Asset', 'block_number', 'staircase', 'apartment']:
            if col in table_df.columns:
                # Use friendly names for the headers
                friendly_names = {
                    'Asset': 'Activo',
                    'block_number': 'Bloque',
                    'staircase': 'Escalera',
                    'apartment': 'Apartamento'
                }
                table_columns.append({
                    "name": friendly_names.get(col, col),
                    "id": col
                })
        
        # Add month columns grouped by month
        month_order = sorted(months_by_name.keys())
        for month in month_order:
            columns_for_month = sorted(months_by_name[month])
            
            for col in columns_for_month:
                match = month_pattern.match(str(col))
                if match:
                    month_str = match.group(1)
                    consumption_type = match.group(2)
                    
                    # Make a nicer display name
                    import datetime
                    try:
                        month_date = datetime.datetime.strptime(month_str, '%Y-%m')
                        month_display = month_date.strftime('%b %Y')  # e.g., "Jan 2023"
                    except:
                        month_display = month_str
                    
                    table_columns.append({
                        "name": [month_display, consumption_type],
                        "id": col
                    })
        
        print(f"[DEBUG] create_monthly_readings_table - Created {len(table_columns)} column definitions")
        
        # Create table with try/except for robustness
        try:
            table = dash_table.DataTable(
                id='monthly-readings-table-interactive',
                columns=table_columns,
                data=table_records,
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
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
                row_selectable=False,
                row_deletable=False,
                merge_duplicate_headers=True
            )
            print(f"[DEBUG] create_monthly_readings_table - Table component created successfully")
        except Exception as e:
            print(f"[ERROR] create_monthly_readings_table - Error creating DataTable: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Return error message if we can't create the table
            return html.Div([
                html.Div([
                    dbc.Row([
                        dbc.Col(html.H5(title, className="mb-0"), width="auto"),
                        dbc.Col(width="auto", className="ms-auto")
                    ], className="d-flex align-items-center"),
                ], className="mb-3"),
                html.Div([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    html.Span(f"Error creating table component: {str(e)}")
                ], className="alert alert-danger")
            ])
        
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
        
        # If we have multiple consumption types, add a legend
        legend_component = html.Div()
        try:
            if consumption_types and len(consumption_types) > 1:
                legend_items = []
                for consumption_type in sorted(consumption_types):
                    if consumption_type != 'Sin Datos' and consumption_type != '':
                        color = consumption_type_colors.get(consumption_type, 'rgba(200, 200, 200, 0.3)')
                        legend_items.append(
                            html.Div([
                                html.Span(className="legend-color", style={
                                    "display": "inline-block", 
                                    "width": "15px", 
                                    "height": "15px", 
                                    "backgroundColor": color,
                                    "marginRight": "5px",
                                    "verticalAlign": "middle",
                                    "border": "1px solid rgba(0,0,0,0.1)"
                                }),
                                html.Span(consumption_type, style={"verticalAlign": "middle"})
                            ], className="legend-item me-3")
                        )
                
                if legend_items:
                    legend_component = html.Div([
                        html.Hr(),
                        html.Div([
                            html.Span("Leyenda de tipos de consumo:", className="me-2 fw-bold"),
                            html.Div(legend_items, style={"display": "inline-flex", "flexWrap": "wrap"})
                        ], className="mt-2 mb-3")
                    ])
                    print(f"[DEBUG] create_monthly_readings_table - Created legend with {len(legend_items)} items")
        except Exception as e:
            print(f"[ERROR] create_monthly_readings_table - Error creating legend: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Don't show legend if there's an error
            legend_component = html.Div()
        
        # Return the final component
        final_component = html.Div([
            header,
            legend_component,
            table
        ])
        print(f"[DEBUG] create_monthly_readings_table - Created final component structure")
        return final_component
        
    except Exception as e:
        print(f"[ERROR] create_monthly_readings_table - Fatal error in table creation: {str(e)}")
        import traceback
        print(traceback.format_exc())
        # Return error message if there's any exception
        return html.Div([
            html.Div([
                dbc.Row([
                    dbc.Col(html.H5(title, className="mb-0"), width="auto"),
                    dbc.Col(width="auto", className="ms-auto")
                ], className="d-flex align-items-center"),
            ], className="mb-3"),
            html.Div([
                html.I(className="fas fa-exclamation-triangle me-2"),
                html.Span(f"Error general al crear la tabla: {str(e)}")
            ], className="alert alert-danger")
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

