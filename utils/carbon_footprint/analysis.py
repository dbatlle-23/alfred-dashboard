import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from utils.logging import get_logger

logger = get_logger(__name__)

# Factores de emisión (kg CO2 por kWh) para diferentes fuentes de energía
# Estos valores pueden variar según país y año, y deberían ser actualizados regularmente
EMISSION_FACTORS = {
    "electricity": 0.108,          # kg CO2 por kWh de electricidad (mix España 2024) - Actualizado en Mar 2024
    "natural_gas": 0.20,           # kg CO2 por kWh de gas natural
    "heating_oil": 0.27,           # kg CO2 por kWh de gasóleo de calefacción
    "thermal_energy_heat": 0.18,   # kg CO2 por kWh de energía térmica de calor
    "thermal_energy_cooling": 0.15 # kg CO2 por kWh de energía térmica de refrigeración
}

def calculate_carbon_emissions(energy_consumption, energy_type="electricity"):
    """
    Calcula las emisiones de CO2 basadas en el consumo de energía.
    
    Args:
        energy_consumption (float or array-like): Consumo de energía en kWh
        energy_type (str): Tipo de energía (electricity, natural_gas, etc.)
        
    Returns:
        float or array-like: Emisiones de CO2 en kg
    """
    if energy_type not in EMISSION_FACTORS:
        logger.warning(f"Tipo de energía '{energy_type}' no reconocido, utilizando factor de electricidad por defecto")
        energy_type = "electricity"
    
    emission_factor = EMISSION_FACTORS[energy_type]
    
    try:
        # Comprobar si es un valor escalar (int o float)
        if isinstance(energy_consumption, (int, float)):
            logger.debug(f"Calculando emisiones para valor escalar: {energy_consumption} kWh, factor: {emission_factor}")
            result = float(energy_consumption) * emission_factor
            logger.debug(f"Resultado emisiones: {result} kg CO2")
            return result
        
        # Si es iterable (lista, array, etc.), convertir a numpy array
        try:
            logger.debug(f"Calculando emisiones para array de longitud {len(energy_consumption) if hasattr(energy_consumption, '__len__') else 'desconocida'}")
            energy_consumption_array = np.array(energy_consumption, dtype=float)
            result = energy_consumption_array * emission_factor
            logger.debug(f"Resultado emisiones: primeros 3 valores: {result[:3] if len(result) > 3 else result}")
            return result
        except (ValueError, TypeError) as e:
            logger.error(f"Error al convertir datos de consumo a valores numéricos: {str(e)}")
            return 0
    except Exception as e:
        logger.error(f"Error al calcular emisiones: {str(e)}")
        # Si hay error en la conversión o multiplicación, devolver 0
        return 0

def calculate_total_emissions(consumption_data, energy_type="electricity"):
    """
    Calcula el total de emisiones de CO2 para un conjunto de datos de consumo.
    
    Args:
        consumption_data (array-like): Datos de consumo de energía en kWh
        energy_type (str): Tipo de energía
        
    Returns:
        float: Total de emisiones de CO2 en kg
    """
    try:
        if consumption_data is None or (isinstance(consumption_data, (list, np.ndarray, pd.Series)) and len(consumption_data) == 0):
            logger.warning("No hay datos de consumo para calcular emisiones totales")
            return 0
            
        if not isinstance(consumption_data, (list, np.ndarray, pd.Series)):
            logger.warning(f"Los datos de consumo deben ser un array, no {type(consumption_data)}")
            # Intentar convertir a lista si es posible
            try:
                consumption_data = [float(consumption_data)]
            except (ValueError, TypeError):
                logger.error("No se pudo convertir el valor a un número")
                return 0
        
        # Registrar información sobre los datos de entrada
        logger.debug(f"Calculando emisiones totales para {len(consumption_data)} valores de consumo")
        logger.debug(f"Tipo de datos de consumo: {type(consumption_data)}")
        logger.debug(f"Primeros 5 valores de consumo: {consumption_data[:5] if len(consumption_data) >= 5 else consumption_data}")
        
        # Asegurarse de que los datos son numéricos
        try:
            consumption_data = np.array(consumption_data, dtype=float)
        except (ValueError, TypeError) as e:
            logger.error(f"Error al convertir datos de consumo a valores numéricos: {str(e)}")
            return 0
        
        # Calcular emisiones y sumarlas
        emissions = calculate_carbon_emissions(consumption_data, energy_type)
        
        # Si emissions es un escalar, devolverlo directamente
        if isinstance(emissions, (int, float)):
            logger.debug(f"Emisiones totales (escalar): {emissions}")
            return emissions
            
        total = float(np.sum(emissions))
        logger.debug(f"Emisiones totales (suma de array): {total}")
        return total
    except Exception as e:
        logger.error(f"Error al calcular emisiones totales: {str(e)}")
        return 0

