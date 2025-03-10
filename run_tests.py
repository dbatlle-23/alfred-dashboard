#!/usr/bin/env python
"""
Script para ejecutar pruebas unitarias sin depender de pytest-dash.
Utiliza unittest directamente para evitar problemas con Selenium y webdriver.Opera.
"""

import os
import sys
import unittest

def run_tests():
    """
    Ejecuta las pruebas unitarias utilizando unittest.
    
    Returns:
        int: Código de salida (0 si todas las pruebas pasan, 1 si hay errores)
    """
    # Configurar el path para importar módulos
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # Importar el módulo de pruebas
    from tests.test_data_loader import TestDataLoader
    
    # Crear un suite de pruebas
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDataLoader)
    
    # Ejecutar las pruebas
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Devolver código de salida
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests()) 