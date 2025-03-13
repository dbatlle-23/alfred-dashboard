# tests/anomaly/test_detector.py
import unittest
import pandas as pd
from datetime import datetime, timedelta
from utils.anomaly.detector import AnomalyDetector

class TestAnomalyDetector(unittest.TestCase):
    def setUp(self):
        self.detector = AnomalyDetector()
        
        # Crear datos de prueba
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(10)]
        
        # Caso normal: valores crecientes
        self.normal_data = pd.DataFrame({
            'date': dates,
            'consumption': [100, 110, 120, 130, 140, 150, 160, 170, 180, 190],
            'asset_id': ['asset1'] * 10,
            'consumption_type': ['electricity'] * 10
        })
        
        # Caso con reinicio de contador
        self.reset_data = pd.DataFrame({
            'date': dates,
            'consumption': [100, 110, 120, 130, 140, 50, 60, 70, 80, 90],  # Reinicio después del día 5
            'asset_id': ['asset1'] * 10,
            'consumption_type': ['electricity'] * 10
        })
    
    def test_no_anomalies_in_normal_data(self):
        """Verifica que no se detecten anomalías en datos normales"""
        anomalies = self.detector.detect_counter_resets(self.normal_data)
        self.assertEqual(len(anomalies), 0, "No deberían detectarse anomalías en datos normales")
    
    def test_detect_counter_reset(self):
        """Verifica que se detecte correctamente un reinicio de contador"""
        anomalies = self.detector.detect_counter_resets(self.reset_data)
        
        # Debería detectar una anomalía
        self.assertEqual(len(anomalies), 1, "Debería detectarse un reinicio de contador")
        
        # Verificar detalles de la anomalía
        anomaly = anomalies[0]
        self.assertEqual(anomaly['type'], 'counter_reset', "El tipo de anomalía debería ser 'counter_reset'")
        self.assertEqual(anomaly['previous_value'], 140, "El valor anterior debería ser 140")
        self.assertEqual(anomaly['current_value'], 50, "El valor actual debería ser 50")
        self.assertEqual(anomaly['offset'], 90, "El offset debería ser 90")

if __name__ == '__main__':
    unittest.main()