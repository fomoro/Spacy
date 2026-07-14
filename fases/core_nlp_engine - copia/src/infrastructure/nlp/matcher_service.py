"""Detección tokenizada de estructuras de intención con spaCy."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping
import json
import re

import spacy
from spacy.language import Language
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span

from .phrase_matcher_service import PhraseMatcherService, PhraseEntity, PhraseMatchResult


@dataclass(frozen=True)
class MatcherEvidence:
    rule_id: str
    intent: str
    subintent: str
    weight: float
    text: str
    start_token: int
    end_token: int
    requires_context: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StructuredExtraction:
    quantities: tuple[int, ...]
    monetary_values: tuple[int, ...]
    has_negation: bool
    referenced_entities: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            'quantities': list(self.quantities),
            'monetary_values': list(self.monetary_values),
            'has_negation': self.has_negation,
            'referenced_entities': list(self.referenced_entities),
        }


@dataclass(frozen=True)
class MatcherResult:
    text: str
    evidence: tuple[MatcherEvidence, ...]
    extraction: StructuredExtraction
    phrase_entities: tuple[PhraseEntity, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            'text': self.text,
            'evidence': [item.to_dict() for item in self.evidence],
            'extraction': self.extraction.to_dict(),
            'phrase_entities': [item.to_dict() for item in self.phrase_entities],
        }


class MatcherService:
    """Detecta estructuras de intención y datos sintácticos básicos.

    Matcher produce evidencia. No selecciona una respuesta ni aplica reglas de negocio.
    """

    def __init__(
        self,
        config: str | Path | Mapping[str, Any],
        phrase_matcher: PhraseMatcherService,
        nlp: Language | None = None,
    ) -> None:
        if phrase_matcher is None:
            raise ValueError('phrase_matcher es obligatorio.')
        self._catalog = self._load_catalog(config)
        self._nlp = nlp or spacy.blank('es')
        self._phrase_matcher = phrase_matcher
        self._matcher = Matcher(self._nlp.vocab)
        self._metadata: dict[int, dict[str, Any]] = {}
        self._build()

    @staticmethod
    def _load_catalog(source: str | Path | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(source, Mapping):
            data = dict(source)
        elif isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise FileNotFoundError(f'No existe la configuración Matcher: {path}')
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise TypeError(f'Se esperaba un objeto JSON en {path}')
        else:
            raise TypeError('config debe ser una ruta o un diccionario')
        data = data.get('matcher', data)
        if not isinstance(data.get('patterns'), list):
            raise ValueError("La configuración debe contener 'matcher.patterns'.")
        return data

    def _build(self) -> None:
        for item in self._catalog['patterns']:
            rule_id = str(item['id'])
            pattern = item['pattern']
            self._matcher.add(rule_id, [pattern])
            match_id = self._nlp.vocab.strings[rule_id]
            self._metadata[match_id] = {
                'rule_id': rule_id,
                'intent': item['intent'],
                'subintent': item['subintent'],
                'weight': float(item['weight']),
                'requires_context': bool(item.get('requires_context', False)),
                'full_text_only': bool(item.get('full_text_only', False)),
            }

    def analyze(
        self,
        text: str,
        phrase_result: PhraseMatchResult | None = None,
    ) -> MatcherResult:
        if not isinstance(text, str):
            raise TypeError('text debe ser str.')
        if not text.strip():
            return MatcherResult(
                text=text,
                evidence=(),
                extraction=StructuredExtraction((), (), False, ()),
                phrase_entities=(),
            )

        doc, phrase_entities = self._build_annotated_doc(text, phrase_result)
        evidence: list[MatcherEvidence] = []
        seen: set[tuple[str, int, int]] = set()

        for match_id, start, end in self._matcher(doc):
            metadata = self._metadata[match_id]
            if metadata['full_text_only'] and any(
                not token.is_space and not token.is_punct
                for token in doc
                if token.i < start or token.i >= end
            ):
                continue
            key = (metadata['rule_id'], start, end)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(MatcherEvidence(
                rule_id=metadata['rule_id'],
                intent=metadata['intent'],
                subintent=metadata['subintent'],
                weight=metadata['weight'],
                text=doc[start:end].text,
                start_token=start,
                end_token=end,
                requires_context=metadata['requires_context'],
            ))

        evidence.sort(key=lambda item: (-item.weight, item.start_token, item.rule_id))
        extraction = self._extract(doc, phrase_entities)
        return MatcherResult(text, tuple(evidence), extraction, tuple(phrase_entities))

    def _build_annotated_doc(
        self,
        text: str,
        phrase_result: PhraseMatchResult | None = None,
    ) -> tuple[Doc, list[PhraseEntity]]:
        doc = self._nlp.make_doc(text)
        phrase_result = phrase_result or self._phrase_matcher.match(text)
        spans: list[Span] = []
        accepted: list[PhraseEntity] = []
        occupied_tokens: set[int] = set()

        # doc.ents no permite solapamientos. Para Matcher se conserva la entidad
        # de mayor longitud/prioridad; el resultado completo de PhraseMatcher
        # permanece disponible en phrase_entities.
        ordered = sorted(
            phrase_result.entities,
            key=lambda entity: (
                -(entity.end_token - entity.start_token),
                -{
                    'PRODUCTO_ESPECIFICO': 1000,
                    'PRODUCTO_BASE': 900,
                    'PREPARACION': 800,
                    'CATEGORIA': 700,
                    'MEDIO_PAGO': 700,
                    'SERVICIO': 600,
                    'ALERGENO': 500,
                    'INGREDIENTE': 400,
                }.get(entity.entity_type, 0),
                -entity.priority,
                entity.start_token,
            ),
        )
        for entity in ordered:
            token_range = set(range(entity.start_token, entity.end_token))
            if occupied_tokens.intersection(token_range):
                continue
            span = doc.char_span(
                entity.start_char,
                entity.end_char,
                label=entity.entity_type,
                span_id=entity.entity_id,
                alignment_mode='contract',
            )
            if span is None:
                continue
            spans.append(span)
            accepted.append(entity)
            occupied_tokens.update(token_range)

        spans.sort(key=lambda span: span.start)
        accepted.sort(key=lambda entity: entity.start_token)
        doc.ents = tuple(spans)
        return doc, accepted

    @staticmethod
    def _extract(doc: Doc, entities: list[PhraseEntity]) -> StructuredExtraction:
        quantities: list[int] = []
        money: list[int] = []
        number_words = {
            'un':1,'una':1,'uno':1,'dos':2,'tres':3,'cuatro':4,'cinco':5,
            'seis':6,'siete':7,'ocho':8,'nueve':9,'diez':10,'once':11,
            'doce':12,'quince':15,'veinte':20,'veinticinco':25,'cincuenta':50,
        }
        for token in doc:
            clean = token.text.lower().replace('.', '').replace(',', '')
            value = None
            if clean.isdigit():
                value = int(clean)
            elif clean in number_words:
                value = number_words[clean]
            if value is None:
                continue
            next_text = doc[token.i + 1].lower_ if token.i + 1 < len(doc) else ''
            if next_text == 'lucas':
                money.append(value * 1000)
            elif next_text in {'mil','pesos'} or '$' in token.text:
                money.append(value * (1000 if next_text == 'mil' else 1))
            else:
                quantities.append(value)

        has_negation = any(token.lower_ in {'sin','no','nunca'} for token in doc)
        refs = tuple({
            'entity_type': e.entity_type,
            'entity_id': e.entity_id,
            'canonical': e.canonical,
            'text': e.text,
        } for e in entities)
        return StructuredExtraction(tuple(quantities), tuple(money), has_negation, refs)

    @property
    def catalog(self) -> dict[str, Any]:
        return self._catalog
