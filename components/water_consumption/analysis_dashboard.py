from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

def create_water_analysis_dashboard(data, config=None):
    """
    Create a dashboard for water consumption analysis.
    
    Args:
        data (dict): Dictionary containing water consumption data
            {
                'daily_data': pandas DataFrame with daily consumption,
                'hourly_data': pandas DataFrame with hourly consumption,
                'monthly_data': pandas DataFrame with monthly aggregation,
                'anomalies': list of detected anomalies,
                'total_consumption': float,
                'average_daily': float,
                'peak_hours': list of strings,
                'num_anomalies': int
            }
        config (dict, optional): Configuration options for the dashboard
            
    Returns:
        dash component: The dashboard component
    """
    if not data or not isinstance(data, dict):
        return html.Div("No hay datos disponibles para el análisis", className="text-center p-4 text-muted")
    
    # Default config
    default_config = {
        'chart_height': 400,
        'primary_color': '#007bff',
        'secondary_color': '#6c757d',
        'danger_color': '#dc3545',
        'success_color': '#28a745',
        'show_hourly': True,
        'show_anomalies': True
    }
    
    # Merge configs
    if config and isinstance(config, dict):
        dashboard_config = {**default_config, **config}
    else:
        dashboard_config = default_config
    
    # Extract data
    total_consumption = data.get('total_consumption', 0)
    average_daily = data.get('average_daily', 0)
    peak_hours = data.get('peak_hours', [])
    num_anomalies = data.get('num_anomalies', 0)
    
    # Format for display
    formatted_total = f"{total_consumption:,.1f} m³"
    formatted_average = f"{average_daily:.1f} m³/día"
    
    # Create the dashboard layout
    dashboard = html.Div([
        # Key metrics row
        dbc.Row([
            # Total consumption
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Volumen Total", className="card-title"),
                        html.H2(formatted_total, className="text-primary"),
                        html.P("Consumo total en el período seleccionado")
                    ])
                ])
            ),
            
            # Average consumption
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Consumo Promedio", className="card-title"),
                        html.H2(formatted_average, className="text-primary"),
                        html.P("Promedio diario en el período")
                    ])
                ])
            ),
            
            # Peak hours
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Horas Pico", className="card-title"),
                        html.H2(", ".join(peak_hours) if peak_hours else "N/A", 
                               className="text-primary"),
                        html.P("Franjas horarias de mayor consumo")
                    ])
                ])
            ),
            
            # Anomalies
            dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Anomalías", className="card-title"),
                        html.H2(
                            f"{num_anomalies} detectadas" if num_anomalies > 0 else "Ninguna",
                            className="text-danger" if num_anomalies > 0 else "text-success"
                        ),
                        html.P("Posibles consumos anómalos")
                    ])
                ])
            )
        ], className="mb-4"),
        
        # Charts row
        dbc.Row([
            # Left column - Time series and monthly
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Evolución del Consumo Diario"),
                    dbc.CardBody([
                        create_daily_consumption_chart(data, dashboard_config)
                    ])
                ], className="mb-4"),
                
                dbc.Card([
                    dbc.CardHeader("Consumo Mensual"),
                    dbc.CardBody([
                        create_monthly_consumption_chart(data, dashboard_config)
                    ])
                ])
            ], width=6),
            
            # Right column - Distribution and hourly
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Distribución del Consumo"),
                    dbc.CardBody([
                        create_consumption_distribution_chart(data, dashboard_config)
                    ])
                ], className="mb-4"),
                
                dbc.Card([
                    dbc.CardHeader("Consumo por Hora del Día"),
                    dbc.CardBody([
                        create_hourly_consumption_chart(data, dashboard_config) 
                        if dashboard_config['show_hourly'] else 
                        html.Div("Datos horarios no disponibles", className="text-center p-4 text-muted")
                    ])
                ])
            ], width=6)
        ], className="mb-4"),
        
        # Anomalies section (if there are any)
        html.Div([
            dbc.Card([
                dbc.CardHeader("Detección de Anomalías"),
                dbc.CardBody([
                    create_anomaly_chart(data, dashboard_config) if dashboard_config['show_anomalies'] else html.Div()
                ])
            ])
        ], className="mb-4", style={'display': 'block' if num_anomalies > 0 else 'none'})
    ])
    
    return dashboard

