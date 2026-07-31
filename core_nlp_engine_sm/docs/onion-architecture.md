# Propuesta de Estructura de Directorios (Arquitectura de Cebolla / Onion Architecture)

En este diseño, la capa más externa contiene la Infraestructura, la API y la Presentación. La capa media contiene la Aplicación (casos de uso) y la capa central contiene el Dominio (modelos de negocio puros y abstracciones).

```
src/
├── domain/                         # Capa de Dominio (Núcleo - Sin dependencias externas)
│   ├── __init__.py
│   ├── model/                      # Modelos puros y entidades de negocio
│   │   ├── taxonomy.py             # Modelos de Intents y Subintents
│   │   ├── slots.py                # Modelos de slots y clasificación de datos
│   │   ├── mapping.py              # Modelos de mapeo de evidencia lingüística
│   │   ├── dialogue.py             # Modelos de reglas de diálogo y preguntas
│   │   ├── resolution.py           # CandidateScore e IntentResolution
│   │   └── response.py             # ResponseTemplate y RenderedResponse
│   └── repository/                 # Interfaces (Abstracciones) de Repositorios
│       ├── taxonomy_repo.py
│       ├── slots_repo.py
│       ├── mapping_repo.py
│       ├── dialogue_repo.py
│       └── response_repo.py
│
├── application/                    # Capa de Aplicación (Casos de uso y orquestación)
│   ├── __init__.py
│   ├── service/                    # Servicios de aplicación que coordinan reglas
│   │   ├── evidence_mapper.py      # Traduce señales de infra a evidencia del dominio
│   │   ├── intent_resolver.py      # Resuelve la intención aplicando lógica de negocio
│   │   └── response_renderer.py    # Renderiza las respuestas basadas en la resolución
│   └── use_case/
│       ├── __init__.py
│       └── analyze_text.py         # Orquestador principal (Caso de uso del Motor NLP)
│
├── api/                            # Capa de API (Capa Externa - Endpoints HTTP, DTOs)
│   ├── __init__.py
│   ├── router/                     # Definición de rutas (ej. FastAPI)
│   │   └── chat.py
│   └── dto/                        # Data Transfer Objects (Request/Response schemas)
│       └── message.py
│
└── infrastructure/                  # Capa de Infraestructura (Capa Externa - Detalles técnicos)
    ├── __init__.py
    ├── nlp/                        # Servicios lingüísticos concretos (adaptadores spaCy)
    │   ├── text_normalizer_service.py
    │   ├── phrase_matcher_service.py
    │   ├── matcher_service.py
    │   ├── lemma_service.py
    │   └── entity_ruler_service.py
    ├── repository/                 # Implementaciones de repositorios (ej. JSON o DB)
    │   ├── json_taxonomy_repo.py
    │   ├── json_slots_repo.py
    │   ├── json_mapping_repo.py
    │   ├── json_dialogue_repo.py
    │   └── json_response_repo.py
    └── resources/                  # Archivos de configuración y reglas de negocio
        ├── nlp/                    # Ajustes de los servicios de spaCy
        │   ├── text_normalizer_service_config.json
        │   ├── phrase_matcher_service_config.json
        │   ├── matcher_service_config.json
        │   ├── lemma_service_config.json
        │   └── entity_ruler_service_config.json
        └── business_rules/         # Reglas del bot (antes en temp/resources)
            ├── intents_and_subintents.json
            ├── conversation_data_fields.json
            ├── conversation_action_rules.json
            ├── linguistic_evidence_mapping.json
            └── response_templates.json
```
