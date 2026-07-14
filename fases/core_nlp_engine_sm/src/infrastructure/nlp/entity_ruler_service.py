"""Entidades temporales y referencias contextuales con EntityRuler."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

import spacy
from spacy.language import Language
from spacy.tokens import Doc


@dataclass(frozen=True)
class EntityRulerEntity:
    entity_type: str
    entity_id: str
    text: str
    start_char: int
    end_char: int
    start_token: int
    end_token: int
    source: str = "EntityRuler"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EntityRulerResult:
    text: str
    entities: tuple[EntityRulerEntity, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "entities": [entity.to_dict() for entity in self.entities],
        }


class EntityRulerService:
    """Gestiona patrones tokenizados mediante el ``entity_ruler`` nativo."""

    def __init__(
        self,
        config: str | Path | Mapping[str, Any],
        nlp: Language | None = None,
        component_name: str = "entity_ruler",
    ) -> None:
        self._patterns = self._load_patterns(config)
        self._nlp = nlp or spacy.blank("es")
        self._component_name = component_name

        if component_name in self._nlp.pipe_names:
            ruler = self._nlp.get_pipe(component_name)
            if not hasattr(ruler, "add_patterns"):
                raise ValueError(f"El componente '{component_name}' no es un EntityRuler.")
        else:
            ruler = self._nlp.add_pipe(
                "entity_ruler",
                name=component_name,
                config={"overwrite_ents": False, "phrase_matcher_attr": "LOWER"},
            )
        ruler.add_patterns(self._patterns)

    @staticmethod
    def _load_patterns(
        source: str | Path | Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        if isinstance(source, Mapping):
            data: Any = dict(source)
        elif isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise FileNotFoundError(f"No existe la configuración EntityRuler: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            raise TypeError("config debe ser una ruta o un diccionario")

        if isinstance(data, dict) and "entity_ruler" in data:
            data = data["entity_ruler"]
        if isinstance(data, dict):
            data = data.get("patterns")
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ValueError("La configuración debe contener una lista 'entity_ruler'.")
        return [dict(item) for item in data]

    def annotate(self, doc: Doc) -> Doc:
        """Aplica el componente in-place y retorna el mismo ``Doc``."""
        if not isinstance(doc, Doc):
            raise TypeError("doc debe ser spacy.tokens.Doc.")
        if doc.vocab is not self._nlp.vocab:
            raise ValueError("doc debe compartir el vocabulario del pipeline configurado.")
        return self._nlp.get_pipe(self._component_name)(doc)

    def analyze(self, text: str) -> EntityRulerResult:
        if not isinstance(text, str):
            raise TypeError("text debe ser str.")
        doc = self.annotate(self._nlp.make_doc(text))
        return self.result_from_doc(doc)

    @staticmethod
    def result_from_doc(doc: Doc) -> EntityRulerResult:
        entities = tuple(
            EntityRulerEntity(
                entity_type=span.label_,
                entity_id=span.ent_id_ or span.label_.casefold(),
                text=span.text,
                start_char=span.start_char,
                end_char=span.end_char,
                start_token=span.start,
                end_token=span.end,
            )
            for span in doc.ents
        )
        return EntityRulerResult(text=doc.text, entities=entities)

    @property
    def nlp(self) -> Language:
        return self._nlp

    @property
    def patterns(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(pattern) for pattern in self._patterns)
