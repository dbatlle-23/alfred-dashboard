from dash import html, dcc, callback_context
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, MATCH
import uuid

class Dialog:
    """
    Componente de diálogo/modal para Dash.
    
    Este componente crea un modal que puede ser mostrado u ocultado mediante callbacks.
    Es equivalente al componente Dialog de Radix UI en React.
    """
    
    def __init__(self, app=None):
        """
        Inicializa el componente Dialog.
        
        Args:
            app: La instancia de la aplicación Dash (opcional)
        """
        self.app = app
        if app is not None:
            self.init_callbacks(app)
    
    def init_callbacks(self, app):
        """
        Inicializa los callbacks para el componente.
        
        Args:
            app: La instancia de la aplicación Dash
        """
        @app.callback(
            Output({"type": "dialog-modal", "id": MATCH}, "is_open"),
            Input({"type": "dialog-trigger", "id": MATCH}, "n_clicks"),
            Input({"type": "dialog-close", "id": MATCH}, "n_clicks"),
            State({"type": "dialog-modal", "id": MATCH}, "is_open"),
            prevent_initial_call=True
        )
        def toggle_modal(trigger_clicks, close_clicks, is_open):
            """Alterna la visibilidad del modal"""
            if trigger_clicks or close_clicks:
                return not is_open
            return is_open
    
    def create(self, dialog_id=None, trigger=None, title=None, description=None, content=None, 
               size="md", centered=True, backdrop="static", scrollable=True, close_button=True,
               fullscreen=False, fade=True):
        """
        Crea un componente de diálogo/modal.
        
        Args:
            dialog_id: ID único para el diálogo (generado automáticamente si no se proporciona)
            trigger: Componente que activará el diálogo
            title: Título del diálogo
            description: Descripción del diálogo
            content: Contenido principal del diálogo
            size: Tamaño del diálogo ("sm", "md", "lg", "xl")
            centered: Si el diálogo debe estar centrado verticalmente
            backdrop: Comportamiento del fondo ("static" o True)
            scrollable: Si el contenido del diálogo debe ser desplazable
            close_button: Si se debe mostrar el botón de cierre
            fullscreen: Si el diálogo debe ocupar toda la pantalla
            fade: Si el diálogo debe tener efecto de desvanecimiento
            
        Returns:
            Un componente Dash que contiene el trigger y el modal
        """
        if dialog_id is None:
            dialog_id = str(uuid.uuid4())
        
        # Crear el modal
        modal = dbc.Modal(
            [
                dbc.ModalHeader(
                    [
                        html.Div([
                            html.H5(title, className="modal-title") if title else None,
                            html.P(description, className="text-muted small") if description else None,
                        ], className="d-flex flex-column"),
                    ],
                    close_button=close_button,
                    id={"type": "dialog-close", "id": dialog_id}
                ) if title or description or close_button else None,
                dbc.ModalBody(content),
            ],
            id={"type": "dialog-modal", "id": dialog_id},
            centered=centered,
            size=size,
            backdrop=backdrop,
            scrollable=scrollable,
            fullscreen=fullscreen,
            fade=fade,
            is_open=False,
            className="dialog-content"
        )
        
        # Si no hay trigger, solo devolver el modal
        if trigger is None:
            return modal
        
        # Envolver el trigger con un div y añadir el ID
        trigger_wrapper = html.Div(
            trigger,
            id={"type": "dialog-trigger", "id": dialog_id}
        )
        
        # Devolver el trigger y el modal
        return html.Div([trigger_wrapper, modal])
    
    def create_dialog_header(self, children, className=""):
        """Crea un encabezado de diálogo"""
        return html.Div(children, className=f"dialog-header {className}")
    
    def create_dialog_footer(self, children, className=""):
        """Crea un pie de diálogo"""
        return html.Div(children, className=f"dialog-footer d-flex justify-content-end mt-3 {className}")
    
    def create_dialog_title(self, children, className=""):
        """Crea un título de diálogo"""
        return html.H5(children, className=f"dialog-title {className}")
    
    def create_dialog_description(self, children, className=""):
        """Crea una descripción de diálogo"""
        return html.P(children, className=f"dialog-description text-muted {className}")

# Crear una instancia del componente Dialog
dialog = Dialog()

# Exportar funciones para crear componentes de diálogo
create_dialog = dialog.create
create_dialog_header = dialog.create_dialog_header
create_dialog_footer = dialog.create_dialog_footer
create_dialog_title = dialog.create_dialog_title
create_dialog_description = dialog.create_dialog_description 