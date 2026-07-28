# Guía operativa para crear conversaciones

## Para qué sirve esta guía

Esta guía permite convertir un escenario de restaurante en una conversación JSON que pueda revisar un usuario de negocio.

El proceso tiene dos controles obligatorios:

1. Verificar que el escenario esté cubierto por los archivos fuente.
2. Crear la conversación únicamente cuando todas las referencias existan.

Los archivos `01` a `06` son las fuentes de verdad. La carpeta `Conversaciones` guarda el resultado.

## Inicio rápido

```text
1. Describe el escenario.
2. Ejecuta el Prompt 1 de esta guía.
3. Revisa el informe de cobertura.
4. Si falta algo, aprueba o rechaza el ajuste propuesto.
5. Cuando todo exista, genera la conversación.
6. Revisa el flujo y después lee el diálogo.
7. Guarda el JSON en bot/Conversaciones.
```

No se debe crear una conversación si falta una intención, una pregunta necesaria, una respuesta aplicable, un producto o un dato indispensable del negocio.

## Qué aporta cada archivo

| Archivo | Cuándo se consulta | Qué aporta |
|---|---|---|
| `00 Leeme.txt` | Para conocer rápidamente el contenido de la carpeta. | Una descripción corta de los archivos. |
| `README.md` | Antes de revisar o construir conversaciones. | El procedimiento, las reglas, la estructura y los prompts. |
| `01 cliente.json` | Cuando el escenario menciona el restaurante. | Ubicación, horarios, parqueaderos, accesibilidad y medios de pago. |
| `02 menu.json` | Cuando el escenario incluye productos. | Categorías, productos, descripciones, precios, presentaciones y porciones. |
| `03 situaciones (Intenciones).json` | Al identificar qué necesita el cliente. | Las intenciones disponibles, agrupadas por dominio del negocio. |
| `04 preguntas al usuario.json` | Cuando falta información para atender una intención. | Las preguntas permitidas y el dato que obtiene cada una. |
| `05 respuestas al usuario.json` | Cuando se conoce el resultado de la intención. | Las respuestas disponibles para resultados confirmados, negativos o pendientes. |
| `06 tipos de usuarios.json` | Al redactar los mensajes del cliente. | Las formas de comunicación que debe representar la conversación. |
| `Conversaciones/` | Después de validar el escenario. | Un archivo JSON por conversación aprobada. |

Cada archivo tiene una responsabilidad. No se debe trasladar información de uno a otro.

## Cómo se arma una conversación

```text
Escenario del usuario
        │
        ▼
Revisión de cobertura
├── Datos del restaurante ─────── 01 cliente.json
├── Productos y precios ───────── 02 menu.json
├── Intenciones ───────────────── 03 situaciones (Intenciones).json
├── Preguntas necesarias ──────── 04 preguntas al usuario.json
├── Respuestas aplicables ─────── 05 respuestas al usuario.json
└── Tipo de usuario ───────────── 06 tipos de usuarios.json
        │
        ▼
¿Todo existe?
├── No ──► Informar faltantes, proponer el ajuste mínimo y esperar aprobación
└── Sí ──► Crear flujo, escribir conversación y validar
```

## Estructura del menú

El menú permite productos directos dentro de una categoría y productos agrupados en subcategorías.

```text
Carta del restaurante
├── Categoría A
│   ├── Producto
│   └── Producto
│
└── Categoría B
    ├── Subcategoría B.1
    │   ├── Producto
    │   └── Producto
    │
    └── Subcategoría B.2
        └── Producto
```

Cada producto puede tener descripción, precio único, precios por presentación y porción cuando aplique.

## Procedimiento operativo

### Paso 1. Entender el escenario

Identificar:

- Qué quiere lograr el cliente.
- Qué producto o servicio menciona.
- Qué información ya entregó.
- Qué resultado espera.
- Si el escenario contiene una o varias necesidades.

Todavía no se escribe la conversación.

### Paso 2. Revisar la cobertura

#### Intenciones

Buscar en `03 situaciones (Intenciones).json` una intención que represente cada necesidad del escenario.

La búsqueda debe hacerse por significado, no solamente por coincidencia de palabras. Si ya existe una intención equivalente, se reutiliza aunque tenga otro nombre.

#### Preguntas

Para cada intención, revisar `04 preguntas al usuario.json`.

