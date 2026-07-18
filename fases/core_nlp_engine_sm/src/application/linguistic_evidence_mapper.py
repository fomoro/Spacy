"""Traducción de observaciones lingüísticas a evidencia del dominio."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from src.application.linguistic_parser import ParsedNLPBundle


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

class LinguisticEvidenceMapper:
    """Traduce señales lingüísticas neutrales a evidencia del dominio.

    Esta clase no extrae texto ni conoce los servicios NLP. Recibe el resultado
    crudo de ``LinguisticParser`` y aplica las decisiones configurables de
    intención, subintención y peso que pertenecen a la capa de aplicación.
    """

    def __init__(self, config: str | Path | Mapping[str, Any]) -> None:
        self._config = self._load_config(config)
        self._matcher_signals = self._config["matcher_signals"]
        self._lemma_signals = self._config["lemma_signals"]
        self._phrase_entity_types = self._config["phrase_entity_types"]
        self._service_entities = self._config["service_entities"]
        self._entity_ruler_types = self._config["entity_ruler_types"]

    def map_bundle(self, parsed_bundle: ParsedNLPBundle) -> LinguisticEvidenceBundle:
        """Convierte un bundle NLP crudo en evidencia lista para resolver."""
        if not isinstance(parsed_bundle, ParsedNLPBundle):
            raise TypeError("parsed_bundle debe ser ParsedNLPBundle.")

        mapped = self.map_sections(
            phrase_matcher=parsed_bundle.phrase_matcher,
            matcher=parsed_bundle.matcher,
            lemmas=parsed_bundle.lemmas,
            entity_ruler=parsed_bundle.entity_ruler,
        )
        return LinguisticEvidenceBundle(
            original_text=parsed_bundle.original_text,
            normalized_text=parsed_bundle.normalized_text,
            normalization=parsed_bundle.normalization,
            phrase_matcher=mapped["phrase_matcher"],
            matcher=mapped["matcher"],
            lemmas=mapped["lemmas"],
            entity_ruler=mapped["entity_ruler"],
        )

    @staticmethod
    def _load_config(source: str | Path | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(source, Mapping):
            data = deepcopy(dict(source))
        elif isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise FileNotFoundError(
                    f"No existe el mapeo de evidencia lingüística: {path}"
                )
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise TypeError(f"Se esperaba un objeto JSON en {path}")
        else:
            raise TypeError("config debe ser una ruta o un diccionario")

        for key in (
            "matcher_signals",
            "lemma_signals",
            "phrase_entity_types",
            "service_entities",
            "entity_ruler_types",
        ):
            if not isinstance(data.get(key), dict):
                raise ValueError(f"El mapeo debe contener '{key}'.")
        return data

    def map_sections(
        self,
        *,
        phrase_matcher: Mapping[str, Any],
        matcher: Mapping[str, Any],
        lemmas: Mapping[str, Any],
        entity_ruler: Mapping[str, Any],
    ) -> dict[str, dict[str, Any]]:
        phrase_payload = deepcopy(dict(phrase_matcher))
        matcher_payload = deepcopy(dict(matcher))
        lemma_payload = deepcopy(dict(lemmas))
        ruler_payload = deepcopy(dict(entity_ruler))

        phrase_entities = list(phrase_payload.get("entities", []))
        matcher_payload["evidence"] = self._map_matcher_signals(
            matcher_payload.get("signals", []),
            phrase_entities,
        )
        extraction = matcher_payload.setdefault("extraction", {})
        extraction["referenced_entities"] = [
            {
                "entity_type": entity.get("entity_type"),
                "entity_id": entity.get("entity_id"),
                "canonical": entity.get("canonical"),
                "text": entity.get("text"),
            }
            for entity in phrase_entities
        ]

        lemma_payload["evidence"] = self._map_lemma_signals(
            lemma_payload.get("signals", [])
        )
        phrase_payload["evidence"] = self._map_phrase_entities(
            phrase_entities,
            str(phrase_payload.get("text", "")),
        )
        ruler_payload["evidence"] = self._map_entity_ruler_entities(
            ruler_payload.get("entities", [])
        )
        return {
            "phrase_matcher": phrase_payload,
            "matcher": matcher_payload,
            "lemmas": lemma_payload,
            "entity_ruler": ruler_payload,
        }

    def _map_matcher_signals(
        self,
        signals: object,
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        if not isinstance(signals, list):
            return evidence
        active_rule_ids = {
            str(signal.get("rule_id", ""))
            for signal in signals
            if isinstance(signal, Mapping)
        }
        modification_rules = {
            "MODIFICATION_REMOVE",
            "MODIFICATION_ADD",
            "MODIFICATION_ADAPT",
        }
        for signal in signals:
            if not isinstance(signal, Mapping):
                continue
            rule_id = str(signal.get("rule_id", ""))
            mapping = self._matcher_signals.get(rule_id)
            if not isinstance(mapping, Mapping):
                continue
            if (
                rule_id == "ORDER_WANT_PRODUCT"
                and active_rule_ids.intersection(modification_rules)
            ):
                continue
            if not self._requirements_are_met(
                mapping.get("entity_requirements", []),
                entities,
                signal,
            ):
                continue
            evidence.append(
                {
                    "rule_id": rule_id,
                    "intent": str(mapping["intent"]),
                    "subintent": str(mapping["subintent"]),
                    "weight": float(mapping["weight"]),
                    "text": str(signal.get("text", "")),
                    "start_token": int(signal.get("start_token", 0)),
                    "end_token": int(signal.get("end_token", 0)),
                    "requires_context": bool(
                        mapping.get("requires_context", False)
                    ),
                }
            )
        evidence.sort(
            key=lambda item: (
                -item["weight"],
                item["start_token"],
                item["rule_id"],
            )
        )
        return evidence

    @staticmethod
    def _requirements_are_met(
        requirements: object,
        entities: list[dict[str, Any]],
        signal: Mapping[str, Any],
    ) -> bool:
        if not isinstance(requirements, list):
            return False
        for requirement in requirements:
            if not isinstance(requirement, Mapping):
                return False
            minimum = int(requirement.get("min_count", 1))
            signal_start = int(signal.get("start_token", 0))
            signal_end = int(signal.get("end_token", signal_start))
            nearby_entities = [
                entity
                for entity in entities
                if LinguisticEvidenceMapper._token_distance(
                    signal_start,
                    signal_end,
                    int(entity.get("start_token", 0)),
                    int(entity.get("end_token", 0)),
                )
                <= 8
            ]
            if "entity_types" in requirement:
                accepted = set(requirement.get("entity_types", []))
                count = sum(
                    entity.get("entity_type") in accepted
                    for entity in nearby_entities
                )
            elif "entity_ids" in requirement:
                accepted = set(requirement.get("entity_ids", []))
                count = sum(
                    entity.get("entity_id") in accepted
                    for entity in nearby_entities
                )
            else:
                return False
            if count < minimum:
                return False
        return True

    @staticmethod
    def _token_distance(
        first_start: int,
        first_end: int,
        second_start: int,
        second_end: int,
    ) -> int:
        if second_end <= first_start:
            return first_start - second_end
        if second_start >= first_end:
            return second_start - first_end
        return 0

    def _map_lemma_signals(self, signals: object) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        if not isinstance(signals, list):
            return evidence
        for signal in signals:
            if not isinstance(signal, Mapping):
                continue
            lemma = str(signal.get("lemma", ""))
            for mapping in self._lemma_signals.get(lemma, []):
                evidence.append(
                    {
                        "lemma": lemma,
                        "matched_text": str(signal.get("matched_text", "")),
                        "intent": str(mapping["intent"]),
                        "subintent": str(mapping["subintent"]),
                        "weight": float(mapping["weight"]),
                        "token_index": int(signal.get("token_index", 0)),
                        "source": str(signal.get("source", "surface")),
                    }
                )
        evidence.sort(
            key=lambda item: (
                -item["weight"],
                item["token_index"],
                item["intent"],
                item["subintent"],
            )
        )
        return evidence

    def _map_phrase_entities(
        self,
        entities: list[dict[str, Any]],
        text: str,
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for entity in entities:
            entity_type = str(entity.get("entity_type", ""))
            entity_id = str(entity.get("entity_id", ""))
            if entity_type == "SERVICIO" and entity_id == "menu_pdf" and self._menu_entity_is_embedded(
                entity, entities, text
            ):
                continue
            mappings: list[Mapping[str, Any]] = []
            service_mapping = self._service_entities.get(entity_id)
            if entity_type == "SERVICIO" and isinstance(service_mapping, Mapping):
                mappings.append(service_mapping)
            type_mappings = self._phrase_entity_types.get(entity_type, [])
            if isinstance(type_mappings, list):
                mappings.extend(
                    item for item in type_mappings if isinstance(item, Mapping)
                )
            for mapping in mappings:
                evidence.append(
                    {
                        "intent": str(mapping["intent"]),
                        "subintent": str(mapping["subintent"]),
                        "weight": float(mapping["weight"]),
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                    }
                )
        return evidence

    @staticmethod
    def _menu_entity_is_embedded(
        menu_entity: Mapping[str, Any],
        entities: list[dict[str, Any]],
        text: str,
    ) -> bool:
        start = int(menu_entity.get("start_char", 0))
        end = int(menu_entity.get("end_char", 0))
        for other in entities:
            if other is menu_entity:
                continue
            other_start = int(other.get("start_char", 0))
            other_end = int(other.get("end_char", 0))
            contains = (
                other_start <= start
                and other_end >= end
                and (other_start < start or other_end > end)
            )
            adjacent = other_start >= end and not text[end:other_start].strip()
            if contains or adjacent:
                return True
        return False

    def _map_entity_ruler_entities(
        self,
        entities: object,
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        if not isinstance(entities, list):
            return evidence
        for entity in entities:
            if not isinstance(entity, Mapping):
                continue
            entity_type = str(entity.get("entity_type", ""))
            mappings = self._entity_ruler_types.get(entity_type, [])
            if not isinstance(mappings, list):
                continue
            for mapping in mappings:
                evidence.append(
                    {
                        "intent": str(mapping["intent"]),
                        "subintent": str(mapping["subintent"]),
                        "weight": float(mapping["weight"]),
                        "entity_type": entity_type,
                        "entity_id": str(entity.get("entity_id", "")),
                    }
                )
        return evidence

    @property
    def config(self) -> dict[str, Any]:
        return deepcopy(self._config)
