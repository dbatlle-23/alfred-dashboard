# Changelog

Todos los cambios notables en el proyecto Alfred Dashboard se documentarán en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2024-03-17

### Cambiado
- Factor de emisión para electricidad actualizado de 0.25 kg CO₂/kWh (2022) a 0.108 kg CO₂/kWh (2024) en `utils/carbon_footprint/analysis.py`, reflejando datos más precisos del mix eléctrico español actual.

### Arreglado
- Solucionado problema con timestamps futuros que resultaba en "0 diferencias de consumo" con las siguientes mejoras:
  - Ampliación del rango de fechas aceptado con un buffer de 2 años
  - Mejora en el procesamiento de datos para aceptar claves 'v' y 'value' en los puntos de datos
  - Ordenamiento automático de puntos por timestamp para cálculos cronológicamente correctos
  - Implementación de método de fallback usando la diferencia total entre primera y última lectura
  - Aumento del umbral de filtrado para diferencias anómalas de 100 a 1000

### Documentación
- Actualizado README.md con información sobre nuevas características y módulos
- Añadido CHANGELOG.md para seguimiento de cambios en el proyecto

## [1.1.0] - 2024-02-15

### Añadido
- Módulo de análisis de huella de carbono para visualizar y analizar emisiones de CO2
- Nuevos gráficos y visualizaciones para análisis de tendencias
- Capacidad de filtrado avanzado por fechas en módulo de métricas

### Mejorado
- Rendimiento en la carga de datos de consumo para activos con muchas lecturas
- Interfaz de usuario para selección de fechas

## [1.0.0] - 2024-01-10

### Añadido
- Versión inicial estable con análisis de consumo de agua
- Sistema de autenticación basado en JWT
- Explorador de base de datos
- Visualización de métricas básicas
- Sistema de detección de anomalías 