# 🚀 Guía Rápida: Deployment en Railway

## ✅ Estado del Proyecto
**Tu proyecto Alfred Dashboard está 100% listo para Railway!**

Archivos configurados:
- ✅ `railway.json` - Configuración específica de Railway
- ✅ `Procfile` - Comando de inicio alternativo
- ✅ `Dockerfile` - Contenedor optimizado
- ✅ `app.py` - Configurado con `server = app.server`
- ✅ `env.example` - Guía de variables de entorno
- ✅ `.gitignore` - Protección de archivos sensibles

## 🎯 Pasos para Deployment (15 minutos)

### 1. Preparar el repositorio
```bash
# Hacer commit de todos los cambios
git add .
git commit -m "feat: configuración para deployment en Railway"
git push origin main
```

### 2. Crear proyecto en Railway
1. Ve a [railway.app](https://railway.app)
2. Inicia sesión con GitHub
3. Clic en **"New Project"**
4. Selecciona **"Deploy from GitHub repo"**
5. Autoriza Railway y selecciona tu repositorio `AlfredDashboard`

### 3. Configurar variables de entorno CRÍTICAS

En Railway Dashboard > Settings > Variables, añade:

```bash
# OBLIGATORIAS
HOST=0.0.0.0
PORT=$PORT
DASH_DEBUG=false
JWT_SECRET_KEY=tu_clave_secreta_super_fuerte_aqui_123456789

# API DE ALFRED SMART (configura según tu setup)
API_BASE_URL=https://tu-alfred-smart-api.com
API_USERNAME=tu_usuario_api
API_PASSWORD=tu_password_api

# OPCIONALES
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
TZ=Europe/Madrid
```

### 4. Añadir base de datos (si necesitas)
- En Railway dashboard: **New** > **Database** > **PostgreSQL**
- Railway creará automáticamente `DATABASE_URL`

### 5. ¡Desplegar!
Railway desplegará automáticamente. Tu app estará en:
`https://tu-app-production.up.railway.app`

## 🔧 Variables de Entorno Explicadas

### Variables críticas:
- **`JWT_SECRET_KEY`**: ⚠️ **MUY IMPORTANTE** - Genera una clave fuerte única
- **`API_BASE_URL`**: URL de tu API de Alfred Smart
- **`API_USERNAME/PASSWORD`**: Credenciales para la API externa

### Variables del sistema:
- **`HOST`**: Siempre `0.0.0.0` para Railway
- **`PORT`**: Railway la asigna automáticamente con `$PORT`
- **`DASH_DEBUG`**: `false` en producción

## 🚨 Checklist de Seguridad

- [ ] `JWT_SECRET_KEY` es única y fuerte (mínimo 32 caracteres)
- [ ] No hay archivos `.env` en el repositorio
- [ ] Credenciales de API son correctas
- [ ] `.gitignore` protege archivos sensibles

## 📊 Costos Estimados

- **Hobby Plan**: $5/mes (512MB RAM, 1GB storage)
- **Pro Plan**: $20/mes (para producción)
- **Tier gratuito**: Disponible con limitaciones

## 🔍 Solución de Problemas

### La app no inicia:
1. Revisa logs en Railway Dashboard > Deployments > Logs
2. Verifica que `JWT_SECRET_KEY` esté configurada
3. Comprueba que las variables de API sean correctas

### Error de dependencias:
1. Verifica que `requirements.txt` esté actualizado
2. Revisa que el `Dockerfile` sea correcto

### Error de base de datos:
1. Asegúrate de que PostgreSQL esté ejecutándose en Railway
2. Verifica que `DATABASE_URL` esté configurada

## 🎉 ¡Listo para Producción!

Tu Alfred Dashboard incluye:
- ✅ Autenticación JWT
- ✅ Análisis de consumos
- ✅ Gestión de cerraduras inteligentes
- ✅ Análisis de huella de carbono
- ✅ Detección de anomalías
- ✅ Explorador de base de datos
- ✅ Métricas avanzadas

## 📞 Soporte

Si tienes problemas:
1. Revisa `DEPLOYMENT.md` para guía detallada
2. Ejecuta `python check_deployment.py` para verificaciones
3. Consulta [docs.railway.app](https://docs.railway.app)

---
**¡Tu proyecto está listo para brillar en Railway! 🌟** 