import requests
import json
from utils.logging import get_logger
from utils.auth import auth_service, AuthService
import os
import concurrent.futures
from datetime import datetime, timedelta
import os
from tqdm import tqdm
import pandas as pd
import re
import pickle
import glob
import shutil

logger = get_logger(__name__)

# Configuración de la API
BASE_URL = "https://services.alfredsmartdata.com"
CLIENTS_ENDPOINT = f"{BASE_URL}/clients"
PROJECTS_ENDPOINT = f"{BASE_URL}/projects"
ASSETS_ENDPOINT = f"{BASE_URL}/assets"

# Función para obtener los headers de autenticación
def get_auth_headers(jwt_token=None):
    """
    Obtiene los headers de autenticación para las llamadas a la API
    
    Args:
        jwt_token: Token JWT (opcional)
        
    Returns:
        dict: Headers de autenticación
    """
    if jwt_token:
        # Usar el token JWT proporcionado
        return auth_service.get_auth_headers_from_token(jwt_token)
    else:
        # Si no hay token JWT, devolver headers vacíos
        logger.warning("No se proporcionó token JWT para obtener headers de autenticación")
        return {}

def extract_list_from_response(data, fallback_func, item_type="items", client_id=None):
    """
    Extrae una lista de elementos de una respuesta de API que puede tener diferentes estructuras
    
    Args:
        data: Datos de respuesta de la API
        fallback_func: Función para obtener datos de fallback
        item_type: Tipo de elementos que se están extrayendo (para mensajes de log)
        client_id: ID de cliente para filtrar (opcional)
        
    Returns:
        list: Lista de elementos extraída o datos de fallback
    """
    # Registrar la estructura de los datos recibida para depuración
    logger.debug(f"Estructura de datos recibida para {item_type}: {type(data)}")
    
    # Caso especial para clientes - verificar si hay una estructura específica para clientes
    if item_type == "clients" and isinstance(data, dict):
        # Verificar si hay una estructura específica para clientes en la API de Alfred
        if "clients" in data and isinstance(data["clients"], list):
            logger.debug(f"Encontrada lista de clientes en la clave 'clients' con {len(data['clients'])} elementos")
            return data["clients"]
        elif "data" in data and isinstance(data["data"], list):
            logger.debug(f"Encontrada lista de clientes en la clave 'data' con {len(data['data'])} elementos")
            return data["data"]
        elif "results" in data and isinstance(data["results"], list):
            logger.debug(f"Encontrada lista de clientes en la clave 'results' con {len(data['results'])} elementos")
            return data["results"]
        
        # Verificar si hay una estructura anidada común en APIs
        if "data" in data and isinstance(data["data"], dict) and "clients" in data["data"] and isinstance(data["data"]["clients"], list):
            logger.debug(f"Encontrada lista de clientes en data.clients con {len(data['data']['clients'])} elementos")
            return data["data"]["clients"]
    
    # Si hay un error en la respuesta, usar fallback
    if isinstance(data, dict) and "error" in data:
        logger.error(f"Error en la respuesta para {item_type}: {data.get('error')}")
        return fallback_func(client_id) if item_type == "projects" else fallback_func()
    
    # Si la respuesta ya es una lista, usarla directamente
    if isinstance(data, list):
        logger.debug(f"La respuesta ya es una lista con {len(data)} elementos")
        # Verificar si los elementos parecen ser del tipo correcto
        if len(data) > 0 and isinstance(data[0], dict):
            logger.debug(f"Primer elemento de la lista: {data[0]}")
            return data
    
    # Si la respuesta es un diccionario, buscar la lista en diferentes claves
    if isinstance(data, dict):
        # Claves comunes donde podría estar la lista
        possible_keys = ['data', item_type, 'results', 'items', 'clients', 'projects', 'response']
        
        # Primero buscar en las claves más probables
        for key in possible_keys:
            if key in data and isinstance(data[key], list):
                logger.debug(f"Encontrada lista en la clave '{key}' con {len(data[key])} elementos")
                if len(data[key]) > 0:
                    logger.debug(f"Primer elemento de la lista: {data[key][0]}")
                return data[key]
        
        # Si no encontramos la lista en las claves comunes, buscar en todas las claves
        for key, value in data.items():
            if isinstance(value, list):
                logger.debug(f"Encontrada lista en la clave '{key}' con {len(value)} elementos")
                if len(value) > 0:
                    logger.debug(f"Primer elemento de la lista: {value[0]}")
                return value
            
            # Si el valor es un diccionario, buscar recursivamente
            if isinstance(value, dict):
                logger.debug(f"Buscando recursivamente en la clave '{key}'")
                result = extract_list_from_response(value, lambda: [], item_type, client_id)
                if result and len(result) > 0:
                    return result
    
    # Si no encontramos la lista, usar fallback
    logger.warning(f"No se pudo encontrar una lista de {item_type} en la respuesta")
    return fallback_func(client_id) if item_type == "projects" else fallback_func()

def get_clientes(jwt_token=None):
    """
    Obtiene la lista de clientes desde la API
    
    Args:
        jwt_token: Token JWT para autenticación (opcional)
        
    Returns:
        list: Lista de clientes con formato [{id, nombre, ...}]
    """
    try:
        # Verificar autenticación
        if jwt_token:
            # Usar el token JWT proporcionado
            logger.debug(f"Verificando autenticación con token JWT: {jwt_token[:10]}...")
            if not auth_service.is_authenticated(jwt_token):
                logger.warning("Token JWT inválido para obtener clientes")
                return get_clientes_fallback()
                
            # Endpoint para clientes (sin la URL base)
            endpoint = "clients"
            
            logger.debug(f"Obteniendo clientes con endpoint: {endpoint}")
            
            # Hacer la solicitud a la API con el token JWT
            logger.debug("Realizando solicitud a la API para obtener clientes")
            response = auth_service.make_api_request(jwt_token, "GET", endpoint)
            logger.debug(f"Respuesta recibida de la API: {type(response)}")
            
            # Registrar la respuesta completa para depuración
            if isinstance(response, dict):
                logger.debug(f"Claves en la respuesta: {list(response.keys())}")
                # Imprimir los primeros 5 elementos si hay una lista en la respuesta
                for key, value in response.items():
                    if isinstance(value, list) and len(value) > 0:
                        logger.debug(f"Lista encontrada en clave '{key}' con {len(value)} elementos")
                        logger.debug(f"Primeros elementos: {value[:min(5, len(value))]}")
            elif isinstance(response, list):
                logger.debug(f"Respuesta es una lista con {len(response)} elementos")
                if len(response) > 0:
                    logger.debug(f"Primeros elementos: {response[:min(5, len(response))]}")
        else:
            # Si no hay token JWT, usar fallback directamente
            logger.info("No se proporcionó token JWT para obtener clientes (comportamiento normal durante inicialización)")
            return get_clientes_fallback()
        
        # Verificar si hay un error en la respuesta
        if isinstance(response, dict) and "error" in response:
            logger.error(f"Error al obtener clientes: {response.get('error')}")
            return get_clientes_fallback()
        
        # Extraer la lista de clientes de la respuesta
        clientes = extract_list_from_response(response, get_clientes_fallback, "clients")
        logger.debug(f"Clientes extraídos: {len(clientes) if isinstance(clientes, list) else 'no es lista'}")
        return clientes
    except Exception as e:
        logger.error(f"Error al obtener clientes: {str(e)}")
        # En caso de excepción, devolver datos de ejemplo como fallback
        return get_clientes_fallback()

def get_clientes_fallback():
    """
    Devuelve datos de ejemplo de clientes como fallback
    
    Returns:
        list: Lista de clientes de ejemplo
    """
    logger.debug("Usando datos de fallback para clientes")
    return [
        {"id": 1, "nombre": "Cliente A (FALLBACK - NO REAL)", "name": "Cliente A (FALLBACK - NO REAL)", "codigo": "CA", "client_id": 1},
        {"id": 2, "nombre": "Cliente B (FALLBACK - NO REAL)", "name": "Cliente B (FALLBACK - NO REAL)", "codigo": "CB", "client_id": 2},
        {"id": 3, "nombre": "Cliente C (FALLBACK - NO REAL)", "name": "Cliente C (FALLBACK - NO REAL)", "codigo": "CC", "client_id": 3},
        {"id": 4, "nombre": "Cliente D (FALLBACK - NO REAL)", "name": "Cliente D (FALLBACK - NO REAL)", "codigo": "CD", "client_id": 4},
    ]

