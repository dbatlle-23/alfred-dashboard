import pandas as pd
import numpy as np
from utils.db_utils import get_common_areas_bookings
from utils.logging import get_logger

logger = get_logger(__name__)

def test_analytics():
    logger.info("Iniciando prueba de análisis")
    
    # Obtener datos
    df = get_common_areas_bookings()
    
    if df is None or df.empty:
        logger.error("No se encontraron datos")
        return
    
    logger.info(f"Se encontraron {len(df)} registros")
    logger.info(f"Columnas disponibles: {df.columns.tolist()}")
    logger.info(f"Tipo de start_time: {type(df['start_time'].iloc[0])}")
    
    try:
        # Procesar datos para el análisis por semana
        df['start_date'] = df['start_time'].dt.date
        df['week'] = df['start_time'].dt.isocalendar().week
        df['year'] = df['start_time'].dt.isocalendar().year
        
        logger.info("Columnas de fecha creadas correctamente")
        
        # Agrupar por semana y contar reservas
        weekly_counts = df.groupby(['year', 'week']).size().reset_index(name='count')
        logger.info(f"Datos agrupados por semana: {len(weekly_counts)} semanas")
        
        if not weekly_counts.empty:
            weekly_counts['week_label'] = weekly_counts['year'].astype(str) + '-W' + weekly_counts['week'].astype(str)
            avg_weekly = f"{weekly_counts['count'].mean():.1f}"
            logger.info(f"Promedio de reservas por semana: {avg_weekly}")
            
            # Calcular línea de tendencia
            if len(weekly_counts) > 1:
                try:
                    x_numeric = list(range(len(weekly_counts)))
                    y_values = weekly_counts['count'].tolist()
                    
                    # Calcular línea de tendencia
                    z = np.polyfit(x_numeric, y_values, 1)
                    p = np.poly1d(z)
                    trend_y = [p(x) for x in x_numeric]
                    
                    logger.info("Línea de tendencia calculada correctamente")
                    logger.info(f"Pendiente de la tendencia: {z[0]}")
                except Exception as e:
                    logger.error(f"Error calculando línea de tendencia: {str(e)}")
        
        # Procesar datos para el análisis por día de la semana
        df['day_of_week'] = df['start_time'].dt.day_name()
        logger.info(f"Días de la semana encontrados: {df['day_of_week'].unique().tolist()}")
        
        # Agrupar por día de la semana y contar reservas
        daily_counts = df.groupby('day_of_week').size().reset_index(name='count')
        logger.info(f"Conteo por día de la semana: {daily_counts.to_dict()}")
        
        logger.info("Prueba completada con éxito")
    except Exception as e:
        logger.error(f"Error en la prueba: {str(e)}")

if __name__ == "__main__":
    test_analytics() 