# Utilitaria

Aplicación Android/Flutter para centralizar notificaciones, registrar transferencias, consultar un saldo operativo y disparar avisos por WhatsApp.

## Arquitectura inicial

- `backend/`: FastAPI + PostgreSQL, ejecutable en el VPS con Docker Compose.
- `flutter_app/`: cliente Flutter (Android primero).
- Captura Android: `NotificationListenerService`, filtrando por paquetes permitidos y enviando eventos a la API.
- Push: Firebase Cloud Messaging para alertas generadas por el backend.
- WhatsApp: adaptador HTTP preparado para el despliegue OpenWA existente.
- TiendaSolar: adaptador HTTP pendiente de conectar a su endpoint/webhook real.

## Arranque del backend

```bash
cd backend
cp .env.example .env
docker compose up -d --build
```

API: `http://localhost:8080` · documentación: `http://localhost:8080/docs`

Página privada de descargas: [descargas.eav-labs.com](https://descargas.eav-labs.com/)

## Cliente Android

Hace falta instalar Flutter en la máquina de desarrollo. Después:

```bash
cd flutter_app
flutter pub get
flutter run
```

Para generar una release firmada con la keystore privada local:

```bash
cd flutter_app
../scripts/build-release.sh
```

La keystore y su contraseña viven fuera del repositorio, en `~/.config/utilitaria-signing/`.

En Android se debe conceder manualmente el permiso de acceso a notificaciones desde Ajustes. La captura de notificaciones solo es viable en Android; iOS no ofrece un equivalente general para leer notificaciones de otras apps.

## Próximos datos necesarios

1. URL, método y autenticación de OpenWA.
2. URL/webhook o método de consulta de TiendaSolar.
3. Lista final de paquetes bancarios que se deben leer y patrones de texto por banco.
4. Dominio o IP HTTPS del VPS para configurar la app y Firebase.

No se deben guardar tokens reales en el repositorio: usar `.env` y secretos del VPS.
