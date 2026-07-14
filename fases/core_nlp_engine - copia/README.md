# `core_nlp_engine`

Motor NLP para normalización, extracción de entidades, análisis lingüístico y resolución de intenciones del restaurante.

---

## Estructura por Temas

El procesador está diseñado bajo una estricta separación de responsabilidades:

```text
core_nlp_engine/
│
├── data/                          # Datasets existentes; aún no se amplían a los 15 perfiles
├── resources/
│   ├── README.md                  # Gobernanza y mantenimiento de recursos
│   ├── nlp/                       # Taxonomía y configuración lingüística
│   │   ├── intent_taxonomy.json
│   │   ├── normalizer_config.json
│   │   ├── matcher_patterns.json
│   │   ├── lemma_signals.json
│   │   ├── entity_ruler_patterns.json
│   │   └── resolver_config.json
│   ├── dialogue/                  # Completitud e intervención conversacional
│   │   └── clarification_policy.json
│   ├── menu/                      # Vocabulario, ofertas y precios
│   │   ├── menu_catalog.json
│   │   └── menu_offerings.json
│   └── profiles/                  # Cobertura conversacional para diseño y evaluación
│       └── conversation_profiles.json
├── src/                           # Código fuente
│   ├── application/               # Parser, resolutor y fachada IntentEngine
│   └── infrastructure/nlp/        # Servicios lingüísticos autónomos con spaCy
├── tests/                         # Pruebas e interactivos por tema
│   ├── normalizer/                # tests, evaluador e interactivo del normalizador
│   ├── phrase_matcher/            # tests, evaluador e interactivo del PhraseMatcher
│   ├── matcher/                   # tests, evaluador e interactivo del Matcher de Intenciones
│   └── lemma/                     # tests, evaluador e interactivo del Analizador de Lemas
└── reports/                       # Reportes generados automáticamente por tema
    ├── normalizer/
    ├── phrase_matcher/
    ├── matcher/
    └── lemma/
```

---

## Tema 1: Normalizador de Texto (Limpiador)

**Foco Principal**: Limpieza controlada y estandarización de español colombiano. Su única responsabilidad es preparar el mensaje del cliente antes de que sea procesado por los extractores. **No** detecta intenciones, **no** extrae platos del menú ni genera respuestas para el usuario.

### Mitigación de Sesgos Sociolingüísticos
Un objetivo crítico de este normalizador es **evitar el sesgo poblacional**. El catálogo ha sido expandido meticulosamente para cubrir todos los perfiles de clientes de nuestro negocio. No solo estandariza la jerga informal o urbana (ej. *"bro"*, *"nea"*, *"corrientazo"*), sino que procesa con la misma eficacia las abreviaciones corporativas de oficinistas (ej. *"rut"*, *"fact"*, *"cotiza"*), el lenguaje respetuoso de adultos mayores (ej. *"mi hijito"*, *"doña"*) y la terminología de dietas/restricciones (ej. *"vege"*, *"lacto"*). Esto garantiza que el chatbot atienda con el mismo nivel de precisión y equidad a cualquier tipo de cliente.

### ¿Cómo probar el Normalizador?

#### 1. Prueba rápida interactiva (Consola interactiva)
Ejecuta el siguiente comando para abrir la consola del normalizador en tiempo real:
```bash
python tests/normalizer/interactive_test.py
```
**5 frases recomendadas para probar:**
*   `Bro, me regala un corrientazo porfa?` *(Estandariza modismos afectuosos y jergas de almuerzos)*
*   `nea, puedo pagar el combito con dabiplata?` *(Corrige ortografía de combos, pasarelas de pago y abreviaciones)*
*   `patrón, mándeme lo de siempre xfa` *(Mapea aliases informales y abreviaciones comunes de chat)*
*   `hola buenas tardes señorita, ¿tienen platos vege o lacto?` *(Estandariza preferencias y restricciones dietarias)*
*   `tengo 25 lucas` *(Extrae montos monetarios colombianos como $25,000 en el campo de valores)*

#### 2. Evaluación de calidad en lote (Simulación masiva)
Para procesar los 400 casos de prueba y generar reportes de calidad detallados:
```bash
python tests/normalizer/evaluate_normalizer.py
```
*   **Reportes generados**: 
    *   `reports/normalizer/evaluacion_normalizador.csv`: Detalle caso por caso con las reglas aplicadas.
    *   `reports/normalizer/resultado_evaluacion.json`: Resumen cuantitativo de cambios y errores.

#### 3. Pruebas unitarias del Normalizador
Para validar de forma automatizada las aserciones de código del normalizador:
```bash
python -m unittest tests/normalizer/test_normalizer.py
```

