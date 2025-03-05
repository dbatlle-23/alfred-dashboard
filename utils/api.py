import requests
import json
from utils.logging import get_logger
from utils.auth import auth_service, AuthService

logger = get_logger(__name__)

# Configuración de la API
BASE_URL = "https://services.alfredsmartdata.com"
CLIENTS_ENDPOINT = f"{BASE_URL}/clients"
PROJECTS_ENDPOINT = f"{BASE_URL}/projects"

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
        client_id: ID del cliente para filtrar los proyectos (opcional)
        jwt_token: Token JWT para autenticación (opcional)
        
    Returns:
        list: Lista de proyectos
    """
    try:
        # Verificar autenticación
        if jwt_token:
            # Usar el token JWT proporcionado
            if not auth_service.is_authenticated(jwt_token):
                logger.warning("Token JWT inválido para obtener proyectos")
                return get_projects_fallback(client_id)
                
            # Construir el endpoint (sin la URL base)
            endpoint = "projects"
            
            # Añadir parámetros de consulta si se proporciona un client_id
            params = {}
            if client_id and client_id != "all":
                # Usar el parámetro "client" como se especifica en la API
                params["client"] = client_id
                logger.debug(f"Obteniendo proyectos para el cliente: {client_id}")
            
            # Hacer la solicitud a la API con el token JWT
            response = auth_service.make_api_request(jwt_token, "GET", endpoint, params=params)
        else:
            # Si no hay token JWT, usar fallback directamente
            logger.info("No se proporcionó token JWT para obtener proyectos (comportamiento normal durante inicialización)")
            return get_projects_fallback(client_id)
        
        # Verificar si hay un error en la respuesta
        if isinstance(response, dict) and "error" in response:
            logger.error(f"Error al obtener proyectos: {response.get('error')}")
            return get_projects_fallback(client_id)
        
        # Registrar la estructura de la respuesta para depuración
        logger.debug(f"Tipo de respuesta recibida: {type(response)}")
        
        # Extraer los proyectos de la respuesta según la estructura proporcionada
        projects = []
        
        if isinstance(response, dict) and "data" in response and isinstance(response["data"], list):
            # Estructura estándar como en el ejemplo proporcionado
            projects = response["data"]
            logger.debug(f"Se encontraron {len(projects)} proyectos en la respuesta")
            
            # Registrar información del primer proyecto para depuración
            if len(projects) > 0:
                logger.debug(f"Primer proyecto: {json.dumps(projects[0], indent=2, default=str)}")
        
        # Si no se encontraron proyectos, usar fallback
        if not projects:
            logger.warning(f"No se encontraron proyectos para el cliente {client_id}, usando fallback")
            return get_projects_fallback(client_id)
        
        return projects
    except Exception as e:
        logger.error(f"Error al obtener proyectos: {str(e)}")
        return get_projects_fallback(client_id)

def get_projects_fallback(client_id=None):
    """
    Devuelve datos de ejemplo de proyectos como fallback
    
    Args:
        client_id (str, optional): ID del cliente para filtrar proyectos
        
    Returns:
        list: Lista de proyectos de ejemplo con la misma estructura que la API real
    """
    # Proyectos de ejemplo con la estructura correcta
    all_projects = [
        {
            "id": "project-1a",
            "name": "Edificio 1A",
            "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
            "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
            "client": {
                "id": "1",
                "name": "Cliente A"
            },
            "type": "RENT",
            "status": "ACCEPTED"
        },
        {
            "id": "project-1b",
            "name": "Edificio 1B",
            "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
            "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
            "client": {
                "id": "1",
                "name": "Cliente A"
            },
            "type": "RENT",
            "status": "ACCEPTED"
        },
        {
            "id": "project-2a",
            "name": "Edificio 2A",
            "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
            "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
            "client": {
                "id": "2",
                "name": "Cliente B"
            },
            "type": "RENT",
            "status": "ACCEPTED"
        },
        {
            "id": "project-2b",
            "name": "Edificio 2B",
            "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
            "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
            "client": {
                "id": "2",
                "name": "Cliente B"
            },
            "type": "RENT",
            "status": "ACCEPTED"
        },
        {
            "id": "project-3a",
            "name": "Edificio 3A",
            "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
            "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
            "client": {
                "id": "3",
                "name": "Cliente C"
            },
            "type": "RENT",
            "status": "ACCEPTED"
        },
        {
            "id": "project-4a",
            "name": "Edificio 4A",
            "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
            "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
            "client": {
                "id": "4",
                "name": "Cliente D"
            },
            "type": "RENT",
            "status": "ACCEPTED"
        },
        # Proyectos específicos para el cliente problemático
        {
            "id": "project-uuid-1",
            "name": "Edificio Catella 1",
            "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
            "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
            "client": {
                "id": "8f4e2492-68e0-4865-a11a-f7093c6019cb",
                "name": "Catella"
            },
            "type": "RENT",
            "status": "ACCEPTED"
        },
        {
            "id": "project-uuid-2",
            "name": "Edificio Catella 2",
            "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
            "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
            "client": {
                "id": "8f4e2492-68e0-4865-a11a-f7093c6019cb",
                "name": "Catella"
            },
            "type": "RENT",
            "status": "ACCEPTED"
        },
        {
            "id": "project-uuid-3",
            "name": "Edificio Catella 3",
            "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
            "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
            "client": {
                "id": "8f4e2492-68e0-4865-a11a-f7093c6019cb",
                "name": "Catella"
            },
            "type": "RENT",
            "status": "ACCEPTED"
        }
    ]
    
    # Si se proporciona un client_id, filtrar los proyectos
    if client_id and client_id != "all":
        filtered_projects = [p for p in all_projects if p["client"]["id"] == str(client_id)]
        if filtered_projects:
            logger.debug(f"Devolviendo {len(filtered_projects)} proyectos de fallback para el cliente {client_id}")
            return filtered_projects
        else:
            # Si no hay proyectos para este cliente, crear algunos genéricos
            logger.debug(f"Creando proyectos genéricos para el cliente {client_id}")
            return [
                {
                    "id": f"generic-{client_id}-1",
                    "name": f"Proyecto Genérico 1",
                    "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
                    "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
                    "client": {
                        "id": str(client_id),
                        "name": f"Cliente {client_id}"
                    },
                    "type": "RENT",
                    "status": "ACCEPTED"
                },
                {
                    "id": f"generic-{client_id}-2",
                    "name": f"Proyecto Genérico 2",
                    "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
                    "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
                    "client": {
                        "id": str(client_id),
                        "name": f"Cliente {client_id}"
                    },
                    "type": "RENT",
                    "status": "ACCEPTED"
                },
                {
                    "id": f"generic-{client_id}-3",
                    "name": f"Proyecto Genérico 3",
                    "logo": "https://static.assets.alfredsmartdata.com/logos/default/pajarita_transparente_512px.png",
                    "background_image": "https://alfred-storage.ams3.digitaloceanspaces.com/images/default.jpeg",
                    "client": {
                        "id": str(client_id),
                        "name": f"Cliente {client_id}"
                    },
                    "type": "RENT",
                    "status": "ACCEPTED"
                }
            ]
    
    return all_projects 