# Jerarquía y Flujo Conceptual de Recursos (temp/resources)

Este documento representa cómo interactúan las definiciones de origen, tanto a nivel conceptual (entre los archivos JSON) como a nivel técnico (con el código Python).

## 1. Flujo Conceptual (Solo Archivos JSON)
Este diagrama muestra la relación lógica entre los archivos de configuración. Muestra cómo la información viaja desde la taxonomía hasta convertirse en una respuesta (El ciclo de "Oídos al Cerebro a la Boca"):

```mermaid
flowchart TD
    intents_and_subintents.json --> linguistic_evidence_mapping.json
    intents_and_subintents.json --> conversation_action_rules.json
    
    %% El ciclo de vida conceptual
    linguistic_evidence_mapping.json -- "1. Entrega Intención (Oídos al Cerebro)" --> conversation_action_rules.json
    conversation_action_rules.json -- "2. Ordena Respuesta (Cerebro a la Boca)" --> response_templates.json
    linguistic_evidence_mapping.json -. "Mapeo Directo (Bypass)" .-> response_templates.json
```

## 2. Flujo de Arquitectura y Ejecución (Python + JSON)
Este diagrama muestra la realidad técnica. Los archivos JSON no tienen vida propia; son consumidos como "manuales de instrucciones" por el Gestor de Diálogo (los scripts `.py`).

```mermaid
flowchart TD
    %% El Motor de Python que orquesta todo
    Engine(("Gestor de Diálogo<br>(Scripts .py)"))

    %% Archivos de Configuración (JSON)
    intents_and_subintents.json -. "Define la taxonomía" .-> Engine
    linguistic_evidence_mapping.json -. "Reglas para traducir texto" .-> Engine
    conversation_action_rules.json -. "Políticas de negocio" .-> Engine
    response_templates.json -. "Guiones de texto" .-> Engine

    %% El ciclo de vida real del procesamiento
    Cliente(("Usuario")) -- "1. Texto de entrada" --> Engine
    Engine -- "2. Consulta NLU" --> linguistic_evidence_mapping.json
    Engine -- "3. Consulta Lógica" --> conversation_action_rules.json
    Engine -- "4. Extrae Respuesta" --> response_templates.json
    Engine -- "5. Respuesta final" --> Cliente
```

### Explicación del Flujo (Arquitectura)

1. **El Origen Semántico (`intents_and_subintents.json`)**: Es el punto de inicio. Define las intenciones y subintenciones de negocio. Esta taxonomía fluye hacia abajo para estructurar:
   * Las reglas que mapean palabras reales a intenciones (`linguistic_evidence_mapping.json`).
   * Las acciones que guían la conversación cuando se detecta esa intención (`conversation_action_rules.json`).

2. **El Puente NLU $\rightarrow$ NLG (`response_templates.json`)**:
   * Cuando el modelo identifica una intención en `linguistic_evidence_mapping.json` (ej: `pedido.cancelar_pedido`), el Gestor de Diálogo cruza el puente utilizando el mapa `direct_response_by_intent_and_subintent`.
   * Esto conecta el ID de la intención NLU directamente con el ID de la plantilla NLG (ej: `order_cancel_confirm`).
   * Aquí mismo se definen las variables (`required_values`) que el sistema debe extraer (ej. `{product}`) para poder entregar la respuesta.

3. **Coherencia Cruzada (Reglas $\leftrightarrow$ Plantillas)**: 
   * Trabajan en equipo (representado por la flecha doble). Si el flujo conversacional de una intención termina sin lanzar una acción especial en las reglas, el sistema exige que exista obligatoriamente una plantilla de respuesta directa para ese caso en los templates.

## 3. Flujo de Orquestación Interna (Solo Scripts de Python)
Este diagrama detalla cómo `dialogue_orchestrator.py` hace visible el pipeline completo y mantiene independientes la extracción y la traducción de señales:

