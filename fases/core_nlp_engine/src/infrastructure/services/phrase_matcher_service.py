
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import json

import spacy
from spacy.language import Language
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc, Span


@dataclass(frozen=True)
class PhraseEntity:
    entity_type: str
    entity_id: str
    canonical: str
    text: str
    normalized_text: str
    start_char: int
    end_char: int
    start_token: int
    end_token: int
    priority: int
    source: str = "PhraseMatcher"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PhraseMatchResult:
    text: str
    entities: tuple[PhraseEntity, ...]
    discarded_overlaps: tuple[PhraseEntity, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "entities": [entity.to_dict() for entity in self.entities],
            "discarded_overlaps": [
                entity.to_dict() for entity in self.discarded_overlaps
            ],
        }


class PhraseMatcherService:
    """
    Detecta vocabulario estable del dominio.

    Responsabilidades:
    - Cargar frases desde JSON.
    - Crear un PhraseMatcher usando LOWER.
    - Resolver solapamientos por longitud y prioridad.
    - Retornar entidades estructuradas.

    No determina intenciones, precios, disponibilidad ni respuestas.
    """

    def __init__(
        self,
        catalog_path: str | Path | dict[str, Any],
        nlp: Language | None = None,
    ) -> None:
        if isinstance(catalog_path, dict):
            self._catalog = catalog_path
            self._catalog_path = None
        else:
            self._catalog_path = Path(catalog_path)
            self._catalog = self._load_catalog(self._catalog_path)
            
        self._nlp = nlp or spacy.blank("es")
        self._matcher = PhraseMatcher(
            self._nlp.vocab,
            attr=self._catalog["metadata"].get("attr", "LOWER"),
        )
        self._metadata_by_match_id: dict[int, dict[str, Any]] = {}
        self._build()

    @staticmethod
    def _load_catalog(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"No existe el catálogo PhraseMatcher: {path}")
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data.get("entity_types"), dict):
            raise ValueError("El catálogo debe contener 'entity_types'.")
        return data

    def _build(self) -> None:
        seen_phrases: set[tuple[str, str, str]] = set()

        for entity_type, group in self._catalog["entity_types"].items():
            priority = int(group.get("priority", 0))
            for item in group.get("items", []):
                entity_id = str(item["id"])
                canonical = str(item.get("canonical", entity_id))
                phrases = self._clean_phrases(item.get("phrases", []))

                for index, phrase in enumerate(phrases):
                    dedupe_key = (entity_type, entity_id, phrase.casefold())
                    if dedupe_key in seen_phrases:
                        continue
                    seen_phrases.add(dedupe_key)

                    label = f"{entity_type}::{entity_id}::{index}"
                    patterns = [self._nlp.make_doc(phrase)]
                    self._matcher.add(label, patterns)
                    match_id = self._nlp.vocab.strings[label]
                    self._metadata_by_match_id[match_id] = {
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "canonical": canonical,
                        "priority": priority,
                    }

    @staticmethod
    def _clean_phrases(values: Iterable[Any]) -> list[str]:
        result: list[str] = []
        for value in values:
            if not isinstance(value, str):
                continue
            cleaned = " ".join(value.strip().split())
            if cleaned:
                result.append(cleaned)
        return result

    def match(self, text: str) -> PhraseMatchResult:
        if not isinstance(text, str):
            raise TypeError("text debe ser str.")

        doc = self._nlp.make_doc(text)
        candidates: list[PhraseEntity] = []

        for match_id, start, end in self._matcher(doc):
            metadata = self._metadata_by_match_id[match_id]
            span = doc[start:end]
            candidates.append(
                PhraseEntity(
                    entity_type=metadata["entity_type"],
                    entity_id=metadata["entity_id"],
                    canonical=metadata["canonical"],
                    text=span.text,
                    normalized_text=span.text.casefold(),
                    start_char=span.start_char,
                    end_char=span.end_char,
                    start_token=start,
                    end_token=end,
                    priority=metadata["priority"],
                )
            )

        selected, discarded = self._resolve_overlaps(candidates)
        return PhraseMatchResult(
            text=text,
            entities=tuple(selected),
            discarded_overlaps=tuple(discarded),
        )

    @staticmethod
    def _resolve_overlaps(
        candidates: list[PhraseEntity],
    ) -> tuple[list[PhraseEntity], list[PhraseEntity]]:
        ordered = sorted(
            candidates,
            key=lambda entity: (
                -(entity.end_char - entity.start_char),
                -entity.priority,
                entity.start_char,
                entity.entity_type,
                entity.entity_id,
            ),
        )

        selected: list[PhraseEntity] = []
        discarded: list[PhraseEntity] = []

        conflict_groups = [
            {"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"},
            {"ALERGENO", "INGREDIENTE"},
        ]

        def conflicts(left: PhraseEntity, right: PhraseEntity) -> bool:
            overlaps = (
                left.start_char < right.end_char
                and left.end_char > right.start_char
            )
            if not overlaps:
                return False
            if left.entity_type == right.entity_type:
                return True
            return any(
                left.entity_type in group and right.entity_type in group
                for group in conflict_groups
            )

        for candidate in ordered:
            has_conflict = any(conflicts(candidate, current) for current in selected)
            if has_conflict:
                discarded.append(candidate)
            else:
                selected.append(candidate)

        selected.sort(key=lambda entity: (entity.start_char, entity.end_char))
        discarded.sort(key=lambda entity: (entity.start_char, entity.end_char))
        return selected, discarded

    def annotate_doc(self, text: str, span_group: str = "phrase_entities") -> Doc:
        doc = self._nlp.make_doc(text)
        result = self.match(text)
        spans: list[Span] = []

        for entity in result.entities:
            span = doc.char_span(
                entity.start_char,
                entity.end_char,
                label=entity.entity_type,
                alignment_mode="contract",
            )
            if span is not None:
                spans.append(span)

        doc.spans[span_group] = spans
        return doc

    @property
    def catalog(self) -> dict[str, Any]:
        return self._catalog
