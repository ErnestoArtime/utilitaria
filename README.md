# Utilitaria

Aplicación Android/Flutter para centralizar notificaciones, registrar transferencias, consultar un saldo operativo y disparar avisos por WhatsApp.

## Arquitectura

- `backend/`: FastAPI + PostgreSQL, ejecutable en el VPS con Docker Compose.
- `flutter_app/`: cliente Flutter (Android primero).
- Captura Android: `NotificationListenerService`, filtrando por paquetes permitidos y enviando eventos a la API.
- Push: Firebase Cloud Messaging para alertas generadas por el backend.
- WhatsApp: adaptador HTTP preparado para el despliegue OpenWA existente.
- Alertas: catálogo TiendaSolar y comprobación periódica de disponibilidad de
  la bombona de gas de Goniogas, con avisos push ante cambios.
- Acceso: credenciales revocables por dispositivo con roles `admin`, `member`,
  `capture` y `service`; la APK no contiene una clave maestra.
- Entrega: cola persistente Android para capturas y outbox con reintentos para
  WhatsApp.
- Respaldo: dump PostgreSQL diario verificado localmente y subida S3/R2 cuando
  se configuran sus credenciales.

## Arranque del backend

```bash
cd backend
cp .env.example .env
docker compose up -d --build
```

API: `http://localhost:8080` · documentación: `http://localhost:8080/docs`

Los códigos de activación se generan fuera del repositorio con:

```bash
./scripts/rotate-auth-secrets.sh
```

Se guardan con permisos privados en
`~/.config/utilitaria-auth/enrollment-codes`. Después de instalar la APK, se
introduce el código de administrador en el teléfono principal y el código de
miembro en el teléfono que solo debe consultar la información.

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

## Operación pendiente

Configurar `S3_BACKUP_*` en `backend/.env` para que la copia diaria, que ya se
genera y valida localmente, también quede fuera del VPS (por ejemplo en R2).

No se deben guardar tokens reales en el repositorio: usar `.env` y secretos del VPS.
