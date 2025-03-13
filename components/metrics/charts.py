import plotly.express as px
import plotly.graph_objects as go
from config.metrics_config import CHART_CONFIG
import pandas as pd

def _limit_bar_width(fig, num_bars):
    """
    Helper function to limit the width of bars in bar charts with few bars.
    
    Args:
        fig (plotly.graph_objects.Figure): The figure to modify
        num_bars (int): Number of bars in the chart
        
    Returns:
        plotly.graph_objects.Figure: The modified figure
    """
    # Only apply width limitation if there are few bars
    if num_bars <= 6:
        # For bar charts with few bars, set a custom width
        # The width decreases as the number of bars decreases
        # but never exceeds 0.3 (30% of the available space)
        for trace in fig.data:
            if trace.type == 'bar':
                # Calculate width based on number of bars
                width = min(0.3, 0.7 / (7 - num_bars))
                # Apply the width to the trace
                trace.width = width
    
    return fig

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

    # Create bar chart with px.bar
    fig = px.bar(
        df,
        x=group_column,
        y='consumption',
        title=title,
        labels={group_column: 'Categoría', 'consumption': 'Consumo'},
        color_discrete_sequence=['royalblue']
    )
    
    # Limit bar width for better aesthetics
    fig = _limit_bar_width(fig, len(df))
    
    # Update layout with bargap for better aesthetics
    fig.update_layout(
        bargap=0.3,
        **CHART_CONFIG
    )
    
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
    
    # Create bar chart with px.bar
    fig = px.bar(
        grouped_df,
        x=group_column,
        y='consumption',
        title=title,
        labels={group_column: 'Categoría', 'consumption': 'Consumo Total'},
        color_discrete_sequence=['royalblue']
    )
    
    # Limit bar width for better aesthetics
    fig = _limit_bar_width(fig, len(grouped_df))
    
    # Update layout with bargap for better aesthetics
    fig.update_layout(
        bargap=0.3,
        **CHART_CONFIG
    )
    
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
    # Si no hay datos, mostrar un mensaje
    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Verificar si existen las columnas necesarias
    if 'month' not in df.columns or 'total_consumption' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Error en los datos: faltan columnas requeridas",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Crear el gráfico de barras de la forma más simple posible
    fig = go.Figure()
    
    fig.add_trace(
        go.Bar(
            x=df['month'],
            y=df['total_consumption'],
            marker_color='royalblue',
            name='Consumo Total'
        )
    )
    
    # Configuración básica
    fig.update_layout(
        title=title,
        xaxis_title="Mes",
        yaxis_title="Consumo Total",
        height=400,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
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
    # Si no hay datos, mostrar un mensaje
    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Verificar si existen las columnas necesarias
    if 'month' not in df.columns or 'average_consumption' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Error en los datos: faltan columnas requeridas",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Crear el gráfico de línea de la forma más simple posible
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=df['month'],
            y=df['average_consumption'],
            mode='lines+markers',
            marker=dict(size=8),
            line=dict(color='green', width=2),
            name='Consumo Promedio'
        )
    )
    
    # Configuración básica
    fig.update_layout(
        title=title,
        xaxis_title="Mes",
        yaxis_title="Consumo Promedio",
        height=400,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig
