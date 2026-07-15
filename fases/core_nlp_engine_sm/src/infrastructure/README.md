# Infraestructura

Esta capa contiene las implementaciones técnicas que producen evidencia para
la aplicación. No decide por sí misma la intención final ni genera respuestas
comerciales.

## NLP

Los servicios de `nlp/` tienen responsabilidades independientes:

- `text_normalizer_service.py`: normalización controlada del texto.
- `phrase_matcher_service.py`: reconocimiento del vocabulario comercial.
- `matcher_service.py`: patrones sintácticos y extracciones estructuradas.
- `lemma_service.py`: lematización y evidencia morfológica.
- `entity_ruler_service.py`: entidades temporales y contextuales.
- `text_categorizer_service.py`: punto de extensión pendiente para evidencia
  estadística de intenciones y subintenciones.

El futuro `TextCategorizerService` deberá entregar puntuaciones al
`IntentResolver`; no tomará la decisión final ni reemplazará las reglas y
prioridades existentes.

## Convención documental

Los archivos de introducción de cada directorio se llaman `README.md`. Pueden
existir varios en el proyecto porque cada uno explica el alcance de su propia
carpeta. Los documentos especializados que no describan una carpeta deben usar
un nombre temático, por ejemplo `arquitectura.md` o `guia_entrenamiento.md`.
