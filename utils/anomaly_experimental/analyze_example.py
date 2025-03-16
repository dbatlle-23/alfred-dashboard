"""
Example script to analyze the specific anomaly mentioned in the user's query.
This script demonstrates how to use the experimental contextual anomaly detection system.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the test harness
from utils.anomaly_experimental.test_harness import analyze_specific_anomaly

def create_example_data():
    """
    Create example data for the specific anomaly mentioned in the user's query.
    
    Returns:
        pd.DataFrame: Example data
    """
    # Create a date range
    dates = pd.date_range(start='2025-02-01', end='2025-03-10', freq='D')
    
    # Create a DataFrame
    df = pd.DataFrame({
        'date': dates,
        'asset_id': 'example_asset',
        'consumption_type': 'ENERGY_ACTIVE',
        'consumption': np.nan,
        'client_id': 'example_client',
        'project_id': 'example_project'
    })
    
    # Set consumption values
    # Normal pattern for most days
    for i in range(len(df)):
        if i == 0:
            df.loc[i, 'consumption'] = 1000000000.0
        else:
            # Add a small random variation (0.1% to 0.5%)
            variation = np.random.uniform(0.001, 0.005)
            df.loc[i, 'consumption'] = df.loc[i-1, 'consumption'] * (1 + variation)
    
    # Set the specific anomaly values
    feb_27_idx = df[df['date'] == '2025-02-27'].index[0]
    feb_28_idx = df[df['date'] == '2025-02-28'].index[0]
    
    df.loc[feb_27_idx, 'consumption'] = 1163298740.1696384
    df.loc[feb_28_idx, 'consumption'] = 1217824597.6496358
    
    # Calculate daily changes
    df['daily_change'] = df['consumption'].diff()
    df['daily_change_pct'] = df['consumption'].pct_change() * 100
    
    return df

def analyze_example():
    """
    Analyze the example anomaly.
    """
    try:
        # Create example data
        example_data = create_example_data()
        
        # Create output directory
        output_dir = "example_analysis"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save example data to CSV
        csv_path = os.path.join(output_dir, "example_data.csv")
        example_data.to_csv(csv_path, index=False)
        logger.info(f"Saved example data to {csv_path}")
        
        # Analyze the specific anomaly
        result = analyze_specific_anomaly(
            asset_id='example_asset',
            date='2025-02-28',
            consumption_type='ENERGY_ACTIVE',
            data_source=example_data,
            days_context=10
        )
        
        # Print results
        if result['success']:
            print("\n=== ANOMALY ANALYSIS RESULTS ===")
            print(f"Asset ID: {result['asset_id']}")
            print(f"Date: {result['date']}")
            print(f"Consumption: {result['consumption']:.2f}")
            
            if result['previous_consumption'] is not None:
                print(f"Previous day consumption: {result['previous_consumption']:.2f}")
            else:
                print("Previous day consumption: Not available")
                
            if result['daily_change'] is not None:
                print(f"Daily change: {result['daily_change']:.2f}")
            else:
                print("Daily change: Not available")
                
            if result['daily_change_pct'] is not None:
                print(f"Daily change percentage: {result['daily_change_pct']:.2f}%")
            else:
                print("Daily change percentage: Not available")
                
            print(f"Is anomaly: {result['is_anomaly']}")
            
            if result['is_anomaly']:
                if result['confidence'] is not None:
                    print(f"Confidence: {result['confidence']:.2f}")
                else:
                    print("Confidence: Not available")
                    
                print(f"Anomaly type: {result['anomaly_type']}")
                
                if result['threshold'] is not None:
                    print(f"Threshold: {result['threshold']:.2f}")
                else:
                    print("Threshold: Not available")
            
            print("\nThresholds used for detection:")
            for key, value in result['thresholds'].items():
                if isinstance(value, (int, float)):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")
            
            if 'visualizations_path' in result:
                print(f"\nVisualizations saved to: {result['visualizations_path']}")
        else:
            print(f"Error: {result['message']}")
        
    except Exception as e:
        logger.error(f"Error analyzing example: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    analyze_example() 