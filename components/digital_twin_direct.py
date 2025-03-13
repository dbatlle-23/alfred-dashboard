import dash_html_components as html
from dash import html

def create_digital_twin_direct(height=500):
    """
    Crea un componente que muestra el Digital Twin creado con Three.js
    mediante incrustación directa del script en la página.
    
    Args:
        height (int): Altura del contenedor en píxeles
        
    Returns:
        dash_html_components.Div: Un contenedor para el Digital Twin
    """
    return html.Div([
        html.H2("Digital Twin (Método Directo)", className="mt-4"),
        html.P("Este Digital Twin está implementado usando incrustación directa de Three.js"),
        
        # Importar Three.js desde CDN
        html.Script(src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"),
        
        # Contenedor para Three.js
        html.Div(
            id="threejs-container",
            style={
                'height': f"{height}px",
                'width': '100%',
                'backgroundColor': '#f0f0f0',
                'borderRadius': '5px',
                'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
                'overflow': 'hidden'
            }
        )
    ], style={
        'padding': '10px',
        'marginBottom': '20px'
    }) 