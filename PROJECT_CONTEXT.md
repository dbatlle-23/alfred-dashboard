# Alfred Dashboard - Project Context

## Project Overview

Alfred Dashboard is a web application built with Dash (a Python framework for building analytical web applications) that provides visualization and analysis capabilities for Alfred Smart data. The dashboard allows users to explore database tables, visualize metrics, and configure various aspects of the system.

## Architecture

The application follows a modular architecture with clear separation of concerns:

### Core Components

1. **Main Application (`app.py`)**: 
   - Entry point for the application
   - Configures the Dash application
   - Sets up authentication
   - Defines the main layout structure
   - Registers callbacks from different modules

2. **Layouts**: 
   - Each page of the application has its own layout module in the `layouts/` directory
   - Layouts define the UI structure of each page
   - Examples include: home, metrics, database explorer, login, etc.

3. **Components**: 
   - Reusable UI elements in the `components/` directory
   - Includes sidebar, navbar, and various specialized components
   - Components can have their own callbacks for internal functionality

4. **Callbacks**: 
   - Dash callbacks that handle interactivity
   - Organized in the `callbacks/` directory
   - Some callbacks are defined within their respective layout or component files
   - Complex features have dedicated callback modules

5. **Utilities**: 
   - Helper functions and services in the `utils/` directory
   - Includes database utilities, authentication, error handling, logging, etc.

### Data Flow

1. User interacts with the UI
2. Dash callbacks process the interaction
3. Callbacks may use utility functions to fetch or process data
4. Results are returned to update the UI

## Authentication System

The application uses JWT (JSON Web Tokens) for authentication:

1. **Token-based**: Each session generates a unique JWT token
2. **Session Storage**: Tokens are stored in the browser's session storage
3. **Independent Sessions**: Each browser tab maintains its own session
4. **Verification**: Tokens are verified on each request
5. **Expiration**: Tokens have a limited lifetime for security

## Error Handling

The application implements a robust error handling system:

1. **Decorators**: Functions like `handle_exceptions` and `safe_db_operation` wrap callbacks and functions
2. **Structured Logging**: Errors are logged with context information
3. **User Feedback**: Errors are displayed to users in a friendly format
4. **Global Error Container**: A dedicated container for displaying application-wide errors

## Logging

The application uses a comprehensive logging system:

1. **Structured Logs**: JSON-formatted logs for machine readability
2. **Multiple Outputs**: Logs to both console and file
3. **Configurable Levels**: Different log levels for console and file
4. **Context Information**: Logs include timestamp, module, function, and line number

## Project Structure

```
alfred-dashboard/
├── app.py                  # Main application entry point
├── components/             # Reusable UI components
│   ├── ui/                 # Generic UI components
│   ├── metrics/            # Metrics-specific components
│   ├── sidebar.py          # Sidebar component
│   ├── navbar.py           # Navigation bar component
│   └── ...
├── layouts/                # Page layouts
│   ├── home.py             # Home page
│   ├── metrics_refactored.py # Metrics visualization
│   ├── login.py            # Login page
│   ├── db_explorer.py      # Database explorer
│   └── ...
├── callbacks/              # Callback functions
│   ├── metrics/            # Metrics-related callbacks
│   ├── db_config.py        # Database configuration callbacks
│   ├── db_explorer.py      # Database explorer callbacks
│   └── ...
├── utils/                  # Utility functions and services
│   ├── logging/            # Logging configuration
│   ├── anomaly/            # Anomaly detection utilities
│   ├── repositories/       # Data access layer
│   ├── adapters/           # Adapters for external services
│   ├── metrics/            # Metrics calculation utilities
│   ├── auth.py             # Authentication service
│   ├── db_utils.py         # Database utilities
│   ├── error_handlers.py   # Error handling utilities
│   └── ...
├── config/                 # Configuration files
├── assets/                 # Static assets (CSS, images)
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── utils/              # Test utilities
│   ├── conftest.py         # Test configuration
│   └── ...
├── logs/                   # Application logs
├── data/                   # Data files
│   └── analyzed_data/      # Processed data
├── constants/              # Application constants
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
└── README.md               # Project documentation
```

## Coding Patterns and Best Practices

### 1. Callback Structure

Callbacks should follow this pattern:

```python
@app.callback(
    Output("output-id", "property"),
    [Input("input-id", "property")],
    [State("state-id", "property")]
)
@handle_exceptions(default_return=some_default_value)
def callback_function(input_value, state_value):
    # Function logic
    return result
```

### 2. Error Handling

