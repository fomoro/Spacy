# Pruebas y herramientas de calidad

Esta carpeta separa las comprobaciones automáticas de la evaluación integral del resolutor. Los datos de referencia no viven aquí: `resources/corpus/benchmarks/customer_intent_benchmark.json` es la única fuente canónica de casos.

## Estructura

```text
tests/
├── infrastructure/  # Pruebas unitarias de los cinco servicios spaCy
└── temp/
    ├── application/      # Parser, mapper, resolutor y DialogueOrchestrator
    ├── json_validators/  # Validadores de archivos JSON
    └── evaluation/       # Evaluación integral que escribe en reports/
```

### `infrastructure/`

Comprueba responsabilidades lingüísticas aisladas: normalización, entidades del menú, señales sintácticas, lemas, EntityRuler y construcción desde diccionarios. Matcher y Lemma reciben texto sin ejecutar otros servicios y no deben producir intenciones ni pesos.

### `temp/application/`

Comprueba el mapeo de señales neutrales, la orquestación de evidencias, resolución de intención, slots, modos de intervención, composición de respuestas y fachada pública. Incluye el contrato de que los slots personales no se infieran desde texto arbitrario.

### `temp/json_validators/`

Contiene validadores ejecutables por archivo o conjunto de archivos. `test_resource_json_validator.py` comprueba las referencias generales, mientras `test_menu_offerings_json_validator.py` y `test_restaurant_profile_json_validator.py` validan por separado los datos comerciales y la información estable del restaurante.

### `temp/evaluation/`

Procesa los 600 casos sin formar parte de la suite unitaria. `evaluate_resolver.py` mide intención, subintención, modo, slots faltantes, clave de pregunta y activación indebida de lecturas excluidas. Los reportes derivados no son fuentes de verdad y no deben contener datos personales reales.

## Comandos

Validadores JSON:

```bash
python -X utf8 tests/temp/json_validators/test_resource_json_validator.py
python -X utf8 tests/temp/json_validators/test_menu_offerings_json_validator.py
python -X utf8 tests/temp/json_validators/test_restaurant_profile_json_validator.py
```

Todas las pruebas automatizadas:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Evaluaciones sobre el benchmark canónico:

```bash
python -X utf8 tests/temp/evaluation/evaluate_resolver.py
```

## Convenciones

- Solo las pruebas automáticas comienzan por `test_`.
- Solo la evaluación integral comienza por `evaluate_`.
- Ninguna prueba redefine taxonomías, perfiles o entidades mediante JSON locales.
- Toda evaluación usa `resources/corpus/benchmarks/customer_intent_benchmark.json` y conserva `profile_id` para segmentar resultados.
- Una prueba unitaria debe ser determinista y no modificar `resources/`.
- Un reporte puede regenerarse; una anotación del dataset requiere revisión lingüística y contractual.
