from dash import html, dcc
import dash_bootstrap_components as dbc
import uuid

def create_input(id=None, type="text", placeholder=None, value=None, 
                 label=None, help_text=None, invalid_feedback=None, valid_feedback=None,
                 size=None, className="", style=None, disabled=False, readonly=False,
                 required=False, debounce=False, pattern=None, min=None, max=None, 
                 minLength=None, maxLength=None, step=None, **kwargs):
    """
    Crea un componente de entrada personalizado.
    
    Args:
        id: ID del input
        type: Tipo de input (text, password, email, number, etc.)
        placeholder: Texto de placeholder
        value: Valor inicial
        label: Etiqueta para el input
        help_text: Texto de ayuda
        invalid_feedback: Mensaje de error para validación
        valid_feedback: Mensaje de éxito para validación
        size: Tamaño del input (sm, lg)
        className: Clases CSS adicionales
        style: Estilos CSS adicionales
        disabled: Si el input está deshabilitado
        readonly: Si el input es de solo lectura
        required: Si el input es requerido
        debounce: Si se debe aplicar debounce a los cambios
        pattern: Patrón de validación (para type="text")
        min: Valor mínimo (para type="number")
        max: Valor máximo (para type="number")
        minLength: Longitud mínima (para type="text")
        maxLength: Longitud máxima (para type="text")
        step: Paso (para type="number")
        **kwargs: Propiedades adicionales para el input
        
    Returns:
        Un componente de entrada de Dash Bootstrap
    """
    # Generar un ID único si no se proporciona uno
    if id is None:
        id = f"input-{str(uuid.uuid4())}"
    
    input_props = {
        "type": type,
        "placeholder": placeholder,
        "value": value,
        "size": size,
        "className": className,
        "style": style or {},
        "disabled": disabled,
        "readonly": readonly,
        "required": required,
        "debounce": debounce,
        "id": id,  # Siempre incluir el ID
        **kwargs
    }
    
    if pattern is not None and type == "text":
        input_props["pattern"] = pattern
    
    if type == "number":
        if min is not None:
            input_props["min"] = min
        if max is not None:
            input_props["max"] = max
        if step is not None:
            input_props["step"] = step
    
    if type in ["text", "password", "email", "search", "tel", "url"]:
        if minLength is not None:
            input_props["minLength"] = minLength
        if maxLength is not None:
            input_props["maxLength"] = maxLength
    
    # Crear el input
    input_element = dbc.Input(**input_props)
    
    # Si no hay label, help_text, invalid_feedback o valid_feedback, devolver solo el input
    if not any([label, help_text, invalid_feedback, valid_feedback]):
        return input_element
    
    # Crear el contenedor con los elementos adicionales (reemplazando FormGroup)
    form_group_children = []
    
    if label:
        form_group_children.append(dbc.Label(label, html_for=id))
    
    form_group_children.append(input_element)
    
    if help_text:
        form_group_children.append(dbc.FormText(help_text))
    
    if invalid_feedback:
        form_group_children.append(dbc.FormFeedback(invalid_feedback, type="invalid"))
    
    if valid_feedback:
        form_group_children.append(dbc.FormFeedback(valid_feedback, type="valid"))
    
    # Usar dbc.Row y dbc.Col en lugar de FormGroup
    return html.Div(form_group_children, className="mb-3")

def create_checkbox(id=None, label=None, value=False, className="", style=None, 
                    disabled=False, **kwargs):
    """
    Crea un componente de checkbox personalizado.
    
    Args:
        id: ID del checkbox
        label: Etiqueta para el checkbox
        value: Valor inicial (True/False)
        className: Clases CSS adicionales
        style: Estilos CSS adicionales
        disabled: Si el checkbox está deshabilitado
        **kwargs: Propiedades adicionales para el checkbox
        
    Returns:
        Un componente de checkbox de Dash Bootstrap
    """
    # Generar un ID único si no se proporciona uno
    if id is None:
        id = f"checkbox-{str(uuid.uuid4())}"
    
    checkbox_props = {
        "value": value,
        "className": className,
        "style": style or {},
        "disabled": disabled,
        "id": id,  # Siempre incluir el ID
        **kwargs
    }
    
    checkbox = dbc.Checkbox(**checkbox_props)
    
    if label:
        # Crear un div con el checkbox y la etiqueta
        return html.Div([
            dbc.Checkbox(
                id=id,
                value=value,
                disabled=disabled,
                className=className,
                **kwargs
            ),
            dbc.Label(
                label,
                html_for=id,
                className="form-check-label ms-2"
            )
        ], className="form-check d-flex align-items-center")
    
    return checkbox 