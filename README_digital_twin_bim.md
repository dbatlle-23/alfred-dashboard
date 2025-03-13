# Digital Twin BIM con Three.js en Dash

Este proyecto demuestra cómo integrar un Digital Twin basado en Three.js en una aplicación Dash para visualizar modelos BIM (Building Information Modeling).

## ¿Qué es BIM?

BIM (Building Information Modeling) es una metodología de trabajo colaborativa para la creación y gestión de proyectos de construcción. A diferencia de los modelos 3D tradicionales, los modelos BIM contienen información detallada sobre la estructura, materiales, sistemas y componentes de un edificio, lo que permite una visualización y análisis más completos.

## Estructura del Proyecto

```
├── digital_twin_bim_example.py    # Ejemplo de integración de Digital Twin BIM
├── components/
│   └── digital_twin_bim_iframe.py # Componente para el método IFrame con BIM
├── assets/
│   └── digital_twin_bim.html      # Archivo HTML para visualizar modelos BIM
└── README_digital_twin_bim.md     # Este archivo
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
python digital_twin_bim_example.py
```

Esto iniciará un servidor local en `http://127.0.0.1:8050/` donde podrás ver la aplicación.

## Funcionalidades

### Visualización de Modelos BIM

El Digital Twin BIM permite visualizar modelos 3D en los siguientes formatos:

- **GLTF/GLB**: Formatos estándar para modelos 3D en la web
- **IFC**: Formato estándar para modelos BIM (requiere carga adicional de bibliotecas)

### Controles de Navegación

El visor 3D incluye los siguientes controles:

- **Rotación**: Haz clic y arrastra para rotar la vista
- **Zoom**: Usa la rueda del ratón para acercar o alejar
- **Movimiento**: Mantén presionada la tecla Shift y arrastra para mover la vista

### Carga de Modelos

Puedes cargar modelos BIM de dos formas:

1. **URL directa**: Introduce la URL de un modelo GLTF, GLB o IFC
2. **Modelos de ejemplo**: Selecciona uno de los modelos predefinidos

## Personalización

### Añadir Modelos de Ejemplo

Para añadir más modelos de ejemplo, modifica el array `options` en el componente `dcc.Dropdown` en el archivo `components/digital_twin_bim_iframe.py`:

```python
dcc.Dropdown(
    id="model-examples-dropdown",
    options=[
        {"label": "Tokyo (GLTF)", "value": "https://threejs.org/examples/models/gltf/LittlestTokyo.glb"},
        {"label": "Edificio de Oficinas (GLTF)", "value": "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/OfficeBuilding/glTF/OfficeBuilding.gltf"},
        # Añade más modelos aquí
    ],
    placeholder="Selecciona un modelo de ejemplo",
    style={"width": "100%"}
)
```

### Personalizar el Visor 3D

Para personalizar el visor 3D, puedes modificar el archivo `assets/digital_twin_bim.html`. Algunas personalizaciones comunes incluyen:

- **Cambiar el color de fondo**: Modifica `scene.background = new THREE.Color(0x333333);`
- **Ajustar la iluminación**: Modifica los parámetros de `ambientLight` y `directionalLight`
- **Añadir más controles**: Implementa funciones adicionales como selección de objetos, mediciones, etc.

## Integración con Datos

### Comunicación entre Dash y el Digital Twin

Para comunicar datos desde Dash al Digital Twin, puedes utilizar el parámetro de URL o mensajes entre ventanas:

#### Usando Parámetros de URL

El visor 3D está configurado para leer el parámetro `model` de la URL:

```python
@app.callback(
    Output(iframe_id, "src"),
    Input(store_id, "data"),
    prevent_initial_call=True
)
def update_iframe(model_url):
    if model_url:
        return f"/assets/digital_twin_bim.html?model={model_url}&t={int(time.time())}"
    return "/assets/digital_twin_bim.html"
```

#### Usando Mensajes entre Ventanas

También puedes enviar mensajes directamente al IFrame:

```javascript
// En JavaScript del lado del cliente
const iframe = document.getElementById('digital-twin-bim-iframe');
iframe.contentWindow.postMessage({modelUrl: 'nueva_url_del_modelo'}, '*');
```

## Recursos Adicionales

- [Documentación de Three.js](https://threejs.org/docs/)
- [Documentación de Dash](https://dash.plotly.com/)
- [Ejemplos de Three.js](https://threejs.org/examples/)
- [Modelos GLTF de ejemplo](https://github.com/KhronosGroup/glTF-Sample-Models)
- [Información sobre BIM](https://www.autodesk.com/solutions/bim)

## Limitaciones y Consideraciones

- **Tamaño de los modelos**: Los modelos BIM pueden ser muy grandes. Considera optimizarlos antes de cargarlos en el navegador.
- **Compatibilidad del navegador**: WebGL es necesario para Three.js. Asegúrate de que los usuarios tengan navegadores compatibles.
- **Seguridad**: Si cargas modelos desde URLs externas, asegúrate de que sean fuentes confiables.
- **Rendimiento**: La visualización de modelos complejos puede afectar el rendimiento. Considera implementar técnicas de nivel de detalle (LOD) para modelos grandes. 