- Usar únicamente preguntas pertenecientes a esa intención.
- Preguntar solo los datos que el cliente no haya entregado.
- No crear otra pregunta si una existente obtiene el mismo dato.
- Una intención puede no requerir preguntas.

La clave `order_items`, por ejemplo, identifica directamente una pregunta. No necesita un campo adicional llamado `id`.

#### Respuestas

Para cada intención, revisar `05 respuestas al usuario.json`.

- Elegir una respuesta cuyo resultado corresponda al caso.
- Revisar estados confirmados, negativos y pendientes.
- No crear otra respuesta si una existente cubre el mismo resultado.
- No confirmar algo que el escenario todavía no permita confirmar.

`borrador_iniciado`, por ejemplo, indica que el pedido fue armado, pero aún no fue autorizado por el cliente.

#### Datos del negocio

Revisar `01 cliente.json` y `02 menu.json` cuando el escenario necesite información del restaurante, productos o precios.

No inventar:

- Productos o presentaciones.
- Precios.
- Horarios.
- Formas de pago.
- Políticas.
- Cobertura.
- Disponibilidad.
- Tiempos.
- Resultados operativos.

#### Tipo de usuario

Seleccionar una clave existente en `06 tipos de usuarios.json`.

El tipo de usuario define cómo habla el cliente. No determina lo que quiere ni cambia las reglas del negocio.

Si el escenario no exige un tipo específico, conviene elegir uno que todavía tenga poca cobertura en `Conversaciones/`.

### Paso 3. Decidir si se puede continuar

```text
Cobertura completa
└── Crear la conversación

Cobertura incompleta
├── No crear la conversación
├── No modificar los archivos fuente
├── Explicar qué existe
├── Explicar qué falta
├── Proponer el ajuste mínimo
└── Esperar autorización
```

El informe de faltantes debe usar este formato:

```text
Escenario: [nombre breve]

Existe:
- [intención, pregunta o respuesta encontrada]

Falta:
- [elemento necesario que no está cubierto]

Propuesta mínima:
- [ajuste concreto sin duplicar reglas existentes]

Archivo que cambiaría:
- [ruta del archivo]

Estado:
- Esperando autorización
```

### Paso 4. Definir el flujo

El flujo explica cómo fue construida la conversación.

Debe contener:

- Un nombre entendible para el negocio.
- Una descripción breve.
- Un tipo de usuario existente.
- Una intención principal.
- Intenciones relacionadas solo cuando sean necesarias.
- El orden de participación.
- La clave exacta de cada pregunta o respuesta utilizada.

### Paso 5. Escribir la conversación

La conversación muestra únicamente:

- Quién habla.
- Qué dice.

Los mensajes del cliente deben reflejar su tipo de usuario con naturalidad. Los mensajes del bot deben usar las preguntas y respuestas seleccionadas.

Las variables de una respuesta solo pueden reemplazarse con:

- Información entregada por el cliente.
- Información de `01 cliente.json`.
- Información de `02 menu.json`.
- Datos ficticios claramente reconocibles como parte de una prueba, como un nombre, teléfono, dirección o referencia de pedido.

### Paso 6. Validar y guardar

El flujo y la conversación deben tener la misma cantidad de intervenciones y el mismo orden de participantes.

El archivo se guarda dentro de `bot/Conversaciones` con un nombre claro en `snake_case`.

## Estructura JSON obligatoria

Cada conversación debe contener únicamente `flujo` y `conversacion`.

```json
{
  "flujo": {
    "nombre": "Nombre claro del caso",
    "descripcion": "Resumen breve del escenario.",
    "tipo_de_usuario": "tipo_existente",
    "intenciones": {
      "principal": "intencion_existente",
      "relacionadas": []
    },
    "orden": [
      {
        "participante": "cliente",
        "intencion": "intencion_existente"
      },
      {
        "participante": "bot",
        "intencion": "intencion_existente",
        "pregunta": "pregunta_existente"
      },
      {
        "participante": "cliente"
      },
      {
        "participante": "bot",
        "intencion": "intencion_existente",
        "respuesta": "respuesta_existente"
      }
    ]
  },
  "conversacion": [
    {
      "participante": "cliente",
      "texto": "Mensaje natural del cliente."
    },
    {
      "participante": "bot",
      "texto": "Pregunta correspondiente."
    },
    {
      "participante": "cliente",
      "texto": "Información solicitada."
    },
    {
      "participante": "bot",
      "texto": "Respuesta correspondiente."
    }
  ]
}
```

