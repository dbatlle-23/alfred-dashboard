import os
import pytest
import configparser
from unittest.mock import patch, MagicMock, mock_open
from sqlalchemy import create_engine

from utils.db_utils import (
    load_db_config,
    get_db_connection,
    test_connection,
    get_tables,
    get_table_structure
)

# Fixture para simular un archivo de configuración
@pytest.fixture
def mock_config_file():
    config_content = """
    [postgresql]
    host = localhost
    port = 5432
    dbname = testdb
    user = testuser
    password = testpass
    """
    return config_content

# Fixture para simular un motor de base de datos
@pytest.fixture
def mock_engine():
    engine = MagicMock()
    connection = MagicMock()
    engine.connect.return_value = connection
    return engine

class TestDbUtils:
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('configparser.ConfigParser')
    def test_load_db_config_success(self, mock_config_parser, mock_file, mock_exists, mock_config_file):
        # Configurar mocks
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = mock_config_file
        
        # Configurar el comportamiento del ConfigParser
        parser_instance = MagicMock()
        parser_instance.has_section.return_value = True
        parser_instance.items.return_value = [
            ('host', 'localhost'),
            ('port', '5432'),
            ('dbname', 'testdb'),
            ('user', 'testuser'),
            ('password', 'testpass')
        ]
        mock_config_parser.return_value = parser_instance
        
        # Ejecutar la función
        result = load_db_config()
        
        # Verificar resultados
        assert result is not None
        assert result['host'] == 'localhost'
        assert result['port'] == '5432'
        assert result['dbname'] == 'testdb'
        assert result['user'] == 'testuser'
        assert result['password'] == 'testpass'
        
    @patch('os.path.exists')
    def test_load_db_config_no_file(self, mock_exists):
        # Configurar mock para simular que el archivo no existe
        mock_exists.return_value = False
        
        # Ejecutar la función
        result = load_db_config()
        
        # Verificar resultados
        assert result is None
    
    @patch('utils.db_utils.load_db_config')
    @patch('utils.db_utils.create_engine')
    def test_get_db_connection_success(self, mock_create_engine, mock_load_config, mock_engine):
        # Configurar mocks
        mock_load_config.return_value = {
            'host': 'localhost',
            'port': '5432',
            'dbname': 'testdb',
            'user': 'testuser',
            'password': 'testpass'
        }
        mock_create_engine.return_value = mock_engine
        
        # Ejecutar la función
        result = get_db_connection()
        
        # Verificar resultados
        assert result is not None
        mock_create_engine.assert_called_once()
        
    @patch('utils.db_utils.load_db_config')
    def test_get_db_connection_no_config(self, mock_load_config):
        # Configurar mock para simular que no hay configuración
        mock_load_config.return_value = None
        
        # Ejecutar la función
        result = get_db_connection()
        
        # Verificar resultados
        assert result is None
    
    @patch('utils.db_utils.get_db_connection')
    def test_test_connection_success(self, mock_get_connection, mock_engine):
        # Configurar mock
        mock_get_connection.return_value = mock_engine
        
        # Ejecutar la función
        success, message, engine = test_connection()
        
        # Verificar resultados
        assert success is True
        assert "Conexión exitosa" in message
        assert engine is mock_engine
        
    @patch('utils.db_utils.get_db_connection')
    def test_test_connection_failure(self, mock_get_connection):
        # Configurar mock para simular fallo de conexión
        mock_get_connection.return_value = None
        
        # Ejecutar la función
        success, message, engine = test_connection()
        
        # Verificar resultados
        assert success is False
        assert "No se pudo establecer" in message
        assert engine is None
    
    @patch('utils.db_utils.get_db_connection')
    def test_get_tables_success(self, mock_get_connection, mock_engine):
        # Configurar mock
        mock_get_connection.return_value = mock_engine
        inspector = MagicMock()
        inspector.get_table_names.return_value = ['table1', 'table2']
        
        with patch('utils.db_utils.inspect', return_value=inspector):
            # Ejecutar la función
            success, tables, message = get_tables()
            
            # Verificar resultados
            assert success is True
            assert len(tables) == 2
            assert 'table1' in tables
            assert 'table2' in tables
            assert message is None
    
    @patch('utils.db_utils.get_db_connection')
    def test_get_tables_no_connection(self, mock_get_connection):
        # Configurar mock para simular fallo de conexión
        mock_get_connection.return_value = None
        
        # Ejecutar la función
        success, tables, message = get_tables()
        
        # Verificar resultados
        assert success is False
        assert tables is None
        assert "No se pudo establecer" in message
