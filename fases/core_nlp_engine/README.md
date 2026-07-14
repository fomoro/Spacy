# Procesador NLP del Restaurante (Normalizador, PhraseMatcher y Matcher de Intenciones)

Este componente centraliza el procesamiento de lenguaje natural (NLP) en tres grandes áreas temáticas: la limpieza y estandarización del texto, la extracción de platos/ingredientes de nuestro menú, y la identificación de intenciones del cliente mediante reglas semánticas y sintácticas.

---

## Estructura por Temas

El procesador está diseñado bajo una estricta separación de responsabilidades:

```text
fase_4_normalizador_integrado/
│
├── data/                          # Dataset de prueba de 400 casos (10 perfiles) y casos contrato
├── resources/                     # Configuraciones y diccionarios
│   ├── normalizer/                # Tema 1: Configuración del normalizador
│   ├── phrase_matcher/            # Tema 2: Catálogo de platos y términos clave del menú
│   ├── matcher/                   # Tema 3: Catálogo de patrones de intención
│   └── lemma/                     # Tema 4: Catálogo de lemas y formas
├── src/                           # Código fuente
│   ├── application/               # Capa de aplicación (orquestador del pipeline)
│   └── infrastructure/            # Capa de infraestructura (loaders y servicios)
│       ├── loaders/               # Cargadores de configuraciones JSON
│       └── services/              # Servicios core de procesamiento de texto con spaCy
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
    *   [evaluacion_normalizador.csv](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/reports/normalizer/evaluacion_normalizador.csv): Detalle caso por caso con las reglas aplicadas en un arreglo (ej: `["lowercase", "phrase:me regala"]`).
    *   [resultado_evaluacion.json](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/reports/normalizer/resultado_evaluacion.json): Resumen cuantitativo de cambios y errores.

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
    *   [evaluacion_phrase_matcher.csv](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/reports/phrase_matcher/evaluacion_phrase_matcher.csv): Detalla los platos y términos detectados (así como los descartados por repetición o solape) en cada caso de prueba.
    *   [resultado_phrase_matcher.json](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/reports/phrase_matcher/resultado_phrase_matcher.json): Métricas consolidadas del PhraseMatcher.

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
    *   [evaluacion_matcher.csv](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/reports/matcher/evaluacion_matcher.csv): Detalle de intenciones detectadas frente a las esperadas para cada caso.
    *   [resultado_matcher.json](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/reports/matcher/resultado_matcher.json): Resumen estadístico y porcentaje de cobertura exacta del contrato.

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
    *   [evaluacion_lemas_contrato.csv](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/reports/lemma/evaluacion_lemas_contrato.csv): Detalle de tokens lematizados, origen (spacy, catalog_fallback, surface) y si apoyan la subintención esperada.
    *   [resultado_lemas.json](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/reports/lemma/resultado_lemas.json): Métricas consolidadas del LemmaService.

#### 3. Pruebas unitarias del LemmaService
Para ejecutar la suite de validación del lematizador y su comportamiento de fallback:
```bash
python -m unittest tests/lemma/test_lemma.py
```

---

## Tema 5: Pipeline de Evidencias Integrado (NlpEvidencePipeline)

**Foco Principal**: Orquestar el flujo secuencial completo de procesamiento NLP. Toma el mensaje original del usuario, lo limpia (Normalizador), extrae las entidades (PhraseMatcher), detecta intenciones por reglas sintácticas (Matcher) y extrae lemas con intenciones secundarias (LemmaService). Empaqueta todo en un objeto inmutable de datos (`NlpEvidenceBundle`) listo para ser consumido por el resolutor de intenciones.

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

**Foco Principal**: Decidir la intención y subintención final del cliente basándose en el bundle de evidencias (`NlpEvidenceBundle`), el contexto conversacional del diálogo (ej. `producto_activo`) y las prioridades de negocio configuradas (como seguridad alimentaria o precios sobre deseos genéricos). No genera respuestas comerciales, solo retorna la intención resuelta, si requiere aclaración (`requires_clarification`) y el estado general (`resolved`, `ambiguous`, `unknown`).

### ¿Cómo probar el Resolutor?

#### 1. Pruebas unitarias del Resolutor
Para validar de forma automatizada las reglas de precedencia, pesos de intención y resolución de contextos:
```bash
python -m unittest tests/resolver/test_intent_resolver.py
```

---

## Tema 7: Pipeline de Análisis Resuelto (ResolvedNlpPipeline)

**Foco Principal**: Actuar como una interfaz simplificada (Facade) que integra todo el flujo secuencial de extracción de evidencias (Tema 5) y la resolución de intención final (Tema 6) en una única llamada, tomando el mensaje original y el contexto.

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
