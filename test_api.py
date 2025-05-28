import logging
import json
from utils.api import get_project_assets
from utils.auth import AuthService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create auth service instance
auth_service = AuthService()

# Get token
token = auth_service.get_token()
if not token:
    logger.error("No se pudo obtener un token JWT válido")
    exit(1)

# Project ID from the logs
project_id = "1dc5fd09-a8cf-4100-b561-c60ef8323c7a"

# Get assets
assets = get_project_assets(project_id=project_id, jwt_token=token)

# Print the structure of the first asset to check the keys
if assets and len(assets) > 0:
    logger.info(f"Se obtuvieron {len(assets)} assets")
    logger.info("Estructura del primer asset:")
    logger.info(json.dumps(assets[0], indent=2))
    
    # Check all keys in all assets
    all_keys = set()
    for asset in assets:
        all_keys.update(asset.keys())
    
    logger.info(f"Todas las claves presentes en los assets: {all_keys}")
else:
    logger.error("No se obtuvieron assets") 