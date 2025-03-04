import pytest
from unittest.mock import patch, MagicMock

from utils.error_handlers import (
    handle_exceptions,
    safe_db_operation,
    format_error_response,
    try_operation
)

class TestErrorHandlers:
    
    def test_handle_exceptions_no_error(self):
        # Definir una función de prueba
        @handle_exceptions()
        def test_func():
            return "success"
        
        # Ejecutar la función
        result = test_func()
        
        # Verificar resultados
        assert result == "success"
    
    def test_handle_exceptions_with_error(self):
        # Definir una función de prueba que lanza una excepción
        @handle_exceptions(default_return="error")
        def test_func():
            raise ValueError("Test error")
        
        # Ejecutar la función
        result = test_func()
        
        # Verificar resultados
        assert result == "error"
    
    def test_safe_db_operation_no_error(self):
        # Definir una función de prueba
        @safe_db_operation()
        def test_db_func():
            return "db success"
        
        # Ejecutar la función
        result = test_db_func()
        
        # Verificar resultados
        assert result == "db success"
    
    def test_safe_db_operation_with_error(self):
        # Definir una función de prueba que lanza una excepción
        @safe_db_operation(default_return="db error")
        def test_db_func():
            raise ValueError("Test DB error")
        
        # Ejecutar la función
        result = test_db_func()
        
        # Verificar resultados
        assert result == "db error"
    
    def test_format_error_response_without_traceback(self):
        # Crear una excepción
        error = ValueError("Test error message")
        
        # Formatear la respuesta
        response = format_error_response(error, include_traceback=False)
        
        # Verificar resultados
        assert response["error"] == "Test error message"
        assert response["error_type"] == "ValueError"
        assert "traceback" not in response
    
    def test_format_error_response_with_traceback(self):
        # Crear una excepción
        error = ValueError("Test error message")
        
        # Formatear la respuesta
        response = format_error_response(error, include_traceback=True)
        
        # Verificar resultados
        assert response["error"] == "Test error message"
        assert response["error_type"] == "ValueError"
        assert "traceback" in response
    
    def test_try_operation_success(self):
        # Definir una función de prueba
        def test_op():
            return "operation success"
        
        # Ejecutar la operación
        success, result, error_msg = try_operation(test_op)
        
        # Verificar resultados
        assert success is True
        assert result == "operation success"
        assert error_msg is None
    
    def test_try_operation_failure(self):
        # Definir una función de prueba que lanza una excepción
        def test_op():
            raise ValueError("Operation failed")
        
        # Ejecutar la operación
        success, result, error_msg = try_operation(test_op)
        
        # Verificar resultados
        assert success is False
        assert result is None
        assert error_msg == "Operation failed"
    
    def test_try_operation_with_args(self):
        # Definir una función de prueba con argumentos
        def test_op_with_args(a, b, c=0):
            return a + b + c
        
        # Ejecutar la operación con argumentos
        success, result, error_msg = try_operation(test_op_with_args, 1, 2, c=3)
        
        # Verificar resultados
        assert success is True
        assert result == 6
        assert error_msg is None 