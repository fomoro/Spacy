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
├── resources/                         # Archivos no Python y su gobernanza
│   ├── README.md
│   ├── config/                    # Reglas, taxonomías y políticas
│   │   ├── intent_taxonomy.json    # Contrato compartido
│   │   ├── infrastructure_nlp/     # Configuración de servicios NLP
│   │   └── application/            # Resolución y aclaración
│   ├── data/
│   │   └── menu/                  # Ofertas y precios suministrados por el usuario
│   └── corpus/                    # Material lingüístico de desarrollo y medición
│       ├── README.md
│       ├── profiles/
│       │   └── conversation_profiles.json
│       └── datasets/
│           └── intent_benchmark/
│               ├── casos_intenciones_clientes.json
│               └── casos_intenciones_clientes.csv
├── src/                           # Código fuente
│   ├── application/               # Parser, resolutor y fachada IntentEngine
│   └── infrastructure/nlp/        # Servicios lingüísticos autónomos con spaCy
├── tests/                         # Calidad separada por capa y tipo de ejecución
│   ├── README.md
│   ├── infrastructure/            # Pruebas unitarias de servicios lingüísticos
│   ├── application/               # Parser, resolutor y fachada
│   ├── contract/                  # Coherencia de recursos y dataset
│   ├── evaluation/                # Evaluaciones masivas sobre 450 casos
│   └── interactive/               # Consolas manuales
└── reports/                       # Reportes generados automáticamente por tema
    ├── normalizer/
    ├── phrase_matcher/
    ├── matcher/
    └── lemma/