Always use error handling decorators for callbacks and functions that might fail:

```python
@handle_exceptions(default_return=html.Div("Error message"))
def some_function():
    # Function that might raise exceptions
    
@safe_db_operation(default_return=[])
def database_function():
    # Database operation that might fail
```

For operations that need to return success/failure status:

```python
success, result, error_message = try_operation(some_function, arg1, arg2)
if success:
    # Handle success
else:
    # Handle error using error_message
```

### 3. Logging

Use the configured logger throughout the application:

```python
from utils.logging import get_logger
logger = get_logger(__name__)

def some_function():
    logger.info("Informational message")
    try:
        # Some operation
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        logger.debug("Detailed debug information", exc_info=True)
```

### 4. Authentication

Always verify authentication for protected routes:

```python
token = token_data.get('token') if token_data else None
if not token or not auth_service.is_authenticated(token):
    # Handle unauthenticated user
```

### 5. Component Structure

Components should be modular and reusable:

```python
def create_component(param1, param2):
    """Create a reusable component.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        dash component
    """
    return html.Div([
        # Component structure
    ])

def register_callbacks(app):
    """Register callbacks for this component.
    
    Args:
        app: Dash application instance
    """
    @app.callback(
        # Callback definition
    )
    def internal_callback():
        # Callback logic
```

### 6. Database Operations

Use SQLAlchemy for database operations and handle connections properly:

```python
from utils.db_utils import get_db_engine

def fetch_data():
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        with engine.connect() as connection:
            result = connection.execute(query)
            return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return []
```

## Adding New Features

When adding new features to the project, follow these steps:

1. **Understand the Feature Context**:
   - Determine which part of the application the feature belongs to
   - Identify related existing components and utilities

2. **Plan the Implementation**:
   - Design the UI components needed
   - Plan the data flow and callback structure
   - Identify required database operations or API calls

3. **Implementation Steps**:
   - Create or modify layout files in `layouts/`
   - Develop reusable components in `components/` if needed
   - Implement callbacks in `callbacks/` or within the layout/component
   - Add utility functions in `utils/` as needed
   - Update the main application (`app.py`) if necessary

4. **Testing**:
   - Write unit tests for new functionality
   - Test the feature manually in the application
   - Verify error handling works correctly

5. **Documentation**:
   - Update docstrings for new functions and components
   - Add comments for complex logic
   - Update README or other documentation if needed

## Debugging and Troubleshooting

1. **Logging**:
   - Check the logs in the `logs/` directory
   - Look for error messages and stack traces
   - Use the appropriate log level (DEBUG for detailed information)

2. **Common Issues**:
   - Authentication problems: Check JWT token validity
   - Database connection issues: Verify connection parameters
   - Callback errors: Look for exceptions in the callback chain
   - UI not updating: Check if callbacks are being triggered

3. **Development Tools**:
   - Use the Dash debug mode (`debug=True`)
   - Check the browser console for JavaScript errors
   - Use the network tab to inspect API requests

## Deployment

The application can be deployed using Docker:

1. Build the Docker image:
   ```
   docker build -t alfred-dashboard .
   ```

2. Run the container:
   ```
   docker run -p 8050:8050 alfred-dashboard
   ```

Alternatively, use the provided script:
```
./build_and_run.sh
```

## Configuration

The application can be configured using environment variables:

- `HOST`: Host to run the application on (default: 0.0.0.0)
- `PORT`: Port to run the application on (default: 8050)
- `DASH_DEBUG`: Enable debug mode (default: false)
- `LOG_LEVEL`: General log level (default: INFO)
- `CONSOLE_LOG_LEVEL`: Console log level (default: INFO)
- `FILE_LOG_LEVEL`: File log level (default: DEBUG)
- `JWT_SECRET_KEY`: Secret key for JWT tokens

## API Integration

The application integrates with the Alfred Smart API to retrieve and process data. Understanding the API structure is essential for working with the application.

### API Endpoints

The application interacts with several key API endpoints:

- `/api/auth/login`: Authentication endpoint to obtain JWT tokens
- `/api/clients`: Retrieve list of clients
- `/api/projects`: Retrieve projects (can be filtered by client)
- `/api/assets`: Retrieve assets (can be filtered by project)
- `/api/readings`: Retrieve consumption readings
- `/api/tags`: Retrieve consumption tags/types
- `/api/corrections`: Submit and retrieve manual corrections

### Authentication Flow

1. The application authenticates with the API using credentials
2. The API returns a JWT token
3. This token is included in the Authorization header for subsequent requests
4. The token is refreshed periodically to maintain the session

