from dash import html, dcc
import dash_bootstrap_components as dbc
from utils.logging import get_logger
from components.smart_locks.device_card import create_lock_device_card

logger = get_logger(__name__)

def create_locks_list(devices=None):
    """
    Crea una lista de dispositivos de cerradura inteligente
    
    Args:
        devices: Lista de dispositivos
        
    Returns:
        Componente con la lista de dispositivos
    """
    if not devices:
        return html.Div([
            html.I(className="fas fa-info-circle me-2"),
            "Seleccione un proyecto para ver las cerraduras disponibles"
        ], className="alert alert-info")
    
    # Si no hay cerraduras en el proyecto
    if not devices:
        return html.Div([
            html.I(className="fas fa-exclamation-circle me-2"),
            "No se encontraron cerraduras inteligentes en este proyecto"
        ], className="alert alert-warning")
    
    # Crear tarjetas para cada dispositivo
    lock_cards = []
    for device in devices:
        card = create_lock_device_card(device)
        if card:
            lock_cards.append(dbc.Col(card, md=4, sm=6, xs=12))
    
    # Contenedor de tarjetas en un grid
    return html.Div([
        # Contador de cerraduras
        html.Div([
            html.Strong(f"Cerraduras encontradas: {len(lock_cards)}"),
        ], className="mb-3"),
        
        # Grid de tarjetas
        dbc.Row(lock_cards, className="g-3")
    ]) 