def calculate_average_emissions(consumption_data, energy_type="electricity"):
    """
    Calcula las emisiones promedio diarias de CO2.
    
    Args:
        consumption_data (array-like): Datos de consumo de energía en kWh
        energy_type (str): Tipo de energía
        
    Returns:
        float: Emisiones promedio de CO2 en kg/día
    """
    if not len(consumption_data):
        return 0
    
    total_emissions = calculate_total_emissions(consumption_data, energy_type)
    return total_emissions / len(consumption_data)

def detect_emission_anomalies(consumption_data, energy_type="electricity", threshold_multiplier=2.0):
    """
    Detecta anomalías en las emisiones de CO2 basadas en desviaciones estándar.
    
    Args:
        consumption_data (list or numpy.ndarray): Datos de consumo de energía
        energy_type (str): Tipo de energía (electricity, natural_gas, etc.)
        threshold_multiplier (float): Multiplicador para establecer el umbral de anomalía
        
    Returns:
        tuple: (anomalies, threshold) donde anomalies es un array booleano que indica
               si cada punto es una anomalía, y threshold es el valor umbral utilizado
    """
    try:
        # Verificar si consumption_data es válido
        if consumption_data is None or len(consumption_data) == 0:
            logger.warning("No se proporcionaron datos de consumo para detección de anomalías")
            return np.array([]), 0
        
        # Convertir a NumPy array si es necesario
        if not isinstance(consumption_data, np.ndarray):
            try:
                consumption_data = np.array(consumption_data, dtype=float)
            except (ValueError, TypeError) as e:
                logger.error(f"Error al convertir datos de consumo a array NumPy: {str(e)}")
                return np.array([]), 0
        
        # Calcular emisiones para cada punto de consumo
        emissions = []
        for consumption_point in consumption_data:
            # Asegurar que cada punto es un valor numérico antes de calcular emisiones
            try:
                value = float(consumption_point)
                emission = calculate_carbon_emissions(value, energy_type)
                emissions.append(emission)
            except (ValueError, TypeError) as e:
                logger.warning(f"Punto de consumo inválido ignorado: {str(e)}")
                emissions.append(0)  # Usar 0 para puntos inválidos
        
        # Convertir lista de emisiones a array de NumPy
        emissions_array = np.array(emissions)
        
        # Calcular estadísticas
        mean_emission = np.mean(emissions_array)
        std_emission = np.std(emissions_array)
        
        # Establecer umbral
        threshold = mean_emission + (threshold_multiplier * std_emission)
        
        # Identificar anomalías (como máscara booleana)
        anomalies = emissions_array > threshold
        
        return anomalies, threshold
        
    except Exception as e:
        logger.error(f"Error durante la detección de anomalías: {str(e)}")
        return np.array([]), 0

