from dash import Input, Output, State
import dash_bootstrap_components as dbc
from dash import html
import traceback
import logging

# Configurar logging
logger = logging.getLogger(__name__)

def register_config_callbacks(app):
    """Registra todos los callbacks relacionados con la configuración de la base de datos"""
    
    # Callback para cargar la configuración existente
    @app.callback(
        [Output("db-host-input", "value"),
         Output("db-port-input", "value"),
         Output("db-name-input", "value"),
         Output("db-user-input", "value"),
         Output("db-password-input", "value"),
         Output("db-sslmode-dropdown", "value")],
        Input("url", "pathname")
    )
    def load_db_config(pathname):
        if pathname != "/db-config":
            return "", "", "", "", "", "prefer"
        
        try:
            # Importar aquí para evitar problemas de importación circular
            from utils.db_utils import load_db_config
            
            logger.info("Cargando configuración de la base de datos")
            
            # Cargar la configuración
            config = load_db_config()
            
            if not config:
                logger.warning("No se encontró configuración de base de datos")
                return "localhost", "5432", "", "", "", "prefer"
            
            # Devolver los valores de configuración
            return (
                config.get("host", "localhost"),
                config.get("port", "5432"),
                config.get("dbname", ""),
                config.get("user", ""),
                config.get("password", ""),
                config.get("sslmode", "prefer")
            )
        except Exception as e:
            logger.error(f"Error al cargar la configuración: {str(e)}")
            traceback.print_exc()
            return "localhost", "5432", "", "", "", "prefer"
    
    # Callback para guardar la configuración
    @app.callback(
        [Output("db-config-status", "children"),
         Output("db-config-status", "color"),
         Output("db-config-status", "is_open")],
        Input("save-db-config-btn", "n_clicks"),
        [State("db-host-input", "value"),
         State("db-port-input", "value"),
         State("db-name-input", "value"),
         State("db-user-input", "value"),
         State("db-password-input", "value"),
         State("db-sslmode-dropdown", "value")],
        prevent_initial_call=True
    )
    def save_db_config(n_clicks, host, port, dbname, user, password, sslmode):
        if not n_clicks:
            return "", "", False
        
        try:
            # Importar aquí para evitar problemas de importación circular
            from utils.db_utils import save_db_config, test_connection
            
            logger.info("Guardando configuración de la base de datos")
            
            # Validar los campos obligatorios
            if not host or not port or not dbname or not user:
                logger.warning("Faltan campos obligatorios en la configuración")
                return "Por favor, complete todos los campos obligatorios.", "warning", True
            
            # Crear el diccionario de configuración
            config = {
                "host": host,
                "port": port,
                "dbname": dbname,
                "user": user,
                "password": password,
                "sslmode": sslmode
            }
            
            # Probar la conexión con la nueva configuración
            success, message, _ = test_connection(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password
            )
            
            if not success:
                logger.warning(f"Error al probar la conexión: {message}")
                return f"Error al probar la conexión: {message}", "danger", True
            
            # Guardar la configuración
            if save_db_config(config):
                logger.info("Configuración guardada correctamente")
                return "Configuración guardada correctamente.", "success", True
            else:
                logger.error("Error al guardar la configuración")
                return "Error al guardar la configuración.", "danger", True
        except Exception as e:
            logger.error(f"Error al guardar la configuración: {str(e)}")
            traceback.print_exc()
            return f"Error al guardar la configuración: {str(e)}", "danger", True
