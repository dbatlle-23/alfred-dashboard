import re

# Corregir indentación en el archivo smart_locks.py
with open('layouts/smart_locks.py', 'r') as file:
    lines = file.readlines()

# Corregir la línea 2862 (crear mensaje de éxito)
if len(lines) > 2862:
    lines[2861] = "        # Actualizar el mensaje de éxito para mostrar información específica\n"
    lines[2862] = "        success_message = html.Div([\n"
    lines[2863] = "            html.I(className=\"fas fa-check-circle me-2\"),\n"
    lines[2864] = "            f\"Se cargaron códigos NFC para {len(nfc_values_by_asset)} assets. Valores para D245FKTBVEX60: {len(known_values)} sensores\"\n"
    lines[2865] = "        ], className=\"alert alert-success\")\n"

# Corregir la línea 2587 y cercanas (problema de indentación)
if len(lines) > 2587:
    lines[2586] = "                elif isinstance(data, dict):\n"
    lines[2587] = "                    # CASO 3: Extraer valores de formato alternativo (sin procesar por fetch_nfc_passwords_for_asset)\n"
    
# Guardar los cambios
with open('layouts/smart_locks.py', 'w') as file:
    file.writelines(lines)

print("Se ha corregido la indentación en el archivo smart_locks.py")

# Importar la función para verificar
try:
    from utils.api import fetch_nfc_passwords_for_asset
    print("Función fetch_nfc_passwords_for_asset importada correctamente")
except ImportError as e:
    print(f"Error al importar: {e}") 