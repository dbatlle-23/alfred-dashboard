import traceback
import functools
import logging
from typing import Callable, Any, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

def handle_exceptions(default_return: Any = None) -> Callable:
    """
    Decorador para manejar excepciones en funciones.
    
    Args:
        default_return: Valor a retornar en caso de excepción
        
    Returns:
        Decorador que maneja excepciones
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error en {func.__name__}: {str(e)}")
                logger.debug(traceback.format_exc())
                return default_return
        return wrapper
    return decorator

def safe_db_operation(default_return: Any = None) -> Callable:
    """
    Decorador específico para operaciones de base de datos.
    
    Args:
        default_return: Valor a retornar en caso de excepción
        
    Returns:
        Decorador que maneja excepciones de base de datos
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error en operación de base de datos {func.__name__}: {str(e)}")
                logger.debug(traceback.format_exc())
                return default_return
        return wrapper
    return decorator

def format_error_response(error: Exception, include_traceback: bool = False) -> Dict[str, str]:
    """
    Formatea una excepción para retornarla como respuesta.
    
    Args:
        error: Excepción a formatear
        include_traceback: Si se debe incluir el traceback completo
        
    Returns:
        Diccionario con información del error
    """
    response = {
        "error": str(error),
        "error_type": error.__class__.__name__
    }
    
    if include_traceback:
        response["traceback"] = traceback.format_exc()
        
    return response

def try_operation(operation: Callable, *args, **kwargs) -> Tuple[bool, Optional[Any], Optional[str]]:
    """
    Ejecuta una operación de forma segura y retorna el resultado o el error.
    
    Args:
        operation: Función a ejecutar
        *args: Argumentos posicionales para la función
        **kwargs: Argumentos de palabra clave para la función
        
    Returns:
        Tupla con (éxito, resultado, mensaje de error)
    """
    try:
        result = operation(*args, **kwargs)
        return True, result, None
    except Exception as e:
        logger.error(f"Error en operación {operation.__name__}: {str(e)}")
        logger.debug(traceback.format_exc())
        return False, None, str(e) 