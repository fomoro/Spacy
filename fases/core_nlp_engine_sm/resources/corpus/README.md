# Corpus conversacional

Este directorio contiene perfiles y conjuntos lingüísticos de `core_nlp_engine` para español colombiano conversacional en el dominio de un restaurante de comida de mar. Su contenido sirve para desarrollar y medir componentes; no contiene configuración de producción.

## Archivos y autoridad

| Archivo | Función |
|---|---|
| `profiles/conversation_profiles.json` | Perfiles conversacionales para diseñar y segmentar cobertura. |
| `datasets/intent_benchmark/casos_intenciones_clientes.json` | Fuente canónica con metadatos, contexto y anotaciones estructuradas. |
| `datasets/intent_benchmark/casos_intenciones_clientes.csv` | Proyección tabular del JSON para inspección y análisis. No se edita de manera independiente. |

Las definiciones que sustentan las anotaciones pertenecen a otros recursos:

- Perfiles: `resources/corpus/profiles/conversation_profiles.json`.
- Intenciones y subintenciones: `resources/config/intent_taxonomy.json`.
- Entidades comerciales: `resources/config/infrastructure_nlp/phrase_matcher_service_config.json`.
- Entidades contextuales: `resources/config/infrastructure_nlp/entity_ruler_service_config.json`.
- Completitud y preguntas: `resources/config/application/clarification_policy.json`.

Si cambia alguno de esos contratos, el benchmark debe revisarse; no se deben redefinir taxonomías, perfiles ni entidades dentro de un dataset.

## Diseño actual

- 450 casos únicos: 15 perfiles conversacionales por 30 casos.
- Cobertura de las 47 combinaciones de intención y subintención.
- Mínimo de 6 casos por combinación.
- Los cinco modos de intervención aparecen en cada perfil.
- Los perfiles representan registros y fenómenos observables; no edad, género, estrato, discapacidad ni otros atributos sensibles.
- Los mensajes son casos sintéticos de evaluación, no conversaciones reales ni datos personales.

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
| `profile_case_number` | Posición del 1 al 30 dentro del perfil. |
| `message` | Texto original del cliente; no debe pre-normalizarse. |
| `context` | Información previa disponible para resolver referencias entre turnos. |
| `expected.intent` | Intención canónica esperada. |
| `expected.subintent` | Subintención canónica esperada. |
| `expected.intervention_mode` | Resultado conversacional esperado. |
| `expected.requires_clarification` | Indica si el flujo necesita intervención antes de responder o ejecutar. |
| `expected.clarification_reason` | Causa estructurada de la intervención; `null` cuando el caso está resuelto. |
| `expected.missing_slots` | Datos que todavía debe aportar o confirmar el cliente. |
| `expected.question_key` | Pregunta mínima definida por la política de aclaración. |
| `expected_entities` | Entidades y valores que deberían reconocerse en el mensaje. |
| `difficulty` | Complejidad lingüística: `easy`, `medium` o `hard`. |
| `phenomena` | Rasgos que justifican el caso y permiten segmentar errores. |
| `scenario` | Familia funcional del caso. |

`expected_entities` representa evidencia explícita en el texto, no inferencias comerciales. La ausencia de un alérgeno en el nombre de un plato nunca permite afirmar que el plato sea seguro.

## Modos de intervención

| Modo | Uso |
|---|---|
| `resolved` | Hay información suficiente para continuar. |
| `needs_user_clarification` | Falta un dato que solo puede aportar el cliente. |
| `needs_transaction_confirmation` | La acción tendría efecto transaccional y necesita confirmación explícita. |
| `needs_business_lookup` | La respuesta depende de disponibilidad, precio variable u otro dato operativo. |
| `needs_human_safety_validation` | Existe una consulta alimentaria que requiere verificación humana segura. |

`requires_clarification` es `false` únicamente para `resolved`. En los demás modos significa que el motor no debe presentar el caso como definitivamente resuelto; la intervención concreta depende del modo.

## Criterios para agregar o modificar casos

1. Editar primero `casos_intenciones_clientes.json`, que es la fuente de verdad.
2. Mantener el mensaje natural para su perfil y anotar únicamente evidencia observable.
3. Usar identificadores existentes en los recursos de referencia.
4. Diferenciar ambigüedad lingüística, confirmación transaccional, consulta operativa y seguridad alimentaria.
5. Actualizar la fila equivalente de `casos_intenciones_clientes.csv` sin alterar ni aplanar los valores JSON de sus columnas estructuradas.
6. Conservar 30 casos por perfil, IDs únicos, numeración continua y cobertura equilibrada.
7. Ejecutar todas las validaciones antes de aceptar el cambio.

No se debe editar solo el CSV, duplicar un mensaje cambiando palabras superficiales, agregar información personal identificable ni ajustar la etiqueta para favorecer la salida actual del motor. Cuando el motor y el caso difieran, primero se auditan la taxonomía, la evidencia lingüística y la política de aclaración.

## Validación y evaluación

Desde la raíz del proyecto:

```bash
python -X utf8 tests/contract/test_resource_contract.py
python -m unittest discover -s tests -p "test_*.py"
python -X utf8 tests/evaluation/evaluate_normalizer.py
python -X utf8 tests/evaluation/evaluate_phrase_matcher.py
python -X utf8 tests/evaluation/evaluate_resolver.py
```

`tests/contract/test_resource_contract.py` comprueba la equivalencia entre JSON y CSV, conteos, IDs, unicidad de mensajes, perfiles, taxonomía, slots, preguntas, entidades y cobertura. Los evaluadores generan resultados en `reports/`; esos archivos son salidas derivadas y no forman parte de la verdad anotada.

Los cinco evaluadores de `tests/evaluation/` recorren este mismo dataset de 450 casos. No existen contratos JSON alternativos dentro de `tests/`.

## Alcance de las métricas

Este corpus es un conjunto de referencia sintético. Haber validado su estructura no significa que el motor acierte los 450 casos. Las métricas deben calcularse con un evaluador que compare predicción y anotación, informarse por intención, subintención, modo de intervención y perfil, y acompañarse del número de casos evaluados.
