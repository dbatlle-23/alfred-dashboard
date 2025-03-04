import os
import configparser
import logging
from sqlalchemy import create_engine, inspect, text
import pandas as pd

# Configurar logging
logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Obtiene una conexión a la base de datos utilizando la configuración guardada.
    
    Returns:
        engine: Objeto de conexión SQLAlchemy o None si hay un error
    """
    try:
        # Cargar la configuración
        config = load_db_config()
        if not config:
            logger.error("No se pudo cargar la configuración de la base de datos.")
            return None
        
        # Construir la URL de conexión
        db_url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['dbname']}"
        
        # Crear el motor de conexión
        engine = create_engine(db_url)
        
        return engine
    except Exception as e:
        logger.error(f"Error al obtener la conexión a la base de datos: {str(e)}")
        return None

def load_db_config():
    """
    Carga la configuración de la base de datos desde el archivo de configuración.
    
    Returns:
        dict: Diccionario con la configuración o None si hay un error
    """
    try:
        config_path = os.path.join("config", "database.ini")
        
        # Verificar si el archivo existe
        if not os.path.exists(config_path):
            logger.warning(f"El archivo de configuración {config_path} no existe.")
            return None
        
        # Crear el parser de configuración
        config_parser = configparser.ConfigParser()
        config_parser.read(config_path)
        
        # Verificar si existe la sección postgresql
        if "postgresql" not in config_parser:
            logger.warning("No se encontró la sección 'postgresql' en el archivo de configuración.")
            return None
        
        # Obtener los valores de configuración
        config = {
            "host": config_parser.get("postgresql", "host"),
            "port": config_parser.get("postgresql", "port"),
            "dbname": config_parser.get("postgresql", "dbname"),
            "user": config_parser.get("postgresql", "user"),
            "password": config_parser.get("postgresql", "password"),
            "sslmode": config_parser.get("postgresql", "sslmode", fallback="prefer")
        }
        
        return config
    except Exception as e:
        logger.error(f"Error cargando configuración de base de datos: {str(e)}")
        return None

def test_connection(host=None, port=None, dbname=None, user=None, password=None):
    """
    Prueba la conexión a la base de datos.
    
    Args:
        host: Host de la base de datos
        port: Puerto de la base de datos
        dbname: Nombre de la base de datos
        user: Usuario de la base de datos
        password: Contraseña de la base de datos
        
    Returns:
        tuple: (éxito, mensaje, engine)
    """
    try:
        if host and port and dbname and user and password:
            # Construir la URL de conexión
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
            
            # Crear el motor de conexión
            engine = create_engine(db_url)
        else:
            # Usar la configuración guardada
            engine = get_db_connection()
            
            if engine is None:
                return False, "No se pudo obtener la conexión a la base de datos.", None
        
        # Probar la conexión
        with engine.connect() as connection:
            # Ejecutar una consulta simple usando text() para crear un objeto SQL ejecutable
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        
        return True, "Conexión exitosa a la base de datos.", engine
    except Exception as e:
        logger.error(f"Error al probar la conexión a la base de datos: {str(e)}")
        return False, f"Error al probar la conexión: {str(e)}", None

def save_db_config(config):
    """
    Guarda la configuración de la base de datos en el archivo de configuración.
    
    Args:
        config (dict): Diccionario con la configuración
        
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    try:
        config_path = os.path.join("config", "database.ini")
        
        # Crear el parser de configuración
        config_parser = configparser.ConfigParser()
        
        # Verificar si el archivo existe
        if os.path.exists(config_path):
            config_parser.read(config_path)
        
        # Verificar si existe la sección postgresql
        if "postgresql" not in config_parser:
            config_parser.add_section("postgresql")
        
        # Establecer los valores de configuración
        config_parser.set("postgresql", "host", config.get("host", "localhost"))
        config_parser.set("postgresql", "port", config.get("port", "5432"))
        config_parser.set("postgresql", "dbname", config.get("dbname", "postgres"))
        config_parser.set("postgresql", "user", config.get("user", "postgres"))
        config_parser.set("postgresql", "password", config.get("password", ""))
        config_parser.set("postgresql", "sslmode", config.get("sslmode", "prefer"))
        
        # Guardar la configuración
        with open(config_path, "w") as f:
            config_parser.write(f)
            
        logger.info("Configuración de base de datos guardada correctamente.")
        return True
    except Exception as e:
        logger.error(f"Error guardando configuración de base de datos: {str(e)}")
        return False

def execute_query(query, params=None):
    """
    Ejecuta una consulta SQL y devuelve los resultados como un DataFrame.
    
    Args:
        query (str): Consulta SQL a ejecutar
        params (tuple, optional): Parámetros para la consulta como una tupla. Por defecto None.
        
    Returns:
        DataFrame: Resultados de la consulta o None si hay un error
    """
    try:
        # Obtener la conexión
        engine = get_db_connection()
        if engine is None:
            return None
        
        # Ejecutar la consulta
        if params:
            df = pd.read_sql_query(query, engine, params=params)
        else:
            df = pd.read_sql_query(query, engine)
        
        return df
    except Exception as e:
        logger.error(f"Error ejecutando consulta: {str(e)}")
        return None

