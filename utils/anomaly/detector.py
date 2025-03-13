# utils/anomaly/detector.py
from datetime import datetime

class AnomalyDetector:
    def __init__(self, repository=None):
        self.repository = repository
    
    def detect_counter_resets(self, readings):
        """Detecta reinicios de contadores en las lecturas"""
        if readings is None or len(readings) < 2:
            return []
            
        anomalies = []
        
        # Asegurar que las lecturas estén ordenadas por fecha
        readings = readings.sort_values('date')
        
        # Iterar por las lecturas
        for i in range(1, len(readings)):
            current = readings.iloc[i]
            previous = readings.iloc[i-1]
            
            # Extraer valores (manejar diferentes nombres de columnas)
            current_value = current.get('consumption', current.get('value', 0))
            previous_value = previous.get('consumption', previous.get('value', 0))
            
            # Detectar salto negativo significativo (reinicio de contador)
            if current_value < previous_value * 0.8:  # Umbral del 80%
                anomaly = {
                    'type': 'counter_reset',
                    'date': current['date'],
                    'previous_value': previous_value,
                    'current_value': current_value,
                    'asset_id': current.get('asset_id'),
                    'consumption_type': current.get('consumption_type'),
                    'detected_at': datetime.now().isoformat(),
                    'offset': previous_value - current_value
                }
                
                anomalies.append(anomaly)
                
                # Guardar anomalía si hay repositorio configurado
                if self.repository:
                    self.repository.save_anomaly(anomaly)
        
        return anomalies