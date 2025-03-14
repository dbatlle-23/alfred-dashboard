# tests/utils/test_anomaly_integration.py
import unittest
import pandas as pd
from datetime import datetime, timedelta
from utils.metrics.data_processing import process_metrics_data
from config.feature_flags import enable_feature, disable_feature

class TestAnomalyIntegration(unittest.TestCase):
    def setUp(self):
        # Crear datos de prueba con una anomalía (reinicio de contador)
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(10)]
        
        # Caso con reinicio de contador
        self.test_data = pd.DataFrame({
            'date': dates,
            'consumption': [100, 110, 120, 130, 140, 50, 60, 70, 80, 90],  # Reinicio después del día 5
            'asset_id': ['asset1'] * 10,
            'consumption_type': ['electricity'] * 10,
            'client_id': ['client1'] * 10,
            'project_id': ['project1'] * 10
        })
    
    def test_anomaly_correction_applied(self):
        """Verifica que la corrección de anomalías se aplica cuando los feature flags están habilitados"""
        # Habilitar feature flags
        enable_feature('enable_anomaly_detection')
        enable_feature('enable_anomaly_correction')
        
        # Procesar datos
        processed_data = process_metrics_data(self.test_data)
        
        # Verificar que se aplicó la corrección
        self.assertIn('corrected_value', processed_data.columns, "La columna corrected_value debería existir")
        self.assertIn('is_corrected', processed_data.columns, "La columna is_corrected debería existir")
        self.assertIn('original_consumption', processed_data.columns, "La columna original_consumption debería existir")
        
        # Verificar que los valores corregidos son diferentes a los originales
        self.assertTrue((processed_data['corrected_value'] != processed_data['original_consumption']).any(), 
                        "Algunos valores deberían haber sido corregidos")
        
        # Verificar que la columna consumption ahora tiene los valores corregidos
        pd.testing.assert_series_equal(processed_data['consumption'], processed_data['corrected_value'],
                                      "La columna consumption debería tener los valores corregidos")
        
        # Verificar que se detectó al menos una anomalía
        self.assertTrue(processed_data['is_corrected'].any(), "Al menos un valor debería estar marcado como corregido")
    
    def test_anomaly_correction_disabled(self):
        """Verifica que la corrección de anomalías no se aplica cuando los feature flags están deshabilitados"""
        # Deshabilitar feature flags
        disable_feature('enable_anomaly_detection')
        disable_feature('enable_anomaly_correction')
        
        # Procesar datos
        processed_data = process_metrics_data(self.test_data)
        
        # Verificar que no se aplicó la corrección (los valores originales se mantienen)
        self.assertEqual(processed_data['consumption'].tolist(), self.test_data['consumption'].tolist(),
                        "Los valores de consumption no deberían cambiar cuando la corrección está deshabilitada")
        
        # La columna corrected_value podría existir pero no debería afectar a consumption
        if 'corrected_value' in processed_data.columns and 'is_corrected' in processed_data.columns:
            self.assertFalse(processed_data['is_corrected'].any(), 
                            "Ningún valor debería estar marcado como corregido")

if __name__ == '__main__':
    unittest.main() 