### Request/Response Format

Most API endpoints accept and return JSON data. Example of a typical response:

```json
{
  "success": true,
  "data": [...],
  "message": "Operation successful",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Error Handling

API errors are handled consistently:

```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid credentials"
  },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### API Client Implementation

The application uses a custom API client implementation in `utils/api_client.py` that:

- Manages authentication
- Handles request formatting
- Processes responses
- Implements error handling and retries
- Provides caching for frequently accessed data

## Conclusion

This project follows a modular, component-based architecture with clear separation of concerns. By understanding the structure and patterns described in this document, you should be able to navigate the codebase, add new features, and fix bugs effectively.

When in doubt, refer to existing implementations as examples of the patterns and practices to follow. 

## Data Structure

The application processes and analyzes consumption data from various sources. Understanding the data structure is crucial for developing new features or maintaining existing ones.

### Data Model Hierarchy

The application follows a hierarchical data model that reflects the real-world organization of buildings and spaces:

1. **Client**: Top-level entity representing an organization or company
   - Has a unique `client_id`
   - Contains multiple projects
   - Example attributes: name, contact information, subscription level

2. **Project**: Represents a physical building or facility
   - Has a unique `project_id`
   - Belongs to a specific client
   - Contains multiple assets
   - Example attributes: name, address, construction date, total area

3. **Asset**: Represents a specific space or area within a project
   - Has a unique `asset_id`
   - Belongs to a specific project
   - Has multiple consumption readings of different types
   - Example attributes: name, type (apartment, common area, etc.), floor, area

4. **Consumption Reading**: Represents a measurement of resource usage
   - Associated with a specific asset
   - Has a specific consumption type (tag)
   - Contains date and value information
   - May have corrections applied

This hierarchy is reflected in the UI navigation, data storage, and API structure.

### Entity Relationships

```
Client (1) ---> (N) Project (1) ---> (N) Asset (1) ---> (N) Consumption Reading
```

- A client can have multiple projects
- A project belongs to exactly one client
- A project can have multiple assets
- An asset belongs to exactly one project
- An asset can have multiple consumption readings
- A consumption reading belongs to exactly one asset

### Directory Structure

Data files are organized in the following structure:

```
data/
└── analyzed_data/
    ├── <project_id>/                      # Directories named with project UUIDs
    │   └── daily_readings_<asset_id>__<consumption_type>.csv  # Daily consumption readings for specific assets
    ├── anomaly_config.json                # Configuration for anomaly detection thresholds
    ├── corrections_log.json               # Log of manual corrections applied to readings
    ├── anomaly_learning.json              # Learning data for anomaly detection
    └── anomaly_feedback.json              # User feedback on detected anomalies
```

### File Formats

#### Daily Readings CSV Files

Daily consumption readings are stored in CSV files with the following naming convention:
`daily_readings_<asset_id>__<consumption_type>.csv`

These files contain the following columns:
- `date`: Date of the reading in YYYY-MM-DD format
- `value`: Consumption value for that day
- `timestamp`: Unix timestamp of when the reading was recorded

Example:
```csv
date,value,timestamp
2024-12-12,0.0,1970-01-21
2024-12-14,0.02,1970-01-21
2025-03-17,0.02,1742184221.0
```

#### Anomaly Configuration (anomaly_config.json)

This file contains threshold configurations for anomaly detection by consumption type:

```json
{
  "default": {
    "daily_max": 10.0,
    "monthly_max": 200.0,
    "sudden_increase": 5.0,
    "std_multiplier": 3.0
  },
  "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER": {
    "daily_max": 5.0,
    "monthly_max": 200.0,
    "sudden_increase": 5.0,
    "std_multiplier": 3.0
  }
}
```

Key parameters:
- `daily_max`: Maximum expected daily consumption
- `monthly_max`: Maximum expected monthly consumption
- `sudden_increase`: Threshold for percentage increase considered anomalous
- `std_multiplier`: Standard deviation multiplier for statistical anomaly detection

#### Corrections Log (corrections_log.json)

Records manual corrections applied to consumption data:

```json
[
  {
    "timestamp": "2025-02-17 18:29:19",
    "project_id": "713713a2-d7f4-4a89-b613-da4cd5113f85",
    "asset_id": "DL39NQJXC2T68",
    "tag_id": "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL",
    "start_date": "2024-03-30",
    "end_date": "2024-11-14",
    "total_consumption": 45,
    "daily_consumption": 0.1956521739130435
  }
]
```

### Data Storage and Access Patterns