```mermaid
flowchart TD
    Cliente(("Usuario")) -->|1. Texto| Engine["dialogue_orchestrator.py<br>(El Director de Orquesta)"]

    %% Oídos
    Engine -->|2. Envía texto| Parser["linguistic_parser.py<br>(Motor NLP SpaCy)"]
    Parser -->|3. Retorna ParsedNLPBundle| Engine
    Engine -->|4. Envía señales crudas| Mapper["linguistic_evidence_mapper.py<br>(Traductor)"]
    Mapper -->|5. Retorna LinguisticEvidenceBundle| Engine

    %% Cerebro
    Engine -->|6. Envía Intención| Resolver["intent_resolver.py<br>(El Cerebro Lógico)"]
    Resolver -->|7. Retorna Acción| Engine

    %% Boca
    Engine -->|8. Envía Acción| Renderer["response_renderer.py<br>(La Boca)"]
    Renderer -->|9. Retorna Mensaje| Engine

    Engine -->|10. Respuesta Final| Cliente
```

## 4. Flujo Completo con Capa de Infraestructura (Servicios NLP)
Para tener la fotografía completa del sistema, este diagrama hace un "zoom" dentro de los Oídos (`linguistic_parser.py`) para mostrar cómo se apoya en los distintos servicios de procesamiento natural ubicados en `src/infrastructure/nlp`.

```mermaid
flowchart TD
    Cliente(("Usuario")) -->|1. Texto| Engine["dialogue_orchestrator.py<br>(Director)"]

    %% Oídos / Lógica de Mapeo
    Engine -->|2. Analizar| Parser["linguistic_parser.py<br>(Core NLP)"]

    %% Infraestructura NLP
    subgraph Infraestructura ["Capa de Infraestructura (src/infrastructure/nlp)"]
        direction TB
        Normalizer["text_normalizer_service.py<br>(Limpieza)"]
        Lemmatizer["lemma_service.py<br>(Lematización)"]
        PhraseMatcher["phrase_matcher_service.py<br>(Búsqueda exacta)"]
        Matcher["matcher_service.py<br>(Patrones)"]
        EntityRuler["entity_ruler_service.py<br>(Entidades)"]
        Categorizer["text_categorizer_service.py<br>(Clasificación)"]
    end

    Parser -.->|a. Normaliza| Normalizer
    Parser -.->|b. Lemas| Lemmatizer
    Parser -.->|c. Frases| PhraseMatcher
    Parser -.->|d. Patrones| Matcher
    Parser -.->|e. Entidades| EntityRuler
    Parser -.->|f. Clasifica| Categorizer

    Parser -->|3. Retorna ParsedNLPBundle| Engine
    Engine -->|4. Traducir señales| Mapper["linguistic_evidence_mapper.py"]
    Mapper -->|5. Retorna LinguisticEvidenceBundle| Engine

    %% Cerebro y Boca simplificados
    Engine -->|6. Aplica Reglas| Resolver["intent_resolver.py"]
    Resolver -->|Retorna Acción| Engine
    Engine -->|7. Renderiza| Renderer["response_renderer.py"]
    Renderer -->|8. Retorna Mensaje| Engine
    Engine -->|9. Respuesta Final| Cliente
```

## 5. Arquitectura del Futuro (Integración con APIs y Memoria)
Este diagrama muestra el mapa maestro definitivo de cómo se vería el sistema en la **Fase 4** (Conexión a Bases de Datos y Memoria), incluyendo todas las capas de infraestructura.

```mermaid
flowchart TD
    Cliente(("👤 Usuario"))
    Engine{"dialogue_orchestrator.py<br>👑 Director"}

    %% Bases de datos y memoria
    subgraph InfraEstado ["💾 Infraestructura de Memoria"]
        Memoria["dialogue_state.py"]
    end

    %% APIs y ejecución
    subgraph InfraAPI ["🔌 Infraestructura de APIs"]
        Ejecutor["fulfillment_service.py"]
    end

    %% Desagregación NLU
    Mapper["linguistic_evidence_mapper.py<br>👂 Los Oídos (Traductor)"]
    Parser["linguistic_parser.py<br>⚙️ Fachada NLP"]

    subgraph InfraNLP ["📚 Infraestructura NLP"]
        direction TB
        ServiciosNLP[["Normalizer<br>Lemmatizer<br>PhraseMatcher<br>Matcher<br>EntityRuler"]]
    end

    %% Reglas y Respuesta
    subgraph CapaLogica ["🧠 Cerebro y 👄 Boca"]
        Resolver["intent_resolver.py"]
        Renderer["response_renderer.py"]
    end

    %% Interacciones
    Cliente -->|"1. Texto"| Engine
    Engine -->|"10. Respuesta"| Cliente

    Engine <-->|"2. Lee/Escribe Contexto"| Memoria

    %% Flujo NLU
    Engine -->|"3. Extraer señales NLP"| Parser
    Parser -.->|"a. Llama a"| InfraNLP
    Parser -->|"4. Retorna señales crudas"| Engine
    Engine -->|"5. Traducir señales"| Mapper
    Mapper -->|"6. Retorna Intención Limpia"| Engine

    %% Flujo Cerebro
    Engine -->|"7. Intención + Contexto"| Resolver
    Resolver -->|"8. Decide Acción"| Engine

    %% Flujo Ejecución
    Engine <-->|"8b. Guardar/Conectar BD"| Ejecutor

    %% Flujo Boca
    Engine -->|"9. Renderizar texto"| Renderer
    Renderer -->|"9b. Retorna Mensaje"| Engine
```

