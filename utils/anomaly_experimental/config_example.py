"""
Example script to demonstrate the use of anomaly_config.json with the experimental system.
This script shows how to load and use the configuration for anomaly detection.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import logging
import json
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_example_data():
    """
    Create example data for different consumption types.
    
    Returns:
        pd.DataFrame: Example data
    """
    # Create a date range
    dates = pd.date_range(start='2025-01-01', end='2025-03-31', freq='D')
    
    # Create a DataFrame with multiple assets and consumption types
    data = []
    
    # Asset 1: ENERGY_ACTIVE
    for i, date in enumerate(dates):
        # Base consumption with weekly pattern
        base = 1000000 + 100000 * np.sin(i * 2 * np.pi / 7)
        
        # Add some random variation
        variation = np.random.normal(0, 10000)
        
        # Add a specific anomaly
        anomaly = 0
        if date.strftime('%Y-%m-%d') == '2025-02-15':
            anomaly = 500000  # Large spike
        
        consumption = base + variation + anomaly
        
        data.append({
            'date': date,
            'asset_id': 'asset_1',
            'consumption_type': '_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL',
            'consumption': consumption,
            'client_id': 'example_client',
            'project_id': 'example_project'
        })
    
    # Asset 2: THERMAL_ENERGY
    for i, date in enumerate(dates):
        # Base consumption with seasonal pattern
        base = 5000 + 2000 * np.sin(i * 2 * np.pi / 90)
        
        # Add some random variation
        variation = np.random.normal(0, 200)
        
        # Add a specific anomaly
        anomaly = 0
        if date.strftime('%Y-%m-%d') == '2025-03-10':
            anomaly = 10000  # Very large spike
        
        consumption = base + variation + anomaly
        
        data.append({
            'date': date,
            'asset_id': 'asset_2',
            'consumption_type': '_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT',
            'consumption': consumption,
            'client_id': 'example_client',
            'project_id': 'example_project'
        })
    
    # Asset 3: DOMESTIC_HOT_WATER
    for i, date in enumerate(dates):
        # Base consumption with daily pattern
        base = 200 + 50 * np.sin(i * 2 * np.pi / 1)
        
        # Add some random variation
        variation = np.random.normal(0, 10)
        
        # Add a specific anomaly
        anomaly = 0
        if date.strftime('%Y-%m-%d') == '2025-02-28':
            anomaly = 300  # Large spike
        
        consumption = base + variation + anomaly
        
        data.append({
            'date': date,
            'asset_id': 'asset_3',
            'consumption_type': '_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER',
            'consumption': consumption,
            'client_id': 'example_client',
            'project_id': 'example_project'
        })
    
    return pd.DataFrame(data)

def run_config_example():
    """
    Run the configuration example.
    """
    try:
        print("Starting configuration example...")
        
        # Import the necessary modules
        try:
            from utils.anomaly_experimental.config_loader import load_anomaly_config, get_config_for_consumption_type
            from utils.anomaly_experimental.integration import detect_contextual_anomalies, analyze_asset_anomalies
            from utils.anomaly_experimental.threshold_calculator import ThresholdCalculator
        except ImportError as e:
            print(f"Error importing modules: {e}")
            traceback.print_exc()
            return
        
        # Create output directory
        output_dir = "config_example"
        os.makedirs(output_dir, exist_ok=True)
        
        # Load the anomaly configuration
        try:
            config = load_anomaly_config()
            print("\n=== ANOMALY CONFIGURATION ===")
            print(json.dumps(config, indent=2))
        except Exception as e:
            print(f"Error loading anomaly configuration: {e}")
            traceback.print_exc()
            return
        
        # Create example data
        try:
            example_data = create_example_data()
            
            # Save example data to CSV
            csv_path = os.path.join(output_dir, "config_example_data.csv")
            example_data.to_csv(csv_path, index=False)
            print(f"Saved example data to {csv_path}")
        except Exception as e:
            print(f"Error creating example data: {e}")
            traceback.print_exc()
            return
        
        # Detect anomalies using configuration
        try:
            print("\n=== DETECTING ANOMALIES USING CONFIGURATION ===")
            result_df = detect_contextual_anomalies(example_data, use_config=True)
            
            # Count anomalies by type
            anomalies = result_df[result_df['is_contextual_anomaly']]
            print(f"Total records: {len(result_df)}")
            print(f"Anomalies detected: {len(anomalies)}")
        except Exception as e:
            print(f"Error detecting anomalies: {e}")
            traceback.print_exc()
            return
        
        # Group by asset and consumption type
        try:
            for (asset_id, consumption_type), group in anomalies.groupby(['asset_id', 'consumption_type']):
                print(f"\nAnomalies for {asset_id} ({consumption_type}):")
                print(f"  Total anomalies: {len(group)}")
                
                # Get configuration for this consumption type
                type_config = get_config_for_consumption_type(consumption_type)
                print(f"  Configuration: {type_config}")
                
                # Group by anomaly type
                type_counts = group['contextual_anomaly_type'].value_counts()
                for anomaly_type, count in type_counts.items():
                    print(f"  {anomaly_type}: {count}")
                
                # Show top anomalies
                print("\n  Top anomalies:")
                top_anomalies = group.sort_values('contextual_anomaly_confidence', ascending=False).head(3)
                for _, row in top_anomalies.iterrows():
                    print(f"    Date: {row['date'].strftime('%Y-%m-%d')}")
                    print(f"    Consumption: {row['consumption']:.2f}")
                    print(f"    Daily change: {row['daily_change']:.2f}")
                    print(f"    Daily change %: {row['daily_change_pct']:.2f}%")
                    print(f"    Type: {row['contextual_anomaly_type']}")
                    print(f"    Confidence: {row['contextual_anomaly_confidence']:.2f}")
                    print(f"    Threshold: {row['contextual_anomaly_threshold']:.2f}")
                    print()
        except Exception as e:
            print(f"Error analyzing anomalies by group: {e}")
            traceback.print_exc()
        
        # Analyze specific assets
        try:
            print("\n=== ANALYZING SPECIFIC ASSETS ===")
            for asset_id, consumption_type in [
                ('asset_1', '_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL'),
                ('asset_2', '_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT'),
                ('asset_3', '_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER')
            ]:
                print(f"\nAnalyzing {asset_id} ({consumption_type}):")
                
                # Get thresholds for this asset
                calculator = ThresholdCalculator(asset_id, consumption_type)
                thresholds = calculator.get_thresholds(df=example_data, method="config")
                
                print(f"  Thresholds:")
                for key, value in thresholds.items():
                    if isinstance(value, (int, float)):
                        print(f"    {key}: {value:.2f}")
                    else:
                        print(f"    {key}: {value}")
                
                # Analyze anomalies
                analysis = analyze_asset_anomalies(
                    asset_id=asset_id,
                    consumption_type=consumption_type,
                    df=example_data,
                    use_config=True
                )
                
                if analysis['success']:
                    print(f"  Total records: {analysis['total_records']}")
                    print(f"  Anomalies: {analysis['anomaly_records']} ({analysis['anomaly_percentage']:.2f}%)")
                    print(f"  High confidence: {analysis['high_confidence']}")
                    print(f"  Medium confidence: {analysis['medium_confidence']}")
                    print(f"  Low confidence: {analysis['low_confidence']}")
                    
                    if analysis['top_anomalies']:
                        print("\n  Top anomalies:")
                        for anomaly in analysis['top_anomalies']:
                            print(f"    Date: {anomaly['date']}")
                            print(f"    Consumption: {anomaly['consumption']:.2f}")
                            if anomaly['previous_consumption'] is not None:
                                print(f"    Previous consumption: {anomaly['previous_consumption']:.2f}")
                            if anomaly['daily_change'] is not None:
                                print(f"    Daily change: {anomaly['daily_change']:.2f}")
                            if anomaly['daily_change_pct'] is not None:
                                print(f"    Daily change %: {anomaly['daily_change_pct']:.2f}%")
                            print(f"    Type: {anomaly['type']}")
                            print(f"    Confidence: {anomaly['confidence']:.2f}")
                            print(f"    Threshold: {anomaly['threshold']:.2f}")
                            print()
                else:
                    print(f"  Error: {analysis['message']}")
        except Exception as e:
            print(f"Error analyzing specific assets: {e}")
            traceback.print_exc()
        
        # Save results
        try:
            results_path = os.path.join(output_dir, "config_example_results.csv")
            result_df.to_csv(results_path, index=False)
            print(f"Saved results to {results_path}")
            
            print(f"\nResults saved to {output_dir}")
        except Exception as e:
            print(f"Error saving results: {e}")
            traceback.print_exc()
        
    except Exception as e:
        print(f"Error running configuration example: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_config_example() 