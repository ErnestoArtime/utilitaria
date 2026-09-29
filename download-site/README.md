# Página de descargas de Utilitaria

Servicio estático para publicar la APK en el VPS.

## Publicación local/VPS

```bash
docker compose up -d --build
curl -I http://127.0.0.1:8120/
curl -I http://127.0.0.1:8120/releases/utilitaria-latest.apk
```

El túnel de Cloudflare `eav-vps` ya apunta `descargas.eav-labs.com` a `http://127.0.0.1:8120`. Las URLs públicas son:

`https://descargas.eav-labs.com/releases/utilitaria-latest.apk`

Página:

`https://descargas.eav-labs.com/`

Para publicar una nueva versión, sustituir `public/releases/utilitaria-latest.apk`, actualizar la versión en `public/index.html` y reconstruir la imagen.