### Qué significa cada campo

| Campo | Uso |
|---|---|
| `nombre` | Identifica el caso para el equipo de negocio. |
| `descripcion` | Resume qué ocurre en el escenario. |
| `tipo_de_usuario` | Referencia una clave de `06 tipos de usuarios.json`. |
| `principal` | Indica la necesidad central del cliente. |
| `relacionadas` | Incluye otras intenciones que aparecen en la misma conversación. |
| `orden` | Muestra la secuencia y las referencias utilizadas. |
| `participante` | Solo puede ser `cliente` o `bot`. |
| `intencion` | Referencia una clave de `03 situaciones (Intenciones).json`. |
| `pregunta` | Referencia una clave de `04 preguntas al usuario.json`. |
| `respuesta` | Referencia una clave de `05 respuestas al usuario.json`. |
| `texto` | Contiene el mensaje que leerá el equipo. |

El orden del arreglo ya define los turnos. No se deben agregar números de turno.

## Reglas prácticas

| Principio | Aplicación en las conversaciones |
|---|---|
| KISS | Usar solo los campos necesarios para entender y validar el caso. |
| YAGNI | No agregar estructuras pensando en necesidades futuras. |
| Least Surprise | Conservar los nombres y significados de las fuentes. |
| SRP | Mantener una sola responsabilidad por archivo y por sección. |
| DRY | Referenciar claves existentes en lugar de duplicar información estructurada. |
| DIP | Hacer que la conversación dependa de las fuentes, no de copias aisladas. |
| Guard Clauses | Detenerse si una referencia o un dato obligatorio no existe. |
| Evitar Feature Envy | No guardar precios fuera del menú ni horarios fuera del archivo del restaurante. |
| Evitar Magic Values | No inventar valores del negocio ni resultados operativos. |

Reglas adicionales:

- No usar campos `id` cuando la clave del JSON ya identifica el elemento.
- No unir referencias artificialmente, como `intencion.pregunta`.
- No agregar `datos_del_caso`, `modalidad`, `accion` ni números de turno sin una necesidad aprobada.
- No preguntar información que el cliente ya entregó.
- No usar el tipo de usuario para decidir la intención.
- No exagerar las señales lingüísticas del cliente.
- No copiar preguntas o respuestas entre intenciones.
- No confirmar un pedido antes de recibir autorización.
- No crear una conversación para ocultar una falta de cobertura.
- No modificar fuentes sin autorización.

## Lista de control

Antes de guardar:

- [ ] El escenario fue revisado antes de escribir.
- [ ] No existe una intención equivalente que se esté duplicando.
- [ ] La intención principal existe.
- [ ] Las intenciones relacionadas existen.
- [ ] Las preguntas existen dentro de sus intenciones.
- [ ] Se preguntan únicamente datos faltantes.
- [ ] Las respuestas existen dentro de sus intenciones.
- [ ] El resultado elegido corresponde al escenario.
- [ ] Los productos y precios coinciden con el menú.
- [ ] Los datos del restaurante coinciden con `01 cliente.json`.
- [ ] El tipo de usuario existe y se representa con naturalidad.
- [ ] El JSON contiene solo `flujo` y `conversacion`.
- [ ] El flujo y la conversación tienen la misma secuencia.
- [ ] No se inventaron reglas ni datos del negocio.
- [ ] El archivo se guardó dentro de `bot/Conversaciones`.

## Prompt 1: recibir un escenario, revisar cobertura y actuar

Este es el prompt recomendado para un usuario de negocio. Solo debe reemplazar `[ESCENARIO]`.

