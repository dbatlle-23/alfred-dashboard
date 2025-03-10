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
    
    logger.debug(f"Obteniendo sensores para el asset {asset_id} con token: {token[:10]}...")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        sensors = response.json().get('data', [])
        if not sensors:
            logger.warning("No se encontraron sensores disponibles para este asset.")
            return []
        else:
            sensor_list = []
            for sensor in sensors:
                gateway_id = sensor.get('gateway_id')
                device_id = sensor.get('device_id')
                sensor_id = sensor.get('sensor_id')

                # Obtener el sensor_uuid utilizando la función auxiliar
                sensor_uuid = get_sensor_uuid(gateway_id, device_id, sensor_id, token)

                # Agregar el sensor con todos sus datos al listado
                sensor_list.append({
                    "sensor_id": sensor_id,
                    "sensor_type": sensor.get('sensor_type'),
                    "tag_name": sensor.get('tag_name'),
                    "sensor_uuid": sensor_uuid,
                    "gateway_id": gateway_id,
                    "device_id": device_id
                })
            return sensor_list
    else:
        logger.error(f"Error al obtener sensores: {response.status_code}, {response.text}")
        return []

def ensure_project_folder_exists(project_id):
    """
    Asegura que exista una carpeta para un proyecto dentro del directorio analyzed_data.
    """
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
        file_name = f"daily_readings_{asset_id}_{tag_name}.csv"
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

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json().get("data", [])
            if data:
                last_entry = data[-1]
                value = last_entry.get("v", "Sin datos disponibles")
                timestamp = datetime.fromtimestamp(last_entry.get("ts") / 1000).strftime("%Y-%m-%d")
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
    
    Args:
        asset_id (str): ID del asset
        tag_name (str): Nombre del tag
        project_folder (str): Ruta a la carpeta del proyecto
        token (str, optional): Token JWT para autenticación
    """
    # Obtener el sensor UUID desde el tag
    sensors = get_sensors_with_tags(asset_id, token)
    sensor = next((s for s in sensors if s.get("tag_name") == tag_name), None)
    if not sensor:
        logger.error(f"No se encontró un sensor con el tag '{tag_name}' para el asset {asset_id}.")
        return

    sensor_uuid = sensor.get("sensor_uuid")
    logger.info(f"Obteniendo lecturas diarias para el sensor {sensor_uuid} ({tag_name}) en el asset {asset_id}.")

    # Configurar rango de fechas
    start_date = datetime(2024, 1, 1)
    end_date = datetime.now()  # Hasta hoy si el año actual, o el 31 de diciembre

    # Nombre del archivo donde se guardan las lecturas
    file_name = f"daily_readings_{asset_id}_{tag_name}.csv"
    file_path = os.path.join(project_folder, file_name)

    # Verificar si el archivo ya existe y cargarlo
    existing_data = None
    if os.path.exists(file_path):
        existing_data = pd.read_csv(file_path)
        try:
            existing_data["date"] = pd.to_datetime(existing_data["date"], errors='coerce')  # Manejar errores de conversión
        except Exception as e:
            logger.error(f"Error al convertir las fechas del archivo existente: {e}")
            return

        logger.info(f"Archivo existente encontrado: {file_name}. Actualizando lecturas faltantes.")

    # Determinar la fecha de inicio para las nuevas lecturas
    if existing_data is not None and not existing_data.empty:
        last_recorded_date = existing_data["date"].max()

        # Asegurar que last_recorded_date es datetime y calcular start_date
        if pd.notnull(last_recorded_date) and isinstance(last_recorded_date, pd.Timestamp):
            start_date = max(start_date, last_recorded_date + timedelta(days=1))
        else:
            logger.error(f"La última fecha registrada no es válida: {last_recorded_date}")
            return

    # Validar que start_date y end_date son datetime antes de comparar
    if not isinstance(start_date, datetime):
        start_date = pd.to_datetime(start_date)

    if not isinstance(end_date, datetime):
        end_date = pd.to_datetime(end_date)

    # Si la fecha de inicio es posterior a la fecha de finalización, no hay nada que actualizar
    if start_date > end_date:
        logger.info(f"Todas las lecturas están actualizadas hasta el día de hoy ({end_date.strftime('%Y-%m-%d')}).")
        return existing_data

    # Generar rango de fechas faltantes
    missing_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    # Obtener lecturas para fechas faltantes
    daily_readings = []
    with tqdm(total=len(missing_dates), desc="Obteniendo lecturas faltantes") as pbar:
        for date in missing_dates:
            # Usar formato MM-DD-YYYY que es el que espera el servidor
            formatted_date = date.strftime("%m-%d-%Y")
            logger.debug(f"Obteniendo lectura para fecha {formatted_date}")
            value, timestamp = get_sensor_value_for_date(asset_id, sensor.get("device_id"), sensor.get("sensor_id"), sensor.get("gateway_id"), formatted_date, token)
            
            # Añadir más información al log, especialmente cuando no hay datos disponibles
            sensor_info = f"asset_id:{asset_id}, device_id:{sensor.get('device_id')}, sensor_id:{sensor.get('sensor_id')}, gateway_id:{sensor.get('gateway_id')}"
            if value == "Sin datos disponibles":
                logger.info(f"t:{formatted_date}:v:{value} - {sensor_info}")
            else:
                logger.info(f"t:{formatted_date}:v:{value}")

            if value != "Sin datos disponibles":
                daily_readings.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "value": value,
                    "timestamp": timestamp
                })
            pbar.update(1)

    # Crear DataFrame con lecturas nuevas
    new_data = pd.DataFrame(daily_readings)
    if not new_data.empty:
        logger.info(f"Lecturas faltantes obtenidas: {len(new_data)} días.")

        # Convertir la columna 'date' de ambos DataFrame a datetime
        if existing_data is not None:
            existing_data["date"] = pd.to_datetime(existing_data["date"], errors='coerce')
        new_data["date"] = pd.to_datetime(new_data["date"], errors='coerce')

        # Combinar con los datos existentes (si los hay)
        if existing_data is not None:
            updated_data = pd.concat([existing_data, new_data]).drop_duplicates(subset=["date"]).sort_values(by="date")
        else:
            updated_data = new_data

        # Verificar que las fechas son consistentes después de la combinación
        if updated_data["date"].isnull().any():
            logger.error("Se encontraron fechas inválidas en el DataFrame combinado. Por favor, verifica los datos.")
            return

        # Guardar los datos actualizados
        updated_data.to_csv(file_path, index=False)
        logger.info(f"Archivo actualizado: {file_path}.")

        # Validar el archivo guardado
        validated_data = pd.read_csv(file_path)
        validated_data["date"] = pd.to_datetime(validated_data["date"], errors='coerce')
        if validated_data["date"].isnull().any():
            logger.error("Error: Las fechas en el archivo actualizado no son válidas.")
            return

        # Mostrar primeras filas como ejemplo
        logger.info("\nEjemplo de datos:")
        logger.info(validated_data.head())
        return updated_data
    else:
        logger.error(f"No se obtuvieron nuevas lecturas para el sensor {sensor_uuid} ({tag_name}).")

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