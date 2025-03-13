# tests/anomaly/test_full_flow.py
import unittest
import pandas as pd
from datetime import datetime, timedelta
from utils.anomaly.detector import AnomalyDetector
from utils.anomaly.corrector import AnomalyCorrector
from utils.anomaly.service import AnomalyService

class TestAnomalyFullFlow(unittest.TestCase):
    def setUp(self):
        # Crear datos de prueba
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(10)]
        
        # Caso con reinicio de contador
        self.reset_data = pd.DataFrame({
            'date': dates,
            'consumption': [100, 110, 120, 130, 140, 50, 60, 70, 80, 90],  # Reinicio después del día 5
            'asset_id': ['asset1'] * 10,
            'consumption_type': ['electricity'] * 10
        })
        
        # Crear componentes
        self.detector = AnomalyDetector()
        self.corrector = AnomalyCorrector()
        self.service = AnomalyService(detector=self.detector, corrector=self.corrector)
    
    def test_full_flow(self):
        """Verifica el flujo completo de detección y corrección de anomalías"""
        # Detectar anomalías
        anomalies = self.detector.detect_counter_resets(self.reset_data)
        
        # Verificar que se detectó una anomalía
        self.assertEqual(len(anomalies), 1, "Debería detectarse un reinicio de contador")
        
        # Corregir anomalías
        corrected_data = self.corrector.correct_counter_resets(self.reset_data, anomalies)
        
        # Verificar que los valores se corrigieron correctamente
        # El offset debería ser 140 - 50 = 90
        expected_values = [100, 110, 120, 130, 140, 50 + 90, 60 + 90, 70 + 90, 80 + 90, 90 + 90]
        actual_values = corrected_data['corrected_value'].tolist()
        
        self.assertEqual(actual_values, expected_values, "Los valores corregidos no coinciden con los esperados")
        
        # Verificar que se marcaron las filas corregidas
        self.assertEqual(corrected_data['is_corrected'].sum(), 5, "Deberían marcarse 5 filas como corregidas")
    
    def test_service_integration(self):
        """Verifica la integración del servicio de anomalías"""
        # Crear un servicio con un repositorio mock
        class MockRepository:
            def get_original_readings(self, asset_id, consumption_type, start_date=None, end_date=None):
                # Devolver los mismos datos de prueba
                return self.reset_data
            
            def get_anomalies(self, asset_id=None, consumption_type=None, start_date=None, end_date=None):
                return []
            
            def save_anomaly(self, anomaly):
                return "mock_filename.json"
        
        # Asignar los datos de prueba al repositorio mock
        mock_repo = MockRepository()
        mock_repo.reset_data = self.reset_data
        
        # Crear servicio con el repositorio mock
        service = AnomalyService(repository=mock_repo, detector=self.detector, corrector=self.corrector)
        
        # Procesar datos con el servicio
        result = service.process_readings(
            asset_id='asset1',
            consumption_type='electricity'
        )
        
        # Verificar que el resultado contiene los datos esperados
        self.assertIn('original', result, "El resultado debería contener los datos originales")
        self.assertIn('corrected', result, "El resultado debería contener los datos corregidos")
        self.assertIn('anomalies', result, "El resultado debería contener las anomalías detectadas")
        
        # Verificar que se detectó una anomalía
        self.assertEqual(len(result['anomalies']), 1, "Debería detectarse un reinicio de contador")

if __name__ == '__main__':
    unittest.main() 