```

---

## Dataset conversacional

`resources/corpus/datasets/intent_benchmark/casos_intenciones_clientes.json` es la fuente canónica de 450 casos. El archivo CSV del mismo directorio es una proyección tabular sincronizada. Cada uno de los 15 perfiles aporta 30 casos y cubre los cinco modos de intervención; los perfiles sirven para segmentar evaluación y nunca se infieren ni se envían al motor en producción.

El comando `python -X utf8 tests/contract/test_resource_contract.py` comprueba conteos, unicidad, cobertura de las 47 subintenciones, referencias al menú, slots, modos de intervención y equivalencia entre JSON y CSV.

El contrato de anotación, los criterios de mantenimiento y el alcance correcto de las métricas están documentados en [`resources/corpus/README.md`](resources/corpus/README.md).

---

## Tema 1: Normalizador de Texto (Limpiador)

**Foco Principal**: Limpieza controlada y estandarización de español colombiano. Su única responsabilidad es preparar el mensaje del cliente antes de que sea procesado por los extractores. **No** detecta intenciones, **no** extrae platos del menú ni genera respuestas para el usuario.

### Cobertura sociolingüística

El normalizador debe tratar con igual rigor registros coloquiales y formales, escritura no estándar, mensajes ultrabreves y dictado por voz. Los perfiles describen fenómenos conversacionales observables, no edad, género, estrato ni capacidad. Solo se corrigen variantes inequívocas; nombres de platos, direcciones y nombres propios se conservan cuando exista ambigüedad.

### ¿Cómo probar el Normalizador?

#### 1. Prueba rápida interactiva (Consola interactiva)
Ejecuta el siguiente comando para abrir la consola del normalizador en tiempo real:
```bash
python tests/interactive/normalizer_console.py
```
**5 frases recomendadas para probar:**
*   `Bro, me regala un corrientazo porfa?` *(Estandariza modismos afectuosos y jergas de almuerzos)*
*   `nea, puedo pagar el combito con dabiplata?` *(Corrige ortografía de combos, pasarelas de pago y abreviaciones)*
*   `patrón, mándeme lo de siempre xfa` *(Mapea aliases informales y abreviaciones comunes de chat)*
*   `hola buenas tardes señorita, ¿tienen platos vege o lacto?` *(Estandariza preferencias y restricciones dietarias)*
*   `tengo 25 lucas` *(Extrae montos monetarios colombianos como $25,000 en el campo de valores)*

#### 2. Evaluación de calidad en lote (Simulación masiva)
Para procesar los 450 casos de prueba y generar reportes de calidad detallados:
```bash
python tests/evaluation/evaluate_normalizer.py
```
*   **Reportes generados**: 
    *   `reports/normalizer/evaluacion_normalizador.csv`: Detalle caso por caso con las reglas aplicadas.
    *   `reports/normalizer/resultado_evaluacion.json`: Resumen cuantitativo de cambios y errores.

#### 3. Pruebas unitarias del Normalizador
Para validar de forma automatizada las aserciones de código del normalizador:
```bash
python -m unittest tests.infrastructure.test_text_normalizer_service
```

---

## Tema 2: Identificador de Productos y Conceptos Clave (PhraseMatcher)

**Foco Principal**: Identificar automáticamente los elementos concretos que menciona el cliente en la conversación (como platos específicos, categorías de comida, ingredientes, alérgenos y medios de pago). Se encarga de asociar las distintas formas de escribir que tienen los clientes a los productos oficiales del menú del restaurante, resolviendo de forma inteligente los conflictos cuando se mencionan varios términos parecidos juntos.

### ¿Cómo probar el PhraseMatcher?

#### 1. Prueba rápida interactiva (Consola interactiva)
Este interactivo primero **normaliza** el mensaje del usuario y luego extrae los conceptos clave e ingredientes identificados en el texto:
```bash
python tests/interactive/phrase_matcher_console.py
```
**5 frases recomendadas para probar:**
*   `¿Cuánto vale la mojarra frita?` *(Detecta "mojarra frita" como Plato Específico)*
*   `¿Qué arroces tienen?` *(Detecta "arroces" como Categoría del Menú)*
*   `quiero una cazuela de mariscos y dos limonaditas` *(Detecta el plato "cazuela de mariscos" y el ingrediente "mariscos")*
*   `¿Tienen platos sin gluten?` *(Detecta "gluten" como restricción de salud/alérgeno)*
*   `¿Reciben nequi?` *(Detecta "nequi" como método de pago)*

#### 2. Evaluación de calidad en lote (Simulación masiva)
Para procesar los 450 casos de prueba midiendo la precisión de la extracción:
```bash
python tests/evaluation/evaluate_phrase_matcher.py
```
*   **Reportes generados**: 
    *   `reports/phrase_matcher/evaluacion_phrase_matcher.csv`: Detalla los términos detectados y descartados por solape.
    *   `reports/phrase_matcher/resultado_phrase_matcher.json`: Métricas consolidadas del PhraseMatcher.

#### 3. Pruebas unitarias del PhraseMatcher
Para ejecutar la suite de validación automatizada de resolución de cruces de palabras en el menú:
```bash
python -m unittest tests.infrastructure.test_phrase_matcher_service
```

---

## Tema 3: Identificador de Intenciones (Matcher)

**Foco Principal**: Identificar la intención o acción que el cliente quiere realizar (ej. consultar un precio, hacer un pedido, solicitar una reserva de mesa, preguntar por medios de pago o alérgenos). Funciona mediante reglas de coincidencia de patrones y nos permite también extraer cantidades numéricas (ej. "dos" platos) y detectar condiciones negativas (ej. "sin" cebolla).

### ¿Cómo probar el Matcher?

#### 1. Prueba rápida interactiva (Consola interactiva)
Este interactivo limpia el mensaje del usuario, identifica el vocabulario del menú y luego deduce la intención del cliente en tiempo real:
```bash
python tests/interactive/matcher_console.py
```
**5 frases recomendadas para probar:**
*   `¿Cuánto vale la cazuela de mariscos?` *(Detecta la acción de consultar precio, identificando el plato)*
*   `Quiero reservar una mesa para cuatro hoy` *(Detecta solicitud de reserva y la cantidad 4)*
*   `Tráigame dos mojarras fritas por favor` *(Detecta inicio de pedido, la cantidad 2 y el plato)*
*   `¿Puedo pagar con tarjeta?` *(Detecta consulta de medios de pago)*
*   `Quiero la trucha pero sin ajo` *(Detecta solicitud de modificación y registra que hay una negación)*

#### 2. Evaluación de calidad en lote
Para medir la cobertura de evidencia sintáctica sobre los 450 casos:
```bash
python tests/evaluation/evaluate_matcher.py
```
*   **Reportes generados**: 
    *   `reports/matcher/evaluacion_matcher.csv`: Detalle de intenciones detectadas frente a las esperadas.
    *   `reports/matcher/resultado_matcher.json`: Resumen estadístico del dataset.

#### 3. Pruebas unitarias del Matcher
Para ejecutar las pruebas lógicas automatizadas de detección de intenciones:
```bash
python -m unittest tests.infrastructure.test_matcher_service
```

---

## Tema 4: Analizador de Lemas (LemmaService)

**Foco Principal**: Lematizar términos en español y generar evidencias secundarias de intención a partir de las raíces de las palabras (lemas). Funciona de forma híbrida: si el modelo en español `es_core_news_sm` está disponible, usa su motor de lematización y resuelve conflictos; si no está, recurre a `lemma_service_config.json` como fallback controlado. Adicionalmente, prioriza las formas del catálogo para garantizar que la jerga del restaurante (ej: "gracias" -> "agradecer", "alérgica" -> "alérgico") se asocie correctamente.

### ¿Cómo probar el LemmaService?

#### 1. Prueba rápida interactiva (Consola interactiva)
Este interactivo primero normaliza el texto, luego procesa cada token a su lema correspondiente y asigna pesos a evidencias secundarias:
```bash
python tests/interactive/lemma_console.py
```
**5 frases recomendadas para probar:**
*   `quiero agradecer por el gran servicio` *(Detecta "agradecer" con intención social/agradecer)*
*   `Soy alérgica a los mariscos` *(Mapea "alérgica" a "alérgico" con intención de consultar alérgenos)*
*   `¿Cuánto me costará el almuerzo?` *(Lematiza "costará" a "costar" con intención de precio)*
*   `Quisiera reservar una mesa` *(Lematiza "quisiera" a "querer" con intención de reserva)*
*   `Hola, buenas` *(Lematiza saludo con intención social/saludar)*

#### 2. Evaluación de lemas en lote
Para procesar los 450 casos evaluando la cobertura de lemas:
```bash
python -X utf8 tests/evaluation/evaluate_lemma.py
```
*   **Reportes generados**:
    *   `reports/lemma/evaluacion_lemas_dataset.csv`: Detalle de tokens, origen y apoyo a la subintención esperada.
    *   `reports/lemma/resultado_lemas.json`: Métricas consolidadas del LemmaService.

#### 3. Pruebas unitarias del LemmaService
Para ejecutar la suite de validación del lematizador y su comportamiento de fallback:
```bash
python -m unittest tests.infrastructure.test_lemma_service
```

---

## Tema 5: Parser lingüístico (`LinguisticParser`)

**Foco Principal**: Orquestar el flujo completo de procesamiento. Normaliza, extrae entidades del menú, detecta patrones sintácticos, analiza lemas y aplica el `EntityRuler`. Empaqueta el resultado en `LinguisticEvidenceBundle`.

### ¿Cómo probar el Pipeline?

#### 1. Prueba rápida interactiva (Consola interactiva del Pipeline)
Permite ingresar cualquier frase en consola y ver el bundle completo de evidencias consolidadas:
```bash
python tests/interactive/linguistic_parser_console.py
```

#### 2. Pruebas unitarias del Pipeline
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

## Tema 7: Fachada de resolución (`IntentEngine`)

**Foco Principal**: Integrar `LinguisticParser` e `IntentResolver` en una única llamada `analyze(text, context)`, retornando `ResolvedNlpResult`.

### ¿Cómo evaluar la calidad del Resolutor?

#### 1. Evaluación de calidad en lote
Para procesar los 450 casos evaluando intención, subintención, aclaración y modo de intervención:
```bash
python -X utf8 tests/evaluation/evaluate_resolver.py
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
python -X utf8 tests/contract/test_resource_contract.py
```
