# Alfred Dashboard

Dashboard para visualización y análisis de datos de Alfred Smart.

## Autenticación con JWT

El dashboard implementa un sistema de autenticación basado en tokens JWT (JSON Web Tokens) para gestionar las sesiones de usuario de forma segura y aislada. Cada navegador o pestaña mantiene su propia sesión independiente.

### Características principales

- **Tokens JWT**: Cada sesión genera un token JWT único que se almacena en el navegador.
- **Almacenamiento por sesión**: Los tokens se guardan en `dcc.Store(storage_type="session")`, lo que garantiza que cada pestaña tenga su propia sesión.
- **Logout independiente**: Al cerrar sesión en una pestaña, solo se elimina el token de esa pestaña, sin afectar a otras sesiones activas.
- **Verificación de tokens**: En cada solicitud se verifica la validez del token JWT.
- **Seguridad mejorada**: Los tokens tienen tiempo de expiración y se validan en cada operación.

### Flujo de autenticación

1. **Login**: El usuario ingresa sus credenciales, que se envían al backend.
2. **Generación de token**: El servidor valida las credenciales y genera un token JWT.
3. **Almacenamiento**: El token se guarda en `dcc.Store` con `storage_type="session"`.
4. **Verificación**: En cada cambio de página o solicitud a la API, se verifica la validez del token.
5. **Logout**: Al cerrar sesión, se elimina el token de la pestaña actual sin afectar otras sesiones.

### Mensajes de log durante la inicialización

Durante la inicialización de la aplicación o cuando se carga una nueva pestaña, es normal ver mensajes en los logs como:

```
No se proporcionó token JWT para obtener clientes
No se proporcionó token JWT para obtener proyectos
```

Estos mensajes son informativos y no indican un error. Ocurren porque:

1. Los componentes (como el selector de clientes) intentan cargar datos al inicializarse
2. En ese momento, el usuario aún no ha iniciado sesión, por lo que no hay token JWT disponible
3. La aplicación maneja correctamente esta situación mostrando opciones por defecto
4. Una vez que el usuario inicia sesión, los componentes se actualizan con datos reales

Este comportamiento es parte del diseño normal de la aplicación y no requiere ninguna acción correctiva.

### Implementación técnica

- `utils/auth.py`: Servicio de autenticación que maneja la generación y verificación de tokens JWT.
- `app.py`: Configuración principal de la aplicación con el store para el token JWT.
- `layouts/login.py`: Manejo del proceso de login y almacenamiento del token.
- `components/navbar.py`: Implementación del logout que solo afecta a la pestaña actual.

## Instalación

Para instalar las dependencias necesarias:

```bash
pip install -r requirements.txt
```

## Ejecución

Para ejecutar la aplicación:

```bash
python app.py
```

Por defecto, la aplicación se ejecutará en `http://0.0.0.0:8050`.

## Configuración

La aplicación puede configurarse mediante variables de entorno:

- `HOST`: Host en el que se ejecutará la aplicación (por defecto: `0.0.0.0`)
- `PORT`: Puerto en el que se ejecutará la aplicación (por defecto: `8050`)
- `DASH_DEBUG`: Modo debug (`true` o `false`, por defecto: `false`)
- `JWT_SECRET_KEY`: Clave secreta para firmar los tokens JWT (por defecto: `alfred-dashboard-secret-key`)

## Estructura del proyecto

- `app.py`: Punto de entrada principal de la aplicación
- `assets/`: Archivos estáticos (CSS, imágenes, etc.)
- `components/`: Componentes reutilizables de la interfaz
- `layouts/`: Layouts para las diferentes páginas
- `utils/`: Utilidades y servicios
- `config/`: Archivos de configuración
- `logs/`: Logs de la aplicación

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