def compare_emission_periods(current_data, previous_data=None, energy_type="electricity"):
    """
    Compara las emisiones entre dos períodos de tiempo y calcula la variación porcentual.
    
    Args:
        current_data (array-like): Datos de consumo actuales
        previous_data (array-like): Datos de consumo del período anterior
        energy_type (str): Tipo de energía
        
    Returns:
        dict: Resultados de la comparación entre períodos
    """
    try:
        # Asegurar que los datos son arrays NumPy
        if not isinstance(current_data, np.ndarray):
            current_data = np.array(current_data, dtype=float)
            
        # Si no hay datos previos, retornamos un diccionario con valores por defecto
        if previous_data is None or len(previous_data) == 0:
            # Generar datos simulados para comparación
            previous_length = len(current_data)
            previous_data = np.random.uniform(
                low=0.8 * np.mean(current_data),
                high=1.2 * np.mean(current_data),
                size=previous_length
            )
            is_simulated = True
        else:
            if not isinstance(previous_data, np.ndarray):
                previous_data = np.array(previous_data, dtype=float)
            is_simulated = False
        
        # Calcular emisiones para ambos períodos
        current_emissions = calculate_carbon_emissions(current_data, energy_type)
        previous_emissions = calculate_carbon_emissions(previous_data, energy_type)
        
        # Si alguno de los valores es 0 debido a errores, devolver 0
        if (isinstance(current_emissions, (int, float)) and current_emissions == 0) or \
           (isinstance(previous_emissions, (int, float)) and previous_emissions == 0):
            logger.warning("No se pudieron calcular emisiones para la comparación de períodos")
            return {
                "current_total": 0,
                "previous_total": 0,
                "change_percentage": 0,
                "is_improved": False,
                "is_simulated": is_simulated
            }
        
        # Calcular total de emisiones para cada período
        total_current = np.sum(current_emissions)
        total_previous = np.sum(previous_emissions)
        
        # Evitar división por cero
        if total_previous == 0:
            change_percentage = 100.0 if total_current > 0 else 0.0
        else:
            # Calcular variación porcentual
            change_percentage = ((total_current - total_previous) / total_previous) * 100
        
        # Determinar si hay mejora (reducción de emisiones)
        is_improved = change_percentage < 0
        
        return {
            "current_total": float(total_current),
            "previous_total": float(total_previous),
            "change_percentage": float(change_percentage),
            "is_improved": is_improved,
            "is_simulated": is_simulated
        }
    except Exception as e:
        logger.error(f"Error al comparar períodos de emisión: {str(e)}")
        return {
            "current_total": 0,
            "previous_total": 0,
            "change_percentage": 0,
            "is_improved": False,
            "is_simulated": True
        }

def estimate_annual_emissions(consumption_data, days_covered, energy_type="electricity"):
    """
    Estima las emisiones anuales basadas en un período más corto.
    
    Args:
        consumption_data (array-like): Datos de consumo de energía en kWh
        days_covered (int): Número de días cubiertos por los datos
        energy_type (str): Tipo de energía
        
    Returns:
        float: Estimación anual de emisiones de CO2 en kg
    """
    try:
        # Validar entrada
        if days_covered is None or days_covered <= 0:
            logger.warning("El número de días debe ser positivo para estimar emisiones anuales")
            return 0
            
        if consumption_data is None or len(consumption_data) == 0:
            logger.warning("No hay datos de consumo para estimar emisiones anuales")
            return 0
        
        # Emisiones totales para el período
        total_emissions = calculate_total_emissions(consumption_data, energy_type)
        
        # Si no hay emisiones, devolver 0
        if total_emissions == 0:
            return 0
        
        # Factor de extrapolación
        annual_factor = 365.0 / float(days_covered)
        
        # Estimación anual
        annual_estimate = total_emissions * annual_factor
        
        return annual_estimate
    except Exception as e:
        logger.error(f"Error al estimar emisiones anuales: {str(e)}")
        return 0

def calculate_emission_reduction_targets(current_annual_emissions, target_years=[1, 5, 10], reduction_percentages=[5, 20, 40]):
    """
    Calcula objetivos de reducción de emisiones para diferentes horizontes temporales.
    
    Args:
        current_annual_emissions (float): Emisiones anuales actuales en kg CO2
        target_years (list): Lista de años objetivo (1, 5, 10 años)
        reduction_percentages (list): Porcentajes de reducción para cada año objetivo
        
    Returns:
        dict: Objetivos de reducción para cada horizonte temporal
    """
    if len(target_years) != len(reduction_percentages):
        logger.error("Las listas de años objetivo y porcentajes de reducción deben tener la misma longitud")
        return {}
    
    targets = {}
    current_year = datetime.now().year
    
    for i, years in enumerate(target_years):
        target_year = current_year + years
        reduction_pct = reduction_percentages[i]
        target_emissions = current_annual_emissions * (1 - reduction_pct/100)
        
        targets[target_year] = {
            "target_emissions": target_emissions,
            "reduction_percentage": reduction_pct,
            "reduction_amount": current_annual_emissions - target_emissions
        }
    
    return targets 