#!/bin/bash

# Backup the original file
cp layouts/smart_locks.py layouts/smart_locks.py.try_except_fix

# Check the current content around the problem area
echo "Current content around line 2127:"
sed -n '2125,2155p' layouts/smart_locks.py

# Create a temporary file with the corrected section
cat > temp_fix.txt << 'EOL'
        # Contador para estadísticas
        nfc_sensors_found = 0
        total_nfc_codes = 0
        errors = []
        results = []
        
        # PASO 1: Obtener información NFC desde la API para todos los assets
        try:
            # Limitar el número de trabajadores a 5 para no sobrecargar la API
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Enviar todas las solicitudes en paralelo
                futures = [
                    executor.submit(fetch_nfc_passwords_for_asset, asset_id, token)
                    for asset_id in asset_ids
                ]
                
                # Esperar a que todas las solicitudes terminen
                for future in concurrent.futures.as_completed(futures):
                    try:
                        asset_id, data = future.result()
                        if data:
                            results.append((asset_id, data))
                        else:
                            logger.warning(f"No se obtuvieron datos NFC para asset_id: {asset_id}")
                    except Exception as e:
                        errors.append(str(e))
                        logger.error(f"Error al obtener datos NFC: {str(e)}")
        except Exception as e:
            errors.append(str(e))
            logger.error(f"Error al crear ThreadPoolExecutor: {str(e)}")
EOL

# Replace the problematic section with the fixed content
# This assumes the section starts at line 2125 and ends at line 2153
sed -i '' '2125,2153c\
        # Contador para estadísticas\
        nfc_sensors_found = 0\
        total_nfc_codes = 0\
        errors = []\
        results = []\
        \
        # PASO 1: Obtener información NFC desde la API para todos los assets\
        try:\
            # Limitar el número de trabajadores a 5 para no sobrecargar la API\
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:\
                # Enviar todas las solicitudes en paralelo\
                futures = [\
                    executor.submit(fetch_nfc_passwords_for_asset, asset_id, token)\
                    for asset_id in asset_ids\
                ]\
                \
                # Esperar a que todas las solicitudes terminen\
                for future in concurrent.futures.as_completed(futures):\
                    try:\
                        asset_id, data = future.result()\
                        if data:\
                            results.append((asset_id, data))\
                        else:\
                            logger.warning(f"No se obtuvieron datos NFC para asset_id: {asset_id}")\
                    except Exception as e:\
                        errors.append(str(e))\
                        logger.error(f"Error al obtener datos NFC: {str(e)}")\
        except Exception as e:\
            errors.append(str(e))\
            logger.error(f"Error al crear ThreadPoolExecutor: {str(e)}")' layouts/smart_locks.py

echo "Fixed try-except block at lines 2127-2153"

# Show the fixed section
echo "Fixed section:"
sed -n '2125,2155p' layouts/smart_locks.py

# Clean up
rm temp_fix.txt 