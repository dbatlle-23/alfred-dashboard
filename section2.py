                            }
                            logger.info(f"Añadida nueva columna para sensor {sensor_id}: 🔑 {sensor_name} ({sensor_pw.get('sensor_type', 'NFC_CODE')})")
                            
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
        
                            # Crear nueva columna en la definición de columnas
                            column_name = f"🔑 {sensor_name} ({sensor_pw.get('sensor_type', 'NFC_CODE')})"
                            updated_columns.append({
                                "name": column_name,
                                "id": cell_id
