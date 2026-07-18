# Corpus conversacional

Este directorio contiene perfiles y conjuntos lingüísticos de `core_nlp_engine` para español colombiano conversacional en el dominio de un restaurante de comida de mar. Su contenido sirve para desarrollar y medir componentes; no contiene configuración de producción.

## Organización

- `benchmarks/`: medir el sistema con casos conocidos y anotaciones esperadas.
- `conversations/`: simular flujos completos de mensajes conservando el estado entre turnos.
- `datasets/`: entrenar, validar y probar modelos estadísticos con particiones separadas.
- `profiles/`: diseñar cobertura lingüística y segmentar el análisis de resultados.

## Archivos y autoridad

| Archivo | Función |
|---|---|
| `profiles/conversation_profiles.json` | Perfiles conversacionales para diseñar y segmentar cobertura. |
| `benchmarks/customer_intent_benchmark.json` | Fuente canónica con metadatos, contexto y anotaciones estructuradas para medir el sistema. |
| `conversations/carlos.json` | Flujo sintético de cinco mensajes del cliente Carlos. |
| `conversations/diego.json` | Flujo sintético de cinco mensajes del cliente Diego. |

Las definiciones que sustentan las anotaciones pertenecen a otros recursos:

- Perfiles: `resources/corpus/profiles/conversation_profiles.json`.
- Intenciones y subintenciones: `src/temp/resources/intent_resolver/intents_and_subintents.json`.
- Campos de datos conversacionales: `src/temp/resources/intent_resolver/conversation_data_fields.json`.
- Entidades comerciales: `src/infrastructure/resources/phrase_matcher_service_config.json`.
- Entidades contextuales: `src/infrastructure/resources/entity_ruler_service_config.json`.
- Mapeo de señales y entidades a intenciones: `src/temp/resources/intent_resolver/linguistic_evidence_mapping.json`.
- Acciones, reglas de completitud y preguntas: `src/temp/resources/intent_resolver/conversation_action_rules.json`.

Si cambia alguno de esos contratos, el benchmark debe revisarse; no se deben redefinir taxonomías, perfiles ni entidades dentro del benchmark.

Los archivos de `conversations/` contienen exclusivamente listas de mensajes. No incluyen metadata, respuestas del bot, intenciones esperadas ni datos personales reales. Sirven para ejecutar una secuencia manual o automatizada conservando el estado entre turnos.

## Diseño actual

- 600 casos únicos: 20 perfiles conversacionales por 30 casos.
- Cobertura de las 56 combinaciones de intención y subintención.
- Mínimo de 8 casos por combinación.
- Cada perfil cubre resolución, confirmación, consulta operativa, seguridad y al menos una intervención de aclaración o verificación; la asistencia humana se usa cuando el flujo debe escalarse.
- 150 casos contienen contexto conversacional; cada perfil aporta entre 6 y 9.
- Los perfiles representan registros y fenómenos observables; no edad, género, estrato, discapacidad ni otros atributos sensibles.
- Los mensajes son casos sintéticos de evaluación, no conversaciones reales ni datos personales. Todo slot personal futuro debe usar valores ficticios o redactados.

Los perfiles sirven para comparar cobertura y desempeño entre estilos comunicativos. No deben inferirse a partir del mensaje ni enviarse al motor durante la ejecución en producción.

## Futuro corpus de TextCategorizer

El benchmark conocido no debe funcionar simultáneamente como evidencia final de calidad y como único material de entrenamiento. Cuando se implemente el clasificador, sus mensajes nuevos se separarán bajo `datasets/text_categorizer/` en:

- `entrenamiento/`: aprendizaje del modelo.
- `validacion/`: ajuste de hiperparámetros y umbrales.
- `prueba/`: medición final sin usar durante el desarrollo.

Estas carpetas se crearán cuando exista contenido real, curado y anonimizado para cada partición.

## Contrato de cada caso

| Campo | Significado |
|---|---|
| `id` | Identificador secuencial `caso_NNN`. |
| `profile_id` | Perfil de evaluación al que pertenece el caso. |
| `message` | Texto original del cliente; no debe pre-normalizarse. |
| `context` | Información previa disponible para resolver referencias entre turnos. |
| `expected.intent` | Intención canónica esperada. |
| `expected.subintent` | Subintención canónica esperada. |
| `expected.intervention_mode` | Resultado conversacional esperado. |
| `expected.missing_slots` | Datos que todavía debe aportar o confirmar el cliente. |
| `expected.question_key` | Pregunta seleccionada por las reglas de acción conversacional. |
| `expected_entities` | Entidades y valores que deberían reconocerse en el mensaje. |
| `annotation` | Evidencia lingüística que explica la lectura esperada, descarta falsos positivos y orienta la acción. |