def get_projects(client_id=None, jwt_token=None):
    """
    Obtiene la lista de proyectos desde la API
    
    Args:
        client_id: ID del cliente para filtrar proyectos (opcional)
        jwt_token: Token JWT para autenticación (opcional)
        
    Returns:
        list: Lista de proyectos con formato [{id, name, ...}]
    """
    try:
        # Verificar si estamos en modo debug
        debug_mode = os.environ.get("DASH_DEBUG", "false").lower() == 'true'
        
        if debug_mode:
            print("\n" + "-"*80)
            print(f"[DEBUG API] INICIO get_projects - client_id: {client_id}")
        
        # Verificar autenticación
        if jwt_token:
            # Usar el token JWT proporcionado
            if debug_mode:
                print(f"[DEBUG API] get_projects - Verificando autenticación con token JWT: {jwt_token[:10]}...")
            if not auth_service.is_authenticated(jwt_token):
                if debug_mode:
                    print("[DEBUG API] get_projects - Token JWT inválido para obtener proyectos")
                    print(f"[DEBUG API] get_projects - Usando fallback para client_id: {client_id}")
                return get_projects_fallback(client_id)
            
            # Construir el endpoint y los parámetros
            endpoint = "projects"
            params = {}
            
            # Añadir el client como parámetro si está presente (no client_id)
            if client_id and client_id != "all":
                if debug_mode:
                    print(f"[DEBUG API] get_projects - Añadiendo filtro de cliente: {client_id}")
                params["client"] = client_id  # Usar 'client' en lugar de 'client_id'
            
            if debug_mode:
                print(f"[DEBUG API] get_projects - Endpoint: {endpoint}, Parámetros: {params}")
            
            # Hacer la solicitud a la API con el token JWT
            if debug_mode:
                print("[DEBUG API] get_projects - Realizando solicitud a la API")
            response = auth_service.make_api_request(jwt_token, "GET", endpoint, params=params)
            if debug_mode:
                print(f"[DEBUG API] get_projects - Respuesta recibida de la API: {type(response)}")
            
            # Extraer la lista de proyectos de la respuesta
            projects = extract_list_from_response(response, lambda: get_projects_fallback(client_id), "data")
            
            # Filtrar por cliente si es necesario
            if client_id and client_id != "all" and projects:
                if debug_mode:
                    print(f"[DEBUG API] get_projects - Verificando filtro de cliente para {len(projects)} proyectos")
                # Filtrar proyectos que pertenecen al cliente especificado
                filtered_projects = []
                for project in projects:
                    # Verificar si el proyecto tiene información de cliente
                    if isinstance(project, dict) and "client" in project:
                        project_client = project["client"]
                        if isinstance(project_client, dict) and "id" in project_client:
                            if project_client["id"] == client_id:
                                filtered_projects.append(project)
                
                if debug_mode:
                    print(f"[DEBUG API] get_projects - Proyectos filtrados por cliente: {len(filtered_projects)} de {len(projects)}")
                projects = filtered_projects
            
            if debug_mode:
                print(f"[DEBUG API] get_projects - Total de proyectos devueltos: {len(projects)}")
                print(f"[DEBUG API] FIN get_projects")
                print("-"*80)
            return projects
        else:
            # Si no hay token JWT, usar datos de fallback
            if debug_mode:
                print("[DEBUG API] get_projects - No hay token JWT, usando datos de fallback")
                print(f"[DEBUG API] FIN get_projects")
                print("-"*80)
            return get_projects_fallback(client_id)
    except Exception as e:
        logger.error(f"Error al obtener proyectos: {str(e)}")
        if os.environ.get("DASH_DEBUG", "false").lower() == 'true':
            print(f"[ERROR API] get_projects: {str(e)}")
            import traceback
            print(traceback.format_exc())
            print(f"[DEBUG API] FIN get_projects (con error)")
            print("-"*80)
        return get_projects_fallback(client_id)

def get_projects_fallback(client_id=None):
    """
    Función de fallback que devuelve datos de ejemplo para proyectos
    cuando no se puede acceder a la API
    
    Args:
        client_id: ID del cliente para filtrar proyectos (opcional)
        
    Returns:
        list: Lista de proyectos de ejemplo
    """
    print("\n" + "-"*80)
    print(f"[DEBUG API] INICIO get_projects_fallback - client_id: {client_id}")
    
    # Datos de ejemplo para proyectos
    projects = [
        {
            "id": "1",
            "name": "Edificio Central",
            "logo": "https://example.com/logo1.png",
            "background_image": "https://example.com/bg1.jpg",
            "client": {
                "id": "1",
                "name": "Cliente A"
            },
            "type": "office",
            "status": "active"
        },
        {
            "id": "2",
            "name": "Campus Tecnológico",
            "logo": "https://example.com/logo2.png",
            "background_image": "https://example.com/bg2.jpg",
            "client": {
                "id": "1",
                "name": "Cliente A"
            },
            "type": "campus",
            "status": "active"
        },
        {
            "id": "3",
            "name": "Torre Norte",
            "logo": "https://example.com/logo3.png",
            "background_image": "https://example.com/bg3.jpg",
            "client": {
                "id": "2",
                "name": "Cliente B"
            },
            "type": "office",
            "status": "active"
        },
        {
            "id": "4",
            "name": "Centro Comercial Este",
            "logo": "https://example.com/logo4.png",
            "background_image": "https://example.com/bg4.jpg",
            "client": {
                "id": "2",
                "name": "Cliente B"
            },
            "type": "retail",
            "status": "active"
        },
        {
            "id": "5",
            "name": "Hospital Sur",
            "logo": "https://example.com/logo5.png",
            "background_image": "https://example.com/bg5.jpg",
            "client": {
                "id": "3",
                "name": "Cliente C"
            },
            "type": "healthcare",
            "status": "active"
        },
        {
            "id": "6",
            "name": "Complejo Deportivo",
            "logo": "https://example.com/logo6.png",
            "background_image": "https://example.com/bg6.jpg",
            "client": {
                "id": "3",
                "name": "Cliente C"
            },
            "type": "sports",
            "status": "active"
        },
        {
            "id": "7",
            "name": "Edificio Problemático",
            "logo": "https://example.com/logo7.png",
            "background_image": "https://example.com/bg7.jpg",
            "client": {
                "id": "4",
                "name": "Cliente Problemático"
            },
            "type": "office",
            "status": "active"
        }
    ]
    
    # Filtrar por cliente si se proporciona un client_id
    if client_id and client_id != "all":
        print(f"[DEBUG API] get_projects_fallback - Filtrando proyectos por client_id: {client_id}")
        filtered_projects = []
        for project in projects:
            if "client" in project and isinstance(project["client"], dict) and "id" in project["client"]:
                project_client_id = str(project["client"]["id"])
                print(f"[DEBUG API] get_projects_fallback - Proyecto {project.get('id', 'N/A')} tiene client_id: {project_client_id}")
                if project_client_id == str(client_id):
                    filtered_projects.append(project)
        
        print(f"[DEBUG API] get_projects_fallback - Proyectos filtrados: {len(filtered_projects)} de {len(projects)}")
        
        # Si no hay proyectos para este cliente, crear algunos genéricos
        if not filtered_projects:
            print(f"[DEBUG API] get_projects_fallback - No se encontraron proyectos para el cliente {client_id}, creando proyectos genéricos")
            for i in range(1, 4):  # Crear 3 proyectos genéricos
                filtered_projects.append({
                    "id": f"generic_{client_id}_{i}",
                    "name": f"Proyecto {i} (Cliente {client_id})",
                    "logo": "https://example.com/generic_logo.png",
                    "background_image": "https://example.com/generic_bg.jpg",
                    "client": {
                        "id": client_id,
                        "name": f"Cliente {client_id}"
                    },
                    "type": "generic",
                    "status": "active"
                })
            print(f"[DEBUG API] get_projects_fallback - Creados {len(filtered_projects)} proyectos genéricos para el cliente {client_id}")
        
        print(f"[DEBUG API] get_projects_fallback - Devolviendo {len(filtered_projects)} proyectos para el cliente {client_id}")
        print(f"[DEBUG API] FIN get_projects_fallback")
        print("-"*80 + "\n")
        return filtered_projects
    
    print(f"[DEBUG API] get_projects_fallback - Devolviendo todos los proyectos ({len(projects)})")
    print(f"[DEBUG API] FIN get_projects_fallback")
    print("-"*80 + "\n")
    return projects

