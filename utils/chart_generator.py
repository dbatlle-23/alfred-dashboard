import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional
import numpy as np

def create_time_series_chart(df: pd.DataFrame, 
                            x_column: str = 'date', 
                            y_column: str = 'value', 
                            color_column: Optional[str] = None,
                            title: str = 'Evolución temporal del consumo',
                            x_title: str = 'Fecha',
                            y_title: str = 'Consumo',
                            height: int = 500) -> Dict:
    """
    Crea un gráfico de líneas para mostrar la evolución temporal del consumo.
    
    Args:
        df: DataFrame con los datos
        x_column: Nombre de la columna para el eje X
        y_column: Nombre de la columna para el eje Y
        color_column: Nombre de la columna para el color de las líneas
        title: Título del gráfico
        x_title: Título del eje X
        y_title: Título del eje Y
        height: Altura del gráfico en píxeles
        
    Returns:
        Figura de Plotly
    """
    if df.empty:
        # Crear un gráfico vacío con mensaje
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles para mostrar",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title=title,
            xaxis_title=x_title,
            yaxis_title=y_title,
            height=height
        )
        return fig
    
    # Crear el gráfico de líneas
    if color_column:
        fig = px.line(df, x=x_column, y=y_column, color=color_column, 
                     title=title, height=height)
    else:
        fig = px.line(df, x=x_column, y=y_column, 
                     title=title, height=height)
    
    # Personalizar el diseño
    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend_title_text='',
        hovermode='closest'
    )
    
    # Mejorar el formato de las fechas en el eje X
    fig.update_xaxes(
        tickformat="%d-%m-%Y",
        tickangle=-45
    )
    
    return fig

def create_bar_chart(df: pd.DataFrame, 
                    x_column: str, 
                    y_column: str = 'value', 
                    color_column: Optional[str] = None,
                    title: str = 'Comparativa de consumo',
                    x_title: str = '',
                    y_title: str = 'Consumo',
                    height: int = 500) -> Dict:
    """
    Crea un gráfico de barras para comparar consumos.
    
    Args:
        df: DataFrame con los datos
        x_column: Nombre de la columna para el eje X
        y_column: Nombre de la columna para el eje Y
        color_column: Nombre de la columna para el color de las barras
        title: Título del gráfico
        x_title: Título del eje X
        y_title: Título del eje Y
        height: Altura del gráfico en píxeles
        
    Returns:
        Figura de Plotly
    """
    if df.empty:
        # Crear un gráfico vacío con mensaje
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles para mostrar",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title=title,
            xaxis_title=x_title,
            yaxis_title=y_title,
            height=height
        )
        return fig
    
    # Crear el gráfico de barras
    if color_column:
        fig = px.bar(df, x=x_column, y=y_column, color=color_column, 
                    title=title, height=height)
    else:
        fig = px.bar(df, x=x_column, y=y_column, 
                    title=title, height=height)
    
    # Personalizar el diseño
    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend_title_text='',
        hovermode='closest'
    )
    
    return fig

def create_heatmap(df: pd.DataFrame, 
                  x_column: str, 
                  y_column: str, 
                  z_column: str = 'value',
                  title: str = 'Mapa de calor de consumo',
                  x_title: str = '',
                  y_title: str = '',
                  height: int = 500) -> Dict:
    """
    Crea un mapa de calor para visualizar patrones de consumo.
    
    Args:
        df: DataFrame con los datos
        x_column: Nombre de la columna para el eje X
        y_column: Nombre de la columna para el eje Y
        z_column: Nombre de la columna para los valores (intensidad del color)
        title: Título del gráfico
        x_title: Título del eje X
        y_title: Título del eje Y
        height: Altura del gráfico en píxeles
        
    Returns:
        Figura de Plotly
    """
    if df.empty:
        # Crear un gráfico vacío con mensaje
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles para mostrar",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title=title,
            xaxis_title=x_title,
            yaxis_title=y_title,
            height=height
        )
        return fig
    
    # Pivotar el DataFrame para crear el mapa de calor
    pivot_df = df.pivot_table(index=y_column, columns=x_column, values=z_column, aggfunc='mean')
    
    # Crear el mapa de calor
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale='Viridis',
        hoverongaps=False
    ))
    
    # Personalizar el diseño
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=height
    )
    
    return fig

