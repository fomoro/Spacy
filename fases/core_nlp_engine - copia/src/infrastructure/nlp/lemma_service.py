
"""Análisis de lemas y evidencia morfológica secundaria."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping
import json
import unicodedata

import spacy
from spacy.language import Language


@dataclass(frozen=True)
class LemmaToken:
    text: str
    normalized: str
    lemma: str
    index: int
    pos: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LemmaEvidence:
    lemma: str
    matched_text: str
    intent: str
    subintent: str
    weight: float
    token_index: int
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LemmaAnalysisResult:
    text: str
    tokens: tuple[LemmaToken, ...]
    evidence: tuple[LemmaEvidence, ...]
    model_has_lemmatizer: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "tokens": [item.to_dict() for item in self.tokens],
            "evidence": [item.to_dict() for item in self.evidence],
            "model_has_lemmatizer": self.model_has_lemmatizer,
        }


class LemmaService:
    """
    Analiza lemas y genera evidencia secundaria de intención.

    Prioridad:
    1. token.lemma_ producido por un pipeline spaCy con lematizador.
    2. Catálogo controlado de formas flexionadas como fallback.

    No resuelve la intención final y no modifica contexto ni reglas de negocio.
    """

    def __init__(
        self,
        config: str | Path | Mapping[str, Any],
        nlp: Language | None = None,
        model_name: str = "es_core_news_sm",
        allow_catalog_fallback: bool = True,
    ) -> None:
        self._catalog = self._load_catalog(config)
        self._allow_catalog_fallback = allow_catalog_fallback
        self._nlp = nlp or self._load_preferred_model(model_name)
        self._model_has_lemmatizer = "lemmatizer" in self._nlp.pipe_names

        self._signals_by_lemma: dict[str, list[dict[str, Any]]] = {}
        self._lemma_by_form: dict[str, str] = {}
        self._stop_lemmas = {
            self._normalize(value)
            for value in self._catalog.get("stop_lemmas", [])
        }
        self._ignored_pos = set(
            self._catalog["metadata"].get("ignored_pos", [])
        )
        self._minimum_token_length = int(
            self._catalog["metadata"].get("minimum_token_length", 1)
        )
        self._build_indexes()

    @staticmethod
    def _load_catalog(source: str | Path | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(source, Mapping):
            data = dict(source)
        elif isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise FileNotFoundError(f"No existe la configuración de lemas: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise TypeError(f"Se esperaba un objeto JSON en {path}")
        else:
            raise TypeError("config debe ser una ruta o un diccionario")
        data = data.get("lemmas", data)
        if not isinstance(data.get("signals"), list):
            raise ValueError("La configuración debe contener 'lemmas.signals'.")
        return data

    @staticmethod
    def _load_preferred_model(model_name: str) -> Language:
        try:
            return spacy.load(model_name)
        except OSError:
            return spacy.blank("es")

    def _build_indexes(self) -> None:
        for signal in self._catalog["signals"]:
            lemma = self._normalize(str(signal["lemma"]))
            evidence = signal.get("evidence", [])
            self._signals_by_lemma.setdefault(lemma, []).extend(evidence)

            forms = set(signal.get("forms", []))
            forms.add(signal["lemma"])
            for form in forms:
                normalized_form = self._normalize(str(form))
                if " " not in normalized_form:
                    self._lemma_by_form[normalized_form] = lemma

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFC", value.casefold().strip())
        return " ".join(normalized.split())

    def analyze(self, text: str) -> LemmaAnalysisResult:
        if not isinstance(text, str):
            raise TypeError("text debe ser str.")
        if not text.strip():
            return LemmaAnalysisResult(text, (), (), self._model_has_lemmatizer)

        doc = self._nlp(text)
        tokens: list[LemmaToken] = []
        evidence: list[LemmaEvidence] = []
        seen_evidence: set[tuple[str, str, str, int]] = set()

        for token in doc:
            if token.is_space or token.is_punct:
                continue
            if token.pos_ in self._ignored_pos:
                continue

            normalized = self._normalize(token.text)
            if len(normalized) < self._minimum_token_length:
                continue

            lemma, source = self._resolve_lemma(token, normalized)
            tokens.append(
                LemmaToken(
                    text=token.text,
                    normalized=normalized,
                    lemma=lemma,
                    index=token.i,
                    pos=token.pos_,
                    source=source,
                )
            )

            if lemma in self._stop_lemmas:
                continue

            for item in self._signals_by_lemma.get(lemma, []):
                key = (
                    lemma,
                    str(item["intent"]),
                    str(item["subintent"]),
                    token.i,
                )
                if key in seen_evidence:
                    continue
                seen_evidence.add(key)
                evidence.append(
                    LemmaEvidence(
                        lemma=lemma,
                        matched_text=token.text,
                        intent=str(item["intent"]),
                        subintent=str(item["subintent"]),
                        weight=float(item["weight"]),
                        token_index=token.i,
                        source=source,
                    )
                )

        evidence.sort(
            key=lambda item: (
                -item.weight,
                item.token_index,
                item.intent,
                item.subintent,
            )
        )
        return LemmaAnalysisResult(
            text=text,
            tokens=tuple(tokens),
            evidence=tuple(evidence),
            model_has_lemmatizer=self._model_has_lemmatizer,
        )

    def _resolve_lemma(self, token: Any, normalized: str) -> tuple[str, str]:
        if self._allow_catalog_fallback:
            fallback = self._lemma_by_form.get(normalized)
            if fallback:
                return fallback, "catalog_fallback"

        spaCy_lemma = self._normalize(token.lemma_) if token.lemma_ else ""
        if (
            self._model_has_lemmatizer
            and spaCy_lemma
            and spaCy_lemma != "-pron-"
        ):
            if self._allow_catalog_fallback:
                fallback = self._lemma_by_form.get(spaCy_lemma)
                if fallback:
                    return fallback, "catalog_fallback"
            return spaCy_lemma, "spacy"

        return normalized, "surface"

    @property
    def model_has_lemmatizer(self) -> bool:
        return self._model_has_lemmatizer

    @property
    def catalog(self) -> dict[str, Any]:
        return self._catalog
