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

## 4. Detalle de la Infraestructura NLP
Este diagrama hace un "zoom" dentro de `linguistic_parser.py` para mostrar cómo se apoya en los servicios ubicados en `src/infrastructure/nlp`.

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
        Categorizer["text_categorizer_service.py<br>(Extensión pendiente)"]
    end

    Parser -.->|a. Normaliza| Normalizer
    Parser -.->|b. Lemas| Lemmatizer
    Parser -.->|c. Frases| PhraseMatcher
    Parser -.->|d. Patrones| Matcher
    Parser -.->|e. Entidades| EntityRuler
    Parser -.->|f. Integración futura| Categorizer

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

## 5. Flujo Completo con Capa de Infraestructura

Este es el mapa consolidado del sistema. Las flechas continuas representan el flujo implementado actualmente; las flechas discontinuas hacia Estado y APIs representan los puntos de extensión documentados para la Fase 4.

```mermaid
flowchart TD
    Cliente(("Usuario / Aplicación cliente"))

    subgraph Aplicacion ["Capa de Aplicación (src/temp)"]
        Orchestrator{"DialogueOrchestrator<br/>dialogue_orchestrator.py"}
        Parser["LinguisticParser<br/>linguistic_parser.py"]
        Mapper["LinguisticEvidenceMapper<br/>linguistic_evidence_mapper.py"]
        Resolver["IntentResolver<br/>intent_resolver.py"]
        Renderer["ResponseRenderer<br/>response_renderer.py"]
    end

    subgraph Infraestructura ["Capa de Infraestructura (src/infrastructure)"]
        subgraph InfraNLP ["nlp/ - Implementado"]
            ServiciosNLP[["TextNormalizerService<br/>PhraseMatcherService<br/>MatcherService<br/>LemmaService<br/>EntityRulerService"]]
        end

        subgraph InfraEstado ["state/ - Placeholder Fase 4"]
            DialogueState["dialogue_state.py<br/>Memoria conversacional"]
        end

        subgraph InfraAPI ["api/ - Placeholder Fase 4"]
            Fulfillment["fulfillment_service.py<br/>APIs y operaciones de negocio"]
        end
    end

    subgraph Recursos ["Recursos de configuración"]
        NLPConfig[["src/infrastructure/resources/<br/>Configuración de servicios NLP"]]
        MappingConfig[["linguistic_evidence_mapping.json"]]
        ResolverConfig[["intents_and_subintents.json<br/>conversation_action_rules.json"]]
        ResponseConfig[["response_templates.json"]]
    end

    Cliente -->|"1. analyze(text, context, response_values)"| Orchestrator

    Orchestrator -->|"2. analyze(text)"| Parser
    Parser <-->|"3. Señales NLP crudas"| ServiciosNLP
    Parser -->|"4. ParsedNLPBundle"| Orchestrator

    Orchestrator -->|"5. map_bundle(parsed_bundle)"| Mapper
    Mapper -->|"6. LinguisticEvidenceBundle"| Orchestrator

    Orchestrator -->|"7. resolve(evidence, context)"| Resolver
    Resolver -->|"8. IntentResolution"| Orchestrator

    Orchestrator -->|"9. render(resolution, response_values)"| Renderer
    Renderer -->|"10. RenderedResponse"| Orchestrator
    Orchestrator -->|"11. ResolvedNlpResult"| Cliente

    NLPConfig -.-> ServiciosNLP
    MappingConfig -.-> Mapper
    ResolverConfig -.-> Resolver
    ResponseConfig -.-> Renderer

    Orchestrator -.->|"Fase 4: leer/escribir contexto"| DialogueState
    Orchestrator -.->|"Fase 4: consultar/ejecutar operaciones"| Fulfillment

    classDef placeholder fill:#fff3cd,stroke:#b8860b,stroke-dasharray: 5 5,color:#5f4500;
    class DialogueState,Fulfillment placeholder;
```

### Estado de cada bloque

| Bloque | Ruta | Estado |
|---|---|---|
| Servicios NLP | `src/infrastructure/nlp/` | Implementados e integrados mediante `LinguisticParser` |
| Estado conversacional | `src/infrastructure/state/dialogue_state.py` | Placeholder; todavía no es invocado |
| APIs y operaciones | `src/infrastructure/api/fulfillment_service.py` | Placeholder; todavía no es invocado |
| Pipeline de aplicación | `src/temp/` | Implementado hasta `ResolvedNlpResult` |