```text
Quiero trabajar con este escenario:
[ESCENARIO]

Usa exclusivamente estas fuentes de verdad:
- bot/01 cliente.json
- bot/02 menu.json
- bot/03 situaciones (Intenciones).json
- bot/04 preguntas al usuario.json
- bot/05 respuestas al usuario.json
- bot/06 tipos de usuarios.json
- bot/Conversaciones, únicamente para revisar cobertura existente

Primero revisa el escenario. No escribas la conversación todavía.

1. Identifica las necesidades del cliente.
2. Busca por significado las intenciones que las cubren.
3. Verifica si las preguntas necesarias ya existen dentro de esas intenciones.
4. Verifica si existen respuestas para todos los resultados requeridos.
5. Revisa los datos necesarios en cliente.json y menu.json.
6. Selecciona un tipo de usuario existente. Si no indico uno, elige uno adecuado y, de ser posible, poco utilizado.
7. Compara con lo existente para evitar intenciones, preguntas o respuestas duplicadas.

Si falta algo:
- No crees la conversación.
- No modifiques archivos.
- Indica qué existe.
- Indica qué falta.
- Propón únicamente el ajuste mínimo.
- Señala qué archivo tendría que cambiar.
- Espera mi autorización.

Si todo existe:
- Crea un JSON dentro de bot/Conversaciones.
- Usa solamente las secciones flujo y conversacion.
- En flujo incluye nombre, descripcion, tipo_de_usuario, intenciones y orden.
- En orden referencia las claves exactas de intención, pregunta y respuesta.
- En conversacion incluye únicamente participante y texto.
- Pregunta solo los datos que el cliente no haya entregado.
- Usa las respuestas del archivo correspondiente y reemplaza sus variables con información disponible.
- Haz que el cliente represente su tipo de usuario con naturalidad.

Aplica KISS, YAGNI, Least Surprise, SRP, DRY y DIP.
Usa Guard Clauses.
Evita Feature Envy y Magic Values.

No inventes productos, precios, horarios, políticas, disponibilidad, cobertura, tiempos ni resultados operativos.
No uses campos id, números de turno, accion, modalidad, datos_del_caso ni referencias unidas con puntos.
No confirmes acciones que el cliente no haya autorizado.

Antes de guardar, valida:
- JSON válido.
- Referencias existentes.
- Productos y precios correctos.
- Preguntas y respuestas pertenecientes a sus intenciones.
- Misma secuencia de participantes en flujo y conversacion.
- Ausencia de reglas o datos inventados.

Al finalizar, informa únicamente:
- Resultado de la revisión.
- Archivo creado o ajuste pendiente de autorización.
```

## Prompt 2: crear una conversación con cobertura ya validada

Usar este prompt cuando las intenciones, preguntas y respuestas ya fueron revisadas.

```text
Crea una conversación para este caso ya validado:
[ESCENARIO]

Tipo de usuario:
[TIPO_DE_USUARIO]

Intención principal:
[INTENCION_PRINCIPAL]

Intenciones relacionadas:
[INTENCIONES_RELACIONADAS]

Usa como fuentes:
- bot/01 cliente.json
- bot/02 menu.json
- bot/03 situaciones (Intenciones).json
- bot/04 preguntas al usuario.json
- bot/05 respuestas al usuario.json
- bot/06 tipos de usuarios.json

Antes de escribir, confirma que todas las claves indicadas existan. Si alguna no existe, detente y repórtala sin modificar archivos.

Crea un único archivo JSON dentro de bot/Conversaciones con esta estructura:
- flujo: nombre, descripcion, tipo_de_usuario, intenciones y orden.
- conversacion: únicamente participante y texto.

En flujo:
- Usa las claves exactas de las intenciones.
- Incluye solo las preguntas necesarias.
- Referencia cada pregunta con su clave real.
- Referencia cada respuesta con su clave real.
- No uses campos id ni números de turno.

En conversacion:
- Mantén el mismo orden de participantes del flujo.
- Representa el tipo de usuario con naturalidad.
- No preguntes datos ya entregados.
- Usa productos, precios y datos reales de las fuentes.
- Reemplaza correctamente las variables de las respuestas.

Aplica KISS, YAGNI, Least Surprise, SRP, DRY y DIP.
Usa Guard Clauses.
Evita Feature Envy y Magic Values.

No inventes reglas, productos, precios, políticas ni resultados operativos.
Entrega el archivo y reporta su ruta.
```

## Resultado esperado

El usuario de negocio debe poder:

1. Escribir un escenario sin conocer la estructura técnica.
2. Saber si el caso ya está cubierto.
3. Entender qué falta antes de autorizar cambios.
4. Leer el flujo para verificar cómo se armó la conversación.
5. Leer el diálogo para evaluar si la atención es correcta y natural.
