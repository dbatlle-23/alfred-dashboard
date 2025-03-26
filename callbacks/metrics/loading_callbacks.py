from dash import Output, Input, State, callback_context, no_update, dcc
import dash
from dash import html
import dash_bootstrap_components as dbc
import time

def register_loading_callbacks(app):
    """Register callbacks for loading toasts and indicators."""
    
    # We'll add these stores to track button click times
    app.layout.children.append(dcc.Store(id="visualize-button-click-time"))
    app.layout.children.append(dcc.Store(id="update-button-click-time"))
    
    # Add an interval component to check for timeouts
    app.layout.children.append(dcc.Interval(
        id="button-timeout-checker",
        interval=5000,  # 5 seconds
        n_intervals=0
    ))
    
    # Callback to show the processing alert notification
    @app.callback(
        Output("processing-notification", "is_open", allow_duplicate=True),
        [Input("metrics-analyze-button", "n_clicks"),
         Input("metrics-update-readings-button", "n_clicks")],
        prevent_initial_call=True
    )
    def show_processing_notification(analyze_clicks, update_clicks):
        """Show processing notification when any action button is clicked."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update
            
        # If either button was clicked, show the notification
        if ctx.triggered[0]["prop_id"].split(".")[0] in ["metrics-analyze-button", "metrics-update-readings-button"]:
            return True
        return no_update
    
    # Callback to hide the processing alert notification
    @app.callback(
        Output("processing-notification", "is_open", allow_duplicate=True),
        [Input("metrics-data-store", "data"),
         Input("metrics-update-readings-result", "children")],
        prevent_initial_call=True
    )
    def hide_processing_notification(data, update_result):
        """Hide processing notification when data is loaded or update completes."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update
            
        # If either action completes, hide the notification
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if (trigger_id == "metrics-data-store") or (trigger_id == "metrics-update-readings-result"):
            return False
        return no_update
    
    # Callback to show the visualization loading toast
    @app.callback(
        Output("visualize-loading-notification", "is_open", allow_duplicate=True),
        [Input("metrics-analyze-button", "n_clicks")],
        prevent_initial_call=True
    )
    def show_visualize_loading(n_clicks):
        """Show loading toast when analyze button is clicked."""
        if n_clicks:
            return True
        return no_update
    
    # Callback to hide the visualization loading toast
    @app.callback(
        Output("visualize-loading-notification", "is_open", allow_duplicate=True),
        [Input("metrics-data-store", "data")],
        prevent_initial_call=True
    )
    def hide_visualize_loading(data):
        """Hide loading toast when data is loaded."""
        return False
    
    # Callback to show the update readings loading toast
    @app.callback(
        Output("update-loading-notification", "is_open", allow_duplicate=True),
        [Input("metrics-update-readings-button", "n_clicks")],
        prevent_initial_call=True
    )
    def show_update_loading(n_clicks):
        """Show loading toast when update button is clicked."""
        if n_clicks:
            return True
        return no_update
    
    # Callback to hide the update readings loading toast
    @app.callback(
        Output("update-loading-notification", "is_open", allow_duplicate=True),
        [Input("metrics-update-readings-result", "children")],
        prevent_initial_call=True
    )
    def hide_update_loading(result):
        """Hide loading toast when update results are available."""
        return False
    
    # Store the time when the visualize button is clicked
    @app.callback(
        Output("visualize-button-click-time", "data"),
        [Input("metrics-analyze-button", "n_clicks")],
        prevent_initial_call=True
    )
    def store_visualize_click_time(n_clicks):
        """Store the time when the visualize button is clicked."""
        if n_clicks:
            return {"time": time.time(), "n_clicks": n_clicks}
        return no_update
    
    # Store the time when the update button is clicked
    @app.callback(
        Output("update-button-click-time", "data"),
        [Input("metrics-update-readings-button", "n_clicks")],
        prevent_initial_call=True
    )
    def store_update_click_time(n_clicks):
        """Store the time when the update button is clicked."""
        if n_clicks:
            return {"time": time.time(), "n_clicks": n_clicks}
        return no_update
    
    @app.callback(
        Output("metrics-analyze-button", "children"),
        [Input("metrics-analyze-button", "n_clicks"),
         Input("metrics-data-store", "data"),
         Input("button-timeout-checker", "n_intervals")],
        [State("visualize-button-click-time", "data")],
        prevent_initial_call=True
    )
    def update_visualize_button_text(n_clicks, data, n_intervals, click_time_data):
        """Update the visualize button text to indicate loading state."""
        ctx = callback_context
        if not ctx.triggered:
            return "Visualizar Consumos"
            
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Show loading indicator when button is clicked
        if trigger_id == "metrics-analyze-button" and n_clicks:
            return html.Div([
                dbc.Spinner(size="sm", color="white", spinner_class_name="me-2"),
                "Procesando..."
            ], className="d-flex align-items-center")
        
        # Reset button text when data store is updated (regardless of content)
        elif trigger_id == "metrics-data-store":
            # We reset the button whenever the data store is updated, even with empty data
            return "Visualizar Consumos"
        
        # Handle timeout - reset button after 30 seconds if still processing
        elif trigger_id == "button-timeout-checker" and click_time_data:
            current_time = time.time()
            click_time = click_time_data.get("time", 0)
            button_clicks = click_time_data.get("n_clicks", 0)
            
            # Only timeout if this matches the last button click and 30 seconds have passed
            if button_clicks == n_clicks and current_time - click_time > 30:
                print(f"Timeout detected for visualize button after {current_time - click_time:.1f} seconds")
                return "Visualizar Consumos"
            
        return "Visualizar Consumos"
    
    @app.callback(
        Output("metrics-update-readings-button", "children"),
        [Input("metrics-update-readings-button", "n_clicks"),
         Input("metrics-update-readings-result", "children"),
         Input("button-timeout-checker", "n_intervals")],
        [State("update-button-click-time", "data")],
        prevent_initial_call=True
    )
    def update_readings_button_text(n_clicks, result, n_intervals, click_time_data):
        """Update the update readings button text to indicate loading state."""
        ctx = callback_context
        if not ctx.triggered:
            return "Actualizar Lecturas"
            
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Show loading indicator when button is clicked
        if trigger_id == "metrics-update-readings-button" and n_clicks:
            return html.Div([
                dbc.Spinner(size="sm", color="white", spinner_class_name="me-2"),
                "Actualizando..."
            ], className="d-flex align-items-center")
        
        # Reset button text when results are available (regardless of content)
        elif trigger_id == "metrics-update-readings-result":
            # We reset the button whenever the result is updated, even if it's an error message
            return "Actualizar Lecturas"
        
        # Handle timeout - reset button after 30 seconds if still processing
        elif trigger_id == "button-timeout-checker" and click_time_data:
            current_time = time.time()
            click_time = click_time_data.get("time", 0)
            button_clicks = click_time_data.get("n_clicks", 0)
            
            # Only timeout if this matches the last button click and 30 seconds have passed
            if button_clicks == n_clicks and current_time - click_time > 30:
                print(f"Timeout detected for update button after {current_time - click_time:.1f} seconds")
                return "Actualizar Lecturas"
            
        return "Actualizar Lecturas"
    
    # Callback to update the processing notification text
    @app.callback(
        Output("processing-notification", "children"),
        [Input("metrics-analyze-button", "n_clicks"),
         Input("metrics-update-readings-button", "n_clicks")],
        prevent_initial_call=True
    )
    def update_processing_text(analyze_clicks, update_clicks):
        """Update processing notification text based on which action is happening."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "metrics-analyze-button":
            return html.Div([
                dbc.Spinner(type="grow", size="sm", color="primary", spinner_class_name="me-2"),
                html.Span("Cargando y procesando datos de consumo...", className="ms-2")
            ], className="d-flex align-items-center")
        elif trigger_id == "metrics-update-readings-button":
            return html.Div([
                dbc.Spinner(type="grow", size="sm", color="primary", spinner_class_name="me-2"),
                html.Span("Actualizando lecturas de consumo...", className="ms-2")
            ], className="d-flex align-items-center")
        
        return no_update 