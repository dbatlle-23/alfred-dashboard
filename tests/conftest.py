import os
import pytest
import tempfile
from unittest.mock import MagicMock

import dash
from dash import html
import dash_bootstrap_components as dbc

@pytest.fixture
def app():
    """Fixture que proporciona una instancia de la aplicación Dash para pruebas."""
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )
    app.layout = html.Div([
        html.Div(id="page-content"),
        html.Div(id="global-error-container")
    ])
    return app

@pytest.fixture
def temp_config_dir():
    """Fixture que proporciona un directorio temporal para archivos de configuración."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_dir = os.getcwd()
        try:
            # Crear subdirectorio config
            config_dir = os.path.join(temp_dir, "config")
            os.makedirs(config_dir, exist_ok=True)
            
            # Cambiar al directorio temporal
            os.chdir(temp_dir)
            yield temp_dir
        finally:
            # Volver al directorio original
            os.chdir(original_dir)

@pytest.fixture
def mock_db_config():
    """Fixture que proporciona una configuración de base de datos simulada."""
    return {
        'host': 'localhost',
        'port': '5432',
        'dbname': 'testdb',
        'user': 'testuser',
        'password': 'testpass'
    }

@pytest.fixture
def mock_db_engine():
    """Fixture que proporciona un motor de base de datos simulado."""
    engine = MagicMock()
    connection = MagicMock()
    engine.connect.return_value = connection
    return engine 