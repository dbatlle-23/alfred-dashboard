import json
import os
from datetime import datetime
import pandas as pd
from config.metrics_config import REGENERATION_CONFIG
from utils.api import get_daily_readings_for_tag
from utils.logging import get_logger

logger = get_logger(__name__)

def is_regeneration_in_progress():
    """Check if a regeneration process is currently running."""
    status_file = os.path.join("data", "regeneration_status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r') as f:
                status = json.load(f)
                return status.get('status') == 'in_progress'
        except:
            return False
    return False

def get_regeneration_status():
    """Get the current status of regeneration process."""
    status_file = os.path.join("data", "regeneration_status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def update_regeneration_status(status_data):
    """Update the regeneration status file."""
    status_file = os.path.join("data", "regeneration_status.json")
    os.makedirs(os.path.dirname(status_file), exist_ok=True)
    
    try:
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
    except Exception as e:
        logger.error(f"Error updating regeneration status: {str(e)}")

def regenerate_readings(asset_id, consumption_type, project_id, token_data, month_year):
    """
    Regenerate readings for a specific asset and consumption type.
    
    Args:
        asset_id (str): Asset ID
        consumption_type (str): Consumption type
        project_id (str): Project ID
        token_data (dict): Token data for authentication
        month_year (str): Month and year in format YYYY-MM
        
    Returns:
        dict: Result of regeneration process
    """
    try:
        logger.info(f"Starting regeneration for asset {asset_id}, type {consumption_type}")
        
        # Get token from token data
        token = token_data.get('token') if token_data else None
        if not token:
            return {
                "success": False,
                "message": "No se proporcionó token de autenticación"
            }
        
        # Ensure project folder exists
        project_folder = os.path.join("data", "projects", project_id)
        os.makedirs(project_folder, exist_ok=True)
        
        # Get readings from API
        df = get_daily_readings_for_tag(
            asset_id=asset_id,
            tag=consumption_type,
            project_folder=project_folder,
            token=token
        )
        
        if df is None or df.empty:
            return {
                "success": False,
                "message": "No se pudieron obtener lecturas del API"
            }
        
        return {
            "success": True,
            "message": "Lecturas regeneradas correctamente",
            "rows": len(df)
        }
        
    except Exception as e:
        logger.error(f"Error regenerating readings: {str(e)}")
        return {
            "success": False,
            "message": f"Error al regenerar lecturas: {str(e)}"
        }

def regenerate_readings_in_bulk(error_list, project_id, token_data, 
                              only_errors=True, continue_on_error=True):
    """
    Regenerate readings in bulk for multiple assets and consumption types.
    
    Args:
        error_list (list): List of items to regenerate
        project_id (str): Project ID
        token_data (dict): Token data for authentication
        only_errors (bool): Whether to regenerate only error readings
        continue_on_error (bool): Whether to continue on error
        
    Returns:
        dict: Result of bulk regeneration process
    """
    if is_regeneration_in_progress():
        return {
            "success": False,
            "message": "Ya hay un proceso de regeneración en curso"
        }
    
    # Initialize status
    status = {
        "status": "in_progress",
        "total": len(error_list),
        "processed": 0,
        "success": 0,
        "failed": 0,
        "errors": [],
        "start_time": datetime.now().isoformat()
    }
    update_regeneration_status(status)
    
    try:
        for item in error_list:
            try:
                result = regenerate_readings(
                    asset_id=item['asset_id'],
                    consumption_type=item['consumption_type'],
                    project_id=project_id,
                    token_data=token_data,
                    month_year=item['period']
                )
                
                status['processed'] += 1
                
                if result['success']:
                    status['success'] += 1
                else:
                    status['failed'] += 1
                    status['errors'].append({
                        'asset_id': item['asset_id'],
                        'consumption_type': item['consumption_type'],
                        'period': item['period'],
                        'error': result['message']
                    })
                    
                    if not continue_on_error:
                        break
                
                # Update status file
                update_regeneration_status(status)
                
            except Exception as e:
                logger.error(f"Error processing item: {str(e)}")
                status['failed'] += 1
                status['errors'].append({
                    'asset_id': item['asset_id'],
                    'consumption_type': item['consumption_type'],
                    'period': item['period'],
                    'error': str(e)
                })
                
                if not continue_on_error:
                    break
                
                # Update status file
                update_regeneration_status(status)
        
        # Update final status
        status['status'] = 'completed'
        status['end_time'] = datetime.now().isoformat()
        update_regeneration_status(status)
        
        return {
            "success": True,
            "message": "Proceso de regeneración completado",
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Error in bulk regeneration: {str(e)}")
        status['status'] = 'failed'
        status['end_time'] = datetime.now().isoformat()
        status['error'] = str(e)
        update_regeneration_status(status)
        
        return {
            "success": False,
            "message": f"Error en regeneración masiva: {str(e)}",
            "status": status
        }
