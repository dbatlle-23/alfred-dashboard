#!/usr/bin/env python3
"""
Script para probar la carga de datos y visualización sin depender de Dash.
Este script permite verificar que los módulos de carga de datos y generación de gráficos
funcionan correctamente de forma independiente.
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from collections import Counter

# Intentar importar los módulos necesarios
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.data_loader import (
        load_all_csv_data, 
        filter_data, 
        get_projects_with_data, 
        get_assets_with_data,
        get_consumption_types,
        aggregate_data_by_consumption_type,
        aggregate_data_by_project
    )
except ImportError as e:
    print(f"Error al importar módulos: {e}")
    print("Asegúrate de ejecutar este script desde el directorio raíz del proyecto.")
    sys.exit(1)

def test_data_loading():
    """
    Prueba la carga de datos desde archivos CSV.
    Muestra información sobre los datos cargados, proyectos y assets.
    """
    print("\nProbando carga de datos...")
    
    try:
        # Cargar todos los datos
        df = load_all_csv_data()
        
        if df is None or df.empty:
            print("No se pudieron cargar datos. Verifica que los archivos CSV existan.")
            return False
            
        # Mostrar información sobre los datos cargados
        print(f"Se cargaron {len(df)} registros de datos.")
        print(f"Columnas disponibles: {', '.join(df.columns)}")
        
        # Verificar valores nulos
        null_counts = df.isnull().sum()
        if null_counts.sum() > 0:
            print("\nValores nulos por columna:")
            for col, count in null_counts[null_counts > 0].items():
                print(f"  - {col}: {count} ({count/len(df)*100:.2f}%)")
        
        # Mostrar información sobre proyectos
        projects = get_projects_with_data(df)
        print(f"\nProyectos encontrados: {len(projects)}")
        
        for i, project in enumerate(projects):
            project_id = project['id']
            project_df = filter_data(df, project_id=project_id)
            assets = get_assets_with_data(project_df)
            
            print(f"  - Proyecto {project_id}")
            print(f"    Assets: {len(assets)}")
            
            # Mostrar algunos assets como ejemplo
            for j, asset in enumerate(assets[:5]):
                print(f"      - Asset {asset['id']}")
            
            if len(assets) > 5:
                print(f"      ... y {len(assets) - 5} más")
        
        # Mostrar información sobre tipos de consumo
        consumption_types = get_consumption_types(df)
        print(f"\nTipos de consumo disponibles: {len(consumption_types)}")
        for consumption_type in consumption_types:
            print(f"  - {consumption_type}")
        
        # Filtrar datos para un proyecto específico
        if projects:
            project_id = projects[0]['id']
            filtered_df = filter_data(df, project_id=project_id)
            print(f"\nDatos filtrados para el proyecto {project_id}: {len(filtered_df)} registros")
            
            # Mostrar estadísticas básicas para este proyecto
            if not filtered_df.empty and 'consumption' in filtered_df.columns:
                # Asegurar que consumption sea numérico
                filtered_df['consumption'] = pd.to_numeric(filtered_df['consumption'], errors='coerce')
                
                # Calcular estadísticas
                stats = filtered_df['consumption'].describe()
                print("\nEstadísticas de consumo para este proyecto:")
                for stat_name in ['mean', '50%', 'min', 'max']:
                    if stat_name in stats:
                        print(f"  - {stat_name.capitalize()}: {stats[stat_name]:.2f}")
                
                # Mostrar distribución temporal
                if 'date' in filtered_df.columns:
                    min_date = filtered_df['date'].min()
                    max_date = filtered_df['date'].max()
                    if pd.notna(min_date) and pd.notna(max_date):
                        print(f"\nRango de fechas: {min_date.date()} a {max_date.date()}")
                    
                    # Contar registros por mes
                    if 'month' in filtered_df.columns:
                        month_counts = filtered_df['month'].value_counts().sort_index()
                        print("\nRegistros por mes:")
                        for month, count in month_counts.items():
                            print(f"  - {month}: {count} registros")
        
        return True
    except Exception as e:
        print(f"Error durante la carga de datos: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_data_visualization():
    """
    Prueba la visualización de datos utilizando matplotlib.
    Genera gráficos de líneas y de barras para mostrar la evolución del consumo
    y el consumo por tipo.
    """
    print("\nProbando visualización de datos...")
    
    try:
        # Cargar datos
        df = load_all_csv_data()
        
        if df is None or df.empty:
            print("No se pudieron cargar datos para visualización.")
            return False
        
        # Seleccionar un proyecto para visualizar
        projects = get_projects_with_data(df)
        if not projects:
            print("No se encontraron proyectos para visualizar.")
            return False
            
        project_id = projects[0]['id']
        filtered_df = filter_data(df, project_id=project_id)
        
        if filtered_df.empty:
            print(f"No hay datos para el proyecto {project_id}.")
            return False
            
        print(f"Visualizando datos para el proyecto {project_id}")
        
        # Asegurar que consumption sea numérico
        if 'consumption' in filtered_df.columns:
            filtered_df['consumption'] = pd.to_numeric(filtered_df['consumption'], errors='coerce')
        elif 'value' in filtered_df.columns:
            filtered_df['consumption'] = pd.to_numeric(filtered_df['value'], errors='coerce')
        else:
            print("No se encontró la columna 'consumption' ni 'value' para la visualización")
            return False
        
        # 1. Gráfico de evolución temporal del consumo
        plt.figure(figsize=(12, 6))
        
        # Agrupar por fecha y sumar el consumo
        if 'date' in filtered_df.columns and 'consumption' in filtered_df.columns:
            # Verificar que date sea datetime
            if not pd.api.types.is_datetime64_any_dtype(filtered_df['date']):
                filtered_df['date'] = pd.to_datetime(filtered_df['date'], errors='coerce')
                
            # Eliminar filas con fechas nulas
            filtered_df = filtered_df.dropna(subset=['date'])
            
            # Resample para tener datos diarios
            try:
                daily_consumption = filtered_df.set_index('date')['consumption'].resample('D').sum()
                
                # Crear gráfico de línea
                plt.plot(daily_consumption.index, daily_consumption.values, marker='o', linestyle='-', markersize=3)
                plt.title(f'Evolución del consumo - Proyecto {project_id}')
                plt.xlabel('Fecha')
                plt.ylabel('Consumo')
                plt.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                # Guardar gráfico
                plt.savefig('consumo_evolucion.png')
                print(f"Gráfico guardado en: {os.path.abspath('consumo_evolucion.png')}")
                plt.close()
            except Exception as e:
                print(f"Error al crear el gráfico de evolución: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # 2. Gráfico de consumo por tipo
        plt.figure(figsize=(10, 6))
        
        # Agrupar por tipo de consumo
        try:
            consumption_by_type = aggregate_data_by_consumption_type(filtered_df)
            
            if not consumption_by_type.empty:
                # Crear gráfico de barras
                plt.bar(consumption_by_type.index, consumption_by_type.values)
                plt.title(f'Consumo por tipo - Proyecto {project_id}')
                plt.xlabel('Tipo de consumo')
                plt.ylabel('Consumo total')
                plt.xticks(rotation=45, ha='right')
                plt.grid(True, axis='y', linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                # Guardar gráfico
                plt.savefig('consumo_por_tipo.png')
                print(f"Gráfico guardado en: {os.path.abspath('consumo_por_tipo.png')}")
                plt.close()
        except Exception as e:
            print(f"Error al crear el gráfico de consumo por tipo: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # 3. Gráfico de consumo por mes (opcional)
        try:
            if 'date' in filtered_df.columns and 'consumption' in filtered_df.columns:
                plt.figure(figsize=(12, 6))
                
                # Crear columna de mes-año
                filtered_df['month_year'] = filtered_df['date'].dt.strftime('%Y-%m')
                
                # Agrupar por mes-año
                monthly_consumption = filtered_df.groupby('month_year')['consumption'].sum().reset_index()
                
                if not monthly_consumption.empty:
                    # Ordenar por mes-año
                    monthly_consumption = monthly_consumption.sort_values('month_year')
                    
                    # Crear gráfico de barras
                    plt.bar(monthly_consumption['month_year'], monthly_consumption['consumption'])
                    plt.title(f'Consumo mensual - Proyecto {project_id}')
                    plt.xlabel('Mes')
                    plt.ylabel('Consumo total')
                    plt.xticks(rotation=45, ha='right')
                    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
                    plt.tight_layout()
                    
                    # Guardar gráfico
                    plt.savefig('consumo_mensual.png')
                    print(f"Gráfico guardado en: {os.path.abspath('consumo_mensual.png')}")
                    plt.close()
        except Exception as e:
            print(f"Error al crear el gráfico de consumo mensual: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return True
    except Exception as e:
        print(f"Error durante la visualización de datos: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    Función principal que ejecuta todas las pruebas.
    """
    print("=== Prueba de carga y visualización de datos ===")
    
    # Ejecutar pruebas
    data_loading_success = test_data_loading()
    data_visualization_success = test_data_visualization()
    
    # Mostrar resumen
    print("\n=== Resumen de pruebas ===")
    print(f"Carga de datos: {'✓ OK' if data_loading_success else '✗ ERROR'}")
    print(f"Visualización de datos: {'✓ OK' if data_visualization_success else '✗ ERROR'}")
    
    if data_loading_success and data_visualization_success:
        print("\n¡Todas las pruebas completadas con éxito!")
        return 0
    else:
        print("\nAlgunas pruebas fallaron. Revisa los mensajes de error.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 