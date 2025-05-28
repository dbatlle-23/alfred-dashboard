import os
import pandas as pd
import numpy as np
import sys
import glob
from datetime import datetime
import pytest

# Agregar el directorio raíz del proyecto al path para importar módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.data_loader import load_asset_detail_data, get_project_for_asset

def test_analyze_asset_detail_data():
    """
    Test para analizar la estructura de los datos que se pasan al modal de detalle.
    Este test no modifica la aplicación, solo analiza los datos.
    """
    # Buscar un proyecto y un asset existente para usar en la prueba
    base_path = "data/analyzed_data"
    project_folders = [d for d in glob.glob(os.path.join(base_path, "*")) if os.path.isdir(d) and not os.path.basename(d).startswith(".")]
    
    if not project_folders:
        pytest.skip("No hay carpetas de proyecto disponibles para la prueba")
        
    # Usar el primer proyecto que encontremos
    project_folder = project_folders[0]
    project_id = os.path.basename(project_folder)
    
    # Buscar archivos CSV en la carpeta del proyecto
    csv_files = glob.glob(os.path.join(project_folder, "daily_readings_*.csv"))
    
    if not csv_files:
        pytest.skip(f"No hay archivos CSV en el proyecto {project_id}")
    
    # Extraer asset_id del primer archivo CSV
    csv_file = csv_files[0]
    filename = os.path.basename(csv_file)
    parts = filename.split("_")
    if len(parts) < 3:
        pytest.skip(f"Formato de archivo CSV no reconocido: {filename}")
        
    asset_id = parts[2]
    print(f"\nAnalizando datos para asset_id: {asset_id}, project_id: {project_id}")
    
    # Determinar un mes para el que hay datos
    df_sample = pd.read_csv(csv_file)
    if 'date' not in df_sample.columns:
        pytest.skip(f"El archivo CSV no tiene una columna 'date': {csv_file}")
        
    df_sample['date'] = pd.to_datetime(df_sample['date'])
    if df_sample.empty:
        pytest.skip(f"El archivo CSV está vacío: {csv_file}")
        
    # Obtener el mes más reciente para el que hay datos
    most_recent_date = df_sample['date'].max()
    month = most_recent_date.strftime('%Y-%m')
    print(f"Usando mes: {month}")
    
    # Cargar los datos detallados (igual que lo hace la aplicación)
    detail_data = load_asset_detail_data(
        project_id=project_id,
        asset_id=asset_id,
        consumption_tags=None,  # Usar None para cargar todos los tags disponibles
        month=month,
        jwt_token=None
    )
    
    # Verificar si se obtuvieron datos
    assert detail_data is not None, f"No se pudieron cargar datos para asset_id={asset_id}, project_id={project_id}, month={month}"
    assert not detail_data.empty, f"Se obtuvieron datos vacíos para asset_id={asset_id}, project_id={project_id}, month={month}"
    
    # Analizar la estructura de los datos
    print("\nEstructura de los datos:")
    print(f"Forma del DataFrame: {detail_data.shape}")
    print(f"Columnas: {detail_data.columns.tolist()}")
    
    # Identificar columnas numéricas
    numeric_cols = detail_data.select_dtypes(include=[np.number]).columns.tolist()
    print(f"\nColumnas numéricas: {numeric_cols}")
    
    # Identificar columnas que serían usadas para generar gráficos de consumo
    consumption_cols = [col for col in numeric_cols 
                        if col == 'value' or col.lower() == 'consumption' 
                        or col.lower().startswith('consumo')]
    print(f"\nColumnas de consumo que generarían gráficos: {consumption_cols}")
    
    # Verificar la razón por la que se generan múltiples gráficos
    if len(consumption_cols) > 1:
        print("\nSe generarían múltiples gráficos porque hay más de una columna de consumo")
        
        # Mostrar base_cols para ver si el filtro de columnas base es efectivo
        base_cols = set([col.split('_')[0].lower() for col in consumption_cols])
        print(f"Nombres base de columnas de consumo: {base_cols}")
        
        if len(base_cols) == 1:
            print("Las columnas tienen el mismo nombre base, por lo que solo se mostraría un gráfico")
        else:
            print("Las columnas tienen nombres base diferentes, por lo que se mostrarían múltiples gráficos")
    
    # Mostrar una muestra de los datos
    print("\nMuestra de los datos:")
    if 'date' in detail_data.columns:
        sample_cols = ['date'] + consumption_cols
    else:
        sample_cols = consumption_cols
        
    print(detail_data[sample_cols].head())
    
    # Análisis de evolución de valores para ver si tiene sentido mostrar múltiples gráficos
    print("\nAnálisis de evolución de valores:")
    for col in consumption_cols:
        if 'date' in detail_data.columns:
            detail_data = detail_data.sort_values('date')
        
        # Calcular diferencia entre lecturas consecutivas
        diff_values = detail_data[col].diff().dropna()
        
        print(f"Columna: {col}")
        print(f"  Valor mínimo: {detail_data[col].min()}")
        print(f"  Valor máximo: {detail_data[col].max()}")
        print(f"  Media: {detail_data[col].mean()}")
        
        if not diff_values.empty:
            print(f"  Diferencia mínima: {diff_values.min()}")
            print(f"  Diferencia máxima: {diff_values.max()}")
            print(f"  Media de diferencias: {diff_values.mean()}")

if __name__ == "__main__":
    test_analyze_asset_detail_data() 