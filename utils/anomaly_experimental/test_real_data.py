"""
Script para realizar pruebas con datos reales del sistema de detección de anomalías contextuales.
Este script está adaptado para trabajar con el formato específico de los archivos CSV disponibles.
"""

import pandas as pd
import numpy as np
import os
import sys
import logging
import glob
import re
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import json
import argparse
import traceback

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importar los módulos necesarios
from utils.anomaly_experimental.contextual_detection import ContextualAnomalyDetector
from utils.anomaly_experimental.threshold_calculator import ThresholdCalculator
from utils.anomaly_experimental.config_loader import load_anomaly_config, get_config_for_consumption_type

def extract_asset_id_from_filename(filename):
    """
    Extrae el ID del activo del nombre del archivo.
    
    Args:
        filename (str): Nombre del archivo
        
    Returns:
        str: ID del activo
    """
    match = re.search(r'daily_readings_([A-Z0-9]+)__', filename)
    if match:
        return match.group(1)
    return None

def extract_consumption_type_from_filename(filename):
    """
    Extrae el tipo de consumo del nombre del archivo.
    
    Args:
        filename (str): Nombre del archivo
        
    Returns:
        str: Tipo de consumo
    """
    match = re.search(r'__(.+)\.csv$', filename)
    if match:
        return match.group(1)
    return None

def load_csv_data(file_path):
    """
    Carga datos desde un archivo CSV y añade columnas de asset_id y consumption_type.
    
    Args:
        file_path (str): Ruta al archivo CSV
        
    Returns:
        pd.DataFrame: DataFrame con los datos cargados
    """
    try:
        # Cargar el CSV
        df = pd.read_csv(file_path)
        
        # Extraer asset_id y consumption_type del nombre del archivo
        asset_id = extract_asset_id_from_filename(os.path.basename(file_path))
        consumption_type = extract_consumption_type_from_filename(os.path.basename(file_path))
        
        # Añadir columnas
        df['asset_id'] = asset_id
        df['consumption_type'] = consumption_type
        
        # Renombrar columna 'value' a 'consumption'
        df = df.rename(columns={'value': 'consumption'})
        
        # Asegurar que la fecha es datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Ordenar por fecha
        df = df.sort_values('date')
        
        # Calcular cambios diarios
        df['daily_change'] = df['consumption'].diff()
        df['daily_change_pct'] = df['consumption'].pct_change() * 100
        
        return df
    
    except Exception as e:
        logger.error(f"Error cargando datos desde {file_path}: {str(e)}")
        return None

def analyze_asset(asset_id, consumption_type, use_config=True, output_dir=None):
    """
    Analyze an asset for anomalies.
    
    Args:
        asset_id (str): The asset ID to analyze
        consumption_type (str): The consumption type to analyze
        use_config (bool): Whether to use the configuration file
        output_dir (str): The output directory for results
    """
    logger.info(f"Analyzing asset {asset_id} for consumption type {consumption_type}")
    
    # Create output directory if it doesn't exist
    if output_dir is None:
        output_dir = f"asset_analysis_{asset_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    asset_output_dir = os.path.join(output_dir, asset_id)
    os.makedirs(asset_output_dir, exist_ok=True)
    
    # Find the CSV file for this asset and consumption type
    file_pattern = f"data/analyzed_data/*/*daily_readings_{asset_id}*{consumption_type}*.csv"
    files = glob.glob(file_pattern)
    
    if not files:
        logger.error(f"No files found for asset {asset_id} with consumption type {consumption_type}")
        return
    
    file_path = files[0]  # Use the first matching file
    logger.info(f"Using file: {file_path}")
    
    try:
        # Load the data
        df = pd.read_csv(file_path)
        
        # Ensure the dataframe has the required columns
        required_columns = ['date', 'value']
        if not all(col in df.columns for col in required_columns):
            # Try to adapt the columns
            if 'Fecha' in df.columns and 'Valor' in df.columns:
                df = df.rename(columns={'Fecha': 'date', 'Valor': 'value'})
            elif 'fecha' in df.columns and 'valor' in df.columns:
                df = df.rename(columns={'fecha': 'date', 'valor': 'value'})
            else:
                logger.error(f"Required columns not found in file {file_path}")
                logger.info(f"Available columns: {df.columns.tolist()}")
                return
        
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Sort by date
        df = df.sort_values('date')
        
        # Convert value to numeric
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        # Drop rows with NaN values
        df = df.dropna(subset=['value'])
        
        if df.empty:
            logger.error(f"No valid data found for asset {asset_id}")
            return
        
        # Save the processed data
        processed_file = os.path.join(asset_output_dir, f"{asset_id}_processed_data.csv")
        df.to_csv(processed_file, index=False)
        logger.info(f"Processed data saved to {processed_file}")
        
        # Load configuration if needed
        config = None
        if use_config:
            try:
                from utils.anomaly_experimental.config_loader import load_anomaly_config
                config = load_anomaly_config()
                logger.info(f"Using configuration: {config}")
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
                config = None
        
        # Detect anomalies
        from utils.anomaly_experimental.integration import analyze_readings
        
        results = analyze_readings(
            df,
            asset_id=asset_id,
            consumption_type=consumption_type,
            use_config=use_config
        )
        
        # Save the results
        anomalies_df = results.get('anomalies')
        if anomalies_df is not None and not anomalies_df.empty:
            anomalies_file = os.path.join(asset_output_dir, f"{asset_id}_anomalies.csv")
            anomalies_df.to_csv(anomalies_file, index=False)
            logger.info(f"Found {len(anomalies_df)} anomalies. Saved to {anomalies_file}")
            
            # Generate visualization
            plt.figure(figsize=(12, 6))
            plt.plot(df['date'], df['value'], label='Readings')
            plt.scatter(anomalies_df['date'], anomalies_df['value'], color='red', label='Anomalies')
            plt.title(f'Anomalies for Asset {asset_id}')
            plt.xlabel('Date')
            plt.ylabel('Value')
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            
            # Save the plot
            plot_file = os.path.join(asset_output_dir, f"{asset_id}_anomalies_plot.png")
            plt.savefig(plot_file)
            plt.close()
            logger.info(f"Visualization saved to {plot_file}")
            
            # Save thresholds
            thresholds = results.get('thresholds')
            if thresholds:
                thresholds_file = os.path.join(asset_output_dir, f"{asset_id}_thresholds.json")
                with open(thresholds_file, 'w') as f:
                    json.dump(thresholds, f, indent=2, default=str)
                logger.info(f"Thresholds saved to {thresholds_file}")
        else:
            logger.info(f"No anomalies found for asset {asset_id}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error analyzing asset {asset_id}: {str(e)}")
        traceback.print_exc()
        return None

