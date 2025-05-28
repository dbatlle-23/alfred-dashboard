            errors = []
            try:
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
