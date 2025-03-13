import plotly.express as px
import plotly.graph_objects as go
from config.metrics_config import CHART_CONFIG
import pandas as pd

def create_time_series_chart(df, color_column=None, title="Evolución temporal del consumo"):
    """Creates a time series chart from the given DataFrame."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title, **CHART_CONFIG)
        return fig

    # Check if 'consumption' column exists, if not, try to use 'value'
    y_column = 'consumption'
    if y_column not in df.columns and 'value' in df.columns:
        y_column = 'value'

    fig = px.line(
        df,
        x='date',
        y=y_column,
        color=color_column,
        title=title,
        labels={'date': 'Fecha', y_column: 'Consumo'}
    )
    fig.update_layout(**CHART_CONFIG)
    return fig

def create_bar_chart(df, group_column, title="Comparativa de consumo"):
    """Creates a bar chart from the given DataFrame."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title, **CHART_CONFIG)
        return fig

    fig = px.bar(
        df,
        x=group_column,
        y='consumption',
        title=title,
        labels={group_column: 'Categoría', 'consumption': 'Consumo'}
    )
    fig.update_layout(**CHART_CONFIG)
    return fig

def create_consumption_comparison_chart(df, group_column, title="Comparativa de consumo"):
    """Creates a comparison chart for consumption data."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title, **CHART_CONFIG)
        return fig

    grouped_df = df.groupby(group_column)['consumption'].sum().reset_index()
    fig = px.bar(
        grouped_df,
        x=group_column,
        y='consumption',
        title=title,
        labels={group_column: 'Categoría', 'consumption': 'Consumo Total'}
    )
    fig.update_layout(**CHART_CONFIG)
    return fig

def create_consumption_trend_chart(df, time_period='M', group_column=None, title="Tendencias de consumo"):
    """Creates a trend chart for consumption data."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title, **CHART_CONFIG)
        return fig

    # Group by date and optional column
    if group_column:
        grouped = df.groupby([pd.Grouper(key='date', freq=time_period), group_column])['consumption'].sum().reset_index()
        fig = px.line(
            grouped,
            x='date',
            y='consumption',
            color=group_column,
            title=title,
            labels={'date': 'Fecha', 'consumption': 'Consumo'}
        )
    else:
        grouped = df.groupby(pd.Grouper(key='date', freq=time_period))['consumption'].sum().reset_index()
        fig = px.line(
            grouped,
            x='date',
            y='consumption',
            title=title,
            labels={'date': 'Fecha', 'consumption': 'Consumo'}
        )

    fig.update_layout(**CHART_CONFIG)
    return fig

def create_consumption_distribution_chart(df, group_column, title="Distribución de consumo"):
    """Creates a distribution chart for consumption data."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title, **CHART_CONFIG)
        return fig

    grouped_df = df.groupby(group_column)['consumption'].sum().reset_index()
    fig = px.pie(
        grouped_df,
        values='consumption',
        names=group_column,
        title=title
    )
    fig.update_layout(**CHART_CONFIG)
    return fig

def create_heatmap(df, title="Mapa de calor de consumo"):
    """Creates a heatmap for consumption data."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title, **CHART_CONFIG)
        return fig

    # Pivot the data for the heatmap
    pivot_df = df.pivot_table(
        values='consumption',
        index=pd.Grouper(key='date', freq='M'),
        columns='asset_id',
        aggfunc='sum'
    )

    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index.strftime('%Y-%m'),
        colorscale='RdYlBu_r'
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Asset ID",
        yaxis_title="Fecha",
        **CHART_CONFIG
    )
    return fig

def create_monthly_totals_chart(df, title="Total de Consumo por Mes"):
    """
    Creates a bar chart showing total consumption by month.
    
    Args:
        df (pd.DataFrame): DataFrame with monthly consumption data
        title (str): Chart title
        
    Returns:
        plotly.graph_objects.Figure: The monthly totals chart
    """
    print("=====================================================")
    print("DEBUGGING MONTHLY TOTALS CHART - FUNCTION CALLED")
    print("=====================================================")
    print(f"[DEBUG] create_monthly_totals_chart - Starting")
    print(f"[DEBUG] create_monthly_totals_chart - DataFrame type: {type(df)}")
    
    if df is None or df.empty:
        print(f"[DEBUG] create_monthly_totals_chart - DataFrame is empty or None")
        if df is None:
            print(f"[DEBUG] create_monthly_totals_chart - DataFrame is None")
        elif df.empty:
            print(f"[DEBUG] create_monthly_totals_chart - DataFrame is empty")
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title, **CHART_CONFIG)
        return fig
    
    print(f"[DEBUG] create_monthly_totals_chart - DataFrame columns: {df.columns.tolist()}")
    print(f"[DEBUG] create_monthly_totals_chart - DataFrame shape: {df.shape}")
    
    # Check if required columns exist
    if 'month' not in df.columns or 'total_consumption' not in df.columns:
        print(f"[ERROR] create_monthly_totals_chart - Required columns missing. Available columns: {df.columns.tolist()}")
        fig = go.Figure()
        fig.add_annotation(
            text="Error en los datos: faltan columnas requeridas",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title, **CHART_CONFIG)
        return fig
    
    # Create the bar chart
    fig = go.Figure()
    
    fig.add_trace(
        go.Bar(
            x=df['month'],
            y=df['total_consumption'],
            marker_color='royalblue',
            name='Consumo Total'
        )
    )
    
    # Set layout
    fig.update_layout(
        title=title,
        xaxis=dict(
            title='Mes',
            tickformat='%b %Y'
        ),
        yaxis=dict(
            title='Consumo Total'
        ),
        **CHART_CONFIG
    )
    
    print(f"[DEBUG] create_monthly_totals_chart - Chart created successfully")
    return fig

def create_monthly_averages_chart(df, title="Promedio de Consumo por Mes"):
    """
    Creates a line chart showing average consumption by month.
    
    Args:
        df (pd.DataFrame): DataFrame with monthly consumption data
        title (str): Chart title
        
    Returns:
        plotly.graph_objects.Figure: The monthly averages chart
    """
    print(f"[DEBUG] create_monthly_averages_chart - Starting")
    
    if df is None or df.empty:
        print(f"[DEBUG] create_monthly_averages_chart - DataFrame is empty or None")
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title, **CHART_CONFIG)
        return fig
    
    print(f"[DEBUG] create_monthly_averages_chart - DataFrame columns: {df.columns.tolist()}")
    print(f"[DEBUG] create_monthly_averages_chart - DataFrame shape: {df.shape}")
    
    # Check if required columns exist
    if 'month' not in df.columns or 'average_consumption' not in df.columns:
        print(f"[ERROR] create_monthly_averages_chart - Required columns missing. Available columns: {df.columns.tolist()}")
        fig = go.Figure()
        fig.add_annotation(
            text="Error en los datos: faltan columnas requeridas",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title, **CHART_CONFIG)
        return fig
    
    # Create the line chart
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=df['month'],
            y=df['average_consumption'],
            mode='lines+markers',
            line=dict(color='green', width=2),
            marker=dict(size=8),
            name='Consumo Promedio'
        )
    )
    
    # Set layout
    fig.update_layout(
        title=title,
        xaxis=dict(
            title='Mes',
            tickformat='%b %Y'
        ),
        yaxis=dict(
            title='Consumo Promedio'
        ),
        **CHART_CONFIG
    )
    
    print(f"[DEBUG] create_monthly_averages_chart - Chart created successfully")
    return fig
