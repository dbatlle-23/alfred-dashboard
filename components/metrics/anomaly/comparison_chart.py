# components/metrics/anomaly/comparison_chart.py
import plotly.graph_objects as go
from dash import html, dcc
import dash_bootstrap_components as dbc

def create_anomaly_comparison_chart(data_result, title="Comparación de Lecturas Originales vs. Corregidas"):
    """
    Crea un gráfico que compara lecturas originales y corregidas, resaltando anomalías
    
    Args:
        data_result: Resultado del procesamiento de anomalías
        title: Título del gráfico
        
    Returns:
        Componente Dash con el gráfico
    """
    # Extraer datos
    original_data = data_result.get('original')
    corrected_data = data_result.get('corrected')
    anomalies = data_result.get('anomalies', [])
    
    # Verificar si hay datos para visualizar
    if original_data is None or original_data.empty:
        return html.Div("No hay datos disponibles para visualizar", className="text-center text-muted my-5")
    
    # Crear figura
    fig = go.Figure()
    
    # Determinar columna de valor
    value_col = 'consumption' if 'consumption' in original_data.columns else 'value'
    
    # Añadir datos originales
    fig.add_trace(go.Scatter(
        x=original_data['date'],
        y=original_data[value_col],
        mode='lines+markers',
        name='Datos Originales',
        line=dict(color='blue', width=1),
        marker=dict(size=5)
    ))
    
    # Añadir datos corregidos si están disponibles
    if 'corrected_value' in corrected_data.columns:
        fig.add_trace(go.Scatter(
            x=corrected_data['date'],
            y=corrected_data['corrected_value'],
            mode='lines+markers',
            name='Datos Corregidos',
            line=dict(color='green', width=1),
            marker=dict(size=5)
        ))
    
    # Resaltar anomalías
    for anomaly in anomalies:
        # Convertir fecha a datetime si es string
        anomaly_date = anomaly['date']
        if isinstance(anomaly_date, str):
            from datetime import datetime
            anomaly_date = datetime.fromisoformat(anomaly_date.replace('Z', '+00:00'))
        
        # Añadir marcador para la anomalía
        fig.add_trace(go.Scatter(
            x=[anomaly_date],
            y=[anomaly['current_value']],
            mode='markers',
            name=f"Anomalía: {anomaly['type']}",
            marker=dict(
                color='red',
                size=10,
                symbol='x'
            ),
            hoverinfo='text',
            hovertext=f"Tipo: {anomaly['type']}<br>Valor anterior: {anomaly['previous_value']}<br>Valor actual: {anomaly['current_value']}"
        ))
    
    # Configurar layout
    fig.update_layout(
        title=title,
        xaxis_title="Fecha",
        yaxis_title="Valor",
        legend_title="Tipo de Datos",
        hovermode="closest"
    )
    
    # Crear componente
    return html.Div([
        dbc.Card([
            dbc.CardHeader(title),
            dbc.CardBody([
                dcc.Graph(
                    figure=fig,
                    config={'displayModeBar': True}
                )
            ])
        ])
    ])