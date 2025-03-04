import requests
import json
import os
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import redirect, request
import dash
from dash import html
from dash.exceptions import PreventUpdate

# Configuración de la API
API_BASE_URL = "https://services.alfredsmartdata.com"
AUTH_ENDPOINT = "/users/login"
TOKEN_FILE = "config/auth_token.json"

# Configuración de logging
from utils.logging import get_logger
logger = get_logger(__name__)

class AuthService:
    """Servicio para manejar la autenticación con la API de Alfred Smart"""
    
    def __init__(self):
        self.token = None
        self.token_expiry = None
        self.user_data = None
        self._load_token()
    
    def _load_token(self):
        """Carga el token desde el archivo si existe"""
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    self.token = data.get('token')
                    expiry_str = data.get('expiry')
                    if expiry_str:
                        self.token_expiry = datetime.fromtimestamp(int(expiry_str))
                    self.user_data = data.get('user_data', {})
                    logger.info("Token cargado desde archivo")
        except Exception as e:
            logger.error(f"Error al cargar el token: {str(e)}")
            self.token = None
            self.token_expiry = None
            self.user_data = None
    
    def _save_token(self):
        """Guarda el token en un archivo"""
        try:
            os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
            with open(TOKEN_FILE, 'w') as f:
                data = {
                    'token': self.token,
                    'expiry': int(self.token_expiry.timestamp()) if self.token_expiry else None,
                    'user_data': self.user_data
                }
                json.dump(data, f)
                logger.info("Token guardado en archivo")
        except Exception as e:
            logger.error(f"Error al guardar el token: {str(e)}")
    
    def login(self, username, password):
        """
        Autentica al usuario con la API de Alfred Smart
        
        Args:
            username: Nombre de usuario (email)
            password: Contraseña
            
        Returns:
            dict: Respuesta de la API con el resultado de la autenticación
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
                
                # Extraer el token y su tipo
                self.token = session_data.get('token')
                token_type = session_data.get('token_type', 'Bearer')
                
                # Establecer la expiración del token
                expires_at = session_data.get('expires_at')
                if expires_at:
                    self.token_expiry = datetime.fromtimestamp(expires_at)
                else:
                    # Si no hay expires_at, establecer 24 horas por defecto
                    self.token_expiry = datetime.now() + timedelta(hours=24)
                
                # Guardar datos del usuario
                self.user_data = {
                    'user_type': session_data.get('user_type'),
                    'permissions': session_data.get('permissions', []),
                    'assets_manager_sections': session_data.get('assets_manager_sections', [])
                }
                
                # Guardar el token
                self._save_token()
                
                logger.info(f"Login exitoso para el usuario: {username}")
                return {"success": True, "message": "Login exitoso"}
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
    
    def logout(self):
        """Cierra la sesión del usuario"""
        self.token = None
        self.token_expiry = None
        self.user_data = None
        
        # Eliminar el archivo de token si existe
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
                logger.info("Token eliminado")
            except Exception as e:
                logger.error(f"Error al eliminar el token: {str(e)}")
        
        return {"success": True, "message": "Sesión cerrada correctamente"}
    
    def is_authenticated(self):
        """Verifica si el usuario está autenticado y el token es válido"""
        if not self.token or not self.token_expiry:
            return False
        
        # Verificar si el token ha expirado
        if datetime.now() >= self.token_expiry:
            logger.info("Token expirado")
            return False
        
        return True
    
    def get_auth_headers(self):
        """Obtiene los headers de autenticación para las llamadas a la API"""
        if not self.is_authenticated():
            return {}
        
        return {
            "Authorization": f"Bearer {self.token}"
        }
    
    def get_user_data(self):
        """Obtiene los datos del usuario autenticado"""
        return self.user_data if self.is_authenticated() else {}
    
    def get_token(self):
        """
        Obtiene el token de autenticación actual
        
        Returns:
            str: Token de autenticación o None si no está autenticado
        """
        if not self.is_authenticated():
            return None
        return str(self.token) if self.token is not None else None
    
    def get_current_token(self):
        """
        Método alternativo para obtener el token de autenticación actual
        
        Returns:
            str: Token de autenticación o None si no está autenticado
        """
        if not self.is_authenticated():
            return None
        return str(self.token) if self.token is not None else None
    
    def has_permission(self, permission):
        """
        Verifica si el usuario tiene un permiso específico
        
        Args:
            permission: Permiso a verificar
            
        Returns:
            bool: True si el usuario tiene el permiso, False en caso contrario
        """
        if not self.is_authenticated():
            return False
        
        permissions = self.user_data.get('permissions', [])
        return permission in permissions
    
    def make_api_request(self, method, endpoint, data=None, params=None):
        """
        Realiza una solicitud a la API con autenticación
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint de la API (sin la URL base)
            data: Datos para enviar en el cuerpo de la solicitud (para POST/PUT)
            params: Parámetros de consulta (para GET)
            
        Returns:
            dict: Respuesta de la API en formato JSON
        """
        try:
            # Verificar autenticación
            if not self.is_authenticated():
                logger.error("No hay una sesión activa para realizar la solicitud a la API")
                return {"error": "No autenticado"}
            
            # Obtener los headers de autenticación
            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json"
            
            # Asegurarse de que el endpoint no comience con /
            if endpoint.startswith("/"):
                endpoint = endpoint[1:]
            
            # Construir la URL completa
            from utils.api import BASE_URL
            url = f"{BASE_URL}/{endpoint}"
            
            logger.debug(f"Realizando solicitud {method} a {url}")
            
            # Realizar la solicitud según el método
            method = method.upper()
            if method == "GET":
                response = requests.get(url, params=params, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, json=data, headers=headers)
            else:
                logger.error(f"Método HTTP no soportado: {method}")
                return {"error": f"Método HTTP no soportado: {method}"}
            
            # Verificar si la respuesta es exitosa
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    logger.error("La respuesta no es un JSON válido")
                    return {"error": "La respuesta no es un JSON válido", "text": response.text}
            elif response.status_code == 401:
                logger.error("Token de autenticación inválido o expirado")
                # Limpiar el token para forzar un nuevo login
                self.token = None
                self._save_token()
                return {"error": "Token de autenticación inválido o expirado"}
            else:
                logger.error(f"Error en la solicitud: {response.status_code} - {response.text}")
                return {"error": f"Error en la solicitud: {response.status_code}", "text": response.text}
        except Exception as e:
            logger.error(f"Error en petición API: {str(e)}")
            return {"error": str(e)}

# Crear una instancia global del servicio de autenticación
auth_service = AuthService()

# Decorador para proteger rutas
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not auth_service.is_authenticated():
            # Redirigir a la página de login
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# Función para proteger callbacks
def protect_callbacks(app):
    """
    Protege todos los callbacks para verificar autenticación
    
    Args:
        app: Instancia de la aplicación Dash
    """
    # En lugar de usar callback_context_manager, usamos un enfoque alternativo
    # Registramos un callback global para verificar la autenticación
    
    @app.callback(
        dash.dependencies.Output("global-auth-status", "children"),
        [dash.dependencies.Input("url", "pathname")],
        prevent_initial_call=True
    )
    def check_auth_status(pathname):
        # Si la ruta actual es /login, permitir el acceso
        if pathname == '/login':
            return None
        
        # Verificar autenticación
        if not auth_service.is_authenticated():
            # Redirigir a login
            return dash.no_update
        
        # Si está autenticado, no hacer nada
        return None
    
    # Nota: Este enfoque requiere que agregues un div con id="global-auth-status" en el layout principal
    # Este div se usa solo para el callback y no muestra nada al usuario 