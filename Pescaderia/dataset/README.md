# Fase 1 — Dataset de 10 clientes

Este entregable contiene 200 casos conversacionales distribuidos en 10 perfiles de clientes bogotanos.

## Archivos

- `dataset_clientes_fase_1.json`: fuente estructurada para desarrollo y pruebas.
- `dataset_clientes_fase_1.csv`: vista tabular para revisión funcional.

## Decisiones incluidas

- Producto específico: se responde con información puntual del producto.
- Categoría específica: se listan únicamente los productos de esa categoría.
- Menú general: se administra el envío del PDF según historial y versión.
- PDF enviado hace menos de siete días: se menciona fecha y hora y se ofrece reenvío.
- Reenvío explícito: se envía sin confirmación adicional.
- Datos no confirmados: se aclaran o escalan; no se inventan.
- Alergias y contaminación cruzada: requieren advertencia y validación operativa.

## Campos principales por caso

- perfil del cliente
- mensaje
- contexto previo
- intención esperada
- entidades esperadas
- acción esperada
- política de menú
- necesidad de aclaración
- resumen de respuesta esperada

## Uso recomendado

Este dataset debe servir primero para validar el modelo de intenciones y entidades. Después se convertirá en casos de prueba para normalización, PhraseMatcher, Matcher, análisis de lemas y resolución de intención.
