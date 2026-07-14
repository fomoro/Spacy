from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from src.infrastructure.services.normalizer_service import TextNormalizer
from src.infrastructure.services.phrase_matcher_service import PhraseMatcherService
from src.infrastructure.services.matcher_service import MatcherService
from src.infrastructure.services.lemma_service import LemmaService
from src.infrastructure.services.entity_ruler_service import EntityRulerService

@dataclass(frozen=True)
class LinguisticEvidenceBundle:
    original_text: str
    normalized_text: str
    normalization: dict[str, Any]
    phrase_matcher: dict[str, Any]
    matcher: dict[str, Any]
    lemmas: dict[str, Any]
    entity_ruler: list[dict[str, Any]]

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
    """Orquesta fuentes de evidencia lingüística (NLP) sin resolver la intención final."""

    def __init__(
        self,
        normalizer: TextNormalizer,
        phrase_matcher: PhraseMatcherService,
        matcher: MatcherService,
        lemma_service: LemmaService,
        entity_ruler: EntityRulerService | None = None,
    ) -> None:
        if normalizer is None:
            raise ValueError("normalizer es obligatorio.")
        if phrase_matcher is None:
            raise ValueError("phrase_matcher es obligatorio.")
        if matcher is None:
            raise ValueError("matcher es obligatorio.")
        if lemma_service is None:
            raise ValueError("lemma_service es obligatorio.")

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
        matcher_result = self._matcher.analyze(normalized)
        lemma_result = self._lemma_service.analyze(normalized)
        
        # EntityRuler extrae entidades directamente de forma independiente
        entity_ruler_result = []
        if self._entity_ruler is not None:
            entity_ruler_result = self._entity_ruler.match(normalized)
            
            # Puente de compatibilidad: inyectamos las entidades de EntityRuler
            # en phrase_result para que IntentResolver las detecte automáticamente.
            if entity_ruler_result:
                current_entities = list(phrase_result.entities)
                from src.infrastructure.services.phrase_matcher_service import PhraseEntity
                for ent_dict in entity_ruler_result:
                    phrase_ent = PhraseEntity(
                        entity_type=ent_dict["entity_type"],
                        entity_id=ent_dict["entity_id"],
                        canonical=ent_dict["canonical"],
                        text=ent_dict["text"],
                        normalized_text=ent_dict["text"].casefold(),
                        start_char=ent_dict["start_char"],
                        end_char=ent_dict["end_char"],
                        start_token=ent_dict["start_token"],
                        end_token=ent_dict["end_token"],
                        priority=ent_dict["priority"],
                        source="EntityRuler"
                    )
                    current_entities.append(phrase_ent)
                
                from src.infrastructure.services.phrase_matcher_service import PhraseMatchResult
                phrase_result = PhraseMatchResult(
                    text=phrase_result.text,
                    entities=tuple(current_entities),
                    discarded_overlaps=phrase_result.discarded_overlaps
                )

        return LinguisticEvidenceBundle(
            original_text=text,
            normalized_text=normalized,
            normalization=normalization.to_dict(),
            phrase_matcher=phrase_result.to_dict(),
            matcher=matcher_result.to_dict(),
            lemmas=lemma_result.to_dict(),
            entity_ruler=entity_ruler_result,
        )
