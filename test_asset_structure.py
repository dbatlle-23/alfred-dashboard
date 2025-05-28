import logging
import json
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulate what the API response might look like
logger.info("SIMULATED API RESPONSE TESTING")
logger.info("==============================")

# Create a simulated API response with different key structures
simulated_assets = [
    {
        "id": "asset1",
        "name": "Asset 1",
        "type": "building"
    },
    {
        "asset_id": "asset2",
        "nombre": "Asset 2",
        "type": "sensor"
    },
    {
        "assetId": "asset3",
        "asset_name": "Asset 3",
        "type": "device"
    },
    {
        "id_activo": "asset4",
        "nombre_activo": "Asset 4",
        "type": "equipment"
    },
    {
        # Missing id and name keys
        "type": "unknown"
    }
]

# Simulate the load_assets function logic
def test_load_assets(assets):
    asset_options = []
    
    for asset in assets:
        if not isinstance(asset, dict):
            continue
            
        # Try to get the name and ID with different possible keys
        nombre = None
        id_asset = None
        
        for key in ['nombre', 'name', 'asset_name', 'nombre_activo']:
            if key in asset and asset[key]:
                nombre = asset[key]
                break
        
        for key in ['id', 'asset_id', 'id_activo', 'assetId']:
            if key in asset and asset[key]:
                id_asset = asset[key]
                break
        
        if nombre and id_asset:
            asset_options.append({"label": nombre, "value": str(id_asset)})
        else:
            logger.warning(f"Asset skipped: missing name or ID keys. Available keys: {list(asset.keys())}")
    
    return asset_options

# Test the function with our simulated assets
logger.info("Testing load_assets function with simulated assets...")
asset_options = test_load_assets(simulated_assets)

logger.info(f"Successfully processed {len(asset_options)}/{len(simulated_assets)} assets")
logger.info("Resulting asset options:")
for opt in asset_options:
    logger.info(f"  - {opt['label']} (ID: {opt['value']})")

# Check for issues
if len(asset_options) < len(simulated_assets):
    logger.warning("Some assets were not processed successfully.")
    logger.info("This could be due to missing name or ID fields in the API response.")

logger.info("\nRECOMMENDATIONS:")
logger.info("1. Ensure the API returns a 'name' or 'nombre' field for each asset.")
logger.info("2. Ensure the API returns an 'id' field for each asset.")
logger.info("3. If the API can't be modified, consider customizing the key lookup in the load_assets function.")

logger.info("\nINSTRUCTIONS FOR MANUAL TESTING:")
logger.info("1. Run the web app with 'python app.py'")
logger.info("2. Login to the application")
logger.info("3. Open the browser's developer tools (F12)")
logger.info("4. Go to the Console tab and run the following JavaScript code:")
logger.info("\nfetch('/projects/{project_id}/assets', { headers: { 'Authorization': `Bearer ${yourToken}` }}).then(r => r.json()).then(data => console.log(data))")
logger.info("\nReplace {project_id} with your project ID and ${yourToken} with your API token") 