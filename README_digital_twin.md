# Integración de Digital Twin con Three.js en Dash

Este proyecto demuestra cómo integrar un Digital Twin basado en Three.js en una aplicación Dash. Se presentan dos métodos diferentes de integración:

1. **Método IFrame**: Carga un archivo HTML independiente con Three.js en un IFrame de Dash.
2. **Método Directo**: Incrusta Three.js directamente en la página de Dash mediante archivos JavaScript en la carpeta assets.

## Estructura del Proyecto

```
├── app.py                     # Aplicación principal de Dash (existente)
├── digital_twin_example.py    # Ejemplo de integración de Digital Twin
├── components/
│   ├── digital_twin_iframe.py # Componente para el método IFrame
│   └── digital_twin_direct.py # Componente para el método directo
├── assets/
│   ├── digital_twin.html      # Archivo HTML para el método IFrame
│   └── threejs_script.js      # Script de Three.js para el método directo
└── README_digital_twin.md     # Este archivo
```

## Requisitos

Para ejecutar este ejemplo, necesitas tener instalado:

```
dash==2.9.3
dash-bootstrap-components==1.4.1
```

Puedes instalar estas dependencias con:

```bash
pip install dash dash-bootstrap-components
```

## Ejecución del Ejemplo

Para ejecutar el ejemplo, simplemente ejecuta:

```bash
python digital_twin_example.py
```

Esto iniciará un servidor local en `http://127.0.0.1:8050/` donde podrás ver la aplicación.

## Métodos de Integración

### Método IFrame

Este método utiliza un componente IFrame de Dash para cargar un archivo HTML independiente que contiene el código de Three.js. El archivo HTML se encuentra en la carpeta 'assets' y se carga automáticamente.

**Ventajas:**
- Separación clara entre el código de Dash y el código de Three.js
- Fácil de implementar y mantener
- Evita conflictos entre las bibliotecas JavaScript
- El archivo HTML puede ser desarrollado y probado de forma independiente

**Desventajas:**
- Comunicación limitada entre Dash y Three.js
- Puede haber problemas de rendimiento al cargar el IFrame
- Dificultad para pasar datos dinámicos desde Dash al modelo 3D

### Método Directo

Este método carga Three.js directamente en la página de Dash y utiliza un archivo JavaScript en la carpeta 'assets' para inicializar y controlar el modelo 3D. Dash carga automáticamente todos los archivos JavaScript y CSS de la carpeta 'assets'.

**Ventajas:**
- Mejor integración con Dash y sus componentes
- Posibilidad de comunicación bidireccional entre Dash y Three.js
- Mejor rendimiento al evitar el uso de IFrames
- Facilidad para actualizar el modelo 3D con datos dinámicos

**Desventajas:**
- Mayor complejidad en la implementación
- Posibles conflictos con otras bibliotecas JavaScript
- Requiere conocimientos más avanzados de JavaScript y Three.js

## Personalización

### Personalizar el Modelo 3D

Para personalizar el modelo 3D, puedes modificar los archivos `digital_twin.html` o `threejs_script.js` según el método que estés utilizando. Puedes cambiar la geometría, los materiales, las luces, etc.

### Comunicación entre Dash y Three.js

#### Método IFrame

Para comunicar datos desde Dash al IFrame, puedes utilizar mensajes entre ventanas (window.postMessage). Por ejemplo:

```javascript
// En Dash (JavaScript del lado del cliente)
const iframe = document.getElementById('digital-twin-iframe');
iframe.contentWindow.postMessage({data: 'some data'}, '*');

// En el IFrame (digital_twin.html)
window.addEventListener('message', function(event) {
    console.log('Received data:', event.data);
    // Actualizar el modelo 3D con los datos recibidos
});
```

#### Método Directo

Para comunicar datos desde Dash al modelo 3D directamente, puedes utilizar callbacks de Dash para actualizar propiedades de elementos HTML y luego acceder a esos elementos desde el script de Three.js:

```python
# En Dash
@app.callback(
    Output('threejs-data', 'data-value'),
    Input('some-input', 'value')
)
def update_threejs_data(value):
    return value
```

```javascript
// En threejs_script.js
document.addEventListener('DOMContentLoaded', function() {
    const dataElement = document.getElementById('threejs-data');
    
    // Observar cambios en el atributo data-value
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === 'data-value') {
                const value = dataElement.getAttribute('data-value');
                console.log('Data updated:', value);
                // Actualizar el modelo 3D con los datos recibidos
            }
        });
    });
    
    observer.observe(dataElement, { attributes: true });
});
```

## Recursos Adicionales

- [Documentación de Three.js](https://threejs.org/docs/)
- [Documentación de Dash](https://dash.plotly.com/)
- [Ejemplos de Three.js](https://threejs.org/examples/) 