#!/usr/bin/env python
import unittest
import sys
import os

# Añadir el directorio raíz al path para poder importar desde utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importar los módulos de prueba
from test_extract_asset_and_tag import TestExtractAssetAndTag

def run_tests():
    """Ejecutar todas las pruebas unitarias"""
    
    # Crear el test suite
    test_suite = unittest.TestSuite()
    
    # Añadir las pruebas de extract_asset_and_tag
    test_suite.addTest(unittest.makeSuite(TestExtractAssetAndTag))
    
    # Ejecutar las pruebas
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Retornar el código de salida basado en el resultado
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests()) 