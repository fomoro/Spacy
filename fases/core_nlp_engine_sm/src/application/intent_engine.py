
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.application.linguistic_parser import LinguisticParser, LinguisticEvidenceBundle
from src.application.intent_resolver import IntentResolver, IntentResolution


@dataclass(frozen=True)
class ResolvedNlpResult:
    evidence: LinguisticEvidenceBundle
    resolution: IntentResolution

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence.to_dict(),
            "resolution": self.resolution.to_dict(),
        }


class IntentEngine:
    """Integra análisis de evidencia y resolución de intención."""

    def __init__(self, parser: LinguisticParser, resolver: IntentResolver) -> None:
        if parser is None:
            raise ValueError("parser es obligatorio.")
        if resolver is None:
            raise ValueError("resolver es obligatorio.")
        self._parser = parser
        self._resolver = resolver

    def analyze(
        self,
        text: str,
        context: Mapping[str, Any] | None = None,
    ) -> ResolvedNlpResult:
        evidence = self._parser.analyze(text)
        resolution = self._resolver.resolve(evidence, context)
        return ResolvedNlpResult(evidence, resolution)
