# Limpiador de Mensajes (Normalizador de Texto)

**Foco Principal del Componente**: Este componente está dedicado *exclusivamente* a la **normalización y limpieza controlada de texto**. Su única responsabilidad es preparar y estandarizar el mensaje del cliente antes de que sea procesado por los motores de lenguaje natural (NLP). **No** detecta intenciones, **no** extrae platos del menú ni genera respuestas para el usuario. Es la primera línea de defensa del chatbot para garantizar que el texto que entra esté libre de errores.

Como parte de los objetivos, el normalizador cuenta con un **catálogo filológico colombiano completo y expandido**. La prioridad aquí no es corregir errores ortográficos genéricos (los cuales serán resueltos por spaCy más adelante), sino normalizar los **modismos pragmáticos, las abreviaciones informales y el léxico regional** que spaCy jamás entendería por sí solo (por ejemplo, el uso de "regalar" para solicitar servicio o la jerga transaccional como "Nequi" y "lucas").

### Mitigación de Sesgos Sociolingüísticos
Un objetivo crítico de este normalizador es **evitar el sesgo poblacional**. El catálogo ha sido expandido meticulosamente para cubrir todos los perfiles de clientes de nuestro negocio. No solo estandariza la jerga informal o urbana (ej. *"bro"*, *"nea"*, *"corrientazo"*), sino que procesa con la misma eficacia las abreviaciones corporativas de oficinistas (ej. *"rut"*, *"fac"*, *"cotiza"*), el lenguaje respetuoso de adultos mayores (ej. *"mi hijito"*, *"doña"*) y la terminología de dietas/restricciones (ej. *"vege"*, *"sin tacc"*). Esto garantiza que el chatbot atienda con el mismo nivel de precisión y equidad a cualquier tipo de cliente, sin importar su edad o estrato.

### ¿Qué hace exactamente?
Cuando un cliente escribe con errores de ortografía, abreviaciones o jerga colombiana, este componente lo traduce a un formato estándar. Por ejemplo:

| Mensaje original del cliente | Mensaje normalizado (Salida) | Información adicional extraída |
| :--- | :--- | :--- |
| "tiene domisilio?" | "tiene domicilio ?" | Ninguna |
| "porfa me manda dos mojarras" | "por favor me manda dos mojarras" | Ninguna |
| "pago con 20 lucas" | "pago con 20 lucas" | Valor monetario detectado: $20,000 COP |
| "ay y ayer" | "hay y ayer" | Ninguna |

### Reglas de oro (Lo que NO hace para proteger el negocio)
* **No inventa palabras**: Si el cliente escribe algo que no conocemos, se deja tal cual para no alterar su pedido.
* **No elimina negaciones**: Si el cliente dice "sin cebolla" o "no quiero picante", el limpiador mantiene intactas las palabras "sin" y "no".
* **No adivina intenciones**: Solo limpia el texto; decidir si el cliente quiere comprar o quejarse se hace en los siguientes pasos del sistema.

### ¿Cómo probarlo?

#### 1. Prueba rápida (Probador interactivo en consola)
Ejecuta el siguiente comando para abrir una consola interactiva donde puedes escribir tus propios mensajes en tiempo real:
```bash
python tests/interactive_test.py
```
Para ayudarte a probar los casos más interesantes y complejos, aquí tienes una tabla de ejemplos recomendados:

| Escribe en la consola (Entrada) | Resultado esperado del programa (Salida normalizada) | Qué comprueba / Perfil evaluado |
| :--- | :--- | :--- |
| `Bro, me regala un corrientazo porfa?` | `bro, por favor me da un almuerzo ejecutivo por favor?` | **Estudiante**: Normaliza modismos pragmáticos (`me regala un` -> `por favor me da un`), aliases (`corrientazo` -> `almuerzo ejecutivo`) y jergas. |
| `hola señorita, cuánto se demora el domicilio?` | `hola señorita, cuál es el tiempo de entrega el domicilio?` | **Oficinista**: Normaliza jergas de entrega temporal (`cuánto se demora` -> `cuál es el tiempo de entrega`). |
| `amigo, ¿tienen parquiadero e infantil?` | `amigo, ¿tienen parqueadero e menú infantil?` | **Padre de familia**: Corrige errores ortográficos de infraestructura y amplía aliases infantiles. |
| `buenas tardes mi hijito, me regala un pescadito` | `buenas tardes mi hijito, por favor me da un pescado` | **Adulta mayor**: Normaliza peticiones afectuosas y diminutivos gastronómicos colombianos. |
| `patrón, mándeme lo de siempre` | `patrón, mándeme el pedido habitual` | **Habitual**: Normaliza modismos implícitos de clientes de confianza. |
| `Estimado caballero, por favor me regala para una reserv` | `estimado caballero, por favor por favor me da para una reserva` | **Profesional**: Mapea abreviaciones formales en contextos ejecutivos. |
| `mano a como tiene el corrientazo hoy ?` | `mano cuánto cuestan el almuerzo ejecutivo hoy?` | **Baja alfabetización**: Corrige formas coloquiales de coste y aliases populares. |
| `nea, puedo pagar el combito con neky?` | `nea, puedo pagar el combo con nequi?` | **Adolescente**: Traduce jerga digital juvenil y pasarelas de pago. |
| `hola, ¿tienen platos sin tacc o vege?` | `hola, ¿tienen platos sin gluten o vegetariano?` | **Restricciones/Fit**: Estandariza modismos dietarios y de salud alimentaria. |
| `Estimada, solicito la fac a nombre de la empresa` | `estimada, solicito la factura necesito factura electrónica` | **Administrativo/Corp**: Traduce requerimientos formales y de facturación. |
| `tengo veinte lucas` | `tengo veinte lucas` *(💰 Extra: $20,000)* | **Monetario**: Extrae y calcula jerga de dinero colombiano ("lucas" -> 1000). |

Para salir de esta consola de pruebas, escribe `salir`, `exit` o `quit`.

#### 2. Evaluación de calidad en lote (Simulación)
Ejecuta este comando para procesar un archivo con 200 mensajes de clientes históricos reales:
```bash
python tests/evaluate_normalizer.py
```
* **¿Qué esperar?**: El script creará automáticamente la carpeta `reports/` (si no existe) y **generará o sobrescribirá** dos archivos con los resultados:
  * [evaluacion_normalizador.csv](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/reports/evaluacion_normalizador.csv): Una tabla con cada mensaje original al lado de su versión normalizada y las reglas que se aplicaron.
  * [resultado_evaluacion.json](file:///C:/Dev/GitHub/Spacy/fases/fase_4_normalizador_integrado/reports/resultado_evaluacion.json): Un resumen estadístico de la prueba (ej: cuántos mensajes se modificaron, cuántos no requirieron cambios y si hubo algún error).
  *(No necesitas limpiar o crear estos archivos manualmente, el script los sobrescribe por ti en cada ejecución).*

#### 3. Pruebas de código (Pruebas unitarias)
Si eres desarrollador, puedes validar que todos los componentes internos funcionen correctamente ejecutando:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
* **¿Qué esperar?**: Verás un reporte de salida en consola con puntos `.......` y al final la palabra `OK` (por ejemplo: `Ran 7 tests in 0.007s`). Esto significa que todos los casos de prueba internos y automáticos pasaron de forma exitosa y el software cumple con los requisitos técnicos.
