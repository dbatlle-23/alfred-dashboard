# 🚀 Guía de Deployment en Railway

## Pre-requisitos

1. **Cuenta en Railway**: [railway.app](https://railway.app)
2. **Repositorio Git**: Tu código debe estar en GitHub, GitLab o Bitbucket
3. **Variables de entorno configuradas** (ver sección Variables de Entorno)

## Pasos para Deployment

### 1. Preparación del repositorio

Asegúrate de que tu repositorio tenga los siguientes archivos:
- ✅ `Dockerfile`
- ✅ `requirements.txt`
- ✅ `railway.json`
- ✅ `Procfile` (respaldo)
- ✅ `env.example` (guía de variables)

### 2. Crear proyecto en Railway

1. Ve a [railway.app](https://railway.app)
2. Inicia sesión con GitHub
3. Haz clic en "New Project"
4. Selecciona "Deploy from GitHub repo"
5. Autoriza Railway para acceder a tu repositorio
6. Selecciona tu repositorio `AlfredDashboard`

### 3. Configurar variables de entorno

En Railway dashboard > Settings > Variables:

#### Variables obligatorias:
```bash
HOST=0.0.0.0
PORT=$PORT  # Railway automáticamente asigna este valor
DASH_DEBUG=false
JWT_SECRET_KEY=genera_una_clave_secreta_fuerte_aqui
```

#### Variables de API (configura según tu Alfred Smart API):
```bash
API_BASE_URL=https://tu-alfred-smart-api.com
API_USERNAME=tu_usuario
API_PASSWORD=tu_password
```

#### Variables opcionales:
```bash
LOG_LEVEL=INFO
CONSOLE_LOG_LEVEL=INFO
FILE_LOG_LEVEL=DEBUG
PYTHONUNBUFFERED=1
TZ=Europe/Madrid
```

### 4. Añadir base de datos (opcional)

Si necesitas PostgreSQL:
1. En Railway dashboard, haz clic en "New"
2. Selecciona "Database" > "PostgreSQL"
3. Railway automáticamente creará la variable `DATABASE_URL`

### 5. Configurar dominio

Railway te proporcionará una URL automática como:
`https://tu-app-production.up.railway.app`

Para dominio personalizado:
1. Ve a Settings > Domains
2. Añade tu dominio personalizado
3. Configura los registros DNS según las instrucciones

## Estructura de archivos para Railway

```
alfred-dashboard/
├── railway.json          # Configuración específica de Railway
├── Procfile             # Comando de inicio (respaldo)
├── Dockerfile           # Contenedor principal
├── requirements.txt     # Dependencias Python
├── app.py              # Aplicación principal (con server = app.server)
├── env.example         # Ejemplo de variables de entorno
└── ...resto del proyecto
```

## Variables de entorno detalladas

### Variables del servidor
- `HOST`: Siempre `0.0.0.0` para Railway
- `PORT`: Railway la asigna automáticamente, usa `$PORT`
- `DASH_DEBUG`: `false` en producción

### Variables de autenticación
- `JWT_SECRET_KEY`: Clave secreta para tokens JWT (¡CRÍTICA!)

### Variables de base de datos
- `DATABASE_URL`: Auto-generada si añades PostgreSQL en Railway

### Variables de logging
- `LOG_LEVEL`: Nivel general de logs (`INFO`, `DEBUG`, `WARNING`, `ERROR`)
- `CONSOLE_LOG_LEVEL`: Nivel para logs en consola
- `FILE_LOG_LEVEL`: Nivel para logs en archivo

## Comandos de Railway CLI (opcional)

Instalar Railway CLI:
```bash
npm install -g @railway/cli
```

Comandos útiles:
```bash
railway login          # Iniciar sesión
railway link           # Vincular proyecto local
railway up             # Desplegar
railway logs           # Ver logs
railway shell          # Acceder al contenedor
railway vars           # Ver variables de entorno
```

## Solución de problemas

### Problema: La aplicación no inicia
**Solución**: 
1. Verifica las variables de entorno
2. Revisa los logs en Railway dashboard
3. Asegúrate de que `server = app.server` esté en app.py

### Problema: Error de dependencias
**Solución**:
1. Verifica que `requirements.txt` esté actualizado
2. Comprueba que no hay dependencias del sistema faltantes en `Dockerfile`

### Problema: Error de base de datos
**Solución**:
1. Verifica que `DATABASE_URL` esté configurada
2. Asegúrate de que la base de datos esté ejecutándose en Railway
3. Revisa las credenciales de conexión

### Problema: Error de autenticación
**Solución**:
1. Verifica que `JWT_SECRET_KEY` esté configurada
2. Asegúrate de que las credenciales de API externa sean correctas

## Monitoreo y mantenimiento

### Logs
- Ve a Railway dashboard > Deployments > Logs
- Los logs se muestran en tiempo real
- Filtra por nivel de severidad

### Métricas
- Railway proporciona métricas básicas de CPU y memoria
- Para métricas avanzadas, considera integrar servicios externos

### Actualizaciones
Railway despliega automáticamente cuando haces push a la rama configurada.

## Costos estimados

Railway tiene un tier gratuito con limitaciones:
- **Hobby Plan**: $5/mes
  - 512MB RAM
  - 1GB almacenamiento
  - Sin límite de requests

Para producción, considera el **Pro Plan**: $20/mes

## Seguridad

### Variables sensibles
- ✅ Usar variables de entorno para toda información sensible
- ✅ No commitear claves en el código
- ✅ Rotar claves periódicamente

### HTTPS
- ✅ Railway proporciona HTTPS automáticamente
- ✅ Configura HSTS si tienes dominio personalizado

### Acceso
- ✅ Railway tiene autenticación JWT built-in
- ✅ Configura OAuth si es necesario

## Backup y recuperación

### Datos
- Railway hace backup automático de bases de datos
- Para datos de aplicación, implementa estrategia de backup externa

### Código
- Mantén el código en repositorio Git
- Usa tags/releases para versiones estables

---

🔗 **Enlaces útiles:**
- [Documentación de Railway](https://docs.railway.app)
- [Railway CLI](https://docs.railway.app/develop/cli)
- [Ejemplos de Railway](https://railway.app/templates) 