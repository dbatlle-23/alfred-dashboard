# utils/adapters/anomaly_adapter.py
from config.feature_flags import is_feature_enabled
from utils.anomaly.service import AnomalyService

class AnomalyAdapter:
    def __init__(self):
        self.anomaly_service = AnomalyService()
    
    def process_readings(self, readings_data, detect_only=False):
        """
        Procesa las lecturas utilizando el servicio de anomalías si está habilitado
        
        Args:
            readings_data: DataFrame con lecturas
            detect_only: Si es True, solo detecta anomalías sin corregir
            
        Returns:
            DataFrame con lecturas procesadas
        """
        # Si la detección de anomalías no está habilitada, devolver datos originales
        if not is_feature_enabled('enable_anomaly_detection'):
            return readings_data
        
        # Verificar si hay datos para procesar
        if readings_data is None or readings_data.empty:
            return readings_data
        
        # Agrupar por asset_id y consumption_type para procesar cada grupo
        processed_data = readings_data.copy()
        
        # Añadir columna para valores corregidos si no existe
        value_col = 'consumption' if 'consumption' in processed_data.columns else 'value'
        processed_data['corrected_value'] = processed_data[value_col]
        
        # Procesar cada grupo de lecturas
        for (asset_id, consumption_type), group in readings_data.groupby(['asset_id', 'consumption_type']):
            # Procesar grupo con el servicio de anomalías
            result = self.anomaly_service.process_readings(
                asset_id, 
                consumption_type,
                detect_only=detect_only
            )
            
            # Si hay correcciones, actualizar los valores en el DataFrame original
            if not result['corrected'].empty and 'corrected_value' in result['corrected'].columns:
                # Crear índice para unir los DataFrames
                corrected_df = result['corrected'].set_index(['date', 'asset_id', 'consumption_type'])
                
                # Actualizar valores corregidos en el DataFrame original
                for idx, row in corrected_df.iterrows():
                    date, asset, consumption = idx
                    mask = (
                        (processed_data['date'] == date) & 
                        (processed_data['asset_id'] == asset) & 
                        (processed_data['consumption_type'] == consumption)
                    )
                    processed_data.loc[mask, 'corrected_value'] = row['corrected_value']
                    processed_data.loc[mask, 'is_corrected'] = row.get('is_corrected', False)
        
        return processed_data