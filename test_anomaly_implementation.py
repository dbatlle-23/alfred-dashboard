#!/usr/bin/env python
# test_anomaly_implementation.py
"""
Script para probar la implementación de la corrección de anomalías.
Este script verifica:
1. La detección de anomalías
2. La corrección de anomalías
3. La integración con el flujo de datos de métricas
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import json

# Añadir el directorio raíz al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar los módulos necesarios
from utils.adapters.anomaly_adapter import AnomalyAdapter
from utils.anomaly.detector import AnomalyDetector
from utils.anomaly.corrector import AnomalyCorrector
from utils.metrics.data_processing import process_metrics_data
from config.feature_flags import enable_feature, disable_feature, is_feature_enabled

def create_test_data(with_anomaly=True):
    """Crea datos de prueba con o sin anomalías"""
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(10)]
    
    if with_anomaly:
        # Caso con reinicio de contador (anomalía)
        consumption = [100, 110, 120, 130, 140, 50, 60, 70, 80, 90]  # Reinicio después del día 5
    else:
        # Caso sin anomalías
        consumption = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190]
    
    return pd.DataFrame({
        'date': dates,
        'consumption': consumption,
        'asset_id': ['asset1'] * 10,
        'consumption_type': ['electricity'] * 10,
        'client_id': ['client1'] * 10,
        'project_id': ['project1'] * 10
    })

def test_anomaly_detector():
    """Prueba el detector de anomalías"""
    print("\n=== Prueba del detector de anomalías ===")
    
    # Crear datos de prueba con anomalía
    test_data = create_test_data(with_anomaly=True)
    
    # Crear detector
    detector = AnomalyDetector()
    
    # Detectar anomalías
    anomalies = detector.detect_counter_resets(test_data)
    
    # Verificar que se detectó una anomalía
    if len(anomalies) > 0:
        print(f"✅ Se detectaron {len(anomalies)} anomalías")
        for i, anomaly in enumerate(anomalies):
            print(f"  Anomalía {i+1}:")
            print(f"    Tipo: {anomaly['type']}")
            print(f"    Fecha: {anomaly['date']}")
            print(f"    Valor anterior: {anomaly['previous_value']}")
            print(f"    Valor actual: {anomaly['current_value']}")
            print(f"    Offset: {anomaly['offset']}")
    else:
        print("❌ No se detectaron anomalías")
    
    # Verificar que no se detectan anomalías en datos normales
    normal_data = create_test_data(with_anomaly=False)
    normal_anomalies = detector.detect_counter_resets(normal_data)
    
    if len(normal_anomalies) == 0:
        print("✅ No se detectaron anomalías en datos normales")
    else:
        print(f"❌ Se detectaron {len(normal_anomalies)} anomalías en datos normales")
    
    return anomalies

def test_anomaly_corrector(anomalies=None):
    """Prueba el corrector de anomalías"""
    print("\n=== Prueba del corrector de anomalías ===")
    
    # Crear datos de prueba con anomalía
    test_data = create_test_data(with_anomaly=True)
    
    # Crear corrector
    corrector = AnomalyCorrector()
    
    # Si no se proporcionaron anomalías, detectarlas
    if anomalies is None:
        detector = AnomalyDetector()
        anomalies = detector.detect_counter_resets(test_data)
    
    # Corregir anomalías
    corrected_data = corrector.correct_counter_resets(test_data, anomalies)
    
    # Verificar que se aplicaron correcciones
    if 'corrected_value' in corrected_data.columns:
        print("✅ Se añadió la columna 'corrected_value'")
        
        # Verificar que hay valores corregidos
        if 'is_corrected' in corrected_data.columns and corrected_data['is_corrected'].any():
            corrected_count = corrected_data['is_corrected'].sum()
            print(f"✅ Se corrigieron {corrected_count} valores")
            
            # Mostrar algunos valores originales y corregidos
            print("\nValores originales vs. corregidos:")
            for i, row in corrected_data[corrected_data['is_corrected']].iterrows():
                print(f"  Fecha: {row['date']}")
                print(f"    Original: {row['consumption']}")
                print(f"    Corregido: {row['corrected_value']}")
        else:
            print("❌ No se marcaron valores como corregidos")
    else:
        print("❌ No se añadió la columna 'corrected_value'")
    
    return corrected_data

def test_anomaly_adapter():
    """Prueba el adaptador de anomalías"""
    print("\n=== Prueba del adaptador de anomalías ===")
    
    # Crear datos de prueba con anomalía
    test_data = create_test_data(with_anomaly=True)
    
    # Crear adaptador
    adapter = AnomalyAdapter()
    
    # Habilitar feature flags
    enable_feature('enable_anomaly_detection')
    enable_feature('enable_anomaly_correction')
    
    print(f"Feature flag 'enable_anomaly_detection': {is_feature_enabled('enable_anomaly_detection')}")
    print(f"Feature flag 'enable_anomaly_correction': {is_feature_enabled('enable_anomaly_correction')}")
    
    # Procesar datos con el adaptador
    processed_data = adapter.process_readings(test_data)
    
    # Verificar que se aplicaron correcciones
    if 'corrected_value' in processed_data.columns:
        print("✅ Se añadió la columna 'corrected_value'")
        
        # Verificar que hay valores corregidos
        if 'is_corrected' in processed_data.columns and processed_data['is_corrected'].any():
            corrected_count = processed_data['is_corrected'].sum()
            print(f"✅ Se corrigieron {corrected_count} valores")
        else:
            print("❌ No se marcaron valores como corregidos")
    else:
        print("❌ No se añadió la columna 'corrected_value'")
    
    # Probar con feature flags deshabilitados
    disable_feature('enable_anomaly_detection')
    disable_feature('enable_anomaly_correction')
    
    print(f"Feature flag 'enable_anomaly_detection': {is_feature_enabled('enable_anomaly_detection')}")
    print(f"Feature flag 'enable_anomaly_correction': {is_feature_enabled('enable_anomaly_correction')}")
    
    # Procesar datos con el adaptador
    processed_data_disabled = adapter.process_readings(test_data)
    
    # Verificar que no se aplicaron correcciones
    if 'is_corrected' not in processed_data_disabled.columns or not processed_data_disabled['is_corrected'].any():
        print("✅ No se aplicaron correcciones cuando los feature flags están deshabilitados")
    else:
        print("❌ Se aplicaron correcciones a pesar de que los feature flags están deshabilitados")
    
    # Volver a habilitar los feature flags para las siguientes pruebas
    enable_feature('enable_anomaly_detection')
    enable_feature('enable_anomaly_correction')
    
    return processed_data

def test_metrics_integration():
    """Prueba la integración con el flujo de datos de métricas"""
    print("\n=== Prueba de integración con el flujo de datos de métricas ===")
    
    # Crear datos de prueba con anomalía
    test_data = create_test_data(with_anomaly=True)
    
    # Habilitar feature flags
    enable_feature('enable_anomaly_detection')
    enable_feature('enable_anomaly_correction')
    
    # Procesar datos con la función process_metrics_data
    processed_data = process_metrics_data(test_data)
    
    # Verificar que se aplicaron correcciones
    if 'original_consumption' in processed_data.columns:
        print("✅ Se añadió la columna 'original_consumption'")
        
        # Verificar que los valores de consumption son los corregidos
        if 'corrected_value' in processed_data.columns:
            equal_values = (processed_data['consumption'] == processed_data['corrected_value']).all()
            if equal_values:
                print("✅ Los valores de 'consumption' son iguales a los valores corregidos")
            else:
                print("❌ Los valores de 'consumption' no son iguales a los valores corregidos")
        else:
            print("❌ No se añadió la columna 'corrected_value'")
    else:
        print("❌ No se añadió la columna 'original_consumption'")
    
    # Probar con feature flags deshabilitados
    disable_feature('enable_anomaly_detection')
    disable_feature('enable_anomaly_correction')
    
    # Procesar datos con la función process_metrics_data
    processed_data_disabled = process_metrics_data(test_data)
    
    # Verificar que no se aplicaron correcciones
    if 'original_consumption' not in processed_data_disabled.columns:
        print("✅ No se añadió la columna 'original_consumption' cuando los feature flags están deshabilitados")
    else:
        print("❌ Se añadió la columna 'original_consumption' a pesar de que los feature flags están deshabilitados")
    
    # Volver a habilitar los feature flags
    enable_feature('enable_anomaly_detection')
    enable_feature('enable_anomaly_correction')
    
    return processed_data

def run_all_tests():
    """Ejecuta todas las pruebas"""
    print("=== Iniciando pruebas de la implementación de corrección de anomalías ===\n")
    
    # Prueba 1: Detector de anomalías
    anomalies = test_anomaly_detector()
    
    # Prueba 2: Corrector de anomalías
    corrected_data = test_anomaly_corrector(anomalies)
    
    # Prueba 3: Adaptador de anomalías
    adapter_data = test_anomaly_adapter()
    
    # Prueba 4: Integración con el flujo de datos de métricas
    metrics_data = test_metrics_integration()
    
    print("\n=== Resumen de pruebas ===")
    print(f"Detector de anomalías: {'✅ Pasó' if len(anomalies) > 0 else '❌ Falló'}")
    print(f"Corrector de anomalías: {'✅ Pasó' if 'corrected_value' in corrected_data.columns else '❌ Falló'}")
    print(f"Adaptador de anomalías: {'✅ Pasó' if 'corrected_value' in adapter_data.columns else '❌ Falló'}")
    print(f"Integración con métricas: {'✅ Pasó' if 'original_consumption' in metrics_data.columns else '❌ Falló'}")
    
    print("\n=== Pruebas completadas ===")

if __name__ == "__main__":
    run_all_tests() 