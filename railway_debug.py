#!/usr/bin/env python3
"""
Script de diagnóstico para Railway deployment
Verifica configuración específica para Railway
"""

import os
import sys
import importlib

def check_port_config():
    """Verifica configuración de puerto"""
    port = os.environ.get('PORT', '8050')
    print(f"✅ Puerto configurado: {port}")
    return True

def check_critical_imports():
    """Verifica que las importaciones críticas funcionen"""
    critical_modules = [
        'dash', 'plotly', 'pandas', 'sqlalchemy', 
        'gunicorn', 'psycopg2', 'requests'
    ]
    
    failed = []
    for module in critical_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module} - OK")
        except ImportError as e:
            print(f"❌ {module} - ERROR: {e}")
            failed.append(module)
    
    return len(failed) == 0

def check_app_structure():
    """Verifica estructura de la aplicación"""
    required_files = [
        'app.py', 'requirements.txt', 'Dockerfile',
        'railway.json', 'Procfile'
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} - Existe")
        else:
            print(f"❌ {file} - NO ENCONTRADO")
            missing.append(file)
    
    return len(missing) == 0

def check_railway_config():
    """Verifica configuración específica de Railway"""
    import json
    
    # Verificar railway.json
    try:
        with open('railway.json', 'r') as f:
            config = json.load(f)
        
        if 'build' in config and config['build'].get('builder') == 'DOCKERFILE':
            print("✅ railway.json - Configuración correcta")
            return True
        else:
            print("❌ railway.json - Configuración incorrecta")
            return False
    except Exception as e:
        print(f"❌ railway.json - Error: {e}")
        return False

def main():
    print("🔍 DIAGNÓSTICO RAILWAY DEPLOYMENT")
    print("=" * 40)
    
    checks = [
        ("Configuración de Puerto", check_port_config),
        ("Importaciones Críticas", check_critical_imports),
        ("Estructura de Archivos", check_app_structure),
        ("Configuración Railway", check_railway_config)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n🔍 {name}:")
        result = check_func()
        all_passed = all_passed and result
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 TODAS LAS VERIFICACIONES PASARON")
        print("✅ Tu aplicación debería funcionar en Railway")
    else:
        print("⚠️  ALGUNOS PROBLEMAS DETECTADOS")
        print("❌ Revisa los errores arriba")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 