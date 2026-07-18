# `core_nlp_engine`

Motor NLP para normalización, extracción de entidades, análisis lingüístico y resolución de intenciones del restaurante.

---

## Entorno

El proyecto está verificado con Python 3.14.6, spaCy 3.8.13 y el modelo español `es_core_news_sm` 3.8.0. Python se instala y administra fuera de `requirements.txt`; las dependencias de Python y el modelo lingüístico se instalan con:

```bash
python -m pip install -r requirements.txt
python -m spacy validate
```

`LemmaService` usa `es_core_news_sm` para el análisis morfológico y la lematización. Si el modelo no está disponible, mantiene un fallback limitado con `spacy.blank("es")` y el catálogo declarativo; ese fallback no sustituye la instalación requerida para evaluación o producción.

---

## Estructura por Temas

El procesador está diseñado bajo una estricta separación de responsabilidades:

```text
core_nlp_engine/
│
├── resources/                         # Datos, contratos y corpus
│   ├── README.md
│   ├── business_data/
│   │   ├── menu/                       # Ofertas, precios y recomendaciones
│   │   └── restaurant/                 # Información estable del negocio
│   └── corpus/                         # Material lingüístico de desarrollo y medición
│       ├── README.md
│       ├── benchmarks/customer_intent_benchmark.json
│       ├── conversations/
│       ├── datasets/
│       └── profiles/conversation_profiles.json
├── src/                               # Código fuente y recursos por capa
│   ├── temp/                          # Código y recursos todavía en revisión
│   │   ├── response_renderer.py
│   │   └── resources/
│   │       ├── response_templates.json
│   │       └── intent_resolver/
│   │           ├── intents_and_subintents.json
│   │           ├── linguistic_evidence_mapping.json
│   │           ├── conversation_data_fields.json
│   │           └── conversation_action_rules.json
│   └── infrastructure/
│       ├── nlp/                       # Servicios lingüísticos autónomos con spaCy
│       └── resources/                 # JSON exclusivos de infraestructura
├── tests/
│   ├── infrastructure/                # Pruebas unitarias de infraestructura
│   └── temp/                          # Pruebas y herramientas aún en validación
└── reports/                           # Reportes generados
```

---

## Benchmark de intenciones

`resources/corpus/benchmarks/customer_intent_benchmark.json` es la única fuente canónica de 600 casos y cubre 56 combinaciones de intención y subintención. Cada uno de los 20 perfiles aporta 30 casos y cubre resolución, confirmación, consulta operativa, seguridad y al menos una intervención de obtención o verificación de información; 150 casos incluyen contexto conversacional. Los perfiles sirven para segmentar evaluación y nunca se infieren ni se envían al motor en producción.

El comando `python -X utf8 tests/temp/json_validators/test_resource_json_validator.py` comprueba la coherencia general de taxonomía, perfiles, slots, acciones y benchmark. El menú y el perfil del restaurante tienen validadores JSON independientes.

El contrato de anotación, los criterios de mantenimiento y el alcance correcto de las métricas están documentados en [`resources/corpus/README.md`](resources/corpus/README.md).

---

## Tema 1: Normalizador de Texto (Limpiador)

**Foco Principal**: Limpieza controlada y estandarización de español colombiano. Su única responsabilidad es preparar el mensaje del cliente antes de que sea procesado por los extractores. **No** detecta intenciones, **no** extrae platos del menú ni genera respuestas para el usuario.

### Cobertura sociolingüística

El normalizador debe tratar con igual rigor registros coloquiales y formales, escritura no estándar, mensajes ultrabreves y dictado por voz. Los perfiles describen fenómenos conversacionales observables, no edad, género, estrato ni capacidad. Solo se corrigen variantes inequívocas; nombres de platos, direcciones y nombres propios se conservan cuando exista ambigüedad.

### ¿Cómo probar el Normalizador?

#### Pruebas unitarias del Normalizador
Para validar de forma automatizada las aserciones de código del normalizador:
```bash
python -m unittest tests.infrastructure.test_text_normalizer_service
```

---

## Tema 2: Identificador de Productos y Conceptos Clave (PhraseMatcher)

**Foco Principal**: Identificar automáticamente los elementos concretos que menciona el cliente en la conversación (como platos específicos, categorías de comida, ingredientes, alérgenos y medios de pago). Se encarga de asociar las distintas formas de escribir que tienen los clientes a los productos oficiales del menú del restaurante, resolviendo de forma inteligente los conflictos cuando se mencionan varios términos parecidos juntos.

