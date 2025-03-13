import dash_html_components as html
import dash_core_components as dcc
from dash import html

def create_digital_twin_iframe(height=600, width="100%"):
    """
    Crea un componente IFrame que muestra el Digital Twin creado con Three.js
    
    Args:
        height (int): Altura del IFrame en píxeles
        width (str): Ancho del IFrame, puede ser en píxeles o porcentaje
        
    Returns:
        dash_html_components.Div: Un contenedor con el IFrame del Digital Twin
    """
    return html.Div([
        html.H2("Digital Twin (Método IFrame)", className="mt-4"),
        html.P("Este Digital Twin está implementado usando un IFrame que carga un archivo HTML con Three.js"),
        html.Div([
            html.Iframe(
                src="/assets/digital_twin.html",
                style={
                    'height': f"{height}px",
                    'width': width,
                    'border': 'none',
                    'borderRadius': '5px',
                    'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
                    'backgroundColor': '#f0f0f0'
                }
            )
        ], style={
            'padding': '10px',
            'marginBottom': '20px'
        })
    ]) 