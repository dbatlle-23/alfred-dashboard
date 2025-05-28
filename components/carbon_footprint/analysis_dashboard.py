from dash import html, dcc
import dash_bootstrap_components as dbc

def create_carbon_analysis_dashboard(data):
    """Create a dashboard for carbon footprint analysis.
    
    Args:
        data (dict): Data containing analysis results
        
    Returns:
        dash component: Dashboard for carbon footprint analysis
    """
    
    # Extracting relevant data
    total_emissions = data.get("total_emissions", 0)
    avg_emissions = data.get("average_emissions", 0)
    emission_trend = data.get("emission_trend", "stable")
    annual_estimate = data.get("annual_estimate", 0)
    
    # Determine trend color and icon
    if emission_trend == "decreasing":
        trend_color = "success"
        trend_icon = "fas fa-arrow-down"
        trend_text = "Tendencia decreciente"
    elif emission_trend == "increasing":
        trend_color = "danger"
        trend_icon = "fas fa-arrow-up"
        trend_text = "Tendencia creciente"
    else:
        trend_color = "secondary"
        trend_icon = "fas fa-equals"
        trend_text = "Tendencia estable"
    
    # Create the dashboard component
    return html.Div([
        dbc.Row([
            # Main metrics card
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Emisiones de CO2", className="bg-primary text-white"),
                    dbc.CardBody([
                        html.H3(f"{total_emissions:.1f} kg CO2", className="card-title text-center"),
                        html.P(f"Emisiones totales en el período analizado", className="card-text text-center"),
                        html.Hr(),
                        html.Div([
                            html.Span([
                                html.I(className=trend_icon, style={"margin-right": "8px"}),
                                trend_text
                            ], className=f"text-{trend_color} fw-bold")
                        ], className="text-center")
                    ])
                ], className="mb-4 shadow")
            ], width=4),
            
            # Additional metrics
            dbc.Col([
                dbc.Row([
                    # Daily average
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Promedio Diario", className="card-title text-center text-muted"),
                                html.H4(f"{avg_emissions:.1f} kg CO2/día", className="text-center")
                            ])
                        ], className="mb-3 shadow-sm")
                    ], width=12),
                    
                    # Annual projection
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Proyección Anual", className="card-title text-center text-muted"),
                                html.H4(f"{annual_estimate:.1f} kg CO2/año", className="text-center")
                            ])
                        ], className="mb-3 shadow-sm")
                    ], width=12)
                ])
            ], width=4),
            
            # Recommendations
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Acciones Recomendadas", className="bg-info text-white"),
                    dbc.CardBody([
                        html.Ul([
                            html.Li("Monitorizar el consumo en horas pico para identificar oportunidades de reducción"),
                            html.Li("Evaluar la contratación de energía renovable certificada"),
                            html.Li("Implementar medidas de eficiencia energética")
                        ])
                    ])
                ], className="shadow")
            ], width=4)
        ]),
        
        # Environmental impact section
        dbc.Card([
            dbc.CardHeader("Impacto Ambiental Equivalente", className="bg-success text-white"),
            dbc.CardBody([
                dbc.Row([
                    # Tree equivalent
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-tree fa-3x text-success mb-2"),
                            html.H5(f"{(total_emissions / 20):.1f} árboles/año", className="mb-0"),
                            html.P("Árboles necesarios para absorber estas emisiones", className="text-muted small")
                        ], className="text-center")
                    ], width=4),
                    
                    # Car equivalent
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-car fa-3x text-secondary mb-2"),
                            html.H5(f"{(total_emissions / 120):.1f} km", className="mb-0"),
                            html.P("Equivalente en kilómetros recorridos en coche", className="text-muted small")
                        ], className="text-center")
                    ], width=4),
                    
                    # Smartphone charging
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-mobile-alt fa-3x text-info mb-2"),
                            html.H5(f"{int(total_emissions * 60)} cargas", className="mb-0"),
                            html.P("Equivalente en cargas de smartphone", className="text-muted small")
                        ], className="text-center")
                    ], width=4)
                ])
            ])
        ], className="mt-4 shadow")
    ]) 