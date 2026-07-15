# Gobernanza de recursos

Este directorio reúne los archivos no Python de `core_nlp_engine`. Su objetivo es que cada elemento tenga un único propietario, pueda auditarse y cambie sin afectar responsabilidades ajenas.

## Organización

- `config/`: reglas, taxonomías y políticas.
- `config/domain/`: vocabulario canónico de intenciones y slots del negocio conversacional.
- `content/responses/es-CO/`: preguntas y plantillas lingüísticas mostrables al usuario.
- `data/`: datos reales del dominio suministrados para el funcionamiento de la aplicación.
- `data/business/`: información estable y validada del restaurante.
- `corpus/`: material lingüístico para desarrollo y experimentación.
- `corpus/datasets/`: conjuntos para entrenar, validar, probar y medir.
- `trained_models/`: artefactos entrenados consumidos por la aplicación; se creará cuando exista el primer modelo.

`config` participa en el runtime actual. Los archivos de `data` conservan la información suministrada por el usuario y deben superar su contrato antes de utilizarse. El contenido de `corpus` no se inyecta al motor en producción.

## Criterios del dominio

Los recursos se diseñan para español colombiano conversacional y un restaurante especializado en comida de mar. Se consideran variación ortográfica y regional, habla informal, flexión verbal, referencias entre turnos y terminología gastronómica local.

Principios obligatorios:

1. Separar reconocimiento lingüístico, resolución de intención e información comercial.
2. Preferir reglas deterministas y evaluables; no aplicar corrección aproximada irrestricta.
3. Conservar nombres propios, direcciones, especies y expresiones que no puedan normalizarse sin ambigüedad.
4. No deducir disponibilidad, composición ni seguridad alimentaria a partir del nombre de un plato.
5. No convertir formatos monetarios de manera implícita; el usuario debe suministrar valores explícitos en COP.

## Mapa de responsabilidades

| Recurso | Propietario de | No debe contener |
|---|---|---|
| `config/domain/intent_taxonomy.json` | Identificadores y definiciones canónicas de intenciones y subintenciones del dominio | Patrones, pesos o respuestas |
| `config/domain/slot_catalog.json` | Datos semánticos, clasificación de privacidad y política mínima de recolección | Valores reales, reglas de extracción, fuentes contextuales o preguntas |
| `config/infrastructure_nlp/text_normalizer_service_config.json` | Errores inequívocos, abreviaturas, variación gráfica y jerga monetaria | Intenciones, entidades o precios |
| `config/infrastructure_nlp/phrase_matcher_service_config.json` | Vocabulario estable de productos, preparaciones, categorías, servicios, pagos, ingredientes y alérgenos reconocido por `PhraseMatcherService` | Precios o disponibilidad diaria |
| `config/infrastructure_nlp/matcher_service_config.json` | Estructuras sintácticas de intención, cantidades, dinero y negación | Inventarios de platos |
| `config/infrastructure_nlp/lemma_service_config.json` | Formas morfológicas y evidencia secundaria de bajo peso | Decisiones finales |
| `config/infrastructure_nlp/entity_ruler_service_config.json` | Tiempo y referencias que requieren contexto conversacional | Productos, ingredientes, precios o negación |
| `config/application/intent_resolver_config.json` | Pesos, umbrales, prioridades y evidencia | Requisitos, preguntas, carta o precios |
| `config/application/clarification_policy.json` | Slots requeridos por intención, decisiones y modos de intervención | Textos de preguntas, definiciones de slots, puntajes o respuestas comerciales |
| `content/responses/es-CO/clarification_questions.json` | Preguntas en español colombiano referenciadas por la política | Reglas de decisión o datos comerciales |
| `content/responses/es-CO/response_templates.json` | Plantillas neutrales para presentar datos ya validados | Precios, disponibilidad o datos personales persistidos |
| `data/business/restaurant_profile.json` | Nombre, ubicación, horario, medios de pago y referencias comerciales estables | Patrones NLP o textos conversacionales |
| `data/menu/menu_offerings.json` | Productos únicos con sus nombres, secciones, presentaciones y precios suministrados por el usuario | Alias, reglas lingüísticas o conversiones implícitas de precios |
| `corpus/profiles/conversation_profiles.json` | Estilos conversacionales para diseño y evaluación de cobertura | Casos, datos personales o reglas de producción |
| `corpus/datasets/customer_intent_benchmark.json` | Casos sintéticos y anotaciones de referencia | Configuración de producción o datos de entrenamiento futuros |

## Cómo decidir el propietario