def analyze_project(project_id, consumption_type, use_config=True, output_dir=None):
    """
    Analyze all assets in a project for anomalies.
    
    Args:
        project_id (str): The project ID to analyze
        consumption_type (str): The consumption type to analyze
        use_config (bool): Whether to use the configuration file
        output_dir (str): The output directory for results
    """
    logger.info(f"Analyzing project {project_id} for consumption type {consumption_type}")
    
    # Create output directory if it doesn't exist
    if output_dir is None:
        output_dir = f"project_analysis_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the project directory
    project_dir = os.path.join(os.getcwd(), "data", "analyzed_data", project_id)
    
    # If the project directory doesn't exist, try using the general data directory
    if not os.path.exists(project_dir):
        logger.info(f"Project directory {project_dir} not found, using general data directory")
        project_dir = os.path.join(os.getcwd(), "data", "analyzed_data")
    
    # Find all CSV files that match the consumption type
    file_pattern = f"{project_dir}/*daily_readings_*{consumption_type}*.csv"
    files = glob.glob(file_pattern)
    
    if not files:
        logger.error(f"No files found matching pattern: {file_pattern}")
        # List files in the directory for debugging
        if os.path.exists(project_dir):
            logger.info("Files in directory:")
            for file in os.listdir(project_dir):
                logger.info(f"  {file}")
        return
    
    logger.info(f"Found {len(files)} files matching consumption type {consumption_type}")
    
    # Limit to 10 files for initial testing
    if len(files) > 10:
        logger.info(f"Limiting to 10 files for initial testing")
        files = files[:10]
    
    # Process each file
    for file_path in files:
        try:
            # Extract asset ID from filename
            filename = os.path.basename(file_path)
            asset_id = filename.split('_')[2].split('__')[0]
            
            logger.info(f"Processing asset {asset_id} from file {filename}")
            
            # Analyze the asset
            analyze_asset(asset_id, consumption_type, use_config, output_dir)
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            traceback.print_exc()
    
    logger.info(f"Project analysis complete. Results saved to {output_dir}")

def main():
    """
    Main function to run the script.
    """
    parser = argparse.ArgumentParser(description='Test anomaly detection with real data')
    parser.add_argument('--type', choices=['asset', 'project'], required=True, help='Type of analysis')
    parser.add_argument('--id', required=True, help='Asset ID or Project ID')
    parser.add_argument('--consumption-type', required=True, help='Consumption type to analyze')
    parser.add_argument('--output-dir', help='Output directory')
    parser.add_argument('--use-config', action='store_true', default=True, help='Use anomaly_config.json')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the appropriate analysis
    if args.type == 'asset':
        logger.info(f"Analyzing asset {args.id} for consumption type {args.consumption_type}")
        analyze_asset(
            asset_id=args.id,
            consumption_type=args.consumption_type,
            use_config=args.use_config,
            output_dir=args.output_dir
        )
    else:
        logger.info(f"Analyzing project {args.id} for consumption type {args.consumption_type}")
        analyze_project(
            project_id=args.id,
            consumption_type=args.consumption_type,
            use_config=args.use_config,
            output_dir=args.output_dir
        )

if __name__ == "__main__":
    sys.exit(main()) 