def create_daily_consumption_chart(data, config):
    """Create a chart showing daily water consumption over time."""
    # Extract daily data
    daily_data = data.get('daily_data', pd.DataFrame())
    anomalies = data.get('anomalies', [])
    
    if daily_data.empty:
        return html.Div("Datos diarios no disponibles", className="text-center p-4 text-muted")
    
    # Create the figure
    fig = go.Figure()
    
    # Add the daily consumption line
    fig.add_trace(go.Scatter(
        x=daily_data.get('date', []),
        y=daily_data.get('consumption', []),
        mode='lines+markers',
        name='Consumo diario',
        line=dict(color=config['primary_color'], width=2),
        marker=dict(size=6)
    ))
    
    # Add anomaly points if there are any
    if anomalies and len(anomalies) > 0:
        anomaly_dates = [a['date'] for a in anomalies]
        anomaly_values = [a['value'] for a in anomalies]
        
        fig.add_trace(go.Scatter(
            x=anomaly_dates,
            y=anomaly_values,
            mode='markers',
            name='Anomalías',
            marker=dict(
                color=config['danger_color'],
                size=10,
                symbol='circle',
                line=dict(width=2, color='white')
            )
        ))
    
    # Update layout
    fig.update_layout(
        title='Evolución del Consumo Diario',
        xaxis_title='Fecha',
        yaxis_title='Consumo (m³)',
        height=config['chart_height'],
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=40, b=40)
    )
    
    return dcc.Graph(figure=fig)

def create_monthly_consumption_chart(data, config):
    """Create a chart showing monthly water consumption."""
    # Extract monthly data
    monthly_data = data.get('monthly_data', pd.DataFrame())
    
    if monthly_data.empty:
        return html.Div("Datos mensuales no disponibles", className="text-center p-4 text-muted")
    
    # Create the figure
    fig = go.Figure()
    
    # Add the monthly consumption bars
    fig.add_trace(go.Bar(
        x=monthly_data.get('month', []),
        y=monthly_data.get('consumption', []),
        name='Consumo mensual',
        marker_color=config['primary_color']
    ))
    
    # Add a target line if available
    if 'target' in monthly_data.columns:
        fig.add_trace(go.Scatter(
            x=monthly_data['month'],
            y=monthly_data['target'],
            mode='lines',
            name='Objetivo',
            line=dict(color=config['success_color'], width=2, dash='dash')
        ))
    
    # Update layout
    fig.update_layout(
        title='Consumo Mensual',
        xaxis_title='Mes',
        yaxis_title='Consumo (m³)',
        height=config['chart_height'],
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=40, b=40)
    )
    
    return dcc.Graph(figure=fig)

def create_consumption_distribution_chart(data, config):
    """Create a chart showing consumption distribution by day of week."""
    # Extract distribution data
    daily_data = data.get('daily_data', pd.DataFrame())
    
    if daily_data.empty or 'date' not in daily_data.columns or 'consumption' not in daily_data.columns:
        return html.Div("Datos de distribución no disponibles", className="text-center p-4 text-muted")
    
    # Calculate day of week distribution if not already in the data
    if 'day_of_week' not in daily_data.columns and 'date' in daily_data.columns:
        # Convert date to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(daily_data['date']):
            daily_data['date'] = pd.to_datetime(daily_data['date'])
        
        # Extract day of week
        daily_data['day_of_week'] = daily_data['date'].dt.day_name()
    
    # If we still don't have day_of_week, return an error
    if 'day_of_week' not in daily_data.columns:
        return html.Div("No se puede calcular la distribución por día", className="text-center p-4 text-muted")
    
    # Calculate average consumption by day of week
    day_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    english_day_map = {
        'Monday': 'Lunes', 
        'Tuesday': 'Martes', 
        'Wednesday': 'Miércoles', 
        'Thursday': 'Jueves', 
        'Friday': 'Viernes', 
        'Saturday': 'Sábado', 
        'Sunday': 'Domingo'
    }
    
    # Map English day names to Spanish if needed
    if daily_data['day_of_week'].iloc[0] in english_day_map:
        daily_data['day_of_week'] = daily_data['day_of_week'].map(english_day_map)
    
    # Calculate average by day
    daily_avg = daily_data.groupby('day_of_week')['consumption'].mean().reset_index()
    
    # Ensure days are in correct order
    daily_avg['day_order'] = daily_avg['day_of_week'].map({day: i for i, day in enumerate(day_order)})
    daily_avg = daily_avg.sort_values('day_order')
    
    # Create the figure
    fig = go.Figure()
    
    # Add the day of week bars
    fig.add_trace(go.Bar(
        x=daily_avg['day_of_week'],
        y=daily_avg['consumption'],
        name='Consumo promedio',
        marker_color=config['primary_color']
    ))
    
    # Update layout
    fig.update_layout(
        title='Distribución por Día de la Semana',
        xaxis_title='Día',
        yaxis_title='Consumo Promedio (m³)',
        height=config['chart_height'],
        margin=dict(l=40, r=40, t=40, b=40)
    )
    
    return dcc.Graph(figure=fig)

