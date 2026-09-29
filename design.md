# Design — Utilitaria

Sistema visual compartido para todas las pantallas de la aplicación. La app
debe sentirse como una herramienta personal de control: clara, táctil y con
ritmo editorial, sin repetir tarjetas genéricas ni diálogos flotantes sin
jerarquía.

## Genre

modern-minimal · utilitario · táctil

## Macrostructure family

- App pages: Workbench compacto — encabezado de contexto, estado de
  sincronización, contenido principal y acciones agrupadas.
- Detail pages: Long Document compacto — resumen visible, bloques de datos y
  edición contextual.
- Catalogue pages: Catalogue — resumen, filtros y cuadrícula/lista de
  productos con estados comparables.

## Theme

- Fondo: azul grisáceo muy claro, nunca blanco puro como fondo general.
- Superficie: blanco cálido para separar áreas de trabajo.
- Tinta: azul petróleo oscuro para textos y encabezados.
- Acento: cian eléctrico para acciones y estados activos.
- Secundario: menta para sincronización, disponibilidad y confirmaciones.
- Advertencia: ámbar tenue para datos pendientes o desactualizados.
- Error: rojo sobrio solo para salidas negativas o errores.

## Typography

- Display: tipografía sans del sistema, peso 700, siempre romana.
- Body: tipografía sans del sistema, peso 400–600.
- Etiquetas: mayúsculas pequeñas con espaciado amplio y uso limitado.
- Los encabezados no se pegan al borde: mínimo 24 dp de margen horizontal.

## Spacing

Escala de 4 dp: 4, 8, 12, 16, 20, 24, 32. Las pantallas usan 16 dp como
gutter base y 24 dp para separaciones de secciones.

## Components

- Encabezado: superficie petróleo/cian, esquina inferior redondeada, título
  alineado después del icono de navegación y acciones en controles circulares.
- Formularios: diálogos anchos, campos apilados de 56 dp, etiquetas claras,
  validación visible y acciones inferiores siempre alcanzables.
- Tarjetas: radio 22 dp, sin sombras pesadas, una sola idea por tarjeta.
- Acciones: una acción primaria rellena y una secundaria contorneada; no usar
  dos botones rellenos compitiendo.
- Estados: disponible, pendiente, agotado y fuera de catálogo deben usar texto
  además de color.
- Catálogo: filtros antes de resultados, búsqueda persistente y comparación
  Miramar/Siboney dentro de cada producto.

## Motion

Movimiento mínimo: refresco y estados de carga discretos. No animar por
decoración. Toda transición debe tolerar `prefers-reduced-motion`.

## Copy and interaction

- Priorizar verbos concretos: Guardar, Filtrar, Comprobar, Ver artículo.
- Explicar quién afecta cada movimiento antes de guardar.
- Los datos cacheados deben indicar hora y estado de sincronización.
- El éxito visible no necesita un toast celebratorio; los errores sí explican
  qué se puede hacer.

## What every page must share

El encabezado, la escala de espaciado, el tratamiento de superficies, los
controles de acción, el estado de sincronización y la navegación inferior.

## What pages may vary

La pantalla financiera puede priorizar números y movimientos; Alertas puede
priorizar estados y cambios; el catálogo puede usar más densidad y filtros.
La estructura cambia por tarea, pero la voz visual no cambia.
