#!/usr/bin/env python3

# Importar la función específica que está causando problemas
from utils.api import fetch_nfc_passwords_for_asset

# Crear un alias/wrapper para la función si hubiera problemas con el nombre
def fetch_for_asset(asset_id, token):
    """Wrapper simple para la función fetch_nfc_passwords_for_asset"""
    return fetch_nfc_passwords_for_asset(asset_id, token)
    
# Crear el archivo con la función de wrapper
with open('utils/nfc_helper.py', 'w') as f:
    f.write("""#!/usr/bin/env python3

from utils.api import fetch_nfc_passwords_for_asset

def fetch_for_asset(asset_id, token):
    \"\"\"Wrapper simple para la función fetch_nfc_passwords_for_asset\"\"\"
    return fetch_nfc_passwords_for_asset(asset_id, token)
""")

print("Función fetch_nfc_passwords_for_asset importada correctamente.")
print("Se ha creado el archivo utils/nfc_helper.py con una función wrapper más simple.") 