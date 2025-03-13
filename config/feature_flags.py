# config/feature_flags.py
import os
import json

# Ruta al archivo de configuración de feature flags
FEATURE_FLAGS_FILE = "config/feature_flags.json"

# Feature flags por defecto
DEFAULT_FEATURE_FLAGS = {
    'enable_anomaly_detection': False,
    'enable_anomaly_visualization': False,
    'enable_anomaly_correction': False
}

def load_feature_flags():
    """Carga los feature flags desde el archivo de configuración"""
    try:
        if os.path.exists(FEATURE_FLAGS_FILE):
            with open(FEATURE_FLAGS_FILE, 'r') as f:
                return json.load(f)
        else:
            # Si no existe el archivo, crear con valores por defecto
            save_feature_flags(DEFAULT_FEATURE_FLAGS)
            return DEFAULT_FEATURE_FLAGS
    except Exception as e:
        print(f"Error al cargar feature flags: {str(e)}")
        return DEFAULT_FEATURE_FLAGS

def save_feature_flags(flags):
    """Guarda los feature flags en el archivo de configuración"""
    try:
        os.makedirs(os.path.dirname(FEATURE_FLAGS_FILE), exist_ok=True)
        with open(FEATURE_FLAGS_FILE, 'w') as f:
            json.dump(flags, f, indent=2)
        return True
    except Exception as e:
        print(f"Error al guardar feature flags: {str(e)}")
        return False

def is_feature_enabled(feature_name):
    """Verifica si un feature flag está habilitado"""
    flags = load_feature_flags()
    return flags.get(feature_name, DEFAULT_FEATURE_FLAGS.get(feature_name, False))

def enable_feature(feature_name):
    """Habilita un feature flag"""
    flags = load_feature_flags()
    flags[feature_name] = True
    return save_feature_flags(flags)

def disable_feature(feature_name):
    """Deshabilita un feature flag"""
    flags = load_feature_flags()
    flags[feature_name] = False
    return save_feature_flags(flags)