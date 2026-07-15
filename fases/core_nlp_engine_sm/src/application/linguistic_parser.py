
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.infrastructure.nlp.text_normalizer_service import TextNormalizerService
from src.infrastructure.nlp.phrase_matcher_service import PhraseMatcherService
from src.infrastructure.nlp.matcher_service import MatcherService
from src.infrastructure.nlp.lemma_service import LemmaService
from src.infrastructure.nlp.entity_ruler_service import EntityRulerService


@dataclass(frozen=True)
class LinguisticEvidenceBundle:
    original_text: str
    normalized_text: str
    normalization: dict[str, Any]
    phrase_matcher: dict[str, Any]
    matcher: dict[str, Any]
    lemmas: dict[str, Any]
    entity_ruler: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "normalization": self.normalization,
            "phrase_matcher": self.phrase_matcher,
            "matcher": self.matcher,
            "lemmas": self.lemmas,
            "entity_ruler": self.entity_ruler,
        }


class LinguisticParser:
    """Orquesta fuentes de evidencia sin resolver la intención final."""

    def __init__(
        self,
        normalizer: TextNormalizerService,
        phrase_matcher: PhraseMatcherService,
        matcher: MatcherService,
        lemma_service: LemmaService,
        entity_ruler: EntityRulerService,
    ) -> None:
        if normalizer is None:
            raise ValueError("normalizer es obligatorio.")
        if phrase_matcher is None:
            raise ValueError("phrase_matcher es obligatorio.")
        if matcher is None:
            raise ValueError("matcher es obligatorio.")
        if lemma_service is None:
            raise ValueError("lemma_service es obligatorio.")
        if entity_ruler is None:
            raise ValueError("entity_ruler es obligatorio.")

        self._normalizer = normalizer
        self._phrase_matcher = phrase_matcher
        self._matcher = matcher
        self._lemma_service = lemma_service
        self._entity_ruler = entity_ruler

    def analyze(self, text: str) -> LinguisticEvidenceBundle:
        if not isinstance(text, str):
            raise TypeError("text debe ser str.")

        normalization = self._normalizer.normalize(text)
        normalized = normalization.normalized
        phrase_result = self._phrase_matcher.match(normalized)
        matcher_result = self._matcher.analyze(normalized, phrase_result)
        lemma_result = self._lemma_service.analyze(normalized)
        entity_ruler_result = self._entity_ruler.analyze(normalized)

        return LinguisticEvidenceBundle(
            original_text=text,
            normalized_text=normalized,
            normalization=normalization.to_dict(),
            phrase_matcher=phrase_result.to_dict(),
            matcher=matcher_result.to_dict(),
            lemmas=lemma_result.to_dict(),
            entity_ruler=entity_ruler_result.to_dict(),
        )
