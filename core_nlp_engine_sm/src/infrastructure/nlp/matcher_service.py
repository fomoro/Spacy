"""Detección tokenizada de señales sintácticas neutrales con spaCy."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping
import json
import re

import spacy
from spacy.language import Language
from spacy.matcher import Matcher
from spacy.tokens import Doc


@dataclass(frozen=True)
class MatcherSignal:
    rule_id: str
    text: str
    start_token: int
    end_token: int

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
    signals: tuple[MatcherSignal, ...]
    extraction: StructuredExtraction

    def to_dict(self) -> dict[str, Any]:
        return {
            'text': self.text,
            'signals': [item.to_dict() for item in self.signals],
            'extraction': self.extraction.to_dict(),
        }


class MatcherService:
    """Detecta señales lingüísticas y datos sintácticos básicos.

    Produce señales técnicas neutrales a partir del texto. No reconoce
    entidades comerciales, asigna intenciones, pondera evidencia ni ejecuta
    otros servicios.
    """

    def __init__(
        self,
        config: str | Path | Mapping[str, Any],
        nlp: Language | None = None,
    ) -> None:
        self._catalog = self._load_catalog(config)
        self._nlp = nlp or spacy.blank('es')
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
            token_pattern = pattern if isinstance(pattern, list) else [pattern]
            self._matcher.add(rule_id, [token_pattern])
            match_id = self._nlp.vocab.strings[rule_id]
            self._metadata[match_id] = {
                'rule_id': rule_id,
                'full_text_only': bool(item.get('full_text_only', False)),
            }

    def analyze(
        self,
        text: str,
    ) -> MatcherResult:
        if not isinstance(text, str):
            raise TypeError('text debe ser str.')
        if not text.strip():
            return MatcherResult(
                text=text,
                signals=(),
                extraction=StructuredExtraction((), (), False, ()),
            )

        doc = self._nlp.make_doc(text)
        signals: list[MatcherSignal] = []
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
            signals.append(MatcherSignal(
                rule_id=metadata['rule_id'],
                text=doc[start:end].text,
                start_token=start,
                end_token=end,
            ))

        signals.sort(key=lambda item: (item.start_token, item.rule_id, item.end_token))
        extraction = self._extract(doc)
        return MatcherResult(text, tuple(signals), extraction)

    @staticmethod
    def _extract(doc: Doc) -> StructuredExtraction:
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
        return StructuredExtraction(tuple(quantities), tuple(money), has_negation, ())

    @property
    def catalog(self) -> dict[str, Any]:
        return self._catalog
