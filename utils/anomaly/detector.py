# utils/anomaly/detector.py
from datetime import datetime

class AnomalyDetector:
    def __init__(self, repository=None):
        self.repository = repository
    
    def detect_counter_resets(self, df, detect_sensor_replacements=False):
        """
        Detecta reinicios de contadores en las lecturas
        
        Args:
            df: DataFrame con lecturas
            detect_sensor_replacements: Si es True, intenta distinguir entre reinicios de contador y reemplazos de sensores
        """
        if df is None or len(df) < 2:
            return []
        
        anomalies = []
        
        # Asegurar que las lecturas estén ordenadas por fecha
        df = df.sort_values('date')
        
        # Iterar por las lecturas
        for i in range(1, len(df)):
            current = df.iloc[i]
            previous = df.iloc[i-1]
            
            # Extraer valores (manejar diferentes nombres de columnas)
            current_value = current.get('consumption', current.get('value', 0))
            previous_value = previous.get('consumption', previous.get('value', 0))
            
            # Convertir a números si son strings
            try:
                if isinstance(current_value, str):
                    current_value = float(current_value)
                if isinstance(previous_value, str):
                    previous_value = float(previous_value)
            except (ValueError, TypeError) as e:
                print(f"Error al convertir valores a números: {str(e)}")
                continue
            
            # Detectar salto negativo significativo (reinicio de contador)
            if current_value < previous_value * 0.8:  # Umbral del 80%
                # Determinar si es un reemplazo de sensor o un reinicio de contador
                anomaly_type = 'counter_reset'
                
                # Si se solicita detectar reemplazos de sensores, aplicar heurística
                if detect_sensor_replacements:
                    # Heurística: si el valor actual es muy pequeño en comparación con el anterior
                    # y el valor anterior era muy grande, podría ser un reemplazo de sensor
                    if current_value < previous_value * 0.05 and previous_value > 1000:
                        anomaly_type = 'sensor_replacement'
                
                anomaly = {
                    'type': anomaly_type,
                    'date': current['date'].isoformat() if hasattr(current['date'], 'isoformat') else current['date'],
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
    
    def reclassify_anomaly(self, anomaly, new_type):
        """
        Reclasifica una anomalía existente a un nuevo tipo
        
        Args:
            anomaly: Diccionario con la anomalía a reclasificar
            new_type: Nuevo tipo de anomalía ('counter_reset' o 'sensor_replacement')
            
        Returns:
            Anomalía actualizada
        """
        if new_type not in ['counter_reset', 'sensor_replacement']:
            raise ValueError(f"Tipo de anomalía no válido: {new_type}")
        
        # Crear copia para no modificar el original
        updated_anomaly = anomaly.copy()
        
        # Guardar el tipo original si no existe
        if 'original_type' not in updated_anomaly:
            updated_anomaly['original_type'] = updated_anomaly['type']
        
        # Actualizar el tipo
        updated_anomaly['type'] = new_type
        updated_anomaly['reclassified_at'] = datetime.now().isoformat()
        updated_anomaly['reclassified'] = True
        
        print(f"Reclasificando anomalía: {updated_anomaly['original_type']} -> {new_type}")
        
        # Actualizar en el repositorio si está disponible
        if self.repository:
            self.repository.update_anomaly(updated_anomaly)
        
        return updated_anomaly