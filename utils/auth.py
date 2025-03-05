import requests
import json
import os
import time
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import redirect, request
import dash
from dash import html, dcc, callback_context
from dash.exceptions import PreventUpdate

# Configuración de la API
API_BASE_URL = "https://services.alfredsmartdata.com"
AUTH_ENDPOINT = "/users/login"

# Configuración JWT
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "alfred-dashboard-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DELTA = timedelta(hours=24)

# Configuración de logging
from utils.logging import get_logger
logger = get_logger(__name__)

class AuthService:
    """Servicio para manejar la autenticación con la API de Alfred Smart usando JWT"""
    
    def __init__(self):
        # No almacenamos el token en la instancia del servicio
        # Los tokens se almacenarán en dcc.Store en el cliente
        pass
    
    def generate_jwt_token(self, user_data):
        """
        Genera un token JWT para el usuario
        
        Args:
            user_data: Datos del usuario a incluir en el token
            
        Returns:
            str: Token JWT generado
        """
        # Establecer tiempo de expiración (usando UTC)
        expiry = datetime.utcnow() + JWT_EXPIRATION_DELTA
        
        # Crear payload del token
        payload = {
            'user_type': user_data.get('user_type'),
            'permissions': user_data.get('permissions', []),
            'assets_manager_sections': user_data.get('assets_manager_sections', []),
            'api_token': user_data.get('api_token'),  # Incluir el token de la API
            'exp': expiry
        }
        
        # Generar token
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        logger.info("Token JWT generado correctamente")
        return token
    
    def verify_jwt_token(self, token):
        """
        Verifica la validez de un token JWT
        
        Args:
            token: Token JWT a verificar
            
        Returns:
            dict: Datos del usuario si el token es válido, None si no lo es
        """
        try:
            # Decodificar el token con verificación de expiración
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            logger.debug("Token JWT verificado correctamente")
            return payload
        except jwt.ExpiredSignatureError:
            logger.info("Token JWT expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Token JWT inválido: {str(e)}")
            return None
    
    def login(self, username, password):
        """
        Autentica al usuario con la API de Alfred Smart y genera un token JWT
        
        Args:
            username: Nombre de usuario (email)
            password: Contraseña
            
        Returns:
            dict: Respuesta con el resultado de la autenticación y el token JWT
        """
        try:
            url = f"{API_BASE_URL}{AUTH_ENDPOINT}"
            payload = {
                "email": username,
                "password": password
            }
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "Accept-version": "1",
                "User-Agent": "Alfred Dashboard/1.0"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                session_data = data.get('session', {})
                
                # Extraer el token de la API
                api_token = session_data.get('token')
                if not api_token:
                    logger.error("No se pudo obtener el token de la API en la respuesta de login")
                    return {"success": False, "message": "Error de autenticación: No se pudo obtener el token"}
                
                # Crear datos de usuario para el token JWT
                user_data = {
                    'user_type': session_data.get('user_type'),
                    'permissions': session_data.get('permissions', []),
                    'assets_manager_sections': session_data.get('assets_manager_sections', []),
                    'api_token': api_token  # Incluimos el token de la API en nuestro JWT
                }
                
                # Generar token JWT
                jwt_token = self.generate_jwt_token(user_data)
                
                logger.info(f"Login exitoso para el usuario: {username}")
                return {
                    "success": True, 
                    "message": "Login exitoso", 
                    "token": jwt_token,
                    "user_data": user_data
                }
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', 'Error desconocido')
                except:
                    error_msg = f"Error {response.status_code}"
                
                logger.error(f"Error de login: {error_msg}")
                return {"success": False, "message": f"Error de autenticación: {error_msg}"}
                
        except Exception as e:
            logger.error(f"Error en el proceso de login: {str(e)}")
            return {"success": False, "message": f"Error de conexión: {str(e)}"}
    
    def is_authenticated(self, token):
        """
        Verifica si el token JWT es válido
        
        Args:
            token: Token JWT a verificar
            
        Returns:
            bool: True si el token es válido, False en caso contrario
        """
        if not token:
            logger.debug("Token JWT no proporcionado")
            return False
        
        # Verificar el token
        user_data = self.verify_jwt_token(token)
        if user_data is None:
            logger.debug("Token JWT inválido o expirado")
            return False
        
        # Verificar que el token contenga el token de la API
        if 'api_token' not in user_data:
            logger.warning("Token JWT válido pero no contiene el token de la API")
            return False
            
        logger.debug("Token JWT válido y contiene el token de la API")
        return True
    
    def get_user_data_from_token(self, token):
        """
        Obtiene los datos del usuario desde un token JWT
        
        Args:
            token: Token JWT
            
        Returns:
            dict: Datos del usuario o un diccionario vacío si el token es inválido
        """
        if not token:
            return {}
        
        user_data = self.verify_jwt_token(token)
        return user_data if user_data else {}
    
    def get_auth_headers_from_token(self, token):
        """
        Obtiene los headers de autenticación a partir de un token JWT
        
        Args:
            token: Token JWT
            
        Returns:
            dict: Headers de autenticación o un diccionario vacío si el token es inválido
        """
        if not token:
            logger.warning("No se proporcionó token JWT para obtener headers de autenticación")
            return {}
        
        user_data = self.verify_jwt_token(token)
        if not user_data:
            logger.warning("Token JWT inválido al intentar obtener headers de autenticación")
            return {}
        
        # Obtener el token de la API del payload JWT
        api_token = user_data.get('api_token')
        if not api_token:
            logger.warning("Token JWT válido pero no contiene el token de la API")
            logger.debug(f"Datos de usuario en el token JWT: {user_data}")
            return {}
        
        logger.debug(f"Token de API extraído correctamente del token JWT: {api_token[:10]}...")
        return {
            "Authorization": f"Bearer {api_token}"
        }
    
    def has_permission(self, token, permission):
        """
        Verifica si el usuario tiene un permiso específico
        
        Args:
            token: Token JWT
            permission: Permiso a verificar
            
        Returns:
            bool: True si el usuario tiene el permiso, False en caso contrario
        """
        if not token:
            return False
        
        user_data = self.verify_jwt_token(token)
        if not user_data:
            return False
        
        permissions = user_data.get('permissions', [])
        return permission in permissions
    
    def make_api_request(self, token, method, endpoint, data=None, params=None):
        """
        Realiza una solicitud a la API con autenticación
        
        Args:
            token: Token JWT
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint de la API (sin la URL base)
            data: Datos para enviar en el cuerpo de la solicitud (para POST/PUT)
            params: Parámetros de consulta (para GET)
            
        Returns:
            dict: Respuesta de la API en formato JSON
        """
        try:
            # Verificar autenticación
            logger.debug(f"Verificando autenticación para solicitud a {endpoint}")
            if not self.is_authenticated(token):
                logger.error("No hay una sesión activa para realizar la solicitud a la API")
                return {"error": "No autenticado"}
            
            # Obtener los headers de autenticación
            headers = self.get_auth_headers_from_token(token)
            headers["Content-Type"] = "application/json"
            
            # Registrar los headers para depuración (ocultando parte del token)
            auth_header = headers.get('Authorization', '')
            if auth_header:
                logger.debug(f"Headers de autenticación: Authorization: Bearer {auth_header.split(' ')[1][:10]}...")
            else:
                logger.warning("No se encontró el header Authorization en los headers de autenticación")
                logger.debug(f"Headers disponibles: {headers}")
            
            # Asegurarse de que el endpoint no comience con /
            if endpoint.startswith("/"):
                endpoint = endpoint[1:]
            
            # Construir la URL completa
            from utils.api import BASE_URL
            url = f"{BASE_URL}/{endpoint}"
            
            logger.debug(f"Realizando solicitud {method} a {url}")
            if params:
                logger.debug(f"Parámetros: {params}")
            
            # Realizar la solicitud según el método
            method = method.upper()
            if method == "GET":
                logger.debug("Ejecutando solicitud GET")
                response = requests.get(url, params=params, headers=headers)
            elif method == "POST":
                logger.debug("Ejecutando solicitud POST")
                response = requests.post(url, json=data, headers=headers)
            elif method == "PUT":
                logger.debug("Ejecutando solicitud PUT")
                response = requests.put(url, json=data, headers=headers)
            elif method == "DELETE":
                logger.debug("Ejecutando solicitud DELETE")
                response = requests.delete(url, json=data, headers=headers)
            else:
                logger.error(f"Método HTTP no soportado: {method}")
                return {"error": f"Método HTTP no soportado: {method}"}
            
            # Verificar si la respuesta es exitosa
            logger.debug(f"Respuesta recibida con código: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    logger.debug(f"Respuesta JSON recibida con claves: {list(json_response.keys()) if isinstance(json_response, dict) else 'no es dict'}")
                    
                    # Registrar más detalles de la respuesta para depuración
                    if isinstance(json_response, dict):
                        for key, value in json_response.items():
                            if isinstance(value, list) and len(value) > 0:
                                logger.debug(f"Lista encontrada en clave '{key}' con {len(value)} elementos")
                                if len(value) > 0 and isinstance(value[0], dict):
                                    logger.debug(f"Primer elemento de la lista: {value[0]}")
                    
                    return json_response
                except ValueError:
                    logger.error("La respuesta no es un JSON válido")
                    logger.debug(f"Texto de respuesta: {response.text[:100]}...")
                    return {"error": "La respuesta no es un JSON válido", "text": response.text}
            elif response.status_code == 401:
                logger.error("Token de autenticación inválido o expirado")
                logger.debug(f"Texto de respuesta: {response.text[:100]}...")
                return {"error": "Token de autenticación inválido o expirado"}
            else:
                logger.error(f"Error en la solicitud: {response.status_code} - {response.text[:100]}...")
                return {"error": f"Error en la solicitud: {response.status_code}", "text": response.text}
        except Exception as e:
            logger.error(f"Error en petición API: {str(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e)}

# Crear una instancia global del servicio de autenticación
auth_service = AuthService()

# Función para proteger callbacks
def protect_callbacks(app):
    """
    Protege todos los callbacks para verificar autenticación
    
    Args:
        app: Instancia de la aplicación Dash
    """
    # Registramos un callback global para verificar la autenticación
    @app.callback(
        dash.dependencies.Output("global-auth-status", "children"),
        [dash.dependencies.Input("url", "pathname")],
        [dash.dependencies.State("jwt-token-store", "data")],
        prevent_initial_call=True
    )
    def check_auth_status(pathname, token_data):
        # Si la ruta actual es /login, permitir el acceso
        if pathname == '/login':
            logger.debug("Accediendo a la página de login, no se requiere autenticación")
            return None
        
        # Obtener el token JWT del store
        token = token_data.get('token') if token_data else None
        
        # Verificar autenticación
        if not token:
            logger.debug("No hay token JWT disponible, redirigiendo a login")
            return dash.no_update
        
        if not auth_service.is_authenticated(token):
            logger.warning("Token JWT inválido o expirado, redirigiendo a login")
            return dash.no_update
        
        # Si está autenticado, no hacer nada
        logger.debug(f"Usuario autenticado accediendo a {pathname}")
        return None 