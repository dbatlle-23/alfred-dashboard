# Contextual Anomaly Detection System (Experimental)

This module implements an experimental contextual anomaly detection system that can identify potential anomalies in consumption data based on asset-specific historical patterns. It is designed to run in parallel with the existing anomaly detection system for testing and validation before integration.

## Overview

The system detects anomalies by:

1. Calculating asset-specific thresholds based on historical consumption patterns
2. Identifying consumption changes that exceed these thresholds
3. Assigning confidence levels to potential anomalies
4. Providing visualization and analysis tools for evaluation

## Components

- **threshold_calculator.py**: Calculates asset-specific thresholds for detecting abnormal consumption changes
- **contextual_detection.py**: Detects anomalies based on the calculated thresholds
- **test_harness.py**: Provides tools for testing and evaluating the system
- **analyze_example.py**: Example script for analyzing a specific anomaly case
- **run_test.py**: Command-line tool for running tests on real data
- **integration.py**: Functions for integrating with the main application

## Usage

### Running the Example

```bash
python -m utils.anomaly_experimental.analyze_example
```

This will analyze the specific anomaly case mentioned in the user's query (2025-02-27 to 2025-02-28) and generate visualizations.

### Testing with Real Data

```bash
python -m utils.anomaly_experimental.run_test --type asset --id <asset_id> --consumption-type <consumption_type>
```

Options:
- `--type`: Type of test to run (`asset`, `project`, or `specific`)
- `--id`: Asset ID or project ID to test
- `--consumption-type`: Consumption type to test (e.g., `ENERGY_ACTIVE`)
- `--data-source`: Path to data file (CSV, JSON, Excel)
- `--threshold-method`: Method to use for threshold calculation (`std_dev` or `percentile`)
- `--percentile`: Percentile to use if method is "percentile"
- `--date`: Date of specific anomaly to analyze (YYYY-MM-DD) (required for `--type specific`)
- `--output-dir`: Directory to save test results

### Integration with Main Application

To use the experimental system in the main application, import the integration module:

```python
from utils.anomaly_experimental.integration import detect_contextual_anomalies, analyze_asset_anomalies, get_asset_thresholds

# Detect anomalies in a DataFrame
result_df = detect_contextual_anomalies(df)

# Analyze anomalies for a specific asset
analysis = analyze_asset_anomalies(asset_id, consumption_type)

# Get thresholds for a specific asset
thresholds = get_asset_thresholds(asset_id, consumption_type)
```

## Next Steps

1. **Extensive Testing**: Test the system with a variety of assets and consumption types to validate its effectiveness
2. **Parameter Tuning**: Experiment with different threshold calculation methods and parameters
3. **User Feedback System**: Implement a system for collecting user feedback on detected anomalies
4. **Learning System**: Develop a learning system that improves detection based on user feedback
5. **UI Integration**: Create a user interface for reviewing and classifying potential anomalies
6. **Performance Optimization**: Optimize the system for large datasets
7. **Full Integration**: Integrate the system with the main application once it has been validated

## Implementation Notes

- The system is designed to be non-intrusive and can run in parallel with the existing anomaly detection system
- All components are isolated in the `utils/anomaly_experimental` directory to avoid affecting the main application
- The integration module provides a clean interface for using the system in the main application

## Dependencies

- pandas
- numpy
- matplotlib
- seaborn

## License

This module is part of the Alfred Dashboard project and is subject to the same license terms. 