#### In-Memory Data Structure

When loaded into the application, data is typically structured as:

```python
{
  'client_id': {
    'name': 'Client Name',
    'projects': {
      'project_id': {
        'name': 'Project Name',
        'assets': {
          'asset_id': {
            'name': 'Asset Name',
            'consumption_data': {
              'consumption_type': pd.DataFrame(...)
            }
          }
        }
      }
    }
  }
}
```

#### Database Schema

For persistent storage, the application uses a relational database with the following key tables:

- `clients`: Stores client information
- `projects`: Stores project information with foreign key to clients
- `assets`: Stores asset information with foreign key to projects
- `consumption_readings`: Stores reading data with foreign key to assets
- `consumption_types`: Stores available consumption types/tags
- `corrections`: Stores manual corrections applied to readings

### Consumption Types

The system handles several consumption types, identified by specific tags:

- `_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER`: Domestic hot water consumption
- `_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT`: Thermal energy for heating
- `_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL`: General energy consumption

### Data Processing Flow

1. Raw data is collected from sensors and stored in the database
2. Data is processed and aggregated into daily readings
3. Daily readings are stored in CSV files in the project-specific directories
4. The application reads these files for visualization and analysis
5. Anomaly detection is performed using thresholds from `anomaly_config.json`
6. Detected anomalies can be corrected manually, with corrections logged in `corrections_log.json`
7. Analysis results are stored in `*_analysis.json` files

### Experimental Anomaly Detection

The system includes an experimental contextual anomaly detection module in `utils/anomaly_experimental/` that:
- Uses asset-specific historical patterns to detect anomalies
- Integrates with the existing configuration in `anomaly_config.json`
- Provides visualization and analysis tools for evaluation
- Can be enabled/disabled via feature flags

Understanding this data structure is essential for developing new features, troubleshooting issues, and maintaining the application effectively. 

## Version Control and Repository Management

This project uses Git for version control. Following these guidelines will help maintain a clean and organized repository.

### Branch Strategy

We follow a simplified Git flow approach:

- `main`: Production-ready code. All code in this branch should be stable and deployable.
- `develop`: Integration branch for features. This is where features are combined and tested together.
- `feature/*`: Feature branches for new development. Create a new branch for each feature or enhancement.
- `bugfix/*`: Branches for bug fixes.
- `hotfix/*`: Emergency fixes for production issues, branched directly from `main`.

Example of creating a feature branch:
```bash
git checkout develop
git pull
git checkout -b feature/anomaly-detection-enhancement
```

### Commit Guidelines

Write clear, concise commit messages that explain the "what" and "why" of your changes:

- Use the imperative mood ("Add feature" not "Added feature")
- Keep the first line under 50 characters
- For complex changes, add a detailed description after the first line
- Reference issue numbers when applicable

Example of a good commit message:
```
Add contextual anomaly detection for thermal energy

- Implement statistical threshold calculation based on historical data
- Add visualization for detected anomalies
- Update configuration to support new detection parameters

Fixes #123
```

### Pull Request Process

1. Create a pull request from your feature branch to `develop`
2. Ensure your code passes all tests
3. Request reviews from at least one team member
4. Address review comments
5. Merge only after approval

### Version Tagging

We use semantic versioning (MAJOR.MINOR.PATCH):

- MAJOR: Incompatible API changes
- MINOR: Backwards-compatible functionality
- PATCH: Backwards-compatible bug fixes

Example of creating a version tag:
```bash
git tag -a v1.2.3 -m "Version 1.2.3 - Add anomaly detection improvements"
git push origin v1.2.3
```

### Repository Structure Maintenance

- Keep third-party libraries out of the repository; use requirements.txt instead
- Don't commit sensitive information (API keys, passwords, etc.)
- Use .gitignore to exclude unnecessary files (cache files, logs, etc.)
- Regularly clean up old branches that have been merged

### Continuous Integration

The repository is integrated with CI/CD pipelines that:

- Run automated tests on pull requests
- Check code quality and style
- Build Docker images for deployment
- Deploy to staging environments for testing

### Handling Large Files

- Avoid committing large data files to the repository
- For data files needed for testing, use a sample subset
- Consider using Git LFS for large binary files if necessary

### Documentation Updates

Always update documentation when making significant changes:

- Update README.md for user-facing changes
- Update PROJECT_CONTEXT.md for architectural changes
- Update docstrings and comments in the code
- Add examples for new features

By following these version control practices, we ensure that the project remains maintainable, the history stays clean and informative, and collaboration between team members is smooth and efficient. 