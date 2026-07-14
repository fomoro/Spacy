from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import spacy
from spacy.language import Language
from spacy.tokens import Doc

class EntityRulerService:
    """
    Servicio que envuelve el EntityRuler nativo de spaCy.
    Permite detectar entidades mediante patrones sintácticos o literales de tokens.
    """

    def __init__(
        self,
        config: str | Path | list[dict[str, Any]],
        nlp: Language | None = None,
    ) -> None:
        self._nlp = nlp or spacy.blank("es")
        
        if isinstance(config, (str, Path)):
            self._patterns = self._load_patterns(Path(config))
        elif isinstance(config, list):
            self._patterns = config
        else:
            raise TypeError("config debe ser una ruta a archivo JSON o una lista de patrones")

        # Configurar el componente de spaCy
        if "entity_ruler" not in self._nlp.pipe_names:
            self._ruler = self._nlp.add_pipe("entity_ruler")
        else:
            self._ruler = self._nlp.get_pipe("entity_ruler")

        self._ruler.add_patterns(self._patterns)

    @staticmethod
    def _load_patterns(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"No existe la configuración para EntityRuler: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Si es el archivo unificado de reglas, extraer la sección entity_ruler
        if isinstance(data, dict):
            return data.get("entity_ruler", [])
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("Formato de patrones de EntityRuler no soportado (debe ser dict con llave 'entity_ruler' o una lista)")

    def annotate(self, doc: Doc) -> Doc:
        """Aplica las reglas sobre un objeto Doc in-place."""
        return self._ruler(doc)

    def match(self, text: str) -> list[dict[str, Any]]:
        """Procesa un texto y extrae las entidades que coincidan con las reglas."""
        doc = self._nlp.make_doc(text)
        doc = self.annotate(doc)
        results = []
        for ent in doc.ents:
            results.append({
                "entity_type": ent.label_,
                "entity_id": ent.ent_id_,
                "canonical": ent.text,
                "text": ent.text,
                "start_char": ent.start_char,
                "end_char": ent.end_char,
                "start_token": ent.start,
                "end_token": ent.end,
                "priority": 0,
                "source": "EntityRuler"
            })
        return results