| Expresión o necesidad | Propietario | Criterio |
|---|---|---|
| `neky → nequi` | Normalizer | Corrección gráfica inequívoca |
| `nequi`, `mojarra frita`, `al ajillo` | PhraseMatcher mediante `phrase_matcher_service_config.json` | Entidad comercial estable |
| `¿reciben Nequi?` | Matcher | Estructura que expresa un acto comunicativo |
| `pagar`, `pago`, `pagando` | Lemmas | Variación morfológica con evidencia secundaria |
| `mañana`, `el domingo`, `ese mismo` | EntityRuler | Tiempo o referencia dependiente del contexto |
| Prioridad de una alergia | Resolver | Política de decisión entre evidencias |
| Decidir que falta una fecha | Política de aclaración | Intervención conversacional posterior al análisis |
| Redactar la pregunta por esa fecha | Catálogo de preguntas | Contenido lingüístico desacoplado de la decisión |
| Precio de la mojarra | `menu_offerings.json` | Dato comercial cambiante |

PhraseMatcher y EntityRuler no deben reconocer la misma expresión. PhraseMatcher identifica vocabulario estable del negocio; EntityRuler delimita expresiones temporales o contextuales sobre el `Doc`. `tests/contract/test_resource_contract.py` comprueba esta frontera.

## Política lingüística

### Alias y ortografía

- Conservar tildes y grafía canónica en nombres principales.
- Poner en el Normalizer únicamente errores y abreviaturas con una transformación inequívoca.
- Poner en `phrases` las variantes legítimas de una entidad, como `mapará` y `mapara`.
- No duplicar una variante en Normalizer y PhraseMatcher sin una razón documentada.
- No eliminar tratamientos o marcadores discursivos si aportan información sociolingüística.
- No corregir aproximadamente especies, barrios, direcciones ni nombres propios.

### Entidades gastronómicas

- **Producto específico:** plato identificable, como `trucha a la marinera`.
- **Producto base:** especie o familia que puede requerir preparación, como `trucha`.
- **Preparación:** técnica o acabado, como `frito`, `al ajillo` o `a la plancha`.
- **Ingrediente:** elemento consultable o modificable, como `ajo` o `patacón`.
- **Alérgeno:** sustancia o familia relevante para la salud, como `crustáceos`, `gluten` o `lácteos`.

Una expresión puede aportar más de una lectura. `camarón`, por ejemplo, puede ser producto y evidencia de crustáceos. La lectura alimentaria solo debe adquirir prioridad cuando existan marcas como `alergia`, `intolerancia`, `contiene`, `trazas` o `contaminación`.

### Seguridad alimentaria

1. No afirmar que un plato es seguro porque el alérgeno no aparece en su nombre.
2. No afirmar ausencia de contaminación cruzada desde estos recursos.
3. Priorizar las consultas explícitas de alergia o contaminación sobre precio, recomendación o pedido.
4. Solicitar validación humana cuando la respuesta dependa de utensilios, aceite, superficies o composición no documentada.
5. Mantener separados `ALERGENO` e `INGREDIENTE`, aunque una expresión pueda aportar evidencia a ambos.

## Intenciones y aclaraciones

Toda intención o subintención debe:

1. Representar un acto comunicativo distinto y necesario.
2. Tener un identificador `snake_case` y una definición que la diferencie de sus vecinas.
3. Declararse primero en `config/domain/intent_taxonomy.json`.
4. Tener al menos una ruta de evidencia en Matcher, Lemmas, PhraseMatcher, EntityRuler o Resolver.
5. Incluir pruebas positivas, ambiguas y negativas.

Una aclaración debe indicar qué falta o qué resulta ambiguo. La política distingue seis modos operativos —información del usuario, confirmación transaccional, consulta comercial, validación humana de seguridad, asistencia humana y verificación de identidad— y el resultado terminal `out_of_scope`. Mantiene separados `missing_slots`, `question_key` y el texto, que vive en `clarification_questions.json`. No se debe usar una pregunta genérica cuando el motor conoce la causa.

Un slot representa el dato requerido, no su procedencia. Por ejemplo, `product` puede satisfacerse con una entidad del mensaje o con `context.producto_activo`; `order`, con `context.pedido_anterior`; y `delivery_address`, con `context.direccion_previa`. Las fuentes contextuales pertenecen al resolver y no crean slots alternativos.

### Datos personales en slots

- `customer_name`, `phone`, `delivery_address`, `order_id`, `reservation_id` e `invoice_data` existen porque algunas operaciones los necesitan; no son evidencia para perfilar al cliente.
- El motor NLP no debe persistirlos ni escribirlos en texto claro en logs o reportes.
- Los valores personales se aceptan desde entrada explícita y validada por la aplicación; no se adivinan desde texto ambiguo.
- `context.identity_verified` solo puede establecerlo la aplicación después de verificar al cliente; el NLP nunca realiza ni presume esa verificación.
- Repetir un pedido o reutilizar una dirección anterior exige `needs_identity_verification` antes de consultar esos datos. Una vez verificada la identidad, la política normal de datos faltantes y confirmación continúa vigente.
- Los datasets de este repositorio solo pueden contener valores sintéticos o redactados. La autorización, finalidad, retención y eliminación pertenecen a la aplicación transaccional.