`expected_entities` representa evidencia explícita en el texto, no inferencias comerciales. La ausencia de un alérgeno en el nombre de un plato nunca permite afirmar que el plato sea seguro.

`context` conserva únicamente estado previo que puede usar el resolver, como `producto_activo`, `pedido_activo`, `pedido_anterior`, `order_id`, `direccion_previa` o el historial de envío del menú. `identity_verified` solo representa una verificación ya realizada por la aplicación. Un objeto vacío significa que el caso debe resolverse solo con el mensaje actual.

`annotation` contiene `target_evidence`, `disambiguating_evidence`, `excluded_readings` y `expected_action`. Las dos evidencias deben aparecer literalmente en el mensaje; las lecturas excluidas deben pertenecer a la taxonomía y sirven para analizar falsos positivos.

## Modos de intervención

| Modo | Uso |
|---|---|
| `resolved` | Hay información suficiente para continuar. |
| `needs_user_clarification` | Falta un dato que solo puede aportar el cliente. |
| `needs_transaction_confirmation` | La acción tendría efecto transaccional y necesita confirmación explícita. |
| `needs_business_lookup` | La respuesta depende de disponibilidad, precio variable u otro dato operativo. |
| `needs_human_safety_validation` | Existe una consulta alimentaria que requiere verificación humana segura. |
| `needs_human_assistance` | Una persona debe continuar una gestión que el motor no puede completar. |
| `needs_identity_verification` | La aplicación debe verificar al cliente antes de consultar o reutilizar pedidos o direcciones anteriores. |
| `out_of_scope` | El mensaje no corresponde a los servicios conocidos; no se fuerza una intención ni una aclaración falsa. |

La compatibilidad `requires_clarification` se deriva del modo declarado por la política. Es falsa para `resolved` y `out_of_scope`; los modos de recolección, verificación, confirmación, consulta o escalamiento detienen la resolución definitiva. La verificación la ejecuta la aplicación y solo comunica al resolutor el booleano confiable `context.identity_verified`.

## Criterios para agregar o modificar casos

1. Editar primero `benchmarks/customer_intent_benchmark.json`, que es la fuente de verdad.
2. Mantener el mensaje natural para su perfil y anotar únicamente evidencia observable.
3. Usar identificadores existentes en los recursos de referencia.
4. Diferenciar ambigüedad lingüística, confirmación transaccional, consulta operativa y seguridad alimentaria.
5. Conservar 30 casos por perfil, IDs únicos, numeración continua y cobertura equilibrada.
6. Ejecutar todas las validaciones antes de aceptar el cambio.

No se debe duplicar un mensaje cambiando palabras superficiales, agregar información personal identificable ni ajustar la etiqueta para favorecer la salida actual del motor. Cuando el motor y el caso difieran, primero se auditan la taxonomía, la evidencia lingüística y las reglas de acción conversacional.

## Validación y evaluación

Desde la raíz del proyecto:

```bash
python -X utf8 tests/temp/json_validators/test_resource_json_validator.py
python -m unittest discover -s tests -p "test_*.py"
python -X utf8 tests/temp/evaluation/evaluate_resolver.py
```

`tests/temp/json_validators/test_resource_json_validator.py` comprueba el JSON canónico, sus metadatos mínimos, conteos, IDs, unicidad de mensajes, perfiles, taxonomía, slots, preguntas, entidades, cobertura y evidencia lingüística de las anotaciones. Los evaluadores generan resultados en `reports/`; esos archivos son salidas derivadas y no forman parte de la verdad anotada.

El evaluador integral `tests/temp/evaluation/evaluate_resolver.py` recorre este benchmark de 600 casos. No existen contratos JSON alternativos dentro de `tests/`.

## Alcance de las métricas

Este corpus es un conjunto de referencia sintético. Haber validado su estructura no significa que el motor acierte los 600 casos. Las métricas deben calcularse con un evaluador que compare predicción y anotación, informarse por intención, subintención, modo de intervención y perfil, y acompañarse del número de casos evaluados.
