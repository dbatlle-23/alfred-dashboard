# Alfred Dashboard

Dashboard para explorar y gestionar la base de datos de Alfred.

## Características

- Exploración de tablas de base de datos PostgreSQL
- Visualización de estructura y datos de tablas
- Configuración de conexión a base de datos
- Sistema robusto de manejo de errores
- Logging avanzado con formato JSON
- Pruebas unitarias

## Requisitos

- Python 3.9+
- PostgreSQL
- Docker (opcional)

## Instalación y ejecución local

1. Clona este repositorio:
   ```
   git clone https://github.com/tu-usuario/alfred-dashboard.git
   cd alfred-dashboard
   ```

2. Crea y activa un entorno virtual:
   ```
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

4. Ejecuta la aplicación:
   ```
   python app.py
   ```

5. Accede a la aplicación en tu navegador:
   ```
   http://localhost:8050
   ```

## Instalación y ejecución con Docker

1. Construye y ejecuta el contenedor Docker:
   ```
   chmod +x build_and_run.sh
   ./build_and_run.sh
   ```

2. Accede a la aplicación en tu navegador:
   ```
   http://localhost:8050
   ```

## Configuración de la base de datos

La primera vez que ejecutes la aplicación, deberás configurar la conexión a la base de datos:

1. Navega a la sección "Configuración DB" en el menú lateral.
2. Completa los datos de conexión a tu base de datos PostgreSQL.
3. Haz clic en "Guardar Configuración".

## Desarrollo

### Estructura del proyecto

```
alfred-dashboard/
├── app.py                  # Punto de entrada de la aplicación
├── components/             # Componentes reutilizables de Dash
├── layouts/                # Layouts de las páginas
├── callbacks/              # Callbacks para la interactividad
├── utils/                  # Utilidades y funciones auxiliares
│   ├── db_utils.py         # Funciones para interactuar con la base de datos
│   ├── error_handlers.py   # Manejadores de errores
│   └── logging/            # Configuración de logging
├── config/                 # Archivos de configuración
├── assets/                 # Archivos estáticos (CSS, imágenes)
├── tests/                  # Pruebas unitarias e integración
└── logs/                   # Archivos de log generados
```

### Ejecutar pruebas

```
pytest
```

Para ver la cobertura de código:

```
pytest --cov=./ --cov-report=term-missing
```

### Formatear código

```
black .
isort .
```

### Verificar estilo de código

```
flake8
```

## Variables de entorno

- `HOST`: Host para el servidor (por defecto: 0.0.0.0)
- `PORT`: Puerto para el servidor (por defecto: 8050)
- `DASH_DEBUG`: Modo debug (por defecto: false)
- `LOG_LEVEL`: Nivel de logging general (por defecto: INFO)
- `CONSOLE_LOG_LEVEL`: Nivel de logging para consola (por defecto: INFO)
- `FILE_LOG_LEVEL`: Nivel de logging para archivo (por defecto: DEBUG)

## Detener la aplicación

Para detener la aplicación en modo local, presiona `Ctrl+C` en la terminal.

Para detener la aplicación en Docker, ejecuta:

```
docker-compose down
```