def get_assets(project_id=None, client_id=None, jwt_token=None):
    """
    Obtiene la lista de assets desde la API
    
    Args:
        project_id: ID del proyecto para filtrar los assets (opcional)
        client_id: ID del cliente para filtrar los assets (opcional)
        jwt_token: Token JWT para autenticación (opcional)
        
    Returns:
        list: Lista de assets con formato [{id, nombre, ...}]
    """
    try:
        # Verificar si hay un token JWT válido
        if not jwt_token:
            token = auth_service.get_token()
            if not token:
                # Si no hay token, usar el fallback silenciosamente sin mostrar mensajes
                # Es normal que no haya token en muchos casos
                return get_assets_fallback(project_id)
        else:
            token = jwt_token
        
        # Parámetros de consulta
        params = {}
        
        # Añadir parámetros de filtro si se proporcionan
        if project_id and project_id != "all":
            # Si tenemos un project_id específico, usamos el endpoint de assets del proyecto
            logger.info(f"Solicitando assets para el proyecto {project_id}")
            
            # Construir la URL del endpoint
            endpoint = f"projects/{project_id}/assets"
            
            # Realizar la solicitud a la API
            response_data = auth_service.make_api_request(token, "GET", endpoint, params=params)
            
            # Verificar si hubo un error en la solicitud
            if "error" in response_data:
                logger.debug(f"Error al obtener assets del proyecto {project_id}: {response_data.get('error')}")
                return get_assets_fallback(project_id)
            
            # Extraer la lista de assets de la respuesta
            assets = extract_list_from_response(response_data, lambda: get_assets_fallback(project_id), "assets")
            
            # Registrar el resultado
            logger.info(f"Solicitud de assets exitosa para el proyecto {project_id}")
            logger.info(f"Se obtuvieron {len(assets)} assets para el proyecto {project_id}")
            
            return assets
        elif client_id and client_id != "all":
            # Si tenemos un client_id, filtramos los assets por cliente
            params["client"] = client_id
            
            # Construir la URL del endpoint
            endpoint = "assets"
            
            # Realizar la solicitud a la API
            response_data = auth_service.make_api_request(token, "GET", endpoint, params=params)
            
            # Verificar si hubo un error en la solicitud
            if "error" in response_data:
                logger.debug(f"Error al obtener assets del cliente {client_id}: {response_data.get('error')}")
                return []
            
            # Extraer la lista de assets de la respuesta
            assets = extract_list_from_response(response_data, lambda: [], "assets")
            
            # Registrar el resultado
            logger.info(f"Solicitud de assets exitosa para el cliente {client_id}")
            logger.info(f"Se obtuvieron {len(assets)} assets para el cliente {client_id}")
            
            return assets
        else:
            # Si no tenemos filtros, devolvemos una lista vacía
            # No es recomendable obtener todos los assets sin filtros
            logger.debug("No se proporcionó client_id ni project_id para filtrar assets")
            return []
    except Exception as e:
        logger.error(f"Error al obtener assets: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return get_assets_fallback(project_id)

def get_assets_fallback(project_id=None):
    """
    Devuelve datos de ejemplo de assets como fallback
    
    Args:
        project_id: ID del proyecto para filtrar (opcional)
        
    Returns:
        list: Lista de assets de ejemplo
    """
    logger.debug("Usando datos de fallback para assets")
    
    # Datos de ejemplo para assets
    assets = [
        {"id": "A1", "nombre": "Asset 1", "name": "Asset 1", "project_id": "P1"},
        {"id": "A2", "nombre": "Asset 2", "name": "Asset 2", "project_id": "P1"},
        {"id": "A3", "nombre": "Asset 3", "name": "Asset 3", "project_id": "P2"},
        {"id": "A4", "nombre": "Asset 4", "name": "Asset 4", "project_id": "P2"},
        {"id": "A5", "nombre": "Asset 5", "name": "Asset 5", "project_id": "P3"},
        {"id": "A6", "nombre": "Asset 6", "name": "Asset 6", "project_id": "P4"}
    ]
    
    # Filtrar por proyecto si se proporciona
    if project_id and project_id != "all":
        assets = [a for a in assets if a["project_id"] == project_id]
    
    return assets

def get_project_assets(project_id, jwt_token=None):
    """
    Obtiene los activos de un proyecto específico.
    
    Args:
        project_id (str): ID del proyecto.
        jwt_token (str, optional): Token JWT para autenticación.
    
    Returns:
        list: Lista de activos o lista vacía en caso de error.
    """
    if not project_id or project_id == "all":
        logger.debug("Se requiere un project_id válido para obtener los assets del proyecto")
        return []
        
    try:
        # Verificar si hay un token JWT válido
        if not jwt_token:
            token = auth_service.get_token()
            if not token:
                # Si no hay token, devolver lista vacía silenciosamente
                # Es normal que no haya token en muchos casos
                return []
        else:
            token = jwt_token
            
        # Construir la URL del endpoint
        url = f"{BASE_URL}/projects/{project_id}/assets"
        
        # Parámetros de consulta
        params = {"page[number]": 1, "page[size]": 1000}
        
        # Realizar la solicitud a la API
        headers = get_auth_headers(token)
        logger.info(f"Solicitando assets para el proyecto {project_id}")
        response = requests.get(url, headers=headers, params=params)
        
        # Verificar si la respuesta es exitosa
        if response.status_code == 200:
            logger.info(f"Solicitud de assets exitosa para el proyecto {project_id}")
            response_data = response.json()
            assets = response_data.get("data", [])
            logger.info(f"Se obtuvieron {len(assets)} assets para el proyecto {project_id}")
            return assets
        else:
            logger.error(f"Error al obtener assets del proyecto {project_id}: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Excepción al obtener assets del proyecto {project_id}: {str(e)}")
        return [] 

def get_sensors_with_tags(asset_id, token=None):
    """
    Obtiene los sensores disponibles de un asset, incluyendo el sensor_uuid, y los retorna.
    
    Args:
        asset_id (str): ID del asset
        token (str, optional): Token JWT para autenticación
        
    Returns:
        list: Lista de sensores con sus tags
    """
    url = f'{BASE_URL}/data/assets/{asset_id}/available-utilities-sensors'
    
    # Usar el token proporcionado o intentar obtenerlo del servicio de autenticación
    if not token:
        token = auth_service.get_token()
        
    # Si no hay token disponible, registrar un error y devolver lista vacía
    if not token:
        logger.error(f"No se pudo obtener un token JWT válido para consultar sensores del asset {asset_id}")
        return []
    
    # Usar get_auth_headers para obtener los headers de autenticación
    headers = get_auth_headers(token)
    
    # Añadir headers adicionales
    headers.update({
        'Accept': 'application/json, text/plain, */*',
    })
    
    logger.debug(f"[DEBUG] get_sensors_with_tags - Obteniendo sensores para el asset {asset_id}")
    
    # Añadir parámetros para obtener más información
    params = {
        "include_details": True,
        "active_only": True
    }
    
    try:
        logger.debug(f"[DEBUG] get_sensors_with_tags - URL: {url}, Params: {params}")
        response = requests.get(url, headers=headers, params=params)
        
        logger.debug(f"[DEBUG] get_sensors_with_tags - Status Code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            logger.debug(f"[DEBUG] get_sensors_with_tags - Respuesta completa: {response_data}")
            
            sensors = response_data.get('data', [])
            logger.debug(f"[DEBUG] get_sensors_with_tags - Sensores obtenidos: {sensors}")
            
            if not sensors:
                logger.warning(f"[WARNING] get_sensors_with_tags - No se encontraron sensores disponibles para el asset {asset_id}")
                return []
            else:
                sensor_list = []
                for sensor in sensors:
                    gateway_id = sensor.get('gateway_id')
                    device_id = sensor.get('device_id')
                    sensor_id = sensor.get('sensor_id')
                    tag_name = sensor.get('tag_name')
                    
                    logger.debug(f"[DEBUG] get_sensors_with_tags - Procesando sensor: gateway_id={gateway_id}, device_id={device_id}, sensor_id={sensor_id}, tag_name={tag_name}")

                    # Obtener el sensor_uuid utilizando la función auxiliar
                    sensor_uuid = get_sensor_uuid(gateway_id, device_id, sensor_id, token)
                    logger.debug(f"[DEBUG] get_sensors_with_tags - Sensor UUID obtenido: {sensor_uuid}")

                    # Agregar el sensor con todos sus datos al listado
                    sensor_data = {
                        "sensor_id": sensor_id,
                        "sensor_type": sensor.get('sensor_type'),
                        "tag_name": tag_name,
                        "sensor_uuid": sensor_uuid,
                        "gateway_id": gateway_id,
                        "device_id": device_id
                    }
                    sensor_list.append(sensor_data)
                    logger.debug(f"[DEBUG] get_sensors_with_tags - Sensor agregado: {sensor_data}")
                
                # Registrar información sobre los sensores encontrados
                logger.info(f"[INFO] get_sensors_with_tags - Se encontraron {len(sensor_list)} sensores para el asset {asset_id}")
                
                # Crear un diccionario para facilitar la búsqueda por tag_name
                sensor_dict = {}
                for s in sensor_list:
                    logger.debug(f"[DEBUG] get_sensors_with_tags - Sensor procesado: tag={s['tag_name']}, gateway={s['gateway_id']}, device={s['device_id']}, sensor={s['sensor_id']}")
                    if s['tag_name']:
                        sensor_dict[s['tag_name']] = s
                
                # Imprimir el diccionario final para depuración
                logger.debug(f"[DEBUG] get_sensors_with_tags - Diccionario de sensores final: {sensor_dict}")
                
                # Retornar la lista original como se espera
                return sensor_list
        else:
            logger.error(f"[ERROR] get_sensors_with_tags - Error al obtener sensores: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logger.error(f"[ERROR] get_sensors_with_tags - Excepción: {str(e)}")
        import traceback
        logger.error(f"[ERROR] get_sensors_with_tags - Traceback: {traceback.format_exc()}")
        return []

def ensure_project_folder_exists(project_id):
    """
    Asegura que exista una carpeta para un proyecto dentro del directorio analyzed_data.
    Valida el formato del project_id para mantener una estructura de carpetas coherente.
    """
    # Verificar si el project_id tiene formato incorrecto (comienza con "asset_")
    if project_id and isinstance(project_id, str) and project_id.startswith("asset_"):
        logger.warning(f"Se detectó un formato incorrecto de project_id: {project_id}")
        # Extraer el ID del asset del project_id incorrecto
        asset_id = project_id.replace("asset_", "")
        logger.info(f"Usando 'general' como project_id en lugar de asset_{asset_id}")
        project_id = "general"  # Usar una carpeta general para todos los assets sin proyecto

    logger.info(f"Asegurando que exista una carpeta para el proyecto {project_id} dentro del directorio analyzed_data.")
    base_folder = "data/analyzed_data"
    project_folder = os.path.join(base_folder, project_id)
    os.makedirs(project_folder, exist_ok=True)
    return project_folder

def get_asset_ids_from_project(project_id, token=None):
    """
    Obtiene los IDs de los assets de un proyecto.
    
    Args:
        project_id (str): ID del proyecto
        token (str, optional): Token JWT para autenticación
        
    Returns:
        list: Lista de IDs de assets
    """
    assets = get_project_assets(project_id, token)
    if not assets:
        return []
    
    return [asset.get("id") for asset in assets]

def process_asset_tags(asset_id, tags, project_folder, token=None):
    """
    Procesa las lecturas diarias para múltiples tags de un asset durante un año.
    Verifica si el archivo ya existe antes de procesar.
    
    Args:
        asset_id (str): ID del asset
        tags (list): Lista de tags
        project_folder (str): Ruta a la carpeta del proyecto
        token (str, optional): Token JWT para autenticación
    """
    for tag_name in tags:
        # Construir el nombre del archivo esperado
        file_name = f"daily_readings_{asset_id}__{tag_name}.csv"
        file_path = os.path.join(project_folder, file_name)

        # Si no existe, procesar las lecturas
        try:
            get_daily_readings_for_tag(asset_id, tag_name, project_folder, token)
        except Exception as e:
            logger.error(f"Error al procesar el asset {asset_id} y tag {tag_name}: {e}")

def get_sensor_value_for_date(asset_id, device_id, sensor_id, gateway_id, date, token=None):
    """
    Obtiene el valor de un sensor específico en una fecha dada.
    
    Args:
        asset_id (str): ID del asset
        device_id (str): ID del dispositivo
        sensor_id (str): ID del sensor
        gateway_id (str): ID del gateway
        date (str): Fecha en formato MM-DD-YYYY (por ejemplo, '01-01-2024' para el 1 de enero de 2024)
        token (str, optional): Token JWT para autenticación
        
    Returns:
        tuple: (valor, timestamp) o ("Sin datos disponibles", None) si no hay datos
    """
    # Define la URL para obtener los datos del sensor
    url = f'{BASE_URL}/data/assets/time-series/{asset_id}'

    # Usar el token proporcionado o intentar obtenerlo del servicio de autenticación
    if not token:
        token = auth_service.get_token()
        
    # Si no hay token disponible, registrar un error y devolver error
    if not token:
        logger.error(f"No se pudo obtener un token JWT válido para consultar datos del sensor (device_id: {device_id}, sensor_id: {sensor_id}, gateway_id: {gateway_id})")
        return "Error", None

    # Parámetros de la consulta
    params = {
        'from': date,
        'until': date,
        'sensor': '',
        'device_id': device_id,
        'sensor_id': sensor_id,
        'gateway_id': gateway_id
    }

    # Usar get_auth_headers para obtener los headers de autenticación
    headers = get_auth_headers(token)
    
    logger.debug(f"Obteniendo valor para sensor (device_id: {device_id}, sensor_id: {sensor_id}, gateway_id: {gateway_id}) en fecha {date} con token: {token[:10]}...")
    logger.debug(f"Asegúrate de que la fecha esté en formato MM-DD-YYYY: {date}")

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json().get("data", [])
            if data:
                last_entry = data[-1]
                value = last_entry.get("v", "Sin datos disponibles")
                timestamp = last_entry.get("ts")
                return value, timestamp
            else:
                # No hay datos disponibles para la fecha
                sensor_info = f"asset_id:{asset_id}, device_id:{device_id}, sensor_id:{sensor_id}, gateway_id:{gateway_id}"
                logger.warning(f"Sin datos disponibles para la fecha {date} - {sensor_info}")
                return "Sin datos disponibles", None
        else:
            sensor_info = f"asset_id:{asset_id}, device_id:{device_id}, sensor_id:{sensor_id}, gateway_id:{gateway_id}"
            logger.error(f"Error al obtener datos: {response.status_code}, {response.text} - {sensor_info}")
            return "Error", None
    except Exception as e:
        sensor_info = f"asset_id:{asset_id}, device_id:{device_id}, sensor_id:{sensor_id}, gateway_id:{gateway_id}"
        logger.error(f"Excepción al consultar datos: {e} - {sensor_info}")
        return "Error", None

def get_daily_readings_for_tag(asset_id, tag_name, project_folder, token=None):
    """
    Obtiene lecturas diarias de un sensor asociado a un tag durante un año.
    Actualiza el archivo existente si ya hay datos guardados, solo a partir del último día registrado y hasta el día actual.
    También limpia los registros con errores e intenta obtener nuevos valores para esas fechas.
    
    Args:
        asset_id (str): ID del asset
        tag_name (str): Nombre del tag
        project_folder (str): Ruta a la carpeta del proyecto
        token (str, optional): Token JWT para autenticación
    """
    # Nombre del archivo donde se guardan las lecturas (con un solo guion bajo entre asset_id y tag_name)
    file_name = f"daily_readings_{asset_id}_{tag_name}.csv"  # Formato según PROJECT_CONTEXT.md
    file_path = os.path.join(project_folder, file_name)
    
    # También verificar si existe archivo con formato antiguo (doble guion bajo)
    old_format_file_name = f"daily_readings_{asset_id}__{tag_name}.csv"
    old_format_file_path = os.path.join(project_folder, old_format_file_name)
    
    # Si existe el archivo con formato antiguo pero no el nuevo, migrar
    if os.path.exists(old_format_file_path) and not os.path.exists(file_path):
        try:
            import shutil
            shutil.copy2(old_format_file_path, file_path)
            logger.info(f"Archivo migrado de formato antiguo a nuevo: {old_format_file_path} -> {file_path}")
        except Exception as e:
            logger.error(f"Error al migrar archivo de formato antiguo a nuevo: {str(e)}")
    
    # Verificar si el archivo existe y limpiar errores si es necesario
    if os.path.exists(file_path):
        logger.info(f"Verificando y limpiando errores en el archivo {file_name}")
        clean_data, error_dates = clean_readings_file_errors(file_path)
        if error_dates:
            logger.info(f"Se encontraron {len(error_dates)} fechas con errores que se intentarán actualizar.")
    
    # Obtener el sensor UUID desde el tag
    sensors = get_sensors_with_tags(asset_id, token)
    logger.debug(f"Sensores obtenidos para el asset {asset_id}: {sensors}")
    
    sensor = next((s for s in sensors if s.get("tag_name") == tag_name), None)
    if not sensor:
        logger.warning(f"Sensor no encontrado ({tag_name}) en el asset {asset_id}. Intentando obtener información del sensor directamente.")
        
        # Intentar obtener información del sensor directamente desde la API
        try:
            # Llamar a la API para obtener los sensores disponibles
            url = f'{BASE_URL}/data/assets/{asset_id}/available-utilities-sensors'
            headers = get_auth_headers(token)
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                api_sensors = response.json().get('data', [])
                logger.debug(f"Sensores obtenidos directamente de la API: {api_sensors}")
                
                # Buscar el sensor con el tag específico
                api_sensor = next((s for s in api_sensors if s.get("tag_name") == tag_name), None)
                
                if api_sensor:
                    logger.info(f"Sensor encontrado directamente en la API: {api_sensor}")
                    gateway_id = api_sensor.get('gateway_id')
                    device_id = api_sensor.get('device_id')
                    sensor_id = api_sensor.get('sensor_id')
                    
                    # Intentar obtener lecturas usando los parámetros del sensor
                    return get_daily_readings_with_sensor_params(asset_id, gateway_id, device_id, sensor_id, tag_name, project_folder, token)
            
            logger.error(f"No se pudo encontrar el sensor con tag {tag_name} para el asset {asset_id} ni siquiera consultando directamente la API.")
        except Exception as e:
            logger.error(f"Error al intentar obtener información del sensor directamente: {str(e)}")
        
        # Crear un DataFrame vacío para indicar que no hay datos pero no es un error
        empty_df = pd.DataFrame(columns=["date", "value", "timestamp"])
        return empty_df

    # Obtener los parámetros del sensor
    gateway_id = sensor.get("gateway_id")
    device_id = sensor.get("device_id")
    sensor_id = sensor.get("sensor_id")
    sensor_uuid = sensor.get("sensor_uuid")
    
    logger.info(f"Obteniendo lecturas diarias para el sensor {sensor_uuid} ({tag_name}) en el asset {asset_id}.")
    logger.info(f"Parámetros del sensor: gateway_id={gateway_id}, device_id={device_id}, sensor_id={sensor_id}")
    
    # Usar la función get_daily_readings_with_sensor_params para obtener las lecturas
    return get_daily_readings_with_sensor_params(asset_id, gateway_id, device_id, sensor_id, tag_name, project_folder, token)

def get_daily_readings_with_sensor_params(asset_id, gateway_id, device_id, sensor_id, tag_name, project_folder, token=None):
    """
    Obtiene lecturas diarias usando los parámetros del sensor directamente.
    
    Args:
        asset_id (str): ID del asset
        gateway_id (str): ID del gateway
        device_id (str): ID del dispositivo
        sensor_id (str): ID del sensor
        tag_name (str): Nombre del tag
        project_folder (str): Ruta a la carpeta del proyecto
        token (str, optional): Token JWT para autenticación
        
    Returns:
        pd.DataFrame: DataFrame con las lecturas diarias
    """
    logger.info(f"Obteniendo lecturas diarias con parámetros directos: asset_id={asset_id}, gateway_id={gateway_id}, device_id={device_id}, sensor_id={sensor_id}")
    
    # Configurar rango de fechas
    start_date = datetime(2024, 1, 1)
    end_date = datetime.now()
    
    # Nombre del archivo donde se guardan las lecturas (con un solo guion bajo)
    file_name = f"daily_readings_{asset_id}_{tag_name}.csv"  # Formato según PROJECT_CONTEXT.md
    file_path = os.path.join(project_folder, file_name)
    
    # Verificar si existe archivo con formato antiguo (doble guion bajo)
    old_format_file_name = f"daily_readings_{asset_id}__{tag_name}.csv"
    old_format_file_path = os.path.join(project_folder, old_format_file_name)
    
    # Si existe el archivo con formato antiguo pero no el nuevo, migrar
    if os.path.exists(old_format_file_path) and not os.path.exists(file_path):
        try:
            import shutil
            shutil.copy2(old_format_file_path, file_path)
            logger.info(f"Archivo migrado de formato antiguo a nuevo: {old_format_file_path} -> {file_path}")
        except Exception as e:
            logger.error(f"Error al migrar archivo de formato antiguo a nuevo: {str(e)}")
    
    # Verificar si el archivo ya existe y cargarlo
    existing_data = None
    error_dates = []
    if os.path.exists(file_path):
        try:
            # Cargar el archivo existente
            existing_data = pd.read_csv(file_path)
            
            # Verificar si hay registros con errores
            error_rows = existing_data[existing_data['value'] == 'Error']
            if not error_rows.empty:
                logger.info(f"Se encontraron {len(error_rows)} registros con errores en el archivo existente.")
                
                # Guardar las fechas con errores para intentar actualizarlas
                error_dates = error_rows['date'].tolist()
                
                # Eliminar los registros con errores
                existing_data = existing_data[existing_data['value'] != 'Error']
                logger.info(f"Se eliminaron los registros con errores. Quedan {len(existing_data)} registros válidos.")
                
                # Guardar el archivo limpio
                existing_data.to_csv(file_path, index=False)
                logger.info(f"Se guardó el archivo limpio: {file_path}")
            
            # Convertir la columna de fecha a datetime
            existing_data["date"] = pd.to_datetime(existing_data["date"], errors='coerce')
            
            # Verificar si hay fechas inválidas
            invalid_dates = existing_data[existing_data["date"].isnull()]
            if not invalid_dates.empty:
                logger.warning(f"Se encontraron {len(invalid_dates)} fechas inválidas en el archivo existente.")
                existing_data = existing_data[~existing_data["date"].isnull()]
                logger.info(f"Se eliminaron las fechas inválidas. Quedan {len(existing_data)} registros válidos.")
            
            logger.info(f"Archivo existente encontrado: {file_name}. Actualizando lecturas faltantes.")
        except Exception as e:
            logger.error(f"Error al procesar el archivo existente: {e}")
            existing_data = None
    
    # Determinar la fecha de inicio para las nuevas lecturas
    if existing_data is not None and not existing_data.empty:
        last_recorded_date = existing_data["date"].max()
        if pd.notnull(last_recorded_date) and isinstance(last_recorded_date, pd.Timestamp):
            # Si hay fechas con errores, asegurarse de que start_date sea anterior a la primera fecha con error
            if error_dates:
                error_dates_dt = pd.to_datetime(error_dates, errors='coerce')
                error_dates_dt = error_dates_dt[~pd.isnull(error_dates_dt)]
                if not error_dates_dt.empty:
                    min_error_date = min(error_dates_dt)
                    start_date = min(start_date, min_error_date)
                    logger.info(f"Ajustando fecha de inicio a {start_date.strftime('%Y-%m-%d')} para incluir fechas con errores.")
            else:
                start_date = max(start_date, last_recorded_date + timedelta(days=1))
                logger.info(f"Última fecha registrada: {last_recorded_date.strftime('%Y-%m-%d')}. Nueva fecha de inicio: {start_date.strftime('%Y-%m-%d')}")
        else:
            logger.error(f"La última fecha registrada no es válida: {last_recorded_date}")
            if existing_data is not None:
                return existing_data
    
    # Validar fechas
    if not isinstance(start_date, datetime):
        start_date = pd.to_datetime(start_date)
    if not isinstance(end_date, datetime):
        end_date = pd.to_datetime(end_date)
    
    # Si la fecha de inicio es posterior a la fecha de finalización y no hay fechas con errores, no hay nada que actualizar
    if start_date > end_date and not error_dates:
        logger.info(f"No hay nuevas lecturas para actualizar. Última fecha registrada: {start_date.strftime('%Y-%m-%d')}")
        return existing_data
    
    # Formatear fechas para la API - Formato MM-DD-YYYY que espera la API
    from_date = start_date.strftime("%m-%d-%Y")
    until_date = end_date.strftime("%m-%d-%Y")
    
    logger.debug(f"Fechas formateadas para la API: from_date={from_date}, until_date={until_date} (formato MM-DD-YYYY)")
    
    # Construir la URL para obtener las lecturas
    url = f"{BASE_URL}/data/assets/time-series/{asset_id}"
    
    # Parámetros de la consulta
    params = {
        "from": from_date,
        "until": until_date,
        "sensor": "",
        "device_id": device_id,
        "sensor_id": sensor_id,
        "gateway_id": gateway_id
    }
    
    # Usar el token proporcionado o intentar obtenerlo del servicio de autenticación
    if not token:
        token = auth_service.get_token()
    
    # Si no hay token disponible, registrar un error y devolver None
    if not token:
        logger.error(f"No se pudo obtener un token JWT válido para consultar lecturas del asset {asset_id}")
        return existing_data if existing_data is not None else None
    
    # Usar get_auth_headers para obtener los headers de autenticación
    headers = get_auth_headers(token)
    
    # Realizar la solicitud a la API
    try:
        logger.info(f"Solicitando datos a la API para el período {from_date} a {until_date}")
        logger.debug(f"URL: {url}")
        logger.debug(f"Parámetros completos: {params}")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            readings = data.get("data", [])
            
            if not readings:
                logger.warning(f"No se encontraron lecturas para el período {from_date} a {until_date}")
                return existing_data if existing_data is not None else pd.DataFrame(columns=["date", "value", "timestamp"])
            
            # Procesar las lecturas
            processed_readings = []
            for reading in readings:
                timestamp = reading.get("ts")
                value = reading.get("v")
                
                if timestamp and value:
                    date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                    processed_readings.append({
                        "date": date,
                        "value": value,
                        "timestamp": timestamp
                    })
            
            # Crear DataFrame con las nuevas lecturas
            new_data = pd.DataFrame(processed_readings)
            if new_data.empty:
                logger.warning("No se pudieron procesar las lecturas obtenidas")
                return existing_data if existing_data is not None else None
            
            # Convertir la columna de fecha a datetime
            new_data["date"] = pd.to_datetime(new_data["date"])
            
            # Agrupar por fecha y tomar el último valor de cada día
            new_data = new_data.sort_values("timestamp").groupby("date").last().reset_index()
            
            # Combinar con datos existentes si los hay
            if existing_data is not None and not existing_data.empty:
                # Eliminar fechas duplicadas (preferir nuevas lecturas)
                existing_data = existing_data[~existing_data["date"].isin(new_data["date"])]
                combined_data = pd.concat([existing_data, new_data], ignore_index=True)
                combined_data = combined_data.sort_values("date")
            else:
                combined_data = new_data
            
            # Guardar los datos combinados
            combined_data.to_csv(file_path, index=False)
            logger.info(f"Lecturas guardadas en {file_path}. Total de registros: {len(combined_data)}")
            
            # Verificar si se actualizaron las fechas con errores
            if error_dates:
                error_dates_dt = pd.to_datetime(error_dates, errors='coerce')
                error_dates_dt = error_dates_dt[~pd.isnull(error_dates_dt)]
                updated_error_dates = combined_data[combined_data["date"].isin(error_dates_dt)]
                logger.info(f"Se actualizaron {len(updated_error_dates)} de {len(error_dates_dt)} fechas que tenían errores.")
            
            return combined_data
        else:
            logger.error(f"Error al obtener lecturas: {response.status_code} - {response.text}")
            return existing_data if existing_data is not None else None
    
    except Exception as e:
        logger.error(f"Error al obtener lecturas: {str(e)}")
        return existing_data if existing_data is not None else None

def clean_readings_file_errors(file_path):
    """
    Limpia los registros con errores de un archivo de lecturas.
    
    Args:
        file_path (str): Ruta al archivo de lecturas
        
    Returns:
        tuple: (DataFrame limpio, lista de fechas con errores)
    """
    if not os.path.exists(file_path):
        logger.warning(f"El archivo {file_path} no existe.")
        return None, []
    
    try:
        # Cargar el archivo
        data = pd.read_csv(file_path)
        
        # Verificar si hay registros con errores
        error_rows = data[data['value'] == 'Error']
        if error_rows.empty:
            logger.info(f"No se encontraron registros con errores en el archivo {file_path}.")
            return data, []
        
        # Guardar las fechas con errores
        error_dates = error_rows['date'].tolist()
        logger.info(f"Se encontraron {len(error_dates)} registros con errores en el archivo {file_path}.")
        
        # Eliminar los registros con errores
        clean_data = data[data['value'] != 'Error']
        logger.info(f"Se eliminaron los registros con errores. Quedan {len(clean_data)} registros válidos.")
        
        # Guardar el archivo limpio
        clean_data.to_csv(file_path, index=False)
        logger.info(f"Se guardó el archivo limpio: {file_path}")
        
        return clean_data, error_dates
    
    except Exception as e:
        logger.error(f"Error al limpiar el archivo {file_path}: {str(e)}")
        return None, []

def get_sensor_uuid(gateway_id, device_id, sensor_id, token=None):
    """
    Obtiene el sensor_uuid para un sensor específico llamando al endpoint /devices.
    
    Args:
        gateway_id (str): ID del gateway
        device_id (str): ID del dispositivo
        sensor_id (str): ID del sensor
        token (str, optional): Token JWT para autenticación
        
    Returns:
        str: UUID del sensor o mensaje de error
    """
    url = f"{BASE_URL}/devices"
    
    # Usar el token proporcionado o intentar obtenerlo del servicio de autenticación
    if not token:
        token = auth_service.get_token()
        
    # Si no hay token disponible, registrar un error y devolver mensaje de error
    if not token:
        logger.error(f"No se pudo obtener un token JWT válido para consultar dispositivos")
        return "Error al obtener UUID"
    
    # Usar get_auth_headers para obtener los headers de autenticación
    headers = get_auth_headers(token)
    
    # Añadir headers adicionales
    headers.update({
        'Accept': 'application/json, text/plain, */*',
    })
    
    params = {
        "gateway_id": gateway_id
    }

    logger.debug(f"Obteniendo UUID para sensor {sensor_id} en dispositivo {device_id} con token: {token[:10]}...")
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        devices = response.json().get('data', [])
        for device in devices:
            if device.get('device_id') == device_id:
                # Buscar el sensor correspondiente
                for sensor in device.get('sensors', []):
                    if sensor.get('sensor_id') == sensor_id:
                        return sensor.get('sensor_uuid', 'Sin UUID')
        return "Sensor no encontrado"
    else:
        logger.error(f"Error al consultar dispositivos: {response.status_code}, {response.text}")
        return "Error al obtener UUID"

def get_daily_readings_for_year_multiple_tags_project_parallel(project_id, tags, year=None, token=None):
    """
    Obtiene lecturas diarias para múltiples tags durante un año para todos los assets de un proyecto en paralelo.
    Guarda los resultados en una carpeta específica del proyecto.
    
    Args:
        project_id (str): ID del proyecto
        tags (list): Lista de tags de consumo
        year (int, optional): Año para el que se obtienen las lecturas. Por defecto, el año actual.
        token (str, optional): Token JWT para autenticación
        
    Returns:
        dict: Resultado de la operación con mensaje de éxito o error
    """
    try:
        # Asegurar la carpeta del proyecto
        project_folder = ensure_project_folder_exists(project_id)
        
        # Obtener los asset IDs del proyecto
        asset_ids = get_asset_ids_from_project(project_id, token)
        if not asset_ids:
            message = f"No se encontraron assets para el proyecto {project_id}."
            logger.error(message)
            return {"success": False, "message": message}
        
        logger.info(f"\nProcesando lecturas diarias para {len(asset_ids)} assets en el proyecto {project_id}...")
        
        # Usar ThreadPoolExecutor para procesar assets en paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = {
                executor.submit(process_asset_tags, asset_id, tags, project_folder, token): asset_id for asset_id in asset_ids
            }
            
            success_count = 0
            error_count = 0
            
            for future in concurrent.futures.as_completed(futures):
                asset_id = futures[future]
                try:
                    future.result()  # Esperar a que termine el procesamiento del asset
                    logger.info(f"Asset {asset_id} procesado con éxito.")
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error al procesar el asset {asset_id}: {e}")
                    error_count += 1
        
        message = f"Lecturas diarias completadas para {success_count} assets con éxito y {error_count} con errores."
        logger.info(f"\n{message}")
        
        return {
            "success": True,
            "message": message,
            "total_assets": len(asset_ids),
            "success_count": success_count,
            "error_count": error_count
        }
    
    except Exception as e:
        message = f"Error al procesar lecturas diarias: {str(e)}"
        logger.error(message)
        return {"success": False, "message": message}

def get_daily_readings_for_period_multiple_tags_project_parallel(project_id, tags, start_date, end_date, token=None):
    """
    Obtiene lecturas diarias para múltiples tags durante un período específico para todos los assets de un proyecto.
    Procesa el rango por meses y actualiza solo los meses dentro del período seleccionado.
    
    Args:
        project_id (str): ID del proyecto
        tags (list): Lista de tags de consumo
        start_date (str o datetime): Fecha de inicio del período en formato YYYY-MM-DD
        end_date (str o datetime): Fecha de fin del período en formato YYYY-MM-DD
        token (str, optional): Token JWT para autenticación
        
    Returns:
        dict: Resultado de la operación con mensaje de éxito o error
    """
    try:
        # Convertir fechas a objetos datetime si son strings
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            
        # Generar lista de meses (YYYY-MM) entre start_date y end_date
        months_to_process = []
        current_month = datetime(start_date.year, start_date.month, 1)
        while current_month <= end_date:
            months_to_process.append(current_month.strftime("%Y-%m"))
            # Avanzar al siguiente mes
            if current_month.month == 12:
                current_month = datetime(current_month.year + 1, 1, 1)
            else:
                current_month = datetime(current_month.year, current_month.month + 1, 1)
        
        logger.info(f"Procesando lecturas para los meses: {months_to_process}")
        
        # Asegurar la carpeta del proyecto
        project_folder = ensure_project_folder_exists(project_id)
        
        # Obtener los asset IDs del proyecto
        asset_ids = get_asset_ids_from_project(project_id, token)
        if not asset_ids:
            message = f"No se encontraron assets para el proyecto {project_id}."
            logger.error(message)
            return {"success": False, "message": message}
        
        # Crear una función de procesamiento para cada combinación de asset, tag y mes
        def process_asset_tag_month(asset_id, tag_name, month):
            try:
                # Obtener sensor con parámetros para el tag
                sensors = get_sensors_with_tags(asset_id, token)
                logger.debug(f"[DEBUG] process_asset_tag_month - Sensores obtenidos para {asset_id}: {sensors}")
                
                # Mejorar la verificación del tag en los sensores
                if not sensors:
                    logger.warning(f"[WARNING] process_asset_tag_month - No se encontraron sensores para el asset {asset_id}")
                    return False
                
                # Verificar si el tag existe en los sensores
                # La función get_sensors_with_tags devuelve una lista de diccionarios
                tag_data = None
                
                # Buscar el tag_name en la lista de sensores
                for sensor in sensors:
                    if isinstance(sensor, dict) and sensor.get('tag_name') == tag_name:
                        tag_data = sensor
                        logger.debug(f"[DEBUG] process_asset_tag_month - Tag {tag_name} encontrado en sensor: {sensor}")
                        break
                
                if not tag_data:
                    # Registrar más información para depuración
                    logger.warning(f"[WARNING] process_asset_tag_month - No se encontró el tag {tag_name} para el asset {asset_id}")
                    logger.debug(f"[DEBUG] process_asset_tag_month - Tags disponibles: {[s.get('tag_name') for s in sensors if isinstance(s, dict)]}")
                    
                    # Verificar en la API directamente
                    import requests
                    url = f"{BASE_URL}/data/assets/{asset_id}/available-utilities-sensors"
                    headers = get_auth_headers(token)
                    params = {
                        "include_details": True,
                        "active_only": True
                    }
                    
                    try:
                        response = requests.get(url, headers=headers, params=params)
                        logger.debug(f"[DEBUG] process_asset_tag_month - API response status: {response.status_code}")
                        
                        if response.status_code == 200:
                            data = response.json().get('data', [])
                            logger.debug(f"[DEBUG] process_asset_tag_month - Sensores desde API directa: {data}")
                            
                            # Buscar el tag en los datos de la API
                            for sensor in data:
                                if sensor.get('tag_name') == tag_name:
                                    # Crear la estructura que espera get_daily_readings_for_tag_monthly
                                    tag_data = {
                                        "gateway_id": sensor.get('gateway_id'),
                                        "device_id": sensor.get('device_id'),
                                        "sensor_id": sensor.get('sensor_id'),
                                        "tag_name": sensor.get('tag_name'),
                                        "sensor_type": sensor.get('sensor_type')
                                    }
                                    logger.info(f"[INFO] process_asset_tag_month - Tag {tag_name} encontrado a través de consulta directa a la API")
                                    break
                    except Exception as e:
                        logger.error(f"[ERROR] process_asset_tag_month - Error al consultar la API directamente: {str(e)}")
                
                if not tag_data:
                    logger.warning(f"[WARNING] process_asset_tag_month - No se pudo encontrar información para el tag {tag_name} en el asset {asset_id}")
                    return False
                
                # Log de los datos del tag que se van a usar
                logger.debug(f"[DEBUG] process_asset_tag_month - Utilizando datos de tag: {tag_data}")
                
                # Llamar a get_daily_readings_for_tag_monthly
                result = get_daily_readings_for_tag_monthly(
                    asset_id,
                    tag_data,
                    month,
                    project_folder,
                    token
                )
                
                success = result is not None
                logger.debug(f"[DEBUG] process_asset_tag_month - Resultado para {asset_id}, {tag_name}, {month}: {'éxito' if success else 'fallido'}")
                return success
            except Exception as e:
                logger.error(f"[ERROR] process_asset_tag_month - Error procesando asset {asset_id}, tag {tag_name}, mes {month}: {str(e)}")
                import traceback
                logger.error(f"[ERROR] process_asset_tag_month - Traceback: {traceback.format_exc()}")
                return False
        
        # Crear todas las tareas para procesar
        tasks = []
        for asset_id in asset_ids:
            for tag_name in tags:
                for month in months_to_process:
                    tasks.append((asset_id, tag_name, month))
        
        logger.info(f"Total de tareas a procesar: {len(tasks)}")
        
        # Procesar en paralelo usando ThreadPoolExecutor
        success_count = 0
        error_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            future_to_task = {
                executor.submit(process_asset_tag_month, asset_id, tag_name, month): (asset_id, tag_name, month)
                for asset_id, tag_name, month in tasks
            }
            
            for future in concurrent.futures.as_completed(future_to_task):
                asset_id, tag_name, month = future_to_task[future]
                try:
                    success = future.result()
                    if success:
                        success_count += 1
                        logger.debug(f"Procesado con éxito: asset {asset_id}, tag {tag_name}, mes {month}")
                    else:
                        error_count += 1
                        logger.warning(f"Error en: asset {asset_id}, tag {tag_name}, mes {month}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Excepción en: asset {asset_id}, tag {tag_name}, mes {month}: {str(e)}")
        
        message = f"Lecturas actualizadas para el período {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}. {success_count} procesos exitosos, {error_count} con errores."
        logger.info(message)
        
        return {
            "success": True,
            "message": message,
            "total_tasks": len(tasks),
            "success_count": success_count,
            "error_count": error_count,
            "months_processed": months_to_process
        }
        
    except Exception as e:
        message = f"Error al procesar lecturas para el período: {str(e)}"
        logger.error(message)
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "message": message}

def migrate_readings_file_if_needed(asset_id, tag_name, project_id="general"):
    """
    Migra un archivo de lectura desde la estructura antigua a la nueva si existe.
    
    Args:
        asset_id (str): ID del asset
        tag_name (str): Nombre del tag
        project_id (str): ID del proyecto destino (por defecto "general")
        
    Returns:
        bool: True si se migró un archivo, False si no era necesario
    """
    # Rutas de carpetas en estructura antigua y nueva
    old_project_folder = os.path.join("data/analyzed_data", f"asset_{asset_id}")
    new_project_folder = os.path.join("data/analyzed_data", project_id)
    
    # Nombre del archivo que buscamos en la estructura antigua
    old_file_patterns = [
        f"daily_readings_{asset_id}_{tag_name}.csv",  # Formato según PROJECT_CONTEXT.md
        f"daily_readings_{asset_id}_{tag_name}_*.csv",  # Con mes en el nombre
        f"daily_readings_{asset_id}__{tag_name}.csv",  # Formato con doble guion bajo
        f"daily_readings_{asset_id}__{tag_name}_*.csv"  # Formato con doble guion bajo y mes
    ]
    
    # Nombre del archivo en la estructura nueva (según PROJECT_CONTEXT.md)
    new_file_name = f"daily_readings_{asset_id}_{tag_name}.csv"
    new_file_path = os.path.join(new_project_folder, new_file_name)
    
    # Verificar si la carpeta antigua existe
    if os.path.exists(old_project_folder):
        # Buscar archivo en la carpeta antigua
        found_files = []
        for pattern in old_file_patterns:
            found_files.extend(glob.glob(os.path.join(old_project_folder, pattern)))
        
        if found_files:
            # Asegurar que existe la carpeta de destino
            os.makedirs(new_project_folder, exist_ok=True)
            
            # Si hay varios archivos (con meses distintos), combinarlos
            if len(found_files) > 1:
                logger.info(f"Encontrados {len(found_files)} archivos para {asset_id}/{tag_name} en estructura antigua. Combinando.")
                combined_data = pd.DataFrame()
                
                for file_path in found_files:
                    try:
                        data = pd.read_csv(file_path)
                        combined_data = pd.concat([combined_data, data], ignore_index=True)
                    except Exception as e:
                        logger.error(f"Error al leer archivo {file_path} durante migración: {str(e)}")
                
                # Eliminar duplicados si hay
                if 'date' in combined_data.columns:
                    combined_data['date'] = pd.to_datetime(combined_data['date'])
                    combined_data = combined_data.sort_values('date').groupby('date', as_index=False).last()
                    combined_data['date'] = combined_data['date'].dt.strftime('%Y-%m-%d')
                
                # Guardar en nueva ubicación
                combined_data.to_csv(new_file_path, index=False)
                logger.info(f"Archivo combinado guardado en nueva estructura: {new_file_path}")
            else:
                # Si solo hay un archivo, moverlo directamente
                old_file_path = found_files[0]
                shutil.copy2(old_file_path, new_file_path)
                logger.info(f"Archivo migrado de {old_file_path} a {new_file_path}")
            
            return True
    
    return False

def get_daily_readings_for_tag_monthly(asset_id, tag, month, project_folder, token=None):
    """
    Obtiene lecturas diarias para un tag y mes específico utilizando los parámetros del sensor.
    Si se solicita el mes actual, solo se obtendrán datos hasta el día de hoy (no incluye fechas futuras).
    Guarda los datos en formato CSV en la estructura estándar del proyecto.
    
    Args:
        asset_id (str): ID del asset para obtener datos
        tag (dict): Diccionario con las propiedades device_id, sensor_id y gateway_id del sensor
        month (str): Mes en formato YYYY-MM (por ejemplo, '2024-01' para enero 2024)
                    Este valor se utilizará para calcular el primer y último día del mes
        project_folder (str): Carpeta del proyecto donde se guardarán los datos
        token (str, opcional): Token JWT para autenticación
        
    Returns:
        pandas.DataFrame: DataFrame con los datos de lecturas diarias o None si hay un error
    """
    # Extraer el ID del proyecto del project_folder
    project_id = os.path.basename(project_folder)
    
    logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Iniciando para asset: {asset_id}, mes: {month}, project_id: {project_id}")
    logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Tag recibido: {tag}")
    
    # Validar formato del mes
    if not month or not re.match(r'^\d{4}-\d{2}$', month):
        logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Formato de mes inválido: {month}. Debe ser YYYY-MM")
        return None
        
    # Extraer el sensor del tag
    device_id = tag.get('device_id')
    sensor_id = tag.get('sensor_id')
    gateway_id = tag.get('gateway_id')
    tag_name = tag.get('tag_name', f"{device_id}_{sensor_id}_{gateway_id}")
    
    logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Parámetros extraídos: device_id={device_id}, sensor_id={sensor_id}, gateway_id={gateway_id}, tag_name={tag_name}")
    
    # Verificar que los parámetros del sensor están presentes
    if not all([device_id, sensor_id, gateway_id]):
        logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Parámetros de sensor incompletos: device_id={device_id}, sensor_id={sensor_id}, gateway_id={gateway_id}")
        logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Estructura completa del tag: {tag}")
        return None
    
    # Verificar si el mes solicitado es futuro (no hay datos disponibles)
    try:
        year, month_num = month.split('-')
        current_date = datetime.now()
        request_date = datetime(int(year), int(month_num), 1)
        
        logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Procesando año={year}, mes={month_num}, fecha actual={current_date}")
        
        if request_date > current_date:
            logger.warning(f"[WARNING] get_daily_readings_for_tag_monthly - Se solicitaron datos para un mes futuro: {month}. No hay datos disponibles.")
            return pd.DataFrame(columns=['date', 'value', 'timestamp'])
    except Exception as e:
        logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Error al validar la fecha del mes: {str(e)}")
        import traceback
        logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Traceback: {traceback.format_exc()}")
    
    # Nombre del archivo donde se guardan las lecturas (usando el formato según PROJECT_CONTEXT.md)
    file_name = f"daily_readings_{asset_id}_{tag_name}.csv"
    file_path = os.path.join(project_folder, file_name)
    
    logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Archivo a procesar: {file_path}")
    
    # Verificar si existe archivo con formato antiguo (doble guion bajo)
    old_format_file_name = f"daily_readings_{asset_id}__{tag_name}.csv"
    old_format_file_path = os.path.join(project_folder, old_format_file_name)
    
    # Si existe el archivo con formato antiguo pero no el nuevo, migrar
    if os.path.exists(old_format_file_path) and not os.path.exists(file_path):
        try:
            import shutil
            shutil.copy2(old_format_file_path, file_path)
            logger.info(f"[INFO] get_daily_readings_for_tag_monthly - Archivo migrado de formato antiguo a nuevo: {old_format_file_path} -> {file_path}")
        except Exception as e:
            logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Error al migrar archivo de formato antiguo a nuevo: {str(e)}")
    
    # Si el archivo no existe en ningún formato, intentar migrarlo desde la antigua estructura de carpetas
    if not os.path.exists(file_path):
        logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Archivo {file_path} no encontrado. Verificando estructura antigua...")
        was_migrated = migrate_readings_file_if_needed(asset_id, tag_name, project_id)
        if was_migrated:
            logger.info(f"[INFO] get_daily_readings_for_tag_monthly - Archivo migrado desde estructura antigua para {asset_id}/{tag_name}")
    
    # Verificar si el archivo existe y limpiar errores si es necesario
    if os.path.exists(file_path):
        logger.info(f"[INFO] get_daily_readings_for_tag_monthly - Verificando y limpiando errores en el archivo {file_name}")
        clean_data, error_dates = clean_readings_file_errors(file_path)
        
        # Si el archivo existe, verificar si hay datos actualizados
        try:
            existing_data = pd.read_csv(file_path)
            logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Datos existentes cargados: {len(existing_data)} registros")
            
            # Convertir la columna de fecha a datetime
            if 'date' in existing_data.columns:
                existing_data["date"] = pd.to_datetime(existing_data["date"], errors='coerce')
                
                # Si es el mes actual, verificar si es necesario actualizar los datos
                if int(year) == current_date.year and int(month_num) == current_date.month:
                    if not existing_data.empty:
                        latest_date = existing_data['date'].max()
                        today = pd.to_datetime(current_date.strftime('%Y-%m-%d'))
                        
                        logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Mes actual: {month}, última fecha: {latest_date}, hoy: {today}")
                        
                        if latest_date >= today and not error_dates:
                            logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Los datos están actualizados hasta hoy ({today.strftime('%Y-%m-%d')})")
                            # Filtrar solo datos del mes solicitado
                            month_mask = (existing_data['date'].dt.year == int(year)) & (existing_data['date'].dt.month == int(month_num))
                            month_data = existing_data[month_mask]
                            logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Retornando {len(month_data)} registros filtrados del mes")
                            return month_data
                        else:
                            if error_dates:
                                logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Se encontraron {len(error_dates)} fechas con errores que se intentarán actualizar.")
                            else:
                                logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Los datos existentes llegan hasta {latest_date.strftime('%Y-%m-%d')}, actualizando hasta hoy ({today.strftime('%Y-%m-%d')})")
                else:
                    # Para meses pasados, si no hay fechas con errores, no es necesario actualizar
                    if not error_dates and 'date' in existing_data.columns:
                        # Filtrar solo datos del mes solicitado
                        month_mask = (existing_data['date'].dt.year == int(year)) & (existing_data['date'].dt.month == int(month_num))
                        month_data = existing_data[month_mask]
                        if not month_data.empty:
                            logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Ya existen datos para el mes {month} y no hay errores que corregir. Retornando {len(month_data)} registros.")
                            return month_data
            
            # Si hay errores o no se puede determinar la última fecha, continuar con la obtención de nuevos datos
            logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Se requiere obtener nuevos datos para el mes {month}")
        except Exception as e:
            logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Error al procesar el archivo existente {file_path}: {str(e)}")
            import traceback
            logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Traceback: {traceback.format_exc()}")
            # Si hay un error al cargar, continuar con la obtención de nuevos datos
    
    # Obtener lecturas desde la API (para el mes específico)
    logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Llamando a get_daily_readings_with_sensor_params_monthly con: asset_id={asset_id}, device_id={device_id}, sensor_id={sensor_id}, gateway_id={gateway_id}, month={month}")
    
    readings_df = get_daily_readings_with_sensor_params_monthly(
        asset_id, device_id, sensor_id, gateway_id, month, token
    )
    
    logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Resultado de get_daily_readings_with_sensor_params_monthly: {readings_df is not None}, filas: {len(readings_df) if readings_df is not None else 0}")
    
    # Procesar y guardar los datos si se obtuvieron correctamente
    if readings_df is not None and not readings_df.empty:
        try:
            # Convertir la columna de fecha a string en formato YYYY-MM-DD si existe
            if 'date' in readings_df.columns:
                if pd.api.types.is_datetime64_any_dtype(readings_df['date']):
                    readings_df['date'] = readings_df['date'].dt.strftime('%Y-%m-%d')
            
            # Si hay datos existentes, combinarlos con los nuevos
            if os.path.exists(file_path):
                try:
                    existing_data = pd.read_csv(file_path)
                    logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Combinando datos existentes ({len(existing_data)} registros) con nuevos datos ({len(readings_df)} registros)")
                    
                    # Convertir las fechas a datetime para comparación
                    if 'date' in existing_data.columns and 'date' in readings_df.columns:
                        existing_data['date'] = pd.to_datetime(existing_data['date'])
                        readings_df['date'] = pd.to_datetime(readings_df['date'])
                        
                        # Eliminar fechas duplicadas (preferir nuevas lecturas)
                        existing_data = existing_data[~existing_data['date'].isin(readings_df['date'])]
                        
                        # Combinar y ordenar por fecha
                        combined_data = pd.concat([existing_data, readings_df], ignore_index=True)
                        combined_data = combined_data.sort_values('date')
                        
                        # Convertir las fechas de nuevo a string
                        combined_data['date'] = combined_data['date'].dt.strftime('%Y-%m-%d')
                        
                        # Guardar los datos combinados
                        combined_data.to_csv(file_path, index=False)
                        logger.info(f"[INFO] get_daily_readings_for_tag_monthly - Datos actualizados guardados en {file_path}. Total: {len(combined_data)} registros.")
                        
                        # Devolver los datos combinados
                        return combined_data
                except Exception as e:
                    logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Error al combinar datos existentes con nuevos datos: {str(e)}")
                    import traceback
                    logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Traceback: {traceback.format_exc()}")
            
            # Si no hay datos existentes o hubo error en la combinación, guardar solo los nuevos datos
            readings_df.to_csv(file_path, index=False)
            logger.info(f"[INFO] get_daily_readings_for_tag_monthly - Datos actualizados guardados en {file_path}. Total: {len(readings_df)} registros.")
        except Exception as e:
            logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Error al guardar datos en {file_path}: {str(e)}")
            import traceback
            logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Traceback: {traceback.format_exc()}")
    else:
        logger.warning(f"[WARNING] get_daily_readings_for_tag_monthly - No se obtuvieron datos para el mes {month}.")
        # Si no hay datos nuevos pero había existentes, devolver los existentes
        if os.path.exists(file_path):
            try:
                existing_data = pd.read_csv(file_path)
                logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - No hay datos nuevos, intentando retornar datos existentes filtrados")
                # Filtrar solo datos del mes solicitado si existe la columna de fecha
                if 'date' in existing_data.columns:
                    existing_data['date'] = pd.to_datetime(existing_data['date'])
                    month_mask = (existing_data['date'].dt.year == int(year)) & (existing_data['date'].dt.month == int(month_num))
                    month_data = existing_data[month_mask]
                    logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Retornando {len(month_data)} registros filtrados del mes")
                    return month_data
                return existing_data
            except Exception as e:
                logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Error al procesar datos existentes: {str(e)}")
                import traceback
                logger.error(f"[ERROR] get_daily_readings_for_tag_monthly - Traceback: {traceback.format_exc()}")
    
    logger.debug(f"[DEBUG] get_daily_readings_for_tag_monthly - Finalizando función, retornando dataframe con {len(readings_df) if readings_df is not None else 0} registros")
    return readings_df

def get_daily_readings_with_sensor_params_monthly(asset_id, device_id, sensor_id, gateway_id, month, token=None):
    """
    Obtiene lecturas diarias para un sensor específico limitado a un mes concreto.
    Si se solicita el mes actual, la fecha final será el día actual en lugar del último día del mes.
    Procesa los datos en formato compatible con get_daily_readings_with_sensor_params.
    
    Args:
        asset_id (str): ID del asset
        device_id (str): ID del dispositivo
        sensor_id (str): ID del sensor
        gateway_id (str): ID del gateway
        month (str): Mes en formato YYYY-MM (por ejemplo, '2024-01' para enero 2024)
        token (str, opcional): Token JWT para autenticación
        
    Returns:
        pandas.DataFrame: DataFrame con los datos de lecturas diarias o None si hay un error
    """
    # Obtener el token si no se proporciona
    if not token:
        token = auth_service.get_token()
        
    if not token:
        logger.error("No se pudo obtener un token JWT válido para consultar datos")
        return None
    
    # Extraer el año y mes del parámetro month (formato YYYY-MM)
    try:
        year, month_num = month.split('-')
        year = int(year)
        month_num = int(month_num)
    except ValueError:
        logger.error(f"Formato de mes inválido: {month}. Debe ser YYYY-MM")
        return None
    
    # Calcular el primer y último día del mes
    import calendar
    from datetime import datetime
    
    # Obtener el número de días en el mes
    _, last_day = calendar.monthrange(year, month_num)
    
    # Crear objeto de fecha para el primer día del mes
    start_date = datetime(year, month_num, 1)
    
    # Obtener la fecha actual
    current_date = datetime.now()
    
    # Para el mes actual, usar la fecha actual como fecha final
    if year == current_date.year and month_num == current_date.month:
        end_date = current_date
        logger.debug(f"Mes actual detectado: limitando fecha final al día de hoy ({current_date.strftime('%Y-%m-%d')})")
    else:
        # Para meses pasados, usar el último día del mes
        end_date = datetime(year, month_num, last_day)
    
    # Validar que el rango de fechas es válido
    if start_date > current_date:
        logger.warning(f"Se solicitaron datos para un mes futuro: {month}. No hay datos disponibles.")
        return pd.DataFrame(columns=['date', 'value', 'timestamp'])
    
    # Formatear las fechas en el formato esperado por la API (MM-DD-YYYY)
    from_date = start_date.strftime("%m-%d-%Y")
    until_date = end_date.strftime("%m-%d-%Y")
    
    logger.debug(f"Obteniendo lecturas para el período: {from_date} hasta {until_date}")
    
    # URL para la API
    url = f'{BASE_URL}/data/assets/time-series/{asset_id}'
    
    # Parámetros para la solicitud
    params = {
        'from': from_date,
        'until': until_date,
        'sensor': '',
        'device_id': device_id,
        'sensor_id': sensor_id,
        'gateway_id': gateway_id,
    }
    
    # Obtener los datos de usuario del token para extraer el email
    try:
        user_data = auth_service.get_user_data_from_token(token)
        if user_data and 'email' in user_data:
            params['email'] = user_data['email']
            logger.debug(f"Añadiendo email al request: {user_data['email']}")
        else:
            logger.warning("No se encontró email en el token JWT para añadir a la solicitud")
    except Exception as e:
        logger.warning(f"Error al intentar extraer email del token: {str(e)}")
    
    # Registrar la URL y los parámetros completos
    logger.debug(f"URL para obtener lecturas: {url}")
    logger.debug(f"Parámetros completos: {params}")
    
    # Obtener los encabezados de autenticación
    headers = get_auth_headers(token)
    
    try:
        # Hacer la solicitud a la API
        response = requests.get(url, params=params, headers=headers)
        
        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            # Procesar la respuesta
            data = response.json().get('data', [])
            if not data:
                logger.warning(f"No se encontraron datos para el sensor (device_id: {device_id}, sensor_id: {sensor_id}) en el período {from_date} a {until_date}")
                return pd.DataFrame(columns=['date', 'value', 'timestamp'])
            
            # Procesar las lecturas de manera similar a get_daily_readings_with_sensor_params
            processed_readings = []
            for reading in data:
                timestamp = reading.get("ts")
                value = reading.get("v")
                
                if timestamp and value is not None:
                    # Convertir el timestamp (segundos) a fecha, igual que en get_daily_readings_with_sensor_params
                    date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                    processed_readings.append({
                        "date": date,
                        "value": value,
                        "timestamp": timestamp
                    })
            
            # Crear DataFrame con las lecturas procesadas
            readings_df = pd.DataFrame(processed_readings)
            if readings_df.empty:
                logger.warning("No se pudieron procesar las lecturas obtenidas")
                return pd.DataFrame(columns=['date', 'value', 'timestamp'])
            
            # Convertir la columna de fecha a datetime
            readings_df["date"] = pd.to_datetime(readings_df["date"])
            
            # Agrupar por fecha y tomar el último valor de cada día
            readings_df = readings_df.sort_values("timestamp").groupby("date").last().reset_index()
            
            logger.info(f"Se obtuvieron {len(readings_df)} lecturas para el sensor (device_id: {device_id}, sensor_id: {sensor_id}) en el período {from_date} a {until_date}")
            return readings_df
        else:
            # Manejar error
            try:
                error_detail = response.json()
                logger.error(f"Error al obtener lecturas: {response.status_code} - {json.dumps(error_detail)}")
            except:
                logger.error(f"Error al obtener lecturas: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error al obtener lecturas: {str(e)}")
        return None

def migrate_all_readings_files_to_new_format(base_path="data/analyzed_data"):
    """
    Migra todos los archivos CSV de lecturas diarias del formato antiguo (doble guion bajo)
    al nuevo formato (un solo guion bajo) según PROJECT_CONTEXT.md.
    
    Args:
        base_path (str): Ruta base donde buscar los archivos CSV
        
    Returns:
        dict: Resultados de la migración con conteo de archivos migrados, errores, etc.
    """
    logger.info(f"Iniciando migración de archivos al nuevo formato según PROJECT_CONTEXT.md")
    
    # Contadores para el informe final
    total_files = 0
    migrated_files = 0
    already_exists = 0
    error_files = 0
    
    # Buscar todos los directorios de proyecto
    project_dirs = [d for d in glob.glob(os.path.join(base_path, "*")) if os.path.isdir(d)]
    logger.info(f"Encontrados {len(project_dirs)} directorios de proyecto")
    
    for project_dir in project_dirs:
        project_id = os.path.basename(project_dir)
        logger.info(f"Procesando directorio de proyecto: {project_id}")
        
        # Buscar archivos CSV con formato antiguo (doble guion bajo)
        csv_files = glob.glob(os.path.join(project_dir, "daily_readings_*__*.csv"))
        total_files += len(csv_files)
        
        logger.info(f"Encontrados {len(csv_files)} archivos CSV con formato antiguo en {project_id}")
        
        for old_file_path in csv_files:
            old_filename = os.path.basename(old_file_path)
            logger.debug(f"Procesando archivo: {old_filename}")
            
            # Extraer el ID del asset y el tag
            try:
                # El formato es daily_readings_ASSETID__TAG.csv
                # Dividir por "__" para obtener ASSETID y TAG
                filename_parts = old_filename.replace("daily_readings_", "").split("__")
                if len(filename_parts) != 2:
                    logger.warning(f"No se pudo analizar el nombre del archivo: {old_filename}, no tiene el formato esperado")
                    error_files += 1
                    continue
                
                asset_id = filename_parts[0]
                tag_with_extension = filename_parts[1]
                tag_name = tag_with_extension.replace(".csv", "")
                
                # Generar el nuevo nombre de archivo (un solo guion bajo)
                new_filename = f"daily_readings_{asset_id}_{tag_name}.csv"
                new_file_path = os.path.join(project_dir, new_filename)
                
                # Verificar si el archivo con nuevo formato ya existe
                if os.path.exists(new_file_path):
                    logger.debug(f"El archivo con nuevo formato ya existe: {new_filename}")
                    already_exists += 1
                    continue
                
                # Copiar el archivo antiguo al nuevo formato
                try:
                    import shutil
                    shutil.copy2(old_file_path, new_file_path)
                    logger.info(f"Archivo migrado: {old_filename} -> {new_filename}")
                    migrated_files += 1
                except Exception as e:
                    logger.error(f"Error al copiar archivo {old_filename}: {str(e)}")
                    error_files += 1
            except Exception as e:
                logger.error(f"Error al procesar archivo {old_filename}: {str(e)}")
                error_files += 1
    
    # Generar informe final
    logger.info(f"Migración completada. Resumen:")
    logger.info(f"  - Total de archivos con formato antiguo: {total_files}")
    logger.info(f"  - Archivos migrados: {migrated_files}")
    logger.info(f"  - Archivos que ya existían en nuevo formato: {already_exists}")
    logger.info(f"  - Errores: {error_files}")
    
    return {
        "total_files": total_files,
        "migrated_files": migrated_files,
        "already_exists": already_exists,
        "error_files": error_files
    }