## 6. Arquitectura Recomendada (Orchestrator como Director Puro)
Este diagrama muestra la arquitectura aplicada al pipeline central: `DialogueOrchestrator` coordina a `LinguisticParser` y `LinguisticEvidenceMapper` de forma **separada e independiente**. Cada clase tiene exactamente un trabajo y el orquestador es el único que conoce el pipeline completo. `dialogue_state.py` y `fulfillment_service.py` ya existen como placeholders documentados; su implementación e integración continúan reservadas para la Fase 4 descrita en el diagrama 5.

```mermaid
flowchart TD
    Cliente(("👤 Usuario"))
    Orchestrator{"dialogue_orchestrator.py<br>👑 Director"}

    %% NLU: dos clases con un solo trabajo cada una
    Parser["linguistic_parser.py<br>⚙️ Fachada NLP<br>Solo extrae señales crudas"]
    Mapper["linguistic_evidence_mapper.py<br>👂 Traductor<br>Solo traduce señales a intenciones"]

    subgraph InfraNLP ["📚 Infraestructura NLP"]
        direction TB
        ServiciosNLP[["Normalizer<br>Lemmatizer<br>PhraseMatcher<br>Matcher<br>EntityRuler"]]
    end

    subgraph CapaLogica ["🧠 Cerebro y 👄 Boca"]
        Resolver["intent_resolver.py"]
        Renderer["response_renderer.py"]
    end

    subgraph InfraEstado ["💾 Infraestructura de Memoria"]
        Memoria["dialogue_state.py"]
    end

    subgraph InfraAPI ["🔌 Infraestructura de APIs"]
        Ejecutor["fulfillment_service.py"]
    end

    %% Flujo principal
    Cliente -->|"1. Texto"| Orchestrator
    Orchestrator -->|"10. Respuesta"| Cliente

    Orchestrator <-->|"2. Lee/Escribe Contexto"| Memoria

    %% Flujo NLU - DialogueOrchestrator coordina cada paso por separado
    Orchestrator -->|"3. Extraer señales crudas"| Parser
    Parser -.->|"a. Usa servicios"| InfraNLP
    Parser -->|"4. ParsedNLPBundle"| Orchestrator

    Orchestrator -->|"5. Traducir señales"| Mapper
    Mapper -->|"6. LinguisticEvidenceBundle"| Orchestrator

    %% Flujo Cerebro
    Orchestrator -->|"7. Intención + Contexto"| Resolver
    Resolver -->|"8. Decide Acción"| Orchestrator

    %% Flujo Ejecución
    Orchestrator <-->|"8b. Guardar/Consultar BD"| Ejecutor

    %% Flujo Boca
    Orchestrator -->|"9. Renderizar texto"| Renderer
    Renderer -->|"9b. Retorna Mensaje"| Orchestrator
```

### Diferencias clave vs. Diagrama 5

| Aspecto | Diagrama 5 (diseño anterior) | Diagrama 6 (pipeline aplicado) |
|---|---|---|
| **Quién orquesta NLU** | El Mapper llama al Parser internamente | `DialogueOrchestrator` coordina Parser y Mapper por separado |
| **Responsabilidad del Mapper** | Traduce Y coordina | Solo traduce |
| **Responsabilidad del Parser** | Solo extrae señales | Solo extrae señales ✅ |
| **Legibilidad del pipeline** | Oculto dentro del Mapper | Visible en `DialogueOrchestrator` |
| **Testabilidad** | Mapper necesita un Parser real o mock anidado | Cada clase se mockea de forma independiente |