def create_consumption_comparison_chart(df: pd.DataFrame, 
                                       group_column: str,
                                       title: str = 'Comparativa de consumo por tipo',
                                       height: int = 500) -> Dict:
    """
    Crea un gráfico de barras para comparar el consumo total por grupo.
    
    Args:
        df: DataFrame con los datos
        group_column: Nombre de la columna para agrupar (ej: 'consumption_type', 'asset_id', 'project_id')
        title: Título del gráfico
        height: Altura del gráfico en píxeles
        
    Returns:
        Figura de Plotly
    """
    if df.empty:
        # Crear un gráfico vacío con mensaje
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles para mostrar",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title=title,
            height=height
        )
        return fig
    
    # Asegurarse de que la columna de agrupación sea de tipo string
    df[group_column] = df[group_column].astype(str)
    
    # Determinar qué columna usar para los valores (consumption o value)
    value_column = 'consumption' if 'consumption' in df.columns else 'value'
    
    # Agrupar los datos por la columna especificada y sumar los valores
    grouped_df = df.groupby(group_column)[value_column].sum().reset_index()
    
    # Ordenar de mayor a menor
    grouped_df = grouped_df.sort_values(value_column, ascending=False)
    
    # Crear el gráfico de barras
    fig = px.bar(grouped_df, x=group_column, y=value_column, 
                title=title, height=height)
    
    # Personalizar el diseño
    fig.update_layout(
        xaxis_title='',
        yaxis_title='Consumo total',
        hovermode='closest'
    )
    
    return fig

def create_consumption_trend_chart(df: pd.DataFrame, 
                                 time_period: str = 'M',  # 'D' para diario, 'W' para semanal, 'M' para mensual
                                 group_column: Optional[str] = None,
                                 title: str = 'Tendencia de consumo',
                                 height: int = 500) -> Dict:
    """
    Crea un gráfico de líneas para mostrar la tendencia de consumo a lo largo del tiempo.
    
    Args:
        df: DataFrame con los datos
        time_period: Período de tiempo para agrupar ('D', 'W', 'M')
        group_column: Nombre de la columna para agrupar y colorear las líneas
        title: Título del gráfico
        height: Altura del gráfico en píxeles
        
    Returns:
        Figura de Plotly
    """
    if df.empty:
        # Crear un gráfico vacío con mensaje
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles para mostrar",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title=title,
            height=height
        )
        return fig
    
    # Asegurarse de que la columna de fecha es de tipo datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Crear una columna de período según el tiempo especificado
    if time_period == 'D':
        df['period'] = df['date']
        period_name = 'Diario'
    elif time_period == 'W':
        df['period'] = df['date'].dt.to_period('W').dt.start_time
        period_name = 'Semanal'
    else:  # 'M' por defecto
        df['period'] = df['date'].dt.to_period('M').dt.start_time
        period_name = 'Mensual'
    
    # Agrupar los datos por período y la columna de grupo si se especifica
    if group_column:
        grouped_df = df.groupby(['period', group_column])['value'].sum().reset_index()
        fig = px.line(grouped_df, x='period', y='value', color=group_column,
                     title=f"{title} - {period_name}", height=height)
    else:
        grouped_df = df.groupby('period')['value'].sum().reset_index()
        fig = px.line(grouped_df, x='period', y='value',
                     title=f"{title} - {period_name}", height=height)
    
    # Personalizar el diseño
    fig.update_layout(
        xaxis_title='Fecha',
        yaxis_title='Consumo',
        legend_title_text='',
        hovermode='closest'
    )
    
    # Mejorar el formato de las fechas en el eje X
    fig.update_xaxes(
        tickformat="%b %Y" if time_period == 'M' else "%d-%m-%Y",
        tickangle=-45
    )
    
    return fig

def create_consumption_distribution_chart(df: pd.DataFrame,
                                        group_column: str,
                                        title: str = 'Distribución de consumo',
                                        height: int = 500) -> Dict:
    """
    Crea un gráfico de pastel para mostrar la distribución del consumo.
    
    Args:
        df: DataFrame con los datos
        group_column: Nombre de la columna para agrupar (ej: 'consumption_type', 'asset_id', 'project_id')
        title: Título del gráfico
        height: Altura del gráfico en píxeles
        
    Returns:
        Figura de Plotly
    """
    if df.empty:
        # Crear un gráfico vacío con mensaje
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles para mostrar",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title=title,
            height=height
        )
        return fig
    
    # Agrupar los datos por la columna especificada y sumar los valores
    grouped_df = df.groupby(group_column)['value'].sum().reset_index()
    
    # Calcular el porcentaje
    total = grouped_df['value'].sum()
    grouped_df['percentage'] = (grouped_df['value'] / total * 100).round(1)
    
    # Crear etiquetas con porcentaje
    grouped_df['label'] = grouped_df.apply(
        lambda row: f"{row[group_column]}: {row['percentage']}%", axis=1
    )
    
    # Crear el gráfico de pastel
    fig = px.pie(grouped_df, values='value', names='label',
                title=title, height=height)
    
    # Personalizar el diseño
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        legend_title_text='',
        uniformtext_minsize=12,
        uniformtext_mode='hide'
    )
    
    return fig 