def get_tables():
    """
    Obtiene la lista de tablas disponibles en la base de datos.
    
    Returns:
        list: Lista de nombres de tablas o None si hay un error
    """
    try:
        # Obtener la conexión
        engine = get_db_connection()
        if engine is None:
            return None
        
        # Obtener el inspector
        inspector = inspect(engine)
        
        # Obtener la lista de tablas
        tables = inspector.get_table_names()
        
        return tables
    except Exception as e:
        logger.error(f"Error obteniendo tablas: {str(e)}")
        return None

def get_table_columns(table_name):
    """
    Obtiene la lista de columnas de una tabla.
    
    Args:
        table_name (str): Nombre de la tabla
        
    Returns:
        list: Lista de diccionarios con información de las columnas o None si hay un error
    """
    try:
        # Obtener la conexión
        engine = get_db_connection()
        if engine is None:
            return None
        
        # Obtener el inspector
        inspector = inspect(engine)
        
        # Obtener la lista de columnas
        columns = inspector.get_columns(table_name)
        
        # Simplificar la información de las columnas
        simplified_columns = []
        for col in columns:
            simplified_columns.append({
                "column_name": col["name"],
                "data_type": str(col["type"])
            })
        
        return simplified_columns
    except Exception as e:
        logger.error(f"Error obteniendo columnas de {table_name}: {str(e)}")
        return None

def get_table_preview(table_name, limit=10):
    """
    Obtiene una vista previa de los datos de una tabla.
    
    Args:
        table_name (str): Nombre de la tabla
        limit (int): Número máximo de filas a devolver
        
    Returns:
        DataFrame: Vista previa de los datos o None si hay un error
    """
    try:
        # Usar %s como marcador de posición para el límite
        query = f'SELECT * FROM "{table_name}" LIMIT %s'
        
        # Obtener la conexión
        engine = get_db_connection()
        if engine is None:
            return None
            
        # Ejecutar la consulta con los parámetros
        df = pd.read_sql_query(query, engine, params=(limit,))
        
        return df
    except Exception as e:
        logger.error(f"Error obteniendo vista previa de {table_name}: {str(e)}")
        return None

# Funciones adicionales para compatibilidad con código existente
def get_available_tables():
    return get_tables()

def get_table_schema(table_name):
    return get_table_columns(table_name)

def get_table_data(table_name, limit=10):
    return get_table_preview(table_name, limit)

def get_reservations_from_db():
    # Implementar según sea necesario
    pass

def get_consumption_from_db():
    # Implementar según sea necesario
    pass

def get_common_areas_bookings(client_id=None, community_uuid=None):
    """
    Obtiene los datos de reservas de áreas comunes desde la tabla common_areas_booking_report.
    
    Esta tabla contiene registros de reservas (bookings) de espacios comunes, no los espacios en sí.
    Cada registro representa una reserva individual de un espacio común.
    
    Args:
        client_id (str, optional): ID del cliente para filtrar. Por defecto None.
        community_uuid (str, optional): UUID de la comunidad/proyecto para filtrar. Por defecto None.
        
    Returns:
        DataFrame: Resultados de la consulta o None si hay un error
    """
    try:
        # Construir la consulta base
        query = "SELECT * FROM common_areas_booking_report"
        
        # Añadir filtros si se proporcionan
        conditions = []
        params = []
        
        if client_id and client_id != "all":
            conditions.append("client_id = %s")
            params.append(client_id)
            
        if community_uuid and community_uuid != "all":
            conditions.append("community_uuid = %s")
            params.append(community_uuid)
            
        # Añadir condiciones a la consulta
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Obtener la conexión
        engine = get_db_connection()
        if engine is None:
            return None
            
        # Ejecutar la consulta con los parámetros
        if params:
            df = pd.read_sql_query(query, engine, params=tuple(params))
        else:
            df = pd.read_sql_query(query, engine)
        
        return df
    except Exception as e:
        logger.error(f"Error obteniendo datos de common_areas_booking_report: {str(e)}")
        return None

def get_unique_common_areas(client_id=None, community_uuid=None):
    """
    Obtiene los espacios comunes únicos basados en los registros de reservas.
    
    Args:
        client_id (str, optional): ID del cliente para filtrar. Por defecto None.
        community_uuid (str, optional): UUID de la comunidad/proyecto para filtrar. Por defecto None.
        
    Returns:
        DataFrame: DataFrame con los espacios comunes únicos o None si hay un error
    """
    try:
        # Construir la consulta base
        query = """
        SELECT DISTINCT common_area_id, common_area_name, community_uuid, community_id, client_id, client_name 
        FROM common_areas_booking_report
        """
        
        # Añadir filtros si se proporcionan
        conditions = []
        params = []
        
        if client_id and client_id != "all":
            conditions.append("client_id = %s")
            params.append(client_id)
            
        if community_uuid and community_uuid != "all":
            conditions.append("community_uuid = %s")
            params.append(community_uuid)
            
        # Añadir condiciones a la consulta
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Obtener la conexión
        engine = get_db_connection()
        if engine is None:
            return None
            
        # Ejecutar la consulta con los parámetros
        if params:
            df = pd.read_sql_query(query, engine, params=tuple(params))
        else:
            df = pd.read_sql_query(query, engine)
        
        return df
    except Exception as e:
        logger.error(f"Error obteniendo espacios comunes únicos: {str(e)}")
        return None
