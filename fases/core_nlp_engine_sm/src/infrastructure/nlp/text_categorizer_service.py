"""Punto de extensión para la futura clasificación estadística de textos."""


class TextCategorizerService:
    """Pendiente de implementación.

    La estrategia de datos prevista para implementar y evaluar el
    TextCategorizer debe mantener separados los siguientes conjuntos:

    - ``resources/corpus/benchmarks/customer_intent_benchmark.json``:
      conservar como benchmark conocido.
    - ``resources/corpus/datasets/text_categorizer/entrenamiento``: entrenar el
      TextCategorizer con mensajes nuevos.
    - ``resources/corpus/datasets/text_categorizer/validacion``: ajustar
      hiperparámetros y umbrales.
    - ``resources/corpus/datasets/text_categorizer/prueba``: medir el resultado
      final sin tocarlo durante el desarrollo.

    Cuando se implemente, este servicio producirá puntuaciones estadísticas
    neutrales. La capa de aplicación será responsable de convertirlas en
    evidencia para el IntentResolver. No deberá sustituir las reglas de
    seguridad, el contexto, la extracción de entidades ni la política de
    aclaración.
    """
