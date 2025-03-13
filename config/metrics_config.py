# Metrics configuration

# Chart settings
CHART_CONFIG = {
    'height': 400,
    'plot_bgcolor': 'white',
    'margin': {'l': 40, 'r': 40, 't': 40, 'b': 40}
}

# Table settings
TABLE_CONFIG = {
    'page_size': 15,
    'style_table': {'overflowX': 'auto'},
    'style_cell': {
        'textAlign': 'left',
        'padding': '10px',
        'whiteSpace': 'normal',
        'height': 'auto',
    },
    'style_header': {
        'backgroundColor': 'rgb(230, 230, 230)',
        'fontWeight': 'bold'
    },
    'style_data_conditional': [
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)'
        }
    ]
}

# Data processing settings
DATA_PROCESSING = {
    'max_rows': 10000,
    'date_format': '%Y-%m-%d',
    'error_threshold': 0.1
}

# Regeneration settings
REGENERATION_CONFIG = {
    'batch_size': 100,
    'timeout': 300,  # seconds
    'max_retries': 3,
    'retry_delay': 5  # seconds
}

# Modal settings
MODAL_CONFIG = {
    'size': 'xl',
    'backdrop': True,
    'keyboard': True,
    'centered': True
}

# Filter settings
FILTER_CONFIG = {
    'default_period': 'last_month',
    'date_ranges': {
        'last_month': 30,
        'last_3_months': 90,
        'last_year': 365
    }
}
