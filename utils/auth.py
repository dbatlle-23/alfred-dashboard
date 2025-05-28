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
    
    def check_token_expiry_and_renew(self, token):
        """
        Verifica si un token está cerca de expirar y lo renueva si es necesario
        
        Args:
            token: Token JWT a verificar
            
        Returns:
            tuple: (is_valid, new_token_or_error_message)
                - is_valid: True si el token es válido (renovado o no), False si hay error
                - new_token_or_error_message: Nuevo token si se renovó, token original si está válido, mensaje de error si falló
        """
        try:
            if not token:
                logger.warning("No se proporcionó token para verificar expiración")
                return False, "No se proporcionó token"
            
            # Verificar el token actual
            user_data = self.verify_jwt_token(token)
            if not user_data:
                logger.info("Token expirado o inválido, necesita renovación")
                return False, "Token JWT expirado"
            
            # Verificar si está cerca de expirar (menos de 5 minutos restantes)
            import jwt
            try:
                # Decodificar sin verificar para obtener el tiempo de expiración
                payload = jwt.decode(token, options={"verify_signature": False})
                exp_timestamp = payload.get('exp')
                if exp_timestamp:
                    from datetime import datetime
                    exp_time = datetime.fromtimestamp(exp_timestamp)
                    now = datetime.now()
                    time_remaining = exp_time - now
                    
                    # Si quedan menos de 5 minutos, considerarlo como "próximo a expirar"
                    if time_remaining.total_seconds() < 300:  # 5 minutos
                        logger.info(f"Token expira en {time_remaining.total_seconds()} segundos, pero aún es válido")
                        # Por ahora, devolver el token como válido
                        # En el futuro se podría implementar renovación automática aquí
                        return True, token
                
            except Exception as decode_error:
                logger.debug(f"Error al decodificar token para verificar expiración: {decode_error}")
            
            # Token válido y no próximo a expirar
            logger.debug("Token válido y no próximo a expirar")
            return True, token
            
        except Exception as e:
            logger.error(f"Error al verificar expiración del token: {str(e)}")
            return False, f"Error al verificar token: {str(e)}"
    
    def make_authenticated_request_with_retry(self, token, method, url, data=None, headers=None, max_retries=2):
        """
        Realiza una solicitud HTTP con reintentos automáticos en caso de token expirado
        
        Args:
            token: Token JWT para autenticación
            method: Método HTTP (GET, POST, etc.)
            url: URL completa para la solicitud
            data: Datos para enviar (para POST/PUT)
            headers: Headers adicionales
            max_retries: Máximo número de reintentos
            
        Returns:
            tuple: (success, response_or_error)
                - success: True si la solicitud fue exitosa, False si falló
                - response_or_error: Objeto Response si exitoso, mensaje de error si falló
        """
        import requests
        
        for attempt in range(max_retries + 1):
            try:
                # Verificar y potencialmente renovar el token
                is_valid, token_result = self.check_token_expiry_and_renew(token)
                if not is_valid:
                    logger.error(f"Token inválido en intento {attempt + 1}: {token_result}")
                    return False, f"Token JWT expirado"
                
                # Usar el token (renovado o original)
                current_token = token_result
                
                # Obtener headers de autenticación
                auth_headers = self.get_auth_headers_from_token(current_token)
                if not auth_headers:
                    return False, "No se pudieron obtener headers de autenticación"
                
                # Combinar headers
                final_headers = auth_headers.copy()
                if headers:
                    final_headers.update(headers)
                
                # Realizar la solicitud
                logger.info(f"Realizando solicitud {method} a {url} (intento {attempt + 1})")
                
                if method.upper() == "GET":
                    response = requests.get(url, headers=final_headers, timeout=10)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=final_headers, json=data, timeout=10)
                elif method.upper() == "PUT":
                    response = requests.put(url, headers=final_headers, json=data, timeout=10)
                elif method.upper() == "DELETE":
                    response = requests.delete(url, headers=final_headers, timeout=10)
                else:
                    return False, f"Método HTTP no soportado: {method}"
                
                # Verificar respuesta
                if response.status_code == 401:
                    logger.warning(f"Error 401 en intento {attempt + 1}, token posiblemente expirado")
                    if attempt < max_retries:
                        logger.info(f"Reintentando... (intento {attempt + 2}/{max_retries + 1})")
                        continue
                    else:
                        return False, "Token JWT expirado"
                elif 200 <= response.status_code < 300:
                    logger.info(f"Solicitud exitosa: HTTP {response.status_code}")
                    return True, response
                else:
                    # Otros errores HTTP no relacionados con autenticación
                    logger.error(f"Error HTTP {response.status_code}: {response.text}")
                    return False, f"Error HTTP {response.status_code}: {response.text}"
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout en intento {attempt + 1}")
                if attempt < max_retries:
                    continue
                return False, "Timeout al realizar la solicitud"
            except requests.exceptions.ConnectionError:
                logger.warning(f"Error de conexión en intento {attempt + 1}")
                if attempt < max_retries:
                    continue
                return False, "Error de conexión"
            except Exception as e:
                logger.error(f"Error inesperado en intento {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    continue
                return False, f"Error inesperado: {str(e)}"
        
        return False, "Se agotaron los reintentos"
    
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
        Realiza una solicitud a la API con autenticación JWT
        
        Args:
            token: Token JWT para autenticación
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API (sin la URL base)
            data: Datos para enviar en la solicitud (para POST, PUT, etc.)
            params: Parámetros de consulta para la URL
            
        Returns:
            dict: Respuesta de la API en formato JSON
        """
        try:
            # Verificar si estamos en modo debug
            debug_mode = os.environ.get("DASH_DEBUG", "false").lower() == 'true'
            
            if debug_mode:
                print("\n" + "="*80)
                print(f"[DEBUG AUTH] INICIO make_api_request - Endpoint: {endpoint}, Método: {method}")
            
            # Verificar que el token sea válido
            if not token:
                if debug_mode:
                    print("[DEBUG AUTH] make_api_request - No se proporcionó token JWT")
                return {"error": "No se proporcionó token JWT"}
            
            # Construir la URL completa
            base_url = os.environ.get("API_BASE_URL", "https://services.alfredsmartdata.com")
            
            # Eliminar barras iniciales y finales para evitar dobles barras
            endpoint_clean = endpoint.strip('/')
            
            url = f"{base_url}/{endpoint_clean}"
            if debug_mode:
                print(f"[DEBUG AUTH] make_api_request - URL completa: {url}")
            
            # Obtener los headers de autenticación
            headers = self.get_auth_headers_from_token(token)
            if debug_mode:
                print(f"[DEBUG AUTH] make_api_request - Headers: {headers}")
            
            # Mostrar los parámetros de la solicitud
            if debug_mode:
                if params:
                    print(f"[DEBUG AUTH] make_api_request - Parámetros: {params}")
                if data:
                    print(f"[DEBUG AUTH] make_api_request - Datos: {data}")
                
                # Realizar la solicitud HTTP
                print(f"[DEBUG AUTH] make_api_request - Realizando solicitud {method} a {url}")
            
            # Simular la respuesta para desarrollo/pruebas
            if os.environ.get("ENVIRONMENT") == "development" or os.environ.get("MOCK_API") == "true":
                if debug_mode:
                    print("[DEBUG AUTH] make_api_request - Modo de desarrollo/pruebas, simulando respuesta")
                
                # Simular respuesta para diferentes endpoints
                if endpoint == "clients":
                    from utils.api import get_clientes_fallback
                    response_data = {"data": get_clientes_fallback()}
                elif endpoint == "projects":
                    from utils.api import get_projects_fallback
                    client_id = params.get("client") if params else None
                    response_data = {"data": get_projects_fallback(client_id)}
                elif endpoint == "assets":
                    from utils.api import get_assets_fallback
                    project_id = params.get("project_id") if params else None
                    response_data = {"data": get_assets_fallback(project_id)}
                else:
                    response_data = {"data": [], "message": "Endpoint no implementado en modo simulación"}
                
                if debug_mode:
                    print(f"[DEBUG AUTH] make_api_request - Respuesta simulada: {type(response_data)}")
                    if isinstance(response_data, dict):
                        print(f"[DEBUG AUTH] make_api_request - Claves en la respuesta: {list(response_data.keys())}")
                        for key, value in response_data.items():
                            if isinstance(value, list):
                                print(f"[DEBUG AUTH] make_api_request - Lista en '{key}' con {len(value)} elementos")
                    
                    print(f"[DEBUG AUTH] FIN make_api_request (simulado)")
                    print("="*80 + "\n")
                
                return response_data
            
            # Realizar la solicitud HTTP real
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, params=params)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, params=params)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, params=params)
            else:
                if debug_mode:
                    print(f"[DEBUG AUTH] make_api_request - Método no soportado: {method}")
                return {"error": f"Método no soportado: {method}"}
            
            # Verificar si la respuesta es exitosa
            if response.status_code >= 200 and response.status_code < 300:
                if debug_mode:
                    print(f"[DEBUG AUTH] make_api_request - Respuesta exitosa: {response.status_code}")
                try:
                    response_data = response.json()
                    if debug_mode:
                        print(f"[DEBUG AUTH] make_api_request - Respuesta JSON: {type(response_data)}")
                        if isinstance(response_data, dict):
                            print(f"[DEBUG AUTH] make_api_request - Claves en la respuesta: {list(response_data.keys())}")
                            for key, value in response_data.items():
                                if isinstance(value, list):
                                    print(f"[DEBUG AUTH] make_api_request - Lista en '{key}' con {len(value)} elementos")
                        print(f"[DEBUG AUTH] FIN make_api_request (exitoso)")
                        print("="*80 + "\n")
                    return response_data
                except ValueError:
                    if debug_mode:
                        print(f"[DEBUG AUTH] make_api_request - La respuesta no es JSON válido: {response.text[:100]}...")
                        print(f"[DEBUG AUTH] FIN make_api_request (error de formato)")
                        print("="*80 + "\n")
                    return {"error": "La respuesta no es JSON válido", "text": response.text[:100]}
            else:
                if debug_mode:
                    print(f"[DEBUG AUTH] make_api_request - Error en la respuesta: {response.status_code}")
                try:
                    error_data = response.json()
                    if debug_mode:
                        print(f"[DEBUG AUTH] make_api_request - Datos de error: {error_data}")
                        print(f"[DEBUG AUTH] FIN make_api_request (error de API)")
                        print("="*80 + "\n")
                    return {"error": f"Error {response.status_code}", "details": error_data}
                except ValueError:
                    if debug_mode:
                        print(f"[DEBUG AUTH] make_api_request - Error sin formato JSON: {response.text[:100]}...")
                        print(f"[DEBUG AUTH] FIN make_api_request (error sin formato)")
                        print("="*80 + "\n")
                    return {"error": f"Error {response.status_code}", "text": response.text[:100]}
        except Exception as e:
            logger.error(f"Error en make_api_request: {str(e)}")
            if os.environ.get("DASH_DEBUG", "false").lower() == 'true':
                print(f"[ERROR AUTH] make_api_request: {str(e)}")
                import traceback
                print(traceback.format_exc())
                print(f"[DEBUG AUTH] FIN make_api_request (excepción)")
                print("="*80 + "\n")
            return {"error": f"Excepción: {str(e)}"}
    
    def get_token(self):
        """
        Obtiene el token JWT actual desde el contexto de la aplicación
        
        Returns:
            str: Token JWT o None si no hay token disponible
        """
        try:
            # Intentar obtener el token del contexto de callback
            from dash import callback_context
            
            # Verificar si estamos en un callback
            if callback_context and hasattr(callback_context, 'triggered'):
                # Buscar el token en los inputs o states del callback
                if hasattr(callback_context, 'inputs') and callback_context.inputs:
                    for key, value in callback_context.inputs.items():
                        if 'jwt-token-store' in key:
                            if isinstance(value, dict) and 'token' in value:
                                logger.debug("Token JWT obtenido del input jwt-token-store")
                                if os.environ.get("DASH_DEBUG", "false").lower() == 'true':
                                    print(f"[DEBUG AUTH] Token obtenido de jwt-token-store en inputs")
                                return value.get('token')
                
                # Si no está en inputs, buscar en states
                if hasattr(callback_context, 'states') and callback_context.states:
                    for key, value in callback_context.states.items():
                        if 'jwt-token-store' in key:
                            if isinstance(value, dict) and 'token' in value:
                                logger.debug("Token JWT obtenido del state jwt-token-store")
                                if os.environ.get("DASH_DEBUG", "false").lower() == 'true':
                                    print(f"[DEBUG AUTH] Token obtenido de jwt-token-store en states")
                                return value.get('token')
                
                # No mostrar advertencia, ya que es normal que no haya token en muchos callbacks
                # Solo registrar en debug
                if callback_context.triggered and os.environ.get("DASH_DEBUG", "false").lower() == 'true':
                    logger.debug("No se pudo obtener el token JWT del contexto de callback")
                    print(f"[DEBUG AUTH] No se pudo obtener token del contexto de callback")
            
            # Si no estamos en un callback o no se encontró el token, devolver None silenciosamente
            return None
        except Exception as e:
            # Solo registrar en debug, no como error
            logger.debug(f"Error al obtener el token JWT: {str(e)}")
            if os.environ.get("DASH_DEBUG", "false").lower() == 'true':
                print(f"[DEBUG AUTH ERROR] Error al obtener token: {str(e)}")
                import traceback
                logger.debug(f"Traceback: {traceback.format_exc()}")
            return None

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