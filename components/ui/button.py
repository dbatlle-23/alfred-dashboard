from dash import html
import dash_bootstrap_components as dbc

def create_button(children, id=None, color="primary", outline=False, size=None, 
                  className="", style=None, disabled=False, n_clicks=0, 
                  href=None, external_link=False, target=None, **kwargs):
    """
    Crea un botón personalizado.
    
    Args:
        children: Contenido del botón
        id: ID del botón
        color: Color del botón (primary, secondary, success, warning, danger, info, light, dark)
        outline: Si el botón debe tener solo contorno
        size: Tamaño del botón (sm, md, lg)
        className: Clases CSS adicionales
        style: Estilos CSS adicionales
        disabled: Si el botón está deshabilitado
        n_clicks: Número inicial de clics
        href: URL para convertir el botón en un enlace
        external_link: Si el enlace es externo
        target: Atributo target para enlaces
        **kwargs: Propiedades adicionales para el botón
        
    Returns:
        Un componente de botón de Dash Bootstrap
    """
    button_props = {
        "children": children,
        "color": color,
        "outline": outline,
        "size": size,
        "className": className,
        "style": style or {},
        "disabled": disabled,
        "n_clicks": n_clicks,
        **kwargs
    }
    
    if id is not None:
        button_props["id"] = id
    
    # Si hay un href, crear un botón de enlace
    if href is not None:
        button_props["href"] = href
        button_props["external_link"] = external_link
        
        if target is not None:
            button_props["target"] = target
            
        return dbc.Button(**button_props)
    
    # Si no hay href, crear un botón normal
    return dbc.Button(**button_props)

def create_icon_button(icon, tooltip=None, id=None, color="primary", outline=False, 
                       size="sm", className="", style=None, disabled=False, n_clicks=0, 
                       href=None, external_link=False, target=None, **kwargs):
    """
    Crea un botón con icono.
    
    Args:
        icon: Icono a mostrar (clase de Font Awesome, ej: "fas fa-plus")
        tooltip: Texto del tooltip
        id: ID del botón
        color: Color del botón
        outline: Si el botón debe tener solo contorno
        size: Tamaño del botón
        className: Clases CSS adicionales
        style: Estilos CSS adicionales
        disabled: Si el botón está deshabilitado
        n_clicks: Número inicial de clics
        href: URL para convertir el botón en un enlace
        external_link: Si el enlace es externo
        target: Atributo target para enlaces
        **kwargs: Propiedades adicionales para el botón
        
    Returns:
        Un componente de botón con icono
    """
    icon_element = html.I(className=icon)
    
    button = create_button(
        icon_element,
        id=id,
        color=color,
        outline=outline,
        size=size,
        className=f"btn-icon {className}",
        style=style,
        disabled=disabled,
        n_clicks=n_clicks,
        href=href,
        external_link=external_link,
        target=target,
        **kwargs
    )
    
    if tooltip:
        return dbc.Tooltip(tooltip, target=id, placement="top")
    
    return button 