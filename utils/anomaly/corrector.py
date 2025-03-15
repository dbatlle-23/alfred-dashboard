# utils/anomaly/corrector.py
from datetime import datetime

class AnomalyCorrector:
    def __init__(self, repository=None):
        self.repository = repository
    
    def correct_counter_resets(self, readings, anomalies=None):
        """Corrige reinicios de contadores en las lecturas"""
        if readings is None or readings.empty or not anomalies:
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
        
        # Ordenar anomalías por fecha
        anomalies = sorted(anomalies, key=lambda x: x['date'])
        
        # Imprimir información de las anomalías para depuración
        print(f"Aplicando correcciones para {len(anomalies)} anomalías:")
        for i, anomaly in enumerate(anomalies):
            print(f"  Anomalía {i+1}: tipo={anomaly['type']}, fecha={anomaly['date']}")
        
        # Procesar cada anomalía secuencialmente
        for i, anomaly in enumerate(anomalies):
            # Obtener fecha de la anomalía
            anomaly_date = anomaly['date']
            if isinstance(anomaly_date, str):
                try:
                    anomaly_date = datetime.fromisoformat(anomaly_date.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        anomaly_date = datetime.strptime(anomaly_date.split('T')[0], '%Y-%m-%d')
                    except ValueError:
                        print(f"No se pudo convertir la fecha de anomalía: {anomaly_date}")
                        continue
            
            # Encontrar la fila exacta de la anomalía
            anomaly_mask = corrected_readings['date'] == anomaly_date
            if 'asset_id' in corrected_readings.columns and 'asset_id' in anomaly:
                anomaly_mask &= corrected_readings['asset_id'] == anomaly['asset_id']
            if 'consumption_type' in corrected_readings.columns and 'consumption_type' in anomaly:
                anomaly_mask &= corrected_readings['consumption_type'] == anomaly['consumption_type']
            
            # Si no encontramos la fila exacta, continuar con la siguiente anomalía
            if not anomaly_mask.any():
                print(f"  No se encontró la fila para la anomalía en fecha {anomaly_date}")
                continue
            
            # Obtener el índice de la fila de la anomalía
            anomaly_idx = corrected_readings[anomaly_mask].index[0]
            
            # Tratar de manera diferente según el tipo de anomalía
            if anomaly['type'] == 'counter_reset':
                try:
                    # Obtener el valor actual y anterior (posiblemente ya corregidos)
                    value_col = 'corrected_value'  # Usar siempre corrected_value para considerar correcciones previas
                    
                    # Encontrar la fila anterior
                    if anomaly_idx > 0:
                        # Filtrar por asset_id y consumption_type si están disponibles
                        prev_mask = corrected_readings.index < anomaly_idx
                        if 'asset_id' in corrected_readings.columns and 'asset_id' in anomaly:
                            prev_mask &= corrected_readings['asset_id'] == anomaly['asset_id']
                        if 'consumption_type' in corrected_readings.columns and 'consumption_type' in anomaly:
                            prev_mask &= corrected_readings['consumption_type'] == anomaly['consumption_type']
                        
                        if prev_mask.any():
                            # Obtener la última fila anterior que cumple con los criterios
                            prev_idx = corrected_readings[prev_mask].index[-1]
                            previous_value = corrected_readings.loc[prev_idx, value_col]
                        else:
                            # Si no hay fila anterior, usar el valor de previous_value de la anomalía
                            previous_value = float(anomaly['previous_value'])
                    else:
                        # Si es la primera fila, usar el valor de previous_value de la anomalía
                        previous_value = float(anomaly['previous_value'])
                    
                    # Obtener el valor actual
                    current_value = corrected_readings.loc[anomaly_idx, value_col]
                    
                    # Convertir a números si son strings
                    if isinstance(previous_value, str):
                        previous_value = float(previous_value)
                    if isinstance(current_value, str):
                        current_value = float(current_value)
                    
                    # Calcular el offset para esta anomalía
                    offset = previous_value - current_value
                    print(f"  Anomalía {i+1}: previous_value={previous_value}, current_value={current_value}, offset={offset}")
                    
                    # Filtrar las filas posteriores a esta anomalía
                    mask = corrected_readings.index > anomaly_idx
                    
                    # Filtrar por asset_id y consumption_type si están disponibles
                    if 'asset_id' in corrected_readings.columns and 'asset_id' in anomaly:
                        mask &= corrected_readings['asset_id'] == anomaly['asset_id']
                    if 'consumption_type' in corrected_readings.columns and 'consumption_type' in anomaly:
                        mask &= corrected_readings['consumption_type'] == anomaly['consumption_type']
                    
                    # Aplicar el offset a las filas posteriores
                    corrected_readings.loc[mask, 'corrected_value'] += offset
                    
                    # Marcar como corregidas
                    corrected_readings.loc[mask, 'is_corrected'] = True
                    corrected_readings.loc[mask, 'correction_type'] = 'counter_reset'
                    
                    print(f"  Aplicada corrección de tipo 'counter_reset' con offset {offset} a {mask.sum()} filas")
                    
                except (ValueError, TypeError) as e:
                    print(f"  Error al procesar anomalía {i+1}: {str(e)}")
                    continue
                    
            elif anomaly['type'] == 'sensor_replacement':
                # Para reemplazos de sensores, no aplicamos offset a las lecturas posteriores
                # Solo marcamos la lectura como un reemplazo de sensor
                try:
                    # Marcar la fila de la anomalía como reemplazo de sensor
                    corrected_readings.loc[anomaly_idx, 'is_sensor_replacement'] = True
                    corrected_readings.loc[anomaly_idx, 'correction_type'] = 'sensor_replacement'
                    
                    # Opcionalmente, podríamos marcar el valor anterior como no válido
                    # Encontrar la fila anterior
                    if anomaly_idx > 0:
                        prev_mask = corrected_readings.index < anomaly_idx
                        if 'asset_id' in corrected_readings.columns and 'asset_id' in anomaly:
                            prev_mask &= corrected_readings['asset_id'] == anomaly['asset_id']
                        if 'consumption_type' in corrected_readings.columns and 'consumption_type' in anomaly:
                            prev_mask &= corrected_readings['consumption_type'] == anomaly['consumption_type']
                        
                        if prev_mask.any():
                            prev_idx = corrected_readings[prev_mask].index[-1]
                            corrected_readings.loc[prev_idx, 'is_last_before_replacement'] = True
                    
                    print(f"  Aplicada corrección de tipo 'sensor_replacement' - No se aplica offset")
                except Exception as e:
                    print(f"  Error al procesar reemplazo de sensor: {str(e)}")
        
        # Añadir columna para indicar si el valor fue corregido si no existe
        value_col = 'consumption' if 'consumption' in corrected_readings.columns else 'value'
        if 'is_corrected' not in corrected_readings.columns:
            corrected_readings['is_corrected'] = corrected_readings['corrected_value'] != corrected_readings[value_col]
        
        return corrected_readings