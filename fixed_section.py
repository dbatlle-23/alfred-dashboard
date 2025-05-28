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
                        logger.error(f"Error al obtener datos NFC: {str(e)}")
            except Exception as e:
                errors.append(str(e))
                logger.error(f"Error en la ejecución de solicitudes paralelas: {str(e)}")
                
            # Añadir columna a todas las filas
            for i, row in enumerate(updated_data):
                if i == row_index and password_value:
                    # Si es la fila actual y hay valor, usar el password obtenido
                    row[cell_id] = password_value
                    logger.info(f"Asignado valor '{password_value}' a nueva columna {cell_id} para dispositivo {device_id}")
                elif i == row_index:
                    # Si es la fila actual pero no hay valor
                    row[cell_id] = "No asignado"
                else:
                    # Para otras filas, marcar como N/A
                    row[cell_id] = "N/A" 