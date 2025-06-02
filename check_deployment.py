#!/usr/bin/env python3
"""
Script de verificación pre-deployment para Railway
Verifica que todos los archivos y configuraciones necesarias estén presentes
"""

import os
import sys
import json
from pathlib import Path

def check_file_exists(filepath, description):
    """Verifica si un archivo existe"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - NO ENCONTRADO")
        return False

def check_requirements():
    """Verifica requirements.txt"""
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt no encontrado")
        return False
    
    with open("requirements.txt", "r") as f:
        content = f.read()
        required_packages = ["dash", "gunicorn", "pandas", "sqlalchemy"]
        missing = []
        
        for package in required_packages:
            if package not in content.lower():
                missing.append(package)
        
        if missing:
            print(f"❌ Paquetes faltantes en requirements.txt: {missing}")
            return False
        else:
            print("✅ requirements.txt contiene paquetes esenciales")
            return True

def check_app_py():
    """Verifica configuración en app.py"""
    if not os.path.exists("app.py"):
        print("❌ app.py no encontrado")
        return False
    
    with open("app.py", "r") as f:
        content = f.read()
        
        checks = [
            ("server = app.server", "Configuración WSGI para gunicorn"),
            ("os.getenv('PORT'", "Configuración de puerto desde entorno"),
            ("os.getenv('HOST'", "Configuración de host desde entorno"),
        ]
        
        all_good = True
        for check, description in checks:
            if check in content:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - NO ENCONTRADO en app.py")
                all_good = False
        
        return all_good

def check_railway_json():
    """Verifica railway.json"""
    if not os.path.exists("railway.json"):
        print("❌ railway.json no encontrado")
        return False
    
    try:
        with open("railway.json", "r") as f:
            config = json.load(f)
            
        required_keys = ["build", "deploy"]
        missing = [key for key in required_keys if key not in config]
        
        if missing:
            print(f"❌ Claves faltantes en railway.json: {missing}")
            return False
        else:
            print("✅ railway.json configurado correctamente")
            return True
    except json.JSONDecodeError:
        print("❌ railway.json tiene formato JSON inválido")
        return False

def check_dockerfile():
    """Verifica Dockerfile"""
    if not os.path.exists("Dockerfile"):
        print("❌ Dockerfile no encontrado")
        return False
    
    with open("Dockerfile", "r") as f:
        content = f.read()
        
        checks = [
            ("FROM python:", "Imagen base de Python"),
            ("COPY requirements.txt", "Copia de requirements.txt"),
            ("RUN pip install", "Instalación de dependencias"),
            ("EXPOSE", "Puerto expuesto"),
            ("CMD", "Comando de inicio"),
        ]
        
        all_good = True
        for check, description in checks:
            if check in content:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - NO ENCONTRADO en Dockerfile")
                all_good = False
        
        return all_good

def check_gitignore():
    """Verifica .gitignore"""
    if not os.path.exists(".gitignore"):
        print("❌ .gitignore no encontrado")
        return False
    
    with open(".gitignore", "r") as f:
        content = f.read()
        
        critical_ignores = [".env", "__pycache__", "*.log"]
        missing = []
        
        for ignore in critical_ignores:
            if ignore not in content:
                missing.append(ignore)
        
        if missing:
            print(f"❌ Patrones críticos faltantes en .gitignore: {missing}")
            return False
        else:
            print("✅ .gitignore configurado correctamente")
            return True

def check_sensitive_files():
    """Verifica que no haya archivos sensibles"""
    sensitive_files = [".env", ".env.local", ".env.production"]
    found_sensitive = []
    
    for file in sensitive_files:
        if os.path.exists(file):
            found_sensitive.append(file)
    
    if found_sensitive:
        print(f"⚠️  ADVERTENCIA: Archivos sensibles encontrados: {found_sensitive}")
        print("   Asegúrate de que estén en .gitignore y no se suban al repositorio")
        return False
    else:
        print("✅ No se encontraron archivos sensibles en el directorio")
        return True

def main():
    """Función principal"""
    print("🔍 Verificando configuración para deployment en Railway...\n")
    
    checks = [
        (lambda: check_file_exists("railway.json", "Configuración de Railway"), True),
        (lambda: check_file_exists("Procfile", "Procfile (respaldo)"), False),
        (lambda: check_file_exists("env.example", "Ejemplo de variables de entorno"), False),
        (check_requirements, True),
        (check_app_py, True),
        (check_railway_json, True),
        (check_dockerfile, True),
        (check_gitignore, True),
        (check_sensitive_files, False),  # False = no crítico
    ]
    
    critical_failed = 0
    warnings = 0
    
    for check_func, is_critical in checks:
        try:
            result = check_func()
            if not result:
                if is_critical:
                    critical_failed += 1
                else:
                    warnings += 1
        except Exception as e:
            print(f"❌ Error ejecutando verificación: {e}")
            if is_critical:
                critical_failed += 1
        print()  # Línea en blanco
    
    print("=" * 50)
    
    if critical_failed == 0:
        print("🎉 ¡Todas las verificaciones críticas pasaron!")
        print("✅ Tu proyecto está listo para deployment en Railway")
        
        if warnings > 0:
            print(f"⚠️  {warnings} advertencia(s) encontrada(s), pero no son críticas")
        
        print("\n📋 Próximos pasos:")
        print("1. Haz commit de todos los cambios")
        print("2. Sube el código a tu repositorio Git")
        print("3. Ve a railway.app y crea un nuevo proyecto")
        print("4. Conecta tu repositorio")
        print("5. Configura las variables de entorno")
        print("6. ¡Despliega!")
        
        return 0
    else:
        print(f"❌ {critical_failed} verificación(es) crítica(s) fallaron")
        print("🔧 Corrige los problemas antes de hacer deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 