def create_hourly_consumption_chart(data, config):
    """Create a chart showing hourly consumption patterns."""
    # Extract hourly data
    hourly_data = data.get('hourly_data', pd.DataFrame())
    
    if hourly_data.empty:
        return html.Div("Datos horarios no disponibles", className="text-center p-4 text-muted")
    
    # Create the figure
    fig = go.Figure()
    
    # Add the hourly consumption line
    fig.add_trace(go.Scatter(
        x=hourly_data.get('hour', list(range(24))),
        y=hourly_data.get('consumption', []),
        mode='lines+markers',
        name='Consumo por hora',
        line=dict(color=config['primary_color'], width=2),
        marker=dict(size=6)
    ))
    
    # Update layout
    fig.update_layout(
        title='Patrón de Consumo por Hora',
        xaxis_title='Hora del Día',
        yaxis_title='Consumo Promedio (m³)',
        height=config['chart_height'],
        xaxis=dict(
            tickmode='array',
            tickvals=list(range(24)),
            ticktext=[f"{h}:00" for h in range(24)]
        ),
        margin=dict(l=40, r=40, t=40, b=40)
    )
    
    return dcc.Graph(figure=fig)

def create_anomaly_chart(data, config):
    """Create a chart highlighting anomalies in water consumption."""
    # Extract daily data and anomalies
    daily_data = data.get('daily_data', pd.DataFrame())
    anomalies = data.get('anomalies', [])
    
    if daily_data.empty or not anomalies:
        return html.Div("No se detectaron anomalías", className="text-center p-4 text-muted")
    
    # Create the figure
    fig = go.Figure()
    
    # Add the daily consumption line
    fig.add_trace(go.Scatter(
        x=daily_data.get('date', []),
        y=daily_data.get('consumption', []),
        mode='lines',
        name='Consumo normal',
        line=dict(color=config['secondary_color'], width=2)
    ))
    
    # Add anomaly points
    anomaly_dates = [a['date'] for a in anomalies]
    anomaly_values = [a['value'] for a in anomalies]
    
    fig.add_trace(go.Scatter(
        x=anomaly_dates,
        y=anomaly_values,
        mode='markers',
        name='Anomalías',
        marker=dict(
            color=config['danger_color'],
            size=12,
            symbol='circle',
            line=dict(width=2, color='white')
        )
    ))
    
    # Update layout
    fig.update_layout(
        title='Detección de Anomalías en el Consumo',
        xaxis_title='Fecha',
        yaxis_title='Consumo (m³)',
        height=config['chart_height'],
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=40, b=40)
    )
    
    # Add a detailed explanation of anomalies
    anomaly_explanation = html.Div([
        html.H5("Análisis de Anomalías", className="mt-3"),
        html.P("Se han detectado las siguientes anomalías en el consumo de agua:"),
        html.Ul([
            html.Li([
                f"El día {a['date'].strftime('%d/%m/%Y') if isinstance(a['date'], (datetime, pd.Timestamp)) else a['date']}: ",
                f"Consumo de {a['value']:.2f} m³ ",
                f"({a.get('percentage', 0):.1f}% {a.get('direction', 'superior')} a lo esperado)"
            ]) for a in anomalies
        ]),
        html.P([
            html.Strong("Posibles causas: "), 
            "Fugas en tuberías, consumo inusual, mal funcionamiento de equipos, o error en la medición."
        ]),
        html.P([
            html.Strong("Recomendación: "), 
            "Verificar el sistema de agua en las fechas indicadas y realizar una inspección si el patrón persiste."
        ])
    ])
    
    return html.Div([
        dcc.Graph(figure=fig),
        anomaly_explanation
    ]) 