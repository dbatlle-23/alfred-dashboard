def corregir_indentacion():
    # Leer el archivo
    with open('layouts/smart_locks.py', 'r') as file:
        lines = file.readlines()
    
    # Líneas problemáticas
    problematic_start = 2570
    problematic_end = 2600
    
    # Niveles de indentación correctos para cada línea
    indentation_levels = {
        2585: 4,  # expect/try/finally
        2586: 4,  # elif isinstance(data, dict):
        2587: 5,  # comentario
        2588: 5,  # for sensor_id
        2589: 6,  # try
        2590: 7,  # if isinstance
        2591: 8,  # Format
        2592: 8,  # for device_id
        2593: 9,  # if device_id
        2594: 10, # correccion
        2595: 10, # verificar
        2596: 10, # continuar
        2597: 10, # formatear
        2598: 10, # log
    }
    
    # Aplicar correcciones de indentación
    for line_number in range(problematic_start, problematic_end + 1):
        if line_number in indentation_levels and line_number < len(lines):
            # Eliminar todas las indentaciones actuales
            content = lines[line_number].lstrip()
            # Aplicar nueva indentación
            lines[line_number] = ' ' * indentation_levels[line_number] * 4 + content
    
    # También corregir el mensaje de éxito en la línea 2862
    if 2862 < len(lines):
        lines[2861] = "        # Actualizar el mensaje de éxito para mostrar información específica\n"
        lines[2862] = "        success_message = html.Div([\n"
        lines[2863] = "            html.I(className=\"fas fa-check-circle me-2\"),\n"
        lines[2864] = "            f\"Se cargaron códigos NFC para {len(nfc_values_by_asset)} assets. Valores para D245FKTBVEX60: {len(known_values)} sensores\"\n"
        lines[2865] = "        ], className=\"alert alert-success\")\n"
    
    # Guardar los cambios
    with open('layouts/smart_locks.py', 'w') as file:
        file.writelines(lines)
    
    print("Correcciones de indentación aplicadas")

if __name__ == "__main__":
    corregir_indentacion() 