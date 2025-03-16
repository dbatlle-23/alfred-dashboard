"""
Script to run the contextual anomaly detection test harness on real data.
This script can be run independently to test the system without affecting the main application.
"""

import argparse
import logging
import os
import sys
import pandas as pd
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the test harness
from utils.anomaly_experimental.test_harness import (
    AnomalyTestHarness,
    run_test_for_asset,
    run_test_for_project,
    analyze_specific_anomaly
)

def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Run contextual anomaly detection tests')
    
    # Test type
    parser.add_argument('--type', choices=['asset', 'project', 'specific'], default='asset',
                        help='Type of test to run (asset, project, or specific anomaly)')
    
    # Asset/project ID
    parser.add_argument('--id', required=True,
                        help='Asset ID or project ID to test')
    
    # Consumption type
    parser.add_argument('--consumption-type', default=None,
                        help='Consumption type to test (e.g., ENERGY_ACTIVE)')
    
    # Data source
    parser.add_argument('--data-source', default=None,
                        help='Path to data file (CSV, JSON, Excel)')
    
    # Threshold method
    parser.add_argument('--threshold-method', choices=['std_dev', 'percentile'], default='std_dev',
                        help='Method to use for threshold calculation')
    
    # Percentile
    parser.add_argument('--percentile', type=float, default=95,
                        help='Percentile to use if method is "percentile"')
    
    # Specific date (for specific anomaly analysis)
    parser.add_argument('--date', default=None,
                        help='Date of specific anomaly to analyze (YYYY-MM-DD)')
    
    # Output directory
    parser.add_argument('--output-dir', default=None,
                        help='Directory to save test results')
    
    return parser.parse_args()

def main():
    """
    Main function to run the test harness.
    """
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Set output directory
        output_dir = args.output_dir
        if not output_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if args.type == 'asset':
                output_dir = f"test_results/asset_{args.id}_{timestamp}"
            elif args.type == 'project':
                output_dir = f"test_results/project_{args.id}_{timestamp}"
            else:
                output_dir = f"test_results/specific_{args.id}_{args.date}_{timestamp}"
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Run the appropriate test
        if args.type == 'asset':
            logger.info(f"Running test for asset {args.id}")
            result = run_test_for_asset(
                asset_id=args.id,
                consumption_type=args.consumption_type,
                data_source=args.data_source,
                threshold_method=args.threshold_method,
                percentile=args.percentile
            )
        elif args.type == 'project':
            logger.info(f"Running test for project {args.id}")
            result = run_test_for_project(
                project_id=args.id,
                consumption_type=args.consumption_type,
                data_source=args.data_source,
                threshold_method=args.threshold_method,
                percentile=args.percentile
            )
        elif args.type == 'specific':
            if not args.date:
                logger.error("Date is required for specific anomaly analysis")
                return 1
                
            logger.info(f"Analyzing specific anomaly for asset {args.id} on {args.date}")
            result = analyze_specific_anomaly(
                asset_id=args.id,
                date=args.date,
                consumption_type=args.consumption_type,
                data_source=args.data_source
            )
        else:
            logger.error(f"Unknown test type: {args.type}")
            return 1
        
        # Print results
        if result['success']:
            if args.type == 'specific':
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
                print("\n=== TEST RESULTS ===")
                print(f"Total records: {result['total_records']}")
                print(f"Anomaly records: {result['anomaly_records']} ({result['anomaly_percentage']:.2f}%)")
                print(f"High confidence anomalies: {result['high_confidence']}")
                print(f"Medium confidence anomalies: {result['medium_confidence']}")
                print(f"Low confidence anomalies: {result['low_confidence']}")
                print(f"Absolute change anomalies: {result['absolute_change']}")
                print(f"Percentage change anomalies: {result['percentage_change']}")
                print(f"Processing time: {result['processing_time']:.2f} seconds")
        else:
            print(f"Error: {result['message']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error running test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 