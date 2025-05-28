from dash import html
import dash_bootstrap_components as dbc

def create_asset_type_insights(asset_type, data):
    """Create context-aware insights based on asset type for carbon footprint.
    
    Args:
        asset_type (str): Type of asset (residential_building, individual_home, etc.)
        data (dict): Data from the analysis, containing total_emissions, average_emissions, etc.
    
    Returns:
        dash component: Card component with insights
    """
    
    total_emissions = data.get("total_emissions", 0)
    average_emissions = data.get("average_emissions", 0)
    peak_hours = data.get("peak_hours", ["N/A"])
    anomalies = data.get("anomalies", 0)
    
    if asset_type == "residential_building":
        title = "Insights para Edificio Residencial"
        insights = [
            html.P(f"El edificio residencial ha generado un total de {total_emissions:.1f} kg CO2 en el período analizado."),
            html.P(f"Con una media de {average_emissions:.1f} kg CO2/día, este consumo está dentro del rango esperado para edificios residenciales de este tamaño."),
            html.P("Las horas pico de emisiones coinciden con los picos de actividad doméstica."),
            html.P(f"Se han detectado {anomalies} anomalías que podrían indicar un uso energético ineficiente."),
            html.H5("Recomendaciones:", className="mt-3"),
            html.Ul([
                html.Li("Considerar mejoras en la envolvente térmica del edificio para reducir necesidades de climatización."),
                html.Li("Evaluar la posibilidad de instalar sistemas de generación renovable (paneles solares)."),
                html.Li("Implementar sistemas automáticos de control para apagar equipos no esenciales en horas no laborables."),
                html.Li("Educar a los residentes sobre prácticas para reducir el consumo eléctrico.")
            ])
        ]
    elif asset_type == "individual_home":
        title = "Insights para Vivienda Individual"
        insights = [
            html.P(f"La vivienda ha generado un total de {total_emissions:.1f} kg CO2 en el período analizado."),
            html.P(f"Con una media de {average_emissions:.1f} kg CO2/día, este nivel es {'alto' if average_emissions > 15 else 'moderado' if average_emissions > 8 else 'bajo'} para una vivienda individual."),
            html.P("Las emisiones se concentran principalmente en las horas de mañana y tarde-noche."),
            html.P(f"Se detectaron {anomalies} anomalías en el período analizado."),
            html.H5("Recomendaciones:", className="mt-3"),
            html.Ul([
                html.Li("Sustituir electrodomésticos por modelos de alta eficiencia energética."),
                html.Li("Mejorar el aislamiento de puertas y ventanas para reducir pérdidas térmicas."),
                html.Li("Considerar la instalación de termostatos inteligentes para optimizar la climatización."),
                html.Li("Evaluar la contratación de energía con certificación de origen renovable.")
            ])
        ]
    elif asset_type == "logistics_center":
        title = "Insights para Centro Logístico"
        insights = [
            html.P(f"El centro logístico ha generado un total de {total_emissions:.1f} kg CO2 en el período analizado."),
            html.P(f"Con una media de {average_emissions:.1f} kg CO2/día, este consumo energético es {'elevado pero dentro de parámetros típicos' if average_emissions > 200 else 'eficiente para este tipo de instalación'}."),
            html.P("Las emisiones tienen una correlación directa con los horarios de operación logística."),
            html.P(f"Se detectaron {anomalies} anomalías que requieren análisis adicional."),
            html.H5("Recomendaciones:", className="mt-3"),
            html.Ul([
                html.Li("Optimizar los sistemas de iluminación con sensores de presencia y tecnología LED."),
                html.Li("Evaluar la implementación de un sistema de gestión energética certificado (ISO 50001)."),
                html.Li("Considerar sistemas de recuperación de calor para procesos industriales."),
                html.Li("Analizar la posibilidad de implementar fuentes renovables para cubrir parte del consumo.")
            ])
        ]
    elif asset_type == "office_building":
        title = "Insights para Edificio de Oficinas"
        insights = [
            html.P(f"El edificio de oficinas ha generado un total de {total_emissions:.1f} kg CO2 en el período analizado."),
            html.P(f"Con una media de {average_emissions:.1f} kg CO2/día, estas emisiones son {'superiores' if average_emissions > 150 else 'acordes'} al benchmark para edificios de oficinas similares."),
            html.P("Las horas de mayor emisión corresponden al horario laboral principal."),
            html.P(f"Se han detectado {anomalies} patrones anómalos que podrían indicar ineficiencias."),
            html.H5("Recomendaciones:", className="mt-3"),
            html.Ul([
                html.Li("Implementar políticas de apagado automático de equipos fuera del horario laboral."),
                html.Li("Optimizar los sistemas de climatización mediante zonificación y programación horaria."),
                html.Li("Considerar la instalación de sistemas de monitorización energética a nivel de planta o departamento."),
                html.Li("Evaluar la certificación de eficiencia energética del edificio (LEED, BREEAM).")
            ])
        ]
    else:  # other
        title = "Insights Generales sobre Huella de Carbono"
        insights = [
            html.P(f"Este activo ha generado un total de {total_emissions:.1f} kg CO2 en el período analizado."),
            html.P(f"Con una media diaria de {average_emissions:.1f} kg CO2, es importante evaluar si este nivel es adecuado para el tipo de uso del activo."),
            html.P("Un análisis más detallado por tipo de activo permitiría establecer objetivos específicos de reducción."),
            html.P(f"Se han detectado {anomalies} anomalías que merecen una investigación adicional."),
            html.H5("Recomendaciones Generales:", className="mt-3"),
            html.Ul([
                html.Li("Realizar una auditoría energética para identificar oportunidades de mejora."),
                html.Li("Implementar un sistema de monitorización continua del consumo energético."),
                html.Li("Evaluar la sustitución de equipos ineficientes."),
                html.Li("Considerar la contratación de energía de origen renovable certificado.")
            ])
        ]
    
    return dbc.Card([
        dbc.CardHeader(title, className="text-primary"),
        dbc.CardBody(insights)
    ], className="mb-4") 