### Flujo de domicilios

- `domicilio.consultar_domicilio` pregunta condiciones generales y termina en `needs_business_lookup`.
- `domicilio.solicitar_domicilio` inicia un envío, requiere `order` y `delivery_address`, y termina en `needs_transaction_confirmation`.
- `domicilio.consultar_estado_domicilio` consulta una entrega existente: primero exige `needs_identity_verification`, después una referencia `order_id|order` y finalmente `needs_business_lookup`.
- `domicilio.usar_direccion_previa` permanece separado porque reutiliza un dato personal almacenado y exige verificación de identidad antes de confirmar.

## Perfiles conversacionales

Los 20 perfiles describen estilos de interacción observables; no clasifican personas. Una misma persona puede usar varios estilos durante una conversación.

- No inferir, almacenar ni enviar el perfil al `LinguisticParser` o al `IntentResolver`.
- No variar por perfil precios, disponibilidad, seguridad, prioridades ni acceso a funciones.
- Definir perfiles mediante registro, longitud, ortografía, elipsis, referencias, negación y estructura del turno.
- Excluir edad, género, etnia, religión, discapacidad, estrato y procedencia social.
- Mantener los casos de referencia en `corpus/datasets/`, nunca dentro del archivo de perfiles.

## Precios y disponibilidad

- Los precios viven en `data/menu/menu_offerings.json` o en una fuente comercial externa.
- `fixed` representa un valor único y `by_size` los tamaños `pequeno`, `mediano` y `grande`.
- Reconocer un producto no significa que esté disponible.
- Un cambio de precio no debe requerir cambios en recursos lingüísticos.

## Procedimiento para modificar recursos

### Producto u oferta

1. Crear un ID estable y sus frases reales en `config/infrastructure_nlp/phrase_matcher_service_config.json`.
2. Evitar frases asignadas a dos IDs del mismo tipo.
3. Crear o actualizar el bloque del producto en `data/menu/menu_offerings.json` usando el mismo `product_id`.
4. Añadir pruebas de detección, solapamiento y precio cuando corresponda.

### Alias, patrón o lema

1. Aplicar la tabla de propietarios anterior.
2. Usar en Matcher IDs únicos y atributos spaCy como `LOWER`, `ENT_TYPE`, `ENT_ID`, `LIKE_NUM` y `OP`.
3. Evitar patrones completamente opcionales.
4. Usar `full_text_only` cuando una señal solo sea válida como mensaje completo.
5. Mantener los lemas como evidencia secundaria y comprobar palabras polisémicas.

### Intención o subintención

1. Definirla en `config/domain/intent_taxonomy.json`.
2. Incorporar evidencia lingüística.
3. Configurar requisitos, pesos o prioridades en el Resolver únicamente si son necesarios.
4. Añadir casos contractuales y de aclaración.

### Política de aclaración

1. Definir primero cada dato semántico en `config/domain/slot_catalog.json`.
2. Declarar en la política los slots obligatorios de la subintención.
3. Elegir `on_missing` y, solo cuando corresponda, `on_complete`.
4. Asociar cada slot faltante con una pregunta existente.
5. Pedir un dato por turno, conservar lo ya comprendido y no prometer información comercial o alimentaria no validada.

### Perfil conversacional

1. Describir fenómenos observables, necesidades y focos de aclaración.
2. No incluir mensajes, casos ni atributos personales.
3. Mantener `profile_count` sincronizado con la lista.

## Decisiones arquitectónicas vigentes

- No usar un `rules_config.json` único: mezcla responsabilidades y aumenta el acoplamiento.
- No usar loaders compartidos: cada servicio valida y carga su propio recurso.
- No guardar precios en `phrase_matcher_service_config.json`: el vocabulario es más estable que la oferta comercial.
- No registrar productos en EntityRuler: duplica PhraseMatcher.
- No representar `sin` como entidad: es negación sintáctica.
- No duplicar un producto por aparecer en carta general y menú ejecutivo; se modelan ofertas distintas, salvo que también cambie la identidad culinaria.
- No resolver alergias por ausencia de palabras: es inseguro e insuficiente.

## Validación obligatoria

Ejecutar, en este orden:

```bash
python -X utf8 tests/contract/test_resource_contract.py
python -m unittest discover -s tests -p "test_*.py"
python -X utf8 tests/evaluation/evaluate_resolver.py
```

La validación debe terminar sin errores. Cualquier cambio en los resultados contractuales debe revisarse y justificarse antes de aceptar el recurso.
