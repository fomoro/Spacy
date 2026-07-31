class SpellCheckerService:
    """
    Servicio de corrección ortográfica (Spell Checker).
    
    PROPOSITO FUTURO:
    Este servicio atrapará el texto crudo del usuario (ej. "kiero anburguesa") 
    y lo corregirá a texto limpio ("quiero hamburguesa") antes de que pase al 
    resto de la infraestructura (lematización, entidades, etc.).
    
    NOTA SOBRE IMPLEMENTACIÓN Y ARQUITECTURA:
    SpaCy por defecto NO trae un corrector ortográfico nativo, ya que su enfoque 
    es el análisis gramatical (entidades, lemas). 
    
    Sin embargo, la mejor práctica de arquitectura para implementar esto en el futuro es:
    1. Usar 'SymSpell' (Súper rápida para aplicaciones de chat).
    2. En lugar de descargar un diccionario gigante de español de internet, 
       SymSpell debe inicializarse leyendo el vocabulario que SpaCy ya tiene 
       cargado en memoria (nlp.vocab).
    3. Para las palabras propias del restaurante (ej. "sancocho", "rappi"), 
       el servicio debe leer automáticamente nuestros propios archivos JSON 
       (del phrase_matcher y entity_ruler) para agregar ese vocabulario al vuelo.
       
    De esta forma, SymSpell actúa como la "escoba" que limpia el texto, y SpaCy 
    como el "analista" que lo procesa, formando la pareja ideal sin acoplar código.
    
    Se recomienda conectarlo directamente en el linguistic_parser.py como el 
    primer paso absoluto (antes de ejecutar text_normalizer_service).
    """

    def __init__(self):
        # TODO Futuro:
        # 1. Inicializar SymSpell aquí.
        # 2. Inyectar el objeto nlp de SpaCy para extraer nlp.vocab.
        # 3. Leer las llaves de los JSONs de infraestructura para extraer palabras del restaurante.
        pass

    def correct(self, text: str) -> str:
        """
        Recibe el texto con posibles errores de ortografía y retorna el texto corregido.
        """
        # TODO: Implementar lógica de corrección en el futuro.
        # Por ahora, actúa como un "passthrough" (devuelve el texto igual).
        return text
