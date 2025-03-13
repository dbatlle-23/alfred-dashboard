import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

# Crear un DataFrame de ejemplo con datos ficticios para pruebas
def create_sample_data():
    # Obtener fechas de inicio y fin
    end = pd.Timestamp.now()
    start = end - pd.DateOffset(months=6)
    
    # Generar fechas mensuales
    date_range = pd.date_range(start=start, end=end, freq='MS')
    
    # Crear DataFrame de ejemplo
    sample_data = {
        'month': [d.strftime('%Y-%m') for d in date_range],
        'total_consumption': [100 * (i+1) for i in range(len(date_range))],
        'average_consumption': [50 * (i+1) for i in range(len(date_range))],
        'min_consumption': [10 * (i+1) for i in range(len(date_range))],
        'max_consumption': [200 * (i+1) for i in range(len(date_range))],
        'asset_count': [5 for _ in range(len(date_range))],
        'date': date_range
    }
    
    sample_df = pd.DataFrame(sample_data)
    print(f"Created sample DataFrame with {len(sample_df)} rows")
    print(f"Sample data: {sample_df.head().to_dict()}")
    
    return sample_df

# Crear un gráfico de barras para el total de consumo por mes
def create_monthly_totals_chart(df):
    print(f"Creating monthly totals chart with DataFrame of shape {df.shape}")
    print(f"DataFrame columns: {df.columns.tolist()}")
    
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
        title="Total de Consumo por Mes",
        xaxis=dict(
            title='Mes',
            tickformat='%b %Y'
        ),
        yaxis=dict(
            title='Consumo Total'
        )
    )
    
    # Guardar el gráfico como HTML
    fig.write_html("monthly_totals_chart.html")
    print("Chart saved as monthly_totals_chart.html")

# Crear un gráfico de líneas para el promedio de consumo por mes
def create_monthly_averages_chart(df):
    print(f"Creating monthly averages chart with DataFrame of shape {df.shape}")
    print(f"DataFrame columns: {df.columns.tolist()}")
    
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
        title="Promedio de Consumo por Mes",
        xaxis=dict(
            title='Mes',
            tickformat='%b %Y'
        ),
        yaxis=dict(
            title='Consumo Promedio'
        )
    )
    
    # Guardar el gráfico como HTML
    fig.write_html("monthly_averages_chart.html")
    print("Chart saved as monthly_averages_chart.html")

# Ejecutar las pruebas
if __name__ == "__main__":
    print("Starting test...")
    
    # Crear datos de ejemplo
    df = create_sample_data()
    
    # Crear gráficos
    create_monthly_totals_chart(df)
    create_monthly_averages_chart(df)
    
    print("Test completed successfully!") 