### ¿Cómo probar el PhraseMatcher?

#### Pruebas unitarias del PhraseMatcher
Para ejecutar la suite de validación automatizada de resolución de cruces de palabras en el menú:
```bash
python -m unittest tests.infrastructure.test_phrase_matcher_service
```

---

## Tema 3: Identificador de Intenciones (Matcher)

**Foco Principal**: Identificar la intención o acción que el cliente quiere realizar (ej. consultar un precio, hacer un pedido, solicitar una reserva de mesa, preguntar por medios de pago o alérgenos). Funciona mediante reglas de coincidencia de patrones y nos permite también extraer cantidades numéricas (ej. "dos" platos) y detectar condiciones negativas (ej. "sin" cebolla).

### ¿Cómo probar el Matcher?

#### Pruebas unitarias del Matcher
Para ejecutar las pruebas lógicas automatizadas de detección de intenciones:
```bash
python -m unittest tests.infrastructure.test_matcher_service
```

---

## Tema 4: Analizador de Lemas (LemmaService)

**Foco Principal**: Lematizar términos en español y producir señales morfológicas neutrales. Si el modelo `es_core_news_sm` está disponible usa su lematizador; si no, recurre a `lemma_service_config.json` como fallback controlado. La relación posterior entre un lema y una intención vive en `src/temp/resources/intent_resolver/linguistic_evidence_mapping.json`.

### ¿Cómo probar el LemmaService?

#### Pruebas unitarias del LemmaService
Para ejecutar la suite de validación del lematizador y su comportamiento de fallback:
```bash
python -m unittest tests.infrastructure.test_lemma_service
```

---

## Tema 5: Parser lingüístico (`LinguisticParser`)

**Foco Principal**: Extraer señales lingüísticas crudas. Normaliza, extrae entidades del menú, detecta patrones sintácticos, analiza lemas y aplica el `EntityRuler`. Empaqueta el resultado en `ParsedNLPBundle`, sin traducirlo a intenciones.

### ¿Cómo probar el Pipeline?

#### Pruebas unitarias del Pipeline
Para ejecutar las pruebas del pipeline de evidencias:
```bash
python -m unittest tests.application.test_linguistic_parser
```

---

## Tema 6: Resolutor de Intenciones (IntentResolver)

**Foco Principal**: Decidir la intención y subintención final basándose en `LinguisticEvidenceBundle`, el contexto conversacional y las prioridades configuradas. Vive en la capa de aplicación y no genera respuestas comerciales.

### ¿Cómo probar el Resolutor?

#### 1. Pruebas unitarias del Resolutor
Para validar de forma automatizada las reglas de precedencia, pesos de intención y resolución de contextos:
```bash
python -m unittest tests.application.test_intent_resolver
```

---

## Tema 7: Orquestador de diálogo (`DialogueOrchestrator`)

**Foco Principal**: Dirigir de forma explícita e independiente a `LinguisticParser`, `LinguisticEvidenceMapper`, `IntentResolver` y `ResponseRenderer` en una única llamada `analyze(text, context, response_values)`. `ResolvedNlpResult` contiene evidencia, resolución y respuesta. Las preguntas y confirmaciones provienen de las reglas conversacionales; las resoluciones directas seleccionan una plantilla de `response_templates.json` y solo interpolan valores comerciales suministrados explícitamente.

### ¿Cómo evaluar la calidad del Resolutor?

#### 1. Evaluación de calidad en lote
Para procesar los 600 casos evaluando intención, subintención, aclaración y modo de intervención:
```bash
python -X utf8 tests/temp/evaluation/evaluate_resolver.py
```
* **Reportes generados**:
  * `reports/resolver/evaluacion_resolutor_dataset.csv`: Detalle caso por caso de la intención, subintención y modo esperados frente a los resueltos.
  * `reports/resolver/resultado_resolutor.json`: Métricas consolidadas sobre el dataset.

---

## Suite de Pruebas Unitarias Integrada

Si deseas ejecutar todas las pruebas automatizadas del proyecto (Normalizador, PhraseMatcher, Matcher, LemmaService, Pipeline y Resolutor) en una sola línea de comandos:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

Para comprobar la coherencia entre taxonomía, carta, Matcher, Lemmas, EntityRuler y Resolver:

```bash
python -X utf8 tests/temp/json_validators/test_resource_json_validator.py
python -X utf8 tests/temp/json_validators/test_menu_offerings_json_validator.py
python -X utf8 tests/temp/json_validators/test_restaurant_profile_json_validator.py
```