---

## Tema 2: Identificador de Productos y Conceptos Clave (PhraseMatcher)

**Foco Principal**: Identificar automáticamente los elementos concretos que menciona el cliente en la conversación (como platos específicos, categorías de comida, ingredientes, alérgenos y medios de pago). Se encarga de asociar las distintas formas de escribir que tienen los clientes a los productos oficiales del menú del restaurante, resolviendo de forma inteligente los conflictos cuando se mencionan varios términos parecidos juntos.

### ¿Cómo probar el PhraseMatcher?

#### 1. Prueba rápida interactiva (Consola interactiva)
Este interactivo primero **normaliza** el mensaje del usuario y luego extrae los conceptos clave e ingredientes identificados en el texto:
```bash
python tests/phrase_matcher/interactive_test.py
```
**5 frases recomendadas para probar:**
*   `¿Cuánto vale la mojarra frita?` *(Detecta "mojarra frita" como Plato Específico)*
*   `¿Qué arroces tienen?` *(Detecta "arroces" como Categoría del Menú)*
*   `quiero una cazuela de mariscos y dos limonaditas` *(Detecta el plato "cazuela de mariscos" y el ingrediente "mariscos")*
*   `¿Tienen platos sin gluten?` *(Detecta "gluten" como restricción de salud/alérgeno)*
*   `¿Reciben nequi?` *(Detecta "nequi" como método de pago)*

#### 2. Evaluación de calidad en lote (Simulación masiva)
Para procesar los 400 casos de prueba midiendo la precisión de la extracción:
```bash
python tests/phrase_matcher/evaluate_phrase_matcher.py
```
*   **Reportes generados**: 
    *   `reports/phrase_matcher/evaluacion_phrase_matcher.csv`: Detalla los términos detectados y descartados por solape.
    *   `reports/phrase_matcher/resultado_phrase_matcher.json`: Métricas consolidadas del PhraseMatcher.

#### 3. Pruebas unitarias del PhraseMatcher
Para ejecutar la suite de validación automatizada de resolución de cruces de palabras en el menú:
```bash
python -m unittest tests/phrase_matcher/test_phrase_matcher.py
```

---

## Tema 3: Identificador de Intenciones (Matcher)

**Foco Principal**: Identificar la intención o acción que el cliente quiere realizar (ej. consultar un precio, hacer un pedido, solicitar una reserva de mesa, preguntar por medios de pago o alérgenos). Funciona mediante reglas de coincidencia de patrones y nos permite también extraer cantidades numéricas (ej. "dos" platos) y detectar condiciones negativas (ej. "sin" cebolla).

### ¿Cómo probar el Matcher?

#### 1. Prueba rápida interactiva (Consola interactiva)
Este interactivo limpia el mensaje del usuario, identifica el vocabulario del menú y luego deduce la intención del cliente en tiempo real:
```bash
python tests/matcher/interactive_test.py
```
**5 frases recomendadas para probar:**
*   `¿Cuánto vale la cazuela de mariscos?` *(Detecta la acción de consultar precio, identificando el plato)*
*   `Quiero reservar una mesa para cuatro hoy` *(Detecta solicitud de reserva y la cantidad 4)*
*   `Tráigame dos mojarras fritas por favor` *(Detecta inicio de pedido, la cantidad 2 y el plato)*
*   `¿Puedo pagar con tarjeta?` *(Detecta consulta de medios de pago)*
*   `Quiero la trucha pero sin ajo` *(Detecta solicitud de modificación y registra que hay una negación)*

#### 2. Evaluación de calidad en lote (Contrato de intenciones)
Para verificar la precisión del clasificador de intenciones contra los 105 casos del contrato:
```bash
python tests/matcher/evaluate_matcher.py
```
*   **Reportes generados**: 
    *   `reports/matcher/evaluacion_matcher.csv`: Detalle de intenciones detectadas frente a las esperadas.
    *   `reports/matcher/resultado_matcher.json`: Resumen estadístico del contrato.

#### 3. Pruebas unitarias del Matcher
Para ejecutar las pruebas lógicas automatizadas de detección de intenciones:
```bash
python -m unittest tests/matcher/test_matcher.py
```

---

## Tema 4: Analizador de Lemas (LemmaService)

**Foco Principal**: Lematizar términos en español y generar evidencias secundarias de intención a partir de las raíces de las palabras (lemas). Funciona de forma híbrida: si el modelo en español `es_core_news_sm` está disponible, usa su motor de lematización y resuelve conflictos; si no está, recurre a un catálogo estático (`lemma_catalog.json`) como fallback. Adicionalmente, prioriza las formas del catálogo para garantizar que la jerga del restaurante (ej: "gracias" -> "agradecer", "alérgica" -> "alérgico") se asocie correctamente.

