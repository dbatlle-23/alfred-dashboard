from dash import Input, Output, State
import dash_bootstrap_components as dbc
from dash import html
import traceback
import logging

# Configurar logging
logger = logging.getLogger(__name__)

def register_callbacks(app):
    """Registra todos los callbacks relacionados con el explorador de base de datos"""
    
    # Callback para probar la conexión
    @app.callback(
        [Output("db-explorer-connection-status", "children"),
         Output("db-explorer-connection-status", "color"),
         Output("db-explorer-connection-status", "is_open")],
        Input("db-explorer-test-connection-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def test_db_connection(n_clicks):
        if not n_clicks:
            return "", "", False
        
        try:
            # Importar aquí para evitar problemas de importación circular
            from utils.db_utils import test_connection
            
            logger.info("Probando conexión a la base de datos")
            
            # Usar la función test_connection para probar la conexión
            success, message, _ = test_connection()
            
            color = "success" if success else "danger"
            return message, color, True
        except Exception as e:
            logger.error(f"Error al probar la conexión: {str(e)}")
            traceback.print_exc()
            return f"Error al probar la conexión: {str(e)}", "danger", True

    # Callback para cargar las tablas
    @app.callback(
        [Output("table-dropdown", "options"),
         Output("db-explorer-connection-status", "children", allow_duplicate=True),
         Output("db-explorer-connection-status", "color", allow_duplicate=True),
         Output("db-explorer-connection-status", "is_open", allow_duplicate=True)],
        Input("load-tables-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def load_tables(n_clicks):
        if not n_clicks:
            return [], "", "", False
        
        try:
            # Importar aquí para evitar problemas de importación circular
            from utils.db_utils import test_connection, get_tables
            
            logger.info("Cargando tablas de la base de datos")
            
            # Probar la conexión primero
            success, message, _ = test_connection()
            
            if not success:
                logger.warning(f"Error de conexión: {message}")
                return [], message, "danger", True
            
            # Obtener la lista de tablas
            tables = get_tables()
            
            if tables is None or len(tables) == 0:
                logger.warning("No se encontraron tablas en la base de datos")
                return [], "No se encontraron tablas en la base de datos.", "warning", True
            
            # Crear opciones para el dropdown
            options = [{"label": table, "value": table} for table in tables]
            
            return options, f"Se cargaron {len(tables)} tablas correctamente.", "success", True
        except Exception as e:
            logger.error(f"Error al cargar las tablas: {str(e)}")
            traceback.print_exc()
            return [], f"Error al cargar las tablas: {str(e)}", "danger", True

    # Callback para mostrar/ocultar la información de la tabla
    @app.callback(
        Output("table-info-container", "style"),
        Input("table-dropdown", "value")
    )
    def toggle_table_info(table_name):
        if table_name:
            return {"display": "block"}
        return {"display": "none"}

    # Callback para mostrar la estructura de la tabla
    @app.callback(
        Output("table-structure-container", "children"),
        [Input("table-dropdown", "value"),
         Input("table-tabs", "active_tab")]
    )
    def show_table_structure(table_name, active_tab):
        if not table_name or active_tab != "structure-tab":
            return []
        
        try:
            # Importar aquí para evitar problemas de importación circular
            from utils.db_utils import get_table_columns
            
            # Obtener la estructura de la tabla
            columns = get_table_columns(table_name)
            
            if columns is None or len(columns) == 0:
                return html.Div("No se pudo obtener la estructura de la tabla.", className="text-danger")
            
            # Crear tabla con la estructura
            table_header = [
                html.Thead(html.Tr([
                    html.Th("Columna"),
                    html.Th("Tipo de Dato")
                ]))
            ]
            
            table_body = [html.Tbody([
                html.Tr([
                    html.Td(col["column_name"]),
                    html.Td(col["data_type"])
                ]) for col in columns
            ])]
            
            return dbc.Table(table_header + table_body, bordered=True, hover=True, striped=True, responsive=True)
        except Exception as e:
            logger.error(f"Error al obtener la estructura de la tabla: {str(e)}")
            traceback.print_exc()
            return html.Div(f"Error al obtener la estructura de la tabla: {str(e)}", className="text-danger")

    # Callback para mostrar la vista previa de la tabla
    @app.callback(
        Output("table-preview-container", "children"),
        [Input("table-dropdown", "value"),
         Input("table-tabs", "active_tab")]
    )
    def show_table_preview(table_name, active_tab):
        if not table_name or active_tab != "preview-tab":
            return []
        
        try:
            # Importar aquí para evitar problemas de importación circular
            from utils.db_utils import get_table_preview
            
            # Obtener la vista previa de la tabla
            df = get_table_preview(table_name)
            
            if df is None or df.empty:
                return html.Div("No se encontraron datos en la tabla.", className="text-warning")
            
            # Crear tabla con la vista previa
            return dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True, responsive=True)
        except Exception as e:
            logger.error(f"Error al obtener la vista previa de la tabla: {str(e)}")
            traceback.print_exc()
            return html.Div(f"Error al obtener la vista previa de la tabla: {str(e)}", className="text-danger")
