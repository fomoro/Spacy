
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.temp.linguistic_parser import LinguisticParser, LinguisticEvidenceBundle
from src.temp.intent_resolver import IntentResolver, IntentResolution
from src.temp.response_renderer import RenderedResponse, ResponseRenderer


@dataclass(frozen=True)
class ResolvedNlpResult:
    evidence: LinguisticEvidenceBundle
    resolution: IntentResolution
    response: RenderedResponse

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence.to_dict(),
            "resolution": self.resolution.to_dict(),
            "response": self.response.to_dict(),
        }


class IntentEngine:
    """Integra análisis de evidencia y resolución de intención."""

    def __init__(
        self,
        parser: LinguisticParser,
        resolver: IntentResolver,
        response_renderer: ResponseRenderer,
    ) -> None:
        if parser is None:
            raise ValueError("parser es obligatorio.")
        if resolver is None:
            raise ValueError("resolver es obligatorio.")
        if response_renderer is None:
            raise ValueError("response_renderer es obligatorio.")
        self._parser = parser
        self._resolver = resolver
        self._response_renderer = response_renderer

    def analyze(
        self,
        text: str,
        context: Mapping[str, Any] | None = None,
        response_values: Mapping[str, Any] | None = None,
    ) -> ResolvedNlpResult:
        evidence = self._parser.analyze(text)
        resolution = self._resolver.resolve(evidence, context)
        response = self._response_renderer.render(resolution, response_values)
        return ResolvedNlpResult(evidence, resolution, response)
