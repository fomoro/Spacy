# Pruebas y herramientas de calidad

Esta carpeta separa las comprobaciones automáticas de las evaluaciones masivas y las consolas manuales. Los datos de referencia no viven aquí: `resources/corpus/benchmarks/customer_intent_benchmark.json` es la única fuente canónica de casos.

## Estructura

```text
tests/
├── infrastructure/  # Pruebas unitarias de los cinco servicios spaCy
├── application/     # Parser, resolutor y fachada IntentEngine
├── contract/        # Coherencia cruzada de recursos y dataset
├── evaluation/      # Evaluaciones masivas que escriben en reports/
└── interactive/     # Consolas manuales; no forman parte de unittest
```

### `infrastructure/`

Comprueba responsabilidades lingüísticas aisladas: normalización, entidades del menú, patrones sintácticos, lemas, EntityRuler y construcción desde diccionarios. No debe probar decisiones finales de intención.

### `application/`

Comprueba la orquestación de evidencias, resolución de intención, slots, modos de intervención, composición de respuestas y fachada pública. Incluye el contrato de que los slots personales no se infieran desde texto arbitrario.

### `contract/`

Valida referencias y fronteras entre taxonomía, recursos, perfiles, menú y dataset. `test_resource_contract.py` también puede ejecutarse directamente para obtener un diagnóstico legible.

### `evaluation/`

Procesa los 600 casos sin formar parte de la suite unitaria. El evaluador del resolutor mide intención, subintención, modo, slots faltantes, clave de pregunta y activación indebida de lecturas excluidas. Los reportes derivados no son fuentes de verdad y no deben contener datos personales reales.

### `interactive/`

Permite escribir mensajes manualmente y observar la salida de un componente. Los archivos se llaman `*_console.py` para que no se confundan con pruebas automáticas.

## Comandos

Contrato de datos y recursos:

```bash
python -X utf8 tests/contract/test_resource_contract.py
```

Todas las pruebas automatizadas:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Evaluaciones sobre el benchmark canónico:

```bash
python -X utf8 tests/evaluation/evaluate_normalizer.py
python -X utf8 tests/evaluation/evaluate_phrase_matcher.py
python -X utf8 tests/evaluation/evaluate_matcher.py
python -X utf8 tests/evaluation/evaluate_lemma.py
python -X utf8 tests/evaluation/evaluate_resolver.py
```

Consolas manuales:

```bash
python -X utf8 tests/interactive/normalizer_console.py
python -X utf8 tests/interactive/phrase_matcher_console.py
python -X utf8 tests/interactive/matcher_console.py
python -X utf8 tests/interactive/lemma_console.py
python -X utf8 tests/interactive/linguistic_parser_console.py
```

## Convenciones

- Solo las pruebas automáticas comienzan por `test_`.
- Solo las evaluaciones masivas comienzan por `evaluate_`.
- Las herramientas manuales terminan en `_console.py`.
- Ninguna prueba redefine taxonomías, perfiles o entidades mediante JSON locales.
- Toda evaluación usa `resources/corpus/benchmarks/customer_intent_benchmark.json` y conserva `profile_id` para segmentar resultados.
- Una prueba unitaria debe ser determinista y no modificar `resources/`.
- Un reporte puede regenerarse; una anotación del dataset requiere revisión lingüística y contractual.
