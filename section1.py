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
