# Endurecimiento de Utilitaria 0.9.0

Implementado y desplegado el 3 de octubre de 2026.

- La autenticación global incrustada se sustituyó por tokens revocables por
  dispositivo y permisos por rol. La compatibilidad con la clave anterior está
  desactivada y la clave fue rotada.
- Las reglas de privacidad se evalúan en backend antes de crear cualquier aviso
  de WhatsApp.
- La captura Android filtra operaciones bancarias ING, persiste una cola de
  hasta 500 pendientes y reintenta con espera exponencial. El servidor usa
  identificadores únicos para evitar duplicados.
- Los saldos operativos se calculan en EUR y el resumen conserva un desglose por
  moneda. Los traspasos entre personas son pares vinculados que se actualizan de
  forma atómica.
- WhatsApp usa una bandeja de salida persistente, seguimiento de estado y hasta
  ocho reintentos; guardar un movimiento ya no espera a OpenWA.
- Flutter conserva caché y fecha de sincronización, muestra errores de API
  comprensibles, incorpora activación segura y abre la sección indicada por una
  notificación push. El cliente HTTP y la activación ya están fuera del archivo
  principal.
- Los contenedores tienen límites, comprobación de salud de la API y versión
  identificable. Se publica la misma versión en web y APK.
- PostgreSQL dispone de backup diario validado. Se verificó una restauración
  temporal de 36 movimientos. Falta aportar credenciales S3/R2 para completar
  la copia externa al VPS.

Verificación realizada: compilación Python, análisis Flutter sin incidencias,
3 pruebas Flutter, 2 pruebas backend de seguridad/finanzas, healthcheck público,
firma de APK y descarga pública.
