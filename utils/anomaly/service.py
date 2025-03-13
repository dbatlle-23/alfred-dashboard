# utils/anomaly/service.py
import pandas as pd
from utils.repositories.reading_repository import ReadingRepository
from utils.anomaly.detector import AnomalyDetector
from utils.anomaly.corrector import AnomalyCorrector

class AnomalyService:
    def __init__(self, repository=None, detector=None, corrector=None):
        # Crear componentes si no se proporcionan
        self.repository = repository or ReadingRepository()
        self.detector = detector or AnomalyDetector(self.repository)
        self.corrector = corrector or AnomalyCorrector(self.repository)
    
    def process_readings(self, asset_id, consumption_type, start_date=None, end_date=None, detect_only=False):
        """
        Procesa las lecturas, detecta y opcionalmente corrige anomalías
        
        Args:
            asset_id: ID del asset
            consumption_type: Tipo de consumo
            start_date: Fecha de inicio (opcional)
            end_date: Fecha de fin (opcional)
            detect_only: Si es True, solo detecta anomalías sin corregir
            
        Returns:
            dict con lecturas originales, corregidas y anomalías
        """
        # Obtener lecturas originales
        original_readings = self.repository.get_original_readings(
            asset_id, consumption_type, start_date, end_date
        )
        
        # Si no hay lecturas, devolver resultado vacío
        if original_readings is None or original_readings.empty:
            return {
                'original': pd.DataFrame(),
                'corrected': pd.DataFrame(),
                'anomalies': []
            }
        
        # Detectar anomalías
        anomalies = self.detector.detect_counter_resets(original_readings)
        
        # Si solo se requiere detección, no corregir
        if detect_only:
            return {
                'original': original_readings,
                'corrected': original_readings,
                'anomalies': anomalies
            }
        
        # Corregir anomalías
        corrected_readings = self.corrector.correct_counter_resets(
            original_readings, anomalies
        )
        
        return {
            'original': original_readings,
            'corrected': corrected_readings,
            'anomalies': anomalies
        }