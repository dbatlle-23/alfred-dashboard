from dash import html
import dash_bootstrap_components as dbc

def create_asset_type_insights(asset_type, analysis_data):
    """
    Create contextual insights based on asset type.
    
    Args:
        asset_type (str): Type of asset ('residential_building', 'individual_home', 
                         'logistics_center', 'office_building', 'other')
        analysis_data (dict): Dictionary containing analysis results
        
    Returns:
        dash component: The insights component
    """
    # Common structure
    insights_card = dbc.Card([
        dbc.CardHeader("Insights Contextuales por Tipo de Activo"),
        dbc.CardBody([
            html.Div(id="asset-type-insights-content")
        ])
    ])
    
    # Specific insights based on asset type
    if asset_type == "residential_building":
        content = html.Div([
            html.H5("Análisis para Edificio Residencial"),
            html.P([
                "El consumo total de ", 
                html.Strong(f"{analysis_data.get('total_consumption', 0):,} m³"), 
                " para este edificio residencial representa:"
            ]),
            html.Ul([
                html.Li([
                    "Un consumo promedio de ",
                    html.Strong(f"{analysis_data.get('average_consumption', 0)} m³/día"),
                    ", lo que está dentro del rango esperado para edificios residenciales (30-50 m³/día)."
                ]),
                html.Li([
                    "Las horas pico de consumo (", 
                    html.Strong(", ".join(analysis_data.get('peak_hours', []))),
                    ") coinciden con patrones típicos de uso doméstico."
                ]),
                html.Li([
                    f"Se detectaron {analysis_data.get('anomalies', 0)} anomalías que podrían indicar fugas o usos excesivos."
                ])
            ]),
            html.P([
                html.Strong("Recomendaciones:"),
            ]),
            html.Ul([
                html.Li("Considerar la instalación de sistemas de recolección de agua de lluvia para reducir el consumo."),
                html.Li("Implementar programas de concientización para residentes sobre el uso responsable del agua."),
                html.Li("Revisar las instalaciones para identificar posibles fugas en los días con anomalías detectadas.")
            ])
        ])
    
    elif asset_type == "individual_home":
        content = html.Div([
            html.H5("Análisis para Vivienda Individual"),
            html.P([
                "El consumo total de ", 
                html.Strong(f"{analysis_data.get('total_consumption', 0):,} m³"), 
                " para esta vivienda representa:"
            ]),
            html.Ul([
                html.Li([
                    "Un consumo promedio de ",
                    html.Strong(f"{analysis_data.get('average_consumption', 0)} m³/día"),
                    ", lo que está por encima del promedio para una vivienda individual (0.5-1.5 m³/día)."
                ]),
                html.Li([
                    "Las horas pico de consumo (", 
                    html.Strong(", ".join(analysis_data.get('peak_hours', []))),
                    ") son consistentes con actividades matutinas y vespertinas en el hogar."
                ]),
                html.Li([
                    f"Se detectaron {analysis_data.get('anomalies', 0)} anomalías que requieren atención."
                ])
            ]),
            html.P([
                html.Strong("Recomendaciones:"),
            ]),
            html.Ul([
                html.Li("Instalar dispositivos de ahorro de agua en grifos y duchas."),
                html.Li("Revisar el sistema de riego si existe jardín, ya que podría ser responsable del alto consumo."),
                html.Li("Verificar posibles fugas en cisternas de baños y conexiones de electrodomésticos.")
            ])
        ])
    
    elif asset_type == "logistics_center":
        content = html.Div([
            html.H5("Análisis para Centro Logístico"),
            html.P([
                "El consumo total de ", 
                html.Strong(f"{analysis_data.get('total_consumption', 0):,} m³"), 
                " para este centro logístico representa:"
            ]),
            html.Ul([
                html.Li([
                    "Un consumo promedio de ",
                    html.Strong(f"{analysis_data.get('average_consumption', 0)} m³/día"),
                    ", lo que es típico para operaciones logísticas de este tamaño."
                ]),
                html.Li([
                    "Las horas pico de consumo (", 
                    html.Strong(", ".join(analysis_data.get('peak_hours', []))),
                    ") coinciden con los horarios de mayor actividad operativa."
                ]),
                html.Li([
                    f"Se detectaron {analysis_data.get('anomalies', 0)} anomalías que podrían relacionarse con procesos industriales específicos."
                ])
            ]),
            html.P([
                html.Strong("Recomendaciones:"),
            ]),
            html.Ul([
                html.Li("Implementar sistemas de recirculación de agua para procesos industriales."),
                html.Li("Evaluar la posibilidad de recolección y tratamiento de aguas grises para reutilización."),
                html.Li("Realizar auditorías periódicas de consumo de agua para identificar oportunidades de mejora.")
            ])
        ])
    
    elif asset_type == "office_building":
        content = html.Div([
            html.H5("Análisis para Edificio de Oficinas"),
            html.P([
                "El consumo total de ", 
                html.Strong(f"{analysis_data.get('total_consumption', 0):,} m³"), 
                " para este edificio de oficinas representa:"
            ]),
            html.Ul([
                html.Li([
                    "Un consumo promedio de ",
                    html.Strong(f"{analysis_data.get('average_consumption', 0)} m³/día"),
                    ", lo que está dentro del rango esperado para edificios de oficinas de este tamaño."
                ]),
                html.Li([
                    "Las horas pico de consumo (", 
                    html.Strong(", ".join(analysis_data.get('peak_hours', []))),
                    ") coinciden con el horario laboral principal."
                ]),
                html.Li([
                    f"Se detectaron {analysis_data.get('anomalies', 0)} anomalías que merecen atención."
                ])
            ]),
            html.P([
                html.Strong("Recomendaciones:"),
            ]),
            html.Ul([
                html.Li("Instalar grifos con sensores en baños para reducir el desperdicio."),
                html.Li("Implementar sistemas de refrigeración eficientes en el uso de agua."),
                html.Li("Desarrollar campañas de concientización sobre el uso del agua entre empleados.")
            ])
        ])
    
    else:  # Default case for 'other'
        content = html.Div([
            html.H5("Análisis General"),
            html.P([
                "El consumo total de ", 
                html.Strong(f"{analysis_data.get('total_consumption', 0):,} m³"), 
                " para este activo representa:"
            ]),
            html.Ul([
                html.Li([
                    "Un consumo promedio de ",
                    html.Strong(f"{analysis_data.get('average_consumption', 0)} m³/día"),
                ]),
                html.Li([
                    "Las horas pico de consumo son: ", 
                    html.Strong(", ".join(analysis_data.get('peak_hours', [])))
                ]),
                html.Li([
                    f"Se detectaron {analysis_data.get('anomalies', 0)} anomalías que podrían indicar consumos inusuales."
                ])
            ]),
            html.P([
                html.Strong("Recomendaciones:"),
            ]),
            html.Ul([
                html.Li("Realizar un análisis detallado del patrón de consumo para establecer una línea base."),
                html.Li("Implementar medidores adicionales para segmentar el consumo por áreas o usos."),
                html.Li("Considerar una auditoría especializada de consumo de agua.")
            ])
        ])
    
    # Update the card content
    insights_card.children[1].children = content
    
    return insights_card 