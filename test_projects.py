#!/usr/bin/env python
"""
Script para probar la función get_projects con diferentes client_ids
"""
import os
import sys
import json

# Configurar el entorno para usar el modo de simulación
os.environ["MOCK_API"] = "true"
os.environ["ENVIRONMENT"] = "development"

# Importar las funciones necesarias
from utils.api import get_projects, get_projects_fallback
from utils.auth import auth_service

def test_get_projects():
    """
    Prueba la función get_projects con diferentes client_ids
    """
    print("\n" + "="*80)
    print("PRUEBA DE get_projects")
    print("="*80)
    
    # Obtener un token JWT (simulado)
    token = auth_service.get_token()
    print(f"Token JWT: {'Presente' if token else 'No presente'}")
    
    # Probar con diferentes client_ids
    client_ids = ["1", "2", "3", "4", "all", None]
    
    for client_id in client_ids:
        print("\n" + "-"*80)
        print(f"Probando get_projects con client_id: {client_id}")
        print("-"*80)
        
        # Llamar a get_projects
        projects = get_projects(client_id=client_id, jwt_token=token)
        
        # Mostrar resultados
        print(f"Número de proyectos obtenidos: {len(projects) if projects else 0}")
        if projects:
            print("Detalles de los proyectos:")
            for i, project in enumerate(projects):
                print(f"Proyecto {i+1}:")
                print(f"  ID: {project.get('id', 'N/A')}")
                print(f"  Nombre: {project.get('name', 'N/A')}")
                if "client" in project and isinstance(project["client"], dict):
                    print(f"  Cliente ID: {project['client'].get('id', 'N/A')}")
                    print(f"  Cliente Nombre: {project['client'].get('name', 'N/A')}")
                else:
                    print("  Cliente: No especificado")
        else:
            print("No se encontraron proyectos")
    
    print("\n" + "="*80)
    print("PRUEBA DE get_projects_fallback")
    print("="*80)
    
    # Probar get_projects_fallback directamente
    for client_id in client_ids:
        print("\n" + "-"*80)
        print(f"Probando get_projects_fallback con client_id: {client_id}")
        print("-"*80)
        
        # Llamar a get_projects_fallback
        projects = get_projects_fallback(client_id=client_id)
        
        # Mostrar resultados
        print(f"Número de proyectos obtenidos: {len(projects) if projects else 0}")
        if projects:
            print("Detalles de los proyectos:")
            for i, project in enumerate(projects):
                print(f"Proyecto {i+1}:")
                print(f"  ID: {project.get('id', 'N/A')}")
                print(f"  Nombre: {project.get('name', 'N/A')}")
                if "client" in project and isinstance(project["client"], dict):
                    print(f"  Cliente ID: {project['client'].get('id', 'N/A')}")
                    print(f"  Cliente Nombre: {project['client'].get('name', 'N/A')}")
                else:
                    print("  Cliente: No especificado")
        else:
            print("No se encontraron proyectos")

if __name__ == "__main__":
    test_get_projects() 