### ¿Cómo probar el LemmaService?

#### 1. Prueba rápida interactiva (Consola interactiva)
Este interactivo primero normaliza el texto, luego procesa cada token a su lema correspondiente y asigna pesos a evidencias secundarias:
```bash
python tests/lemma/interactive_test.py
```
**5 frases recomendadas para probar:**
*   `quiero agradecer por el gran servicio` *(Detecta "agradecer" con intención social/agradecer)*
*   `Soy alérgica a los mariscos` *(Mapea "alérgica" a "alérgico" con intención de consultar alérgenos)*
*   `¿Cuánto me costará el almuerzo?` *(Lematiza "costará" a "costar" con intención de precio)*
*   `Quisiera reservar una mesa` *(Lematiza "quisiera" a "querer" con intención de reserva)*
*   `Hola, buenas` *(Lematiza saludo con intención social/saludar)*

#### 2. Evaluación de lemas en lote
Para procesar los 105 casos del contrato evaluando la cobertura de lemas:
```bash
python -X utf8 tests/lemma/evaluate_lemma.py
```
*   **Reportes generados**:
    *   `reports/lemma/evaluacion_lemas_contrato.csv`: Detalle de tokens, origen y apoyo a la subintención esperada.
    *   `reports/lemma/resultado_lemas.json`: Métricas consolidadas del LemmaService.

#### 3. Pruebas unitarias del LemmaService
Para ejecutar la suite de validación del lematizador y su comportamiento de fallback:
```bash
python -m unittest tests/lemma/test_lemma.py
```

---

## Tema 5: Parser lingüístico (`LinguisticParser`)

**Foco Principal**: Orquestar el flujo completo de procesamiento. Normaliza, extrae entidades del menú, detecta patrones sintácticos, analiza lemas y aplica el `EntityRuler`. Empaqueta el resultado en `LinguisticEvidenceBundle`.

### ¿Cómo probar el Pipeline?

#### 1. Prueba rápida interactiva (Consola interactiva del Pipeline)
Permite ingresar cualquier frase en consola y ver el bundle completo de evidencias consolidadas:
```bash
python tests/pipeline_interactive.py
```

#### 2. Pruebas unitarias del Pipeline
Para ejecutar las pruebas del pipeline de evidencias:
```bash
python -m unittest tests/lemma/test_evidence_pipeline.py
```

---

## Tema 6: Resolutor de Intenciones (IntentResolver)

**Foco Principal**: Decidir la intención y subintención final basándose en `LinguisticEvidenceBundle`, el contexto conversacional y las prioridades configuradas. Vive en la capa de aplicación y no genera respuestas comerciales.

### ¿Cómo probar el Resolutor?

#### 1. Pruebas unitarias del Resolutor
Para validar de forma automatizada las reglas de precedencia, pesos de intención y resolución de contextos:
```bash
python -m unittest tests/resolver/test_intent_resolver.py
```

---

## Tema 7: Fachada de resolución (`IntentEngine`)

**Foco Principal**: Integrar `LinguisticParser` e `IntentResolver` en una única llamada `analyze(text, context)`, retornando `ResolvedNlpResult`.

### ¿Cómo evaluar la calidad del Resolutor contra el Contrato?

#### 1. Evaluación de calidad en lote (Simulación del contrato)
Para procesar los 105 casos del contrato evaluando la precisión de la resolución de intenciones y generación de aclaraciones:
```bash
python -X utf8 tests/resolver/evaluate_resolver.py
```
* **Reportes generados**:
  * [evaluacion_resolutor_contrato.csv](file:///C:/Dev/GitHub/Spacy/fases/core_nlp_engine/reports/resolver/evaluacion_resolutor_contrato.csv): Detalle caso por caso de la intención y subintención esperada vs. resuelta.
  * [resultado_resolutor.json](file:///C:/Dev/GitHub/Spacy/fases/core_nlp_engine/reports/resolver/resultado_resolutor.json): Métricas consolidadas de precisión sobre el contrato.

---

## Suite de Pruebas Unitarias Integrada

Si deseas ejecutar todas las pruebas automatizadas del proyecto (Normalizador, PhraseMatcher, Matcher, LemmaService, Pipeline y Resolutor) en una sola línea de comandos:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

Para comprobar la coherencia entre taxonomía, carta, Matcher, Lemmas, EntityRuler y Resolver:

```bash
python -X utf8 scripts/validate_resources.py
```
