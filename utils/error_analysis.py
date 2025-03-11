"""
Funciones para el análisis de errores en las lecturas de consumo.
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime

def analyze_readings_errors(df):
    """
    Analiza un DataFrame para detectar y agrupar errores en las lecturas.
    
    Args:
        df: DataFrame con lecturas de consumo
        
    Returns:
        dict: Diccionario con información de errores
    """
    print(f"[DEBUG] analyze_readings_errors - DataFrame shape: {df.shape}")
    
    if df is None or df.empty:
        print("[DEBUG] analyze_readings_errors - DataFrame vacío o None")
        return {
            'total_errors': 0,
            'errors_by_asset': {},
            'errors_by_consumption_type': {},
            'errors_by_period': {},
            'items': []
        }
    
    # Verificar columnas requeridas
    required_columns = ['date', 'asset_id', 'consumption_type']
    print(f"[DEBUG] analyze_readings_errors - Columnas del DataFrame: {df.columns.tolist()}")
    
    # Verificar y añadir columnas requeridas si no existen
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"[DEBUG] analyze_readings_errors - Faltan columnas: {missing_columns}")
        
        # Si falta la columna 'date', intentar encontrarla con otro nombre
        if 'date' in missing_columns and 'fecha' in df.columns:
            df['date'] = df['fecha']
            missing_columns.remove('date')
        
        # Si falta la columna 'asset_id', intentar encontrarla con otro nombre
        if 'asset_id' in missing_columns and 'id_asset' in df.columns:
            df['asset_id'] = df['id_asset']
            missing_columns.remove('asset_id')
        
        # Si falta la columna 'consumption_type', intentar encontrarla con otro nombre
        if 'consumption_type' in missing_columns and 'tipo_consumo' in df.columns:
            df['consumption_type'] = df['tipo_consumo']
            missing_columns.remove('consumption_type')
        
        # Si todavía faltan columnas, crear columnas vacías
        for col in missing_columns:
            print(f"[DEBUG] analyze_readings_errors - Creando columna vacía: {col}")
            df[col] = "Unknown"
    
    # Asegurar que la columna de fecha esté en formato datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Verificar columna de consumo
    consumption_col = None
    if 'consumption' in df.columns:
        consumption_col = 'consumption'
    elif 'Consumo' in df.columns:
        consumption_col = 'Consumo'
    elif 'consumo' in df.columns:
        consumption_col = 'consumo'
    else:
        # Crear una columna de consumo con valores de error para simular datos con errores
        print("[DEBUG] analyze_readings_errors - Creando columna de consumo con errores simulados")
        df['consumption'] = 'Error'
        consumption_col = 'consumption'
    
    print(f"[DEBUG] analyze_readings_errors - Columna de consumo seleccionada: {consumption_col}")
    
    # Filtrar filas con errores
    error_df = df[df[consumption_col] == 'Error'].copy()
    print(f"[DEBUG] analyze_readings_errors - Filas con error: {len(error_df)}")
    
    if error_df.empty:
        return {
            'total_errors': 0,
            'errors_by_asset': {},
            'errors_by_consumption_type': {},
            'errors_by_period': {},
            'items': []
        }
    
    # Añadir columna de período (año-mes)
    error_df['period'] = error_df['date'].dt.strftime('%Y-%m')
    
    # Agrupar por asset
    errors_by_asset = error_df.groupby('asset_id').size().to_dict()
    
    # Agrupar por tipo de consumo
    errors_by_consumption_type = error_df.groupby('consumption_type').size().to_dict()
    
    # Agrupar por período
    errors_by_period = error_df.groupby('period').size().to_dict()
    
    # Crear lista detallada de errores
    detailed_errors = []
    for _, row in error_df.iterrows():
        detailed_errors.append({
            'asset_id': row['asset_id'],
            'consumption_type': row['consumption_type'],
            'period': row['period'],
            'date': row['date'].strftime('%Y-%m-%d')
        })
    
    # Crear el diccionario de resultados
    result = {
        'total_errors': len(error_df),
        'errors_by_asset': errors_by_asset,
        'errors_by_consumption_type': errors_by_consumption_type,
        'errors_by_period': errors_by_period,
        'items': detailed_errors
    }
    
    print(f"[DEBUG] analyze_readings_errors - Resultado: {result}")
    
    return result

def filter_errors_by_criteria(error_data, criteria):
    """
    Filtra los errores según criterios específicos.
    
    Args:
        error_data: Datos de errores analizados
        criteria: Diccionario con criterios de filtrado
            - mode: Modo de filtrado ('all', 'by_asset', 'by_consumption_type', 'by_period')
            - asset_id: ID del asset (para mode='by_asset')
            - consumption_type: Tipo de consumo (para mode='by_consumption_type')
            - period: Período en formato 'YYYY-MM' (para mode='by_period')
        
    Returns:
        dict: Datos filtrados con los errores que cumplen los criterios
    """
    print(f"[DEBUG] filter_errors_by_criteria - Criterios: {criteria}")
    print(f"[DEBUG] filter_errors_by_criteria - Error data keys: {error_data.keys() if error_data else None}")
    
    if not error_data or error_data.get('total_errors', 0) == 0:
        print("[DEBUG] filter_errors_by_criteria - No hay errores para filtrar")
        return {
            'total': 0,
            'items': []
        }
    
    mode = criteria.get('mode', 'all')
    detailed_errors = error_data.get('items', [])
    
    print(f"[DEBUG] filter_errors_by_criteria - Modo: {mode}, Total errores: {len(detailed_errors)}")
    
    if mode == 'all':
        filtered_items = detailed_errors
    elif mode == 'by_asset':
        asset_id = criteria.get('asset_id')
        if not asset_id:
            print("[DEBUG] filter_errors_by_criteria - No se especificó asset_id")
            return {'total': 0, 'items': []}
        filtered_items = [item for item in detailed_errors if item['asset_id'] == asset_id]
    elif mode == 'by_consumption_type':
        consumption_type = criteria.get('consumption_type')
        if not consumption_type:
            print("[DEBUG] filter_errors_by_criteria - No se especificó consumption_type")
            return {'total': 0, 'items': []}
        filtered_items = [item for item in detailed_errors if item['consumption_type'] == consumption_type]
    elif mode == 'by_period':
        period = criteria.get('period')
        if not period:
            print("[DEBUG] filter_errors_by_criteria - No se especificó period")
            return {'total': 0, 'items': []}
        filtered_items = [item for item in detailed_errors if item['period'] == period]
    else:
        print(f"[DEBUG] filter_errors_by_criteria - Modo desconocido: {mode}")
        filtered_items = []
    
    result = {
        'total': len(filtered_items),
        'items': filtered_items
    }
    
    print(f"[DEBUG] filter_errors_by_criteria - Resultado: {len(filtered_items)} items filtrados")
    
    return result

def prepare_regeneration_preview(filtered_errors):
    """
    Prepara una vista previa de las regeneraciones a realizar.
    
    Args:
        filtered_errors: Lista de errores filtrados
        
    Returns:
        dict: Datos para la vista previa
    """
    print(f"[DEBUG] prepare_regeneration_preview - Filtered errors: {filtered_errors}")
    
    if not filtered_errors or not filtered_errors.get('items'):
        print("[DEBUG] prepare_regeneration_preview - No hay errores filtrados")
        return {
            'total': 0,
            'items': []
        }
    
    items = filtered_errors.get('items', [])
    
    print(f"[DEBUG] prepare_regeneration_preview - Total items: {len(items)}")
    
    # Agrupar por asset, tipo de consumo y período para evitar duplicados
    unique_items = {}
    for item in items:
        try:
            key = f"{item['asset_id']}_{item['consumption_type']}_{item['period']}"
            if key not in unique_items:
                unique_items[key] = {
                    'asset_id': item['asset_id'],
                    'consumption_type': item['consumption_type'],
                    'period': item['period']
                }
        except KeyError as e:
            print(f"[DEBUG] prepare_regeneration_preview - Error al procesar item: {item}, Error: {e}")
            # Intentar crear un item con valores por defecto para las claves faltantes
            asset_id = item.get('asset_id', 'Unknown')
            consumption_type = item.get('consumption_type', 'Unknown')
            period = item.get('period', 'Unknown')
            
            key = f"{asset_id}_{consumption_type}_{period}"
            if key not in unique_items:
                unique_items[key] = {
                    'asset_id': asset_id,
                    'consumption_type': consumption_type,
                    'period': period
                }
    
    result = {
        'total': len(unique_items),
        'items': list(unique_items.values())
    }
    
    print(f"[DEBUG] prepare_regeneration_preview - Resultado: {len(unique_items)} items únicos")
    
    return result

def group_errors_for_regeneration(filtered_errors, only_errors=True):
    """
    Agrupa los errores para su regeneración eficiente.
    
    Args:
        filtered_errors: Lista de errores filtrados
        only_errors: Si es True, solo se regenerarán los valores con error;
                    si es False, se regenerarán archivos completos
        
    Returns:
        list: Lista de tareas de regeneración agrupadas
    """
    print(f"[DEBUG] group_errors_for_regeneration - filtered_errors: {filtered_errors}")
    
    if not filtered_errors:
        print("[DEBUG] group_errors_for_regeneration - No hay errores filtrados")
        return []
    
    if isinstance(filtered_errors, str):
        try:
            import json
            filtered_errors = json.loads(filtered_errors)
            print(f"[DEBUG] group_errors_for_regeneration - Convertido string JSON a diccionario")
        except Exception as e:
            print(f"[DEBUG] group_errors_for_regeneration - Error al convertir string JSON: {e}")
            return []
    
    if not isinstance(filtered_errors, dict):
        print(f"[DEBUG] group_errors_for_regeneration - filtered_errors no es un diccionario: {type(filtered_errors)}")
        return []
    
    items = filtered_errors.get('items', [])
    print(f"[DEBUG] group_errors_for_regeneration - Total items: {len(items)}")
    
    if not items:
        return []
    
    if only_errors:
        # Regenerar solo los valores con error (más granular)
        return items
    else:
        # Regenerar archivos completos (agrupar por asset, tipo de consumo y período)
        unique_items = {}
        for item in items:
            try:
                asset_id = item.get('asset_id', 'unknown')
                consumption_type = item.get('consumption_type', 'unknown')
                period = item.get('period', 'unknown')
                
                key = f"{asset_id}_{consumption_type}_{period}"
                if key not in unique_items:
                    unique_items[key] = {
                        'asset_id': asset_id,
                        'consumption_type': consumption_type,
                        'period': period
                    }
            except Exception as e:
                print(f"[DEBUG] group_errors_for_regeneration - Error al procesar item: {item}, Error: {e}")
                continue
        
        print(f"[DEBUG] group_errors_for_regeneration - Total items únicos: {len(unique_items)}")
        return list(unique_items.values()) 