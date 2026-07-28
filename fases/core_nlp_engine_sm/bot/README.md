# Carpeta bot: estructura y funcionamiento

Esta carpeta reúne los datos y reglas con los que se construyen conversaciones de atención y venta para un restaurante. Los archivos `01` a `06` son las fuentes de verdad y `Conversaciones/` guarda los casos terminados.

## Qué aporta cada archivo

| Archivo | Qué contiene | Para qué sirve | Cuándo se consulta |
|---|---|---|---|
| `01 datos del cliente.json` | Datos del restaurante: ubicación, horarios, parqueaderos, accesibilidad y medios de pago. | Responder consultas sobre el establecimiento sin inventar información. | Cuando el escenario menciona datos del restaurante. |
| `02 menu.json` | Categorías, productos, descripciones, precios, presentaciones y porciones. | Consultar, ofrecer o vender productos de la carta. | Cuando el escenario incluye comida o bebidas. |
| `03 situaciones (Intenciones).json` | Necesidades del cliente agrupadas por dominio del negocio. | Identificar qué quiere lograr el cliente y definir el flujo. | Al comenzar la revisión del escenario. |
| `04 preguntas al usuario.json` | Preguntas asociadas a cada intención. | Obtener únicamente los datos que faltan para continuar. | Después de identificar la intención. |
| `05 respuestas al usuario.json` | Respuestas para resultados confirmados, negativos o pendientes. | Responder de forma consistente según el resultado del caso. | Cuando ya se conoce el resultado de la intención. |
| `06 tipos de usuarios.json` | Formas observables de comunicación del cliente. | Redactar los mensajes del cliente con un estilo lingüístico definido. | Al escribir la conversación. |
| `Conversaciones/` | Un archivo JSON por conversación terminada. | Guardar los casos que revisará el equipo de negocio. | Después de validar y construir la conversación. |

Cada archivo tiene una responsabilidad. No se debe trasladar información de uno a otro.

## Cómo se arma una conversación

```text
Escenario del usuario
        │
        ▼
Revisión de cobertura
├── Datos del restaurante ─────── 01 datos del cliente.json
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

1. **Entender el escenario:** identificar qué quiere el cliente, qué información ya entregó y qué resultado espera. Si tiene varias necesidades, separarlas.
2. **Revisar la cobertura:** una intención es la acción concreta que quiere realizar el cliente. Buscar intenciones equivalentes, preguntas para los datos faltantes, respuestas aplicables y datos del negocio. Si no se indica un tipo de usuario, revisar `tipo_de_usuario` en las conversaciones existentes y elegir uno con menor cobertura.
3. **Resolver faltantes:** si falta algo, informar qué existe, proponer el ajuste mínimo y esperar autorización. Si se aprueba, ajustar las fuentes y validar nuevamente antes de continuar.
4. **Crear y validar:** construir `flujo` y `conversacion` con claves existentes, comprobar que tengan la misma secuencia y guardar el JSON en `bot/Conversaciones`.

No se deben duplicar reglas por usar nombres distintos. `order_items`, por ejemplo, es la clave de una pregunta y no necesita un campo `id`. `borrador_iniciado` es una respuesta para un pedido armado que todavía no ha sido confirmado.

No inventes reglas, productos, presentaciones, precios, horarios, medios de pago, políticas, cobertura, disponibilidad, tiempos ni resultados operativos.

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

## Reglas para mantener los archivos claros

| Regla | Qué hacer |
|---|---|
| Simplicidad — KISS y YAGNI | Usar solo lo necesario para el caso actual. |
| Nombres previsibles — Least Surprise | Conservar las claves y significados de las fuentes. |
| Una responsabilidad — SRP y evitar Feature Envy | Mantener cada dato en el archivo al que pertenece. |
| Sin duplicación — DRY | Referenciar lo existente en lugar de copiarlo. |
| Fuentes confiables — DIP y evitar Magic Values | Depender de los archivos fuente y no de valores inventados. |
| Validación temprana — Guard Clauses | Detenerse cuando falte una referencia o un dato obligatorio. |

Reglas adicionales:

- No usar campos `id`, referencias como `intencion.pregunta` ni campos adicionales sin una necesidad aprobada.
- No preguntar datos ya entregados ni confirmar acciones que el cliente no haya autorizado.
- El tipo de usuario define cómo habla el cliente; no decide su intención y no debe exagerarse.
- No copiar preguntas o respuestas entre intenciones ni ocultar faltantes dentro de una conversación.
- No modificar los archivos fuente sin autorización.

## Lista de control

Antes de guardar:

- [ ] El escenario está cubierto y no duplica una intención equivalente.
- [ ] Las intenciones, preguntas y respuestas existen y están relacionadas correctamente.
- [ ] Solo se preguntan datos que faltan.
- [ ] Los datos del restaurante, productos y precios coinciden con sus fuentes.
- [ ] El tipo de usuario existe y se representa con naturalidad.
- [ ] El JSON contiene solo `flujo` y `conversacion`.
- [ ] El flujo y la conversación tienen la misma secuencia.
- [ ] No se inventaron reglas, datos del negocio ni resultados operativos.
- [ ] El archivo se guardó dentro de `bot/Conversaciones`.

## Prompt 1: recibir un escenario, revisar cobertura y actuar

Este es el prompt recomendado para un usuario de negocio. Solo debe reemplazar `[ESCENARIO]`.

```text
Quiero trabajar con este escenario:
[ESCENARIO]

Usa exclusivamente estas fuentes de verdad:
- bot/01 datos del cliente.json
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
5. Revisa los datos necesarios en datos del cliente.json y menu.json.
6. Selecciona un tipo de usuario existente. Si no indico uno, revisa el campo tipo_de_usuario de las conversaciones actuales y elige uno adecuado con menor cobertura.
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

No inventes reglas, productos, presentaciones, precios, horarios, medios de pago, políticas, cobertura, disponibilidad, tiempos ni resultados operativos.
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

Usa los archivos 01 a 06 de bot como fuentes de verdad.

Antes de escribir, verifica que el tipo de usuario, las intenciones, las preguntas y las respuestas existan. Si falta una referencia, detente y repórtala sin modificar archivos.

Crea un único JSON en bot/Conversaciones:
- flujo: nombre, descripcion, tipo_de_usuario, intenciones y orden.
- conversacion: únicamente participante y texto.

Usa las claves exactas de las fuentes, pregunta solo datos faltantes y mantén la misma secuencia de participantes en ambas secciones. No uses campos id ni números de turno.

Representa el tipo de usuario con naturalidad y reemplaza las variables únicamente con información disponible.

Aplica KISS, YAGNI, Least Surprise, SRP, DRY y DIP. Usa Guard Clauses. Evita Feature Envy y Magic Values.

No inventes reglas, productos, presentaciones, precios, horarios, medios de pago, políticas, cobertura, disponibilidad, tiempos ni resultados operativos.

Valida el JSON y reporta la ruta creada.
```

## Ejemplos disponibles

Los siguientes archivos muestran la estructura aprobada:

- `Conversaciones/venta_a_domicilio_camino_feliz.json`
- `Conversaciones/venta_para_recoger_por_descripcion.json`
