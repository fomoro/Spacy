# Gobernanza de recursos

Este directorio contiene la configuración lingüística y comercial de `core_nlp_engine`. Su objetivo es que cada dato tenga un único propietario, pueda auditarse y cambie sin afectar responsabilidades ajenas.

## Criterios del dominio

Los recursos se diseñan para español colombiano conversacional y un restaurante especializado en comida de mar. Se consideran variación ortográfica y regional, habla informal, flexión verbal, referencias entre turnos y terminología gastronómica local.

Principios obligatorios:

1. Separar reconocimiento lingüístico, resolución de intención e información comercial.
2. Preferir reglas deterministas y evaluables; no aplicar corrección aproximada irrestricta.
3. Conservar nombres propios, direcciones, especies y expresiones que no puedan normalizarse sin ambigüedad.
4. No deducir disponibilidad, composición ni seguridad alimentaria a partir del nombre de un plato.
5. Confirmar con una fuente autorizada los precios temporales y cualquier condición operativa del restaurante.

## Mapa de responsabilidades

| Recurso | Propietario de | No debe contener |
|---|---|---|
| `nlp/intent_taxonomy.json` | Identificadores y definiciones de intenciones y subintenciones | Patrones, pesos o respuestas |
| `nlp/normalizer_config.json` | Errores inequívocos, abreviaturas, variación gráfica y jerga monetaria | Intenciones, entidades o precios |
| `nlp/matcher_patterns.json` | Estructuras sintácticas de intención, cantidades, dinero y negación | Inventarios de platos |
| `nlp/lemma_signals.json` | Formas morfológicas y evidencia secundaria de bajo peso | Decisiones finales |
| `nlp/entity_ruler_patterns.json` | Tiempo y referencias que requieren contexto conversacional | Productos, ingredientes, precios o negación |
| `nlp/resolver_config.json` | Pesos, umbrales, prioridades y evidencia | Requisitos, preguntas, carta o precios |
| `dialogue/clarification_policy.json` | Slots obligatorios, modos de intervención y preguntas mínimas | Puntajes de intención o respuestas comerciales |
| `menu/menu_catalog.json` | Vocabulario estable de productos, preparaciones, categorías, servicios, pagos, ingredientes y alérgenos | Precios o disponibilidad diaria |
| `menu/menu_offerings.json` | Secciones, presentaciones y precios asociados por `product_id` | Alias y reglas lingüísticas |
| `profiles/conversation_profiles.json` | Estilos conversacionales para diseño y evaluación de cobertura | Casos, datos personales o reglas de producción |

## Cómo decidir el propietario

| Expresión o necesidad | Propietario | Criterio |
|---|---|---|
| `neky → nequi` | Normalizer | Corrección gráfica inequívoca |
| `nequi`, `mojarra frita`, `al ajillo` | PhraseMatcher mediante `menu_catalog.json` | Entidad comercial estable |
| `¿reciben Nequi?` | Matcher | Estructura que expresa un acto comunicativo |
| `pagar`, `pago`, `pagando` | Lemmas | Variación morfológica con evidencia secundaria |
| `mañana`, `el domingo`, `ese mismo` | EntityRuler | Tiempo o referencia dependiente del contexto |
| Prioridad de una alergia | Resolver | Política de decisión entre evidencias |
| Pregunta por una fecha faltante | Política de aclaración | Intervención conversacional posterior al análisis |
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
3. Declararse primero en `intent_taxonomy.json`.
4. Tener al menos una ruta de evidencia en Matcher, Lemmas, PhraseMatcher, EntityRuler o Resolver.
5. Incluir pruebas positivas, ambiguas y negativas.

Una aclaración debe indicar qué falta o qué resulta ambiguo. `dialogue/clarification_policy.json` distingue cuatro modos: información que debe aportar el usuario, confirmación transaccional, consulta comercial y validación humana de seguridad. Mantiene separados `missing_slots`, `question_key` y el texto mostrado por compatibilidad. No se debe usar una pregunta genérica cuando el motor conoce la causa.

## Perfiles conversacionales

Los 15 perfiles describen estilos de interacción observables; no clasifican personas. Una misma persona puede usar varios estilos durante una conversación.

- No inferir, almacenar ni enviar el perfil al `LinguisticParser` o al `IntentResolver`.
- No variar por perfil precios, disponibilidad, seguridad, prioridades ni acceso a funciones.
- Definir perfiles mediante registro, longitud, ortografía, elipsis, referencias, negación y estructura del turno.
- Excluir edad, género, etnia, religión, discapacidad, estrato y procedencia social.
- Mantener los casos de evaluación en `data/` o `tests/`, nunca dentro del recurso de perfiles.

## Precios y disponibilidad

- Los precios viven en `menu/menu_offerings.json` o en una fuente comercial externa.
- `fixed` representa un valor único; `range`, un intervalo; `by_size`, los tamaños `pequeno`, `mediano` y `grande`.
- Todo precio con `temporary: true` debe declarar `requires_confirmation: true`.
- Reconocer un producto no significa que esté disponible.
- Un cambio de precio no debe requerir cambios en recursos lingüísticos.

## Procedimiento para modificar recursos

### Producto u oferta

1. Crear un ID estable y sus frases reales en `menu_catalog.json`.
2. Evitar frases asignadas a dos IDs del mismo tipo.
3. Crear la oferta correspondiente en `menu_offerings.json` usando el mismo `product_id`.
4. Añadir pruebas de detección, solapamiento y precio cuando corresponda.

### Alias, patrón o lema

1. Aplicar la tabla de propietarios anterior.
2. Usar en Matcher IDs únicos y atributos spaCy como `LOWER`, `ENT_TYPE`, `ENT_ID`, `LIKE_NUM` y `OP`.
3. Evitar patrones completamente opcionales.
4. Usar `full_text_only` cuando una señal solo sea válida como mensaje completo.
5. Mantener los lemas como evidencia secundaria y comprobar palabras polisémicas.

### Intención o subintención

1. Definirla en `intent_taxonomy.json`.
2. Incorporar evidencia lingüística.
3. Configurar requisitos, pesos o prioridades en el Resolver únicamente si son necesarios.
4. Añadir casos contractuales y de aclaración.

### Política de aclaración

1. Declarar los slots obligatorios o alternativos de la subintención.
2. Elegir `on_missing` y, solo cuando corresponda, `on_complete`.
3. Asociar cada slot faltante con una pregunta existente.
4. Pedir un dato por turno, conservar lo ya comprendido y no prometer información comercial o alimentaria no validada.

### Perfil conversacional

1. Describir fenómenos observables, necesidades y focos de aclaración.
2. No incluir mensajes, casos ni atributos personales.
3. Mantener `profile_count` sincronizado con la lista.

## Decisiones arquitectónicas vigentes

- No usar un `rules_config.json` único: mezcla responsabilidades y aumenta el acoplamiento.
- No usar loaders compartidos: cada servicio valida y carga su propio recurso.
- No guardar precios en `menu_catalog.json`: el vocabulario es más estable que la oferta comercial.
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
