import pandas as pd
import json
from utils.metrics.data_processing import generate_monthly_consumption_summary
from components.metrics.charts import create_monthly_totals_chart, create_monthly_averages_chart
from components.metrics.tables import create_monthly_summary_table

# Crear un DataFrame de ejemplo con datos ficticios para pruebas
def create_sample_data():
    # Obtener fechas de inicio y fin
    end = pd.Timestamp.now()
    start = end - pd.DateOffset(months=6)
    
    # Generar fechas mensuales
    date_range = pd.date_range(start=start, end=end, freq='MS')
    
    # Crear DataFrame de ejemplo
    sample_data = {
        'date': date_range,
        'consumption': [100 * (i+1) for i in range(len(date_range))],
        'asset_id': ['asset1' for _ in range(len(date_range))],
        'consumption_type': ['water' for _ in range(len(date_range))],
        'client_id': ['client1' for _ in range(len(date_range))],
        'project_id': ['project1' for _ in range(len(date_range))]
    }
    
    sample_df = pd.DataFrame(sample_data)
    print(f"Created sample DataFrame with {len(sample_df)} rows")
    print(f"Sample data: {sample_df.head().to_dict()}")
    
    return sample_df

# Simular el flujo de datos a través de los callbacks
def simulate_callbacks():
    print("Simulating callbacks...")
    
    # Crear datos de ejemplo
    df = create_sample_data()
    
    # Convertir a JSON (simular el almacenamiento en metrics-data-store)
    json_data = df.to_json(orient='records', date_format='iso')
    print(f"Converted DataFrame to JSON with length {len(json_data)}")
    
    # Simular el callback update_monthly_totals_chart
    print("\nSimulating update_monthly_totals_chart callback...")
    client_id = 'client1'
    project_id = 'project1'
    consumption_tags = ['water']
    start_date = None
    end_date = None
    
    # Convertir JSON a DataFrame
    df_from_json = pd.DataFrame(json.loads(json_data))
    print(f"Loaded DataFrame from JSON with {len(df_from_json)} rows")
    
    # Generar resumen mensual
    monthly_summary = generate_monthly_consumption_summary(df_from_json, start_date, end_date)
    print(f"Generated monthly summary with {len(monthly_summary)} rows")
    print(f"Monthly summary columns: {monthly_summary.columns.tolist()}")
    
    # Crear gráfico de totales mensuales
    totals_chart = create_monthly_totals_chart(monthly_summary)
    print("Created monthly totals chart")
    
    # Crear gráfico de promedios mensuales
    averages_chart = create_monthly_averages_chart(monthly_summary)
    print("Created monthly averages chart")
    
    # Crear tabla de resumen mensual
    summary_table = create_monthly_summary_table(monthly_summary)
    print("Created monthly summary table")
    
    print("\nCallback simulation completed successfully!")

# Ejecutar la simulación
if __name__ == "__main__":
    print("Starting callback simulation...")
    simulate_callbacks()
    print("Simulation completed!") 