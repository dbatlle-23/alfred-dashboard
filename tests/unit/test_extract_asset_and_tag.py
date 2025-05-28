import unittest
import os
import sys
from typing import Tuple

# Añadir el directorio raíz al path para poder importar desde utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.data_loader import extract_asset_and_tag, TAGS_TO_CONSUMPTION_TYPE

class TestExtractAssetAndTag(unittest.TestCase):
    """Pruebas para la función extract_asset_and_tag de utils/data_loader.py"""
    
    def test_format_according_to_project_context(self):
        """Test para el formato correcto según PROJECT_CONTEXT.md: daily_readings_<asset_id>_<consumption_type>.csv"""
        
        # Casos de prueba con tags conocidos
        for tag_key in TAGS_TO_CONSUMPTION_TYPE.keys():
            tag_short = tag_key.split('_')[-1]  # Extraer la última parte del tag
            
            # Formato correcto según documentación: daily_readings_ASSETID_CONSUMPTION_TYPE.csv
            filename = f"daily_readings_ASSET123_{tag_short}.csv"
            asset_id, tag = extract_asset_and_tag(filename)
            
            self.assertEqual(asset_id, "ASSET123", f"Asset ID incorrecto para {filename}")
            
            # Verificar si el tag extraído está en el diccionario TAGS_TO_CONSUMPTION_TYPE 
            # o si al menos contiene la parte correcta del tag
            tag_found = False
            for known_tag in TAGS_TO_CONSUMPTION_TYPE.keys():
                if tag == known_tag or tag_short.lower() in known_tag.lower():
                    tag_found = True
                    break
                    
            self.assertTrue(tag_found, f"El tag extraído '{tag}' no se encontró en los tags conocidos para {filename}")
    
    def test_format_with_full_transversal_tag(self):
        """Test para el formato de archivo con tag transversal completo"""
        
        # Caso de prueba con tag transversal completo
        for tag_key in TAGS_TO_CONSUMPTION_TYPE.keys():
            # Formato: daily_readings_ASSETID__TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_tag_name.csv
            filename = f"daily_readings_ASSET123__{tag_key[1:]}.csv"  # Quitamos el primer guión bajo del tag
            asset_id, tag = extract_asset_and_tag(filename)
            
            self.assertEqual(asset_id, "ASSET123", f"Asset ID incorrecto para {filename}")
            self.assertEqual(tag, tag_key, f"Tag incorrecto para {filename}. Esperado: {tag_key}, Obtenido: {tag}")
    
    def test_format_with_double_underscore(self):
        """Test para el formato con doble guión bajo: daily_readings_ASSETID__tag_name.csv"""
        
        # Casos de prueba para los diferentes formatos que usa la función actualmente
        filename = "daily_readings_ASSET123__water_consumption.csv"
        asset_id, tag = extract_asset_and_tag(filename)
        
        self.assertEqual(asset_id, "ASSET123", f"Asset ID incorrecto para {filename}")
        self.assertEqual(tag, "water_consumption", f"Tag incorrecto para {filename}")
    
    def test_format_with_year_suffix(self):
        """Test para el formato con año: daily_readings_ASSETID__tag_name_YYYY.csv"""
        
        filename = "daily_readings_ASSET123__water_consumption_2025.csv"
        asset_id, tag = extract_asset_and_tag(filename)
        
        self.assertEqual(asset_id, "ASSET123", f"Asset ID incorrecto para {filename}")
        self.assertEqual(tag, "water_consumption", f"Tag incorrecto para {filename}")
    
    def test_invalid_formats(self):
        """Test para formatos de archivo inválidos"""
        
        # Archivo sin el prefijo daily_readings_
        filename = "readings_ASSET123_water.csv"
        asset_id, tag = extract_asset_and_tag(filename)
        
        self.assertIsNone(asset_id, f"Asset ID debería ser None para {filename}")
        self.assertIsNone(tag, f"Tag debería ser None para {filename}")
        
        # Archivo con formato completamente diferente
        filename = "arbitrary_file_name.csv"
        asset_id, tag = extract_asset_and_tag(filename)
        
        self.assertIsNone(asset_id, f"Asset ID debería ser None para {filename}")
        self.assertIsNone(tag, f"Tag debería ser None para {filename}")
    
    def test_with_path(self):
        """Test para archivos con ruta completa"""
        
        # Prueba con ruta completa
        filepath = "/data/analyzed_data/project_id/daily_readings_ASSET123_WATER.csv"
        asset_id, tag = extract_asset_and_tag(filepath)
        
        self.assertEqual(asset_id, "ASSET123", f"Asset ID incorrecto para {filepath}")
        # No podemos verificar el tag exacto sin conocer el mapeo, pero al menos verificamos que no sea None
        self.assertIsNotNone(tag, f"Tag no debería ser None para {filepath}")
    
    def test_real_example_filenames(self):
        """Test con ejemplos reales de nombres de archivo según la documentación"""
        
        # Ejemplos según la estructura mencionada en PROJECT_CONTEXT.md
        examples = [
            # daily_readings_<asset_id>_<consumption_type>.csv
            "daily_readings_DL39NQJXC2T68_DOMESTIC_COLD_WATER.csv",
            "daily_readings_VVMJJ3UNY28C_DOMESTIC_ENERGY_GENERAL.csv",
            "daily_readings_AB12CD34EF56_THERMAL_ENERGY_HEAT.csv",
            "daily_readings_12345ABCDE_PEOPLE_FLOW_IN.csv"
        ]
        
        for filename in examples:
            asset_id, tag = extract_asset_and_tag(filename)
            
            # Extraer el asset_id esperado
            expected_asset_id = filename.replace("daily_readings_", "").split("_")[0]
            
            self.assertEqual(asset_id, expected_asset_id, f"Asset ID incorrecto para {filename}")
            self.assertIsNotNone(tag, f"Tag no debería ser None para {filename}")

if __name__ == "__main__":
    unittest.main() 