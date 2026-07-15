"""Punto de extensión para la futura clasificación estadística de textos."""


class TextCategorizerService:
    """Pendiente de implementación.

    La estrategia de datos prevista para implementar y evaluar el
    TextCategorizer debe mantener separados los siguientes conjuntos:

    - ``resources/corpus/datasets/intent_benchmark/casos_intenciones_clientes.json``:
      conservar como benchmark conocido.
    - ``resources/corpus/datasets/text_categorizer/entrenamiento``: entrenar el
      TextCategorizer con mensajes nuevos.
    - ``resources/corpus/datasets/text_categorizer/validacion``: ajustar
      hiperparámetros y umbrales.
    - ``resources/corpus/datasets/text_categorizer/prueba``: medir el resultado
      final sin tocarlo durante el desarrollo.

    Cuando se implemente, este servicio producirá evidencia estadística para
    el IntentResolver. No deberá sustituir las reglas de seguridad, el contexto,
    la extracción de entidades ni la política de aclaración.
    """
