# utils/anomaly/corrector.py
from datetime import datetime

class AnomalyCorrector:
    def __init__(self, repository=None):
        self.repository = repository
    
    def correct_counter_resets(self, readings, anomalies=None):
        """Corrige reinicios de contadores en las lecturas"""
        if readings is None or readings.empty:
            return readings
            
        # Crear copia para no modificar los datos originales
        corrected_readings = readings.copy()
        
        # Añadir columna para valores corregidos si no existe
        if 'corrected_value' not in corrected_readings.columns:
            value_col = 'consumption' if 'consumption' in corrected_readings.columns else 'value'
            corrected_readings['corrected_value'] = corrected_readings[value_col]
        
        # Si no se proporcionaron anomalías y hay repositorio, intentar obtenerlas
        if anomalies is None and self.repository:
            asset_ids = corrected_readings['asset_id'].unique()
            consumption_types = corrected_readings['consumption_type'].unique()
            
            all_anomalies = []
            for asset_id in asset_ids:
                for consumption_type in consumption_types:
                    asset_anomalies = self.repository.get_anomalies(
                        asset_id=asset_id,
                        consumption_type=consumption_type
                    )
                    all_anomalies.extend(asset_anomalies)
            
            anomalies = all_anomalies
        
        # Si no hay anomalías, devolver los datos sin cambios
        if not anomalies:
            return corrected_readings
        
        # Ordenar anomalías por fecha
        anomalies = sorted(anomalies, key=lambda x: x['date'])
        
        # Aplicar correcciones para cada anomalía
        for anomaly in anomalies:
            if anomaly['type'] == 'counter_reset':
                # Convertir fecha de anomalía a datetime si es string
                anomaly_date = anomaly['date']
                if isinstance(anomaly_date, str):
                    anomaly_date = datetime.fromisoformat(anomaly_date.replace('Z', '+00:00'))
                
                # Filtrar por asset_id y consumption_type si están disponibles
                mask = corrected_readings['date'] >= anomaly_date
                
                if 'asset_id' in corrected_readings.columns and 'asset_id' in anomaly:
                    mask &= corrected_readings['asset_id'] == anomaly['asset_id']
                
                if 'consumption_type' in corrected_readings.columns and 'consumption_type' in anomaly:
                    mask &= corrected_readings['consumption_type'] == anomaly['consumption_type']
                
                # Aplicar offset a las lecturas posteriores a la anomalía
                offset = anomaly.get('offset', anomaly['previous_value'] - anomaly['current_value'])
                corrected_readings.loc[mask, 'corrected_value'] += offset
        
        # Añadir columna para indicar si el valor fue corregido
        value_col = 'consumption' if 'consumption' in corrected_readings.columns else 'value'
        corrected_readings['is_corrected'] = corrected_readings['corrected_value'] != corrected_readings[value_col]
        
        return corrected_readings