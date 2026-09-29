# Previsualización web de Utilitaria

La versión web permite revisar la navegación y las pantallas desde cualquier navegador sin instalar la APK. Las funciones exclusivas de Android, como leer notificaciones del sistema, no están disponibles en el navegador.

## Publicar

Desde la raíz de `utilitaria`:

```bash
export PATH=/home/ernesto/flutter/bin:$PATH
cd flutter_app
flutter build web --release
cd ../web-preview
docker compose up -d --build
```

Origen local: `http://127.0.0.1:8125`.
