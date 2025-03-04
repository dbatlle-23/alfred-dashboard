import logging
import os
import sys
from datetime import datetime
import structlog
from pythonjsonlogger import jsonlogger

# Configuración de directorios
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Nombre del archivo de log basado en la fecha
LOG_FILE = os.path.join(LOG_DIR, f"alfred_dashboard_{datetime.now().strftime('%Y%m%d')}.log")

# Configuración de niveles de log
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
CONSOLE_LOG_LEVEL = os.getenv("CONSOLE_LOG_LEVEL", "INFO").upper()
FILE_LOG_LEVEL = os.getenv("FILE_LOG_LEVEL", "DEBUG").upper()

# Configuración de formato para logs JSON
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.now().isoformat()
        log_record['level'] = record.levelname
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

def configure_logging():
    """Configura el sistema de logging con salida a consola y archivo"""
    # Configuración de structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configuración de handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Limpiar handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, CONSOLE_LOG_LEVEL))
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Handler para archivo
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(getattr(logging, FILE_LOG_LEVEL))
    file_formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(module)s %(function)s %(line)s %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Agregar handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Log inicial
    logging.info(f"Logging configurado. Archivo de log: {LOG_FILE}")
    
    return root_logger

def get_logger(name):
    """Obtiene un logger configurado para el módulo especificado"""
    return structlog.get_logger(name)
