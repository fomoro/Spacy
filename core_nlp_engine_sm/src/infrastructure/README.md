# Infraestructura

Esta capa contiene adaptadores técnicos separados por capacidad. `nlp/`
produce texto normalizado, entidades y señales neutrales; `state/` alojará la
persistencia conversacional y `api/` las integraciones con sistemas externos.
Ningún adaptador dirige por sí mismo el flujo completo del diálogo.

## NLP

Los servicios de `nlp/` tienen responsabilidades independientes:

- `text_normalizer_service.py`: normalización controlada del texto.
- `phrase_matcher_service.py`: reconocimiento del vocabulario comercial.
- `matcher_service.py`: señales sintácticas neutrales, cantidades, dinero y negación.
- `lemma_service.py`: lematización y señales morfológicas neutrales.
- `entity_ruler_service.py`: entidades temporales y contextuales.
- `text_categorizer_service.py`: punto de extensión pendiente para
  puntuaciones estadísticas neutrales.

El futuro `TextCategorizerService` entregará puntuaciones a la capa de
aplicación; no tomará la decisión final ni reemplazará las reglas y prioridades
existentes.

Cada servicio recibe texto y puede probarse sin construir otro servicio. La
capa de aplicación combina después sus resultados mediante
`LinguisticEvidenceMapper`; por ello Matcher no recibe `PhraseMatchResult` y
Lemma no contiene intenciones ni pesos.

## Estado conversacional

`state/dialogue_state.py` es un placeholder de Fase 4. Alojará el adaptador de
persistencia para recuperar y guardar contexto entre turnos; no analizará
texto ni decidirá intenciones.

## APIs y ejecución

`api/fulfillment_service.py` es un placeholder de Fase 4. Alojará las
integraciones con APIs o bases de datos para consultas y acciones de negocio;
no redactará respuestas para el usuario.

## Resources

La carpeta `resources/` contiene únicamente las configuraciones JSON que
pertenecen directamente a los servicios de esta capa:

- `text_normalizer_service_config.json`
- `phrase_matcher_service_config.json`
- `matcher_service_config.json`
- `lemma_service_config.json`
- `entity_ruler_service_config.json`

No contiene taxonomías, reglas conversacionales, benchmarks ni datos del
restaurante. `TextCategorizerService` todavía no tiene configuración porque su
implementación permanece pendiente.

## Convención documental

Los archivos de introducción de cada directorio se llaman `README.md`. Pueden
existir varios en el proyecto porque cada uno explica el alcance de su propia
carpeta. Los documentos especializados que no describan una carpeta deben usar
un nombre temático, por ejemplo `arquitectura.md` o `guia_entrenamiento.md`.
