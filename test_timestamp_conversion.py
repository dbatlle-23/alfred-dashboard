#!/usr/bin/env python3
"""
Script para probar la conversión de timestamp
"""

from datetime import datetime

def main():
    # Timestamp del archivo que contiene 1970-01-21 (formato incorrecto)
    timestamp_original = 1742544410.0
    
    # Convertir el timestamp según la lógica original (dividiendo por 1000)
    date_original = datetime.fromtimestamp(timestamp_original / 1000).strftime("%Y-%m-%d")
    
    # Convertir el timestamp según la lógica corregida (sin dividir por 1000)
    date_corrected = datetime.fromtimestamp(timestamp_original).strftime("%Y-%m-%d")
    
    print(f"Timestamp original: {timestamp_original}")
    print(f"Fecha con lógica original (dividido por 1000): {date_original}")
    print(f"Fecha con lógica corregida (sin dividir): {date_corrected}")

if __name__ == "__main__":
    main() 