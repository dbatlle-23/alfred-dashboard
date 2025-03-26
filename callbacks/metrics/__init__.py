from callbacks.metrics.table_callbacks import register_table_callbacks
from callbacks.metrics.filter_callbacks import register_filter_callbacks
from callbacks.metrics.chart_callbacks import register_chart_callbacks
from callbacks.metrics.metrics_callbacks import register_metrics_callbacks
from callbacks.metrics.modal_callbacks import register_modal_callbacks
from callbacks.metrics.anomaly_indicator_callbacks import register_anomaly_indicator_callbacks
from callbacks.metrics.loading_callbacks import register_loading_callbacks
from components.metrics.asset_detail_modal import register_asset_detail_modal_callbacks

def register_callbacks(app):
    """Register all metrics callbacks."""
    register_filter_callbacks(app)
    register_chart_callbacks(app)
    register_metrics_callbacks(app)
    register_table_callbacks(app)
    register_modal_callbacks(app)
    register_anomaly_indicator_callbacks(app)
    register_loading_callbacks(app)
    register_asset_detail_modal_callbacks(app)
