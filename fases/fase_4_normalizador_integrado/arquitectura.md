# Arquitectura del Normalizador

Este documento describe la estructura organizativa, responsabilidades y límites técnicos del componente de normalización de texto.

**Foco Principal del Componente**: Este componente implementa *exclusivamente* la normalización y limpieza controlada del mensaje. Su único objetivo es tomar el texto en bruto ingresado por el usuario final, corregir problemas tipográficos, ortografía común y jerga local, y retornar un texto estandarizado y uniforme. Queda explícitamente fuera de su alcance la detección de intenciones, la extracción de entidades de negocio (productos) y la generación de cualquier tipo de respuesta.

## Estructura del Proyecto

A continuación se detalla la distribución de archivos y carpetas del componente, junto con la función específica de cada uno:

```text
fase_4_normalizador_integrado/
│
├── data/                          # DATOS DE ENTRADA (Datasets)
│   ├── dataset_clientes.json      # Mensajes reales recopilados para pruebas e histórico
│   └── dataset_clientes.csv      
│
├── reports/                       # SALIDAS (Reportes generados por la evaluación)
│   ├── evaluacion_normalizador.csv  # Archivo detallado con la normalización de cada mensaje
│   └── resultado_evaluacion.json  # Estadísticas consolidadas (errores, cambios, totales)
│
├── resources/                     # CONFIGURACIONES Y DICCIONARIOS
│   │
│   ├── normalizer/                # Configuración activa del normalizador (dividida en 7 secciones)
│   │   ├── metadata.json          # Metadatos del archivo de configuración (versión, idioma, fase)
│   │   ├── options.json           # Opciones técnicas de limpieza (lowercase, unicode_form, etc.)
│   │   ├── orthographic_replacements.json # Correcciones ortográficas y aliases individuales
│   │   ├── phrase_replacements.json       # Reemplazos para frases compuestas complejas
│   │   ├── monetary_slang.json    # Mapeo de valores de jerga de dinero ("lucas" -> 1000)
│   │   ├── non_semantic_tokens.json       # Palabras sin relevancia semántica (vocativos)
│   │   └── rules.json             # Reglas y principios lógicos para desarrolladores
│   │
│   └── nlp_rules/                 # Reglas y patrones para procesamiento NLP futuro
│       └── protected_patterns.json# Expresiones regulares para identificar direcciones, teléfonos, etc.
│
├── src/                           # CÓDIGO FUENTE (Lógica de procesamiento)
│   │
│   ├── infrastructure/
│   │   └── json_loader.py         # Carga segura y unificación de archivos JSON de configuración
│   │
│   └── nlp/
│       └── normalizer.py          # Clase TextNormalizer y lógica de transformación
│
├── tests/                         # PRUEBAS Y VALIDACIONES
│   ├── test_normalizer.py         # Pruebas unitarias de software (cobertura técnica)
│   ├── evaluate_normalizer.py     # Script evaluador por lote sobre el dataset de clientes
│   └── interactive_test.py        # Probador en tiempo real por consola para humanos
│
├── assets/                        # RECURSOS ESTÁTICOS
│   └── menu_mar_azul_del_pacifico.pdf # Menú oficial digitalizado del restaurante
│
├── README.md                      # Documentación del proyecto orientada a negocio
├── arquitectura.md                # Este documento (arquitectura técnica)
└── requirements.txt               # Lista de dependencias del entorno de Python
```

---

## Detalle de la Configuración del Normalizador (`resources/normalizer/`)

Para evitar un archivo de configuración monolítico y facilitar el mantenimiento de las reglas, la configuración del normalizador se ha dividido en 7 archivos JSON independientes en [resources/normalizer/](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/resources/normalizer/):

1.  **`metadata.json`**: Contiene información de control administrativo (versión del esquema, idioma `es-CO` y número de la fase actual).
2.  **`options.json`**: Contiene modificadores booleanos (`true`/`false`) para activar o desactivar transformaciones técnicas básicas en el normalizador (como minúsculas, espaciado de puntuación, y conversión Unicode).
3.  **`orthographic_replacements.json`**: Mapea palabras individuales mal escritas o abreviaciones a su versión corregida estándar (ej. `domisilio` -> `domicilio`, `vale` -> `valer`). Se aplican con límites de palabra para evitar errores colaterales.
4.  **`phrase_replacements.json`**: Mapea frases de varias palabras o modismos típicos (ej. `xfa` -> `por favor`, `cuanto balen` -> `cuánto valen`). Se procesan antes que las palabras sueltas.
5.  **`monetary_slang.json`**: Define los términos coloquiales colombianos para referirse a dinero (como `luca` y `lucas`) junto con su multiplicador numérico correspondiente (`1000`). Esto permite al normalizador traducir de forma estructurada frases como "veinte lucas" a un valor de `$20,000`.
6.  **`non_semantic_tokens.json`**: Lista de palabras o expresiones de relleno (vocativos como `parce` o `mijo`) que no aportan significado semántico a la intención de compra del cliente y que son de utilidad para fases de filtrado subsiguientes.
7.  **`rules.json`**: Lista de directrices de lógica e integridad bajo las cuales debe operar el normalizador (sirve como documentación y restricción técnica para el programador).

---

## Responsabilidades de Componentes Código

*   `TextNormalizer`: Ejecuta la secuencia ordenada de limpieza (Unicode, minúsculas, reemplazo de frases cortas, aliases, puntuación y extracción de jerga monetaria como "lucas" $\rightarrow$ `1000`).
*   `NormalizationResult`: Contenedor inmutable que almacena el texto original, el texto normalizado, las transformaciones secuenciales aplicadas y los montos monetarios extraídos.
*   `json_loader`: Carga archivos JSON de forma segura verificando tipos de datos y controlando errores de formato.

---

## Límites de Diseño

*   **No semántica**: El normalizador no asume intenciones, no decide si una palabra es un producto del menú y no responde al usuario.
*   **Sin autocorrectores abiertos**: No se utiliza autocorrección general (como diccionarios automáticos tipo Aspell) para evitar deformar nombres de platos, calles o personas. Todo cambio debe estar especificado explícitamente en el catálogo de aliases.
*   **Conservación**: No elimina palabras clave críticas como negaciones (ej. "no", "sin") o preguntas de aclaración.

---

## Dependencias

*   El normalizador utiliza **exclusivamente la biblioteca estándar de Python** (módulos `re`, `unicodedata`, `json`, `pathlib`, etc.).
*   La integración con la biblioteca `spaCy` (para análisis gramatical avanzado, lematización, Matcher y PhraseMatcher) se implementará en módulos posteriores sobre la salida de este normalizador.

---

## Riesgos Controlados

*   **Reemplazos parciales indeseados**: Se implementan límites de palabra mediante expresiones regulares (`\b` o `(?<!\w)...(?!\w)`) para evitar que "domi" reemplace palabras como "domingo".
*   **Pérdida de trazabilidad**: Toda transformación se documenta con la regla que la originó, el texto antes del cambio y el texto posterior, permitiendo auditoría.
