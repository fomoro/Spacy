"""Renderiza la salida textual correspondiente a una resolución de intención."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from string import Formatter
from typing import Any, Mapping

from src.temp.intent_resolver import IntentResolution


@dataclass(frozen=True)
class RenderedResponse:
    """Respuesta producida y trazabilidad de la regla que la seleccionó."""

    text: str
    source: str
    template_key: str
    missing_values: tuple[str, ...] = ()
    used_fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "template_key": self.template_key,
            "missing_values": list(self.missing_values),
            "used_fallback": self.used_fallback,
        }


class ResponseRenderer:
    """Selecciona una respuesta directa o conserva la acción conversacional.

    Las preguntas, confirmaciones y avisos de intervención ya renderizados por
    ``IntentResolver`` tienen prioridad. Las plantillas de respuesta se usan
    únicamente cuando la intención termina directamente en ``resolved``.
    """

    def __init__(self, templates: str | Path | Mapping[str, Any]) -> None:
        self._config = self._load_config(templates)
        self._templates = self._normalize_templates(self._config)
        self._direct_responses = self._config[
            "direct_response_by_intent_and_subintent"
        ]
        self._fallback_template = str(self._config.get("fallback_template", "unknown"))
        self._validate_config()

    @staticmethod
    def _normalize_templates(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        """Adapta el catálogo simple y el catálogo con variantes al runtime."""
        raw_templates = config.get("templates", config.get("responses"))
        if not isinstance(raw_templates, Mapping) or not raw_templates:
            raise ValueError(
                "response_templates.json debe contener 'templates' o 'responses'."
            )

        unknown = raw_templates.get("unknown", {})
        unknown_variants = (
            unknown.get("templates", []) if isinstance(unknown, Mapping) else []
        )
        safe_fallback = (
            str(unknown_variants[0])
            if isinstance(unknown_variants, list) and unknown_variants
            else "No pude preparar una respuesta segura con la información disponible."
        )

        normalized: dict[str, dict[str, Any]] = {}
        for key, raw_definition in raw_templates.items():
            if not isinstance(raw_definition, Mapping):
                raise ValueError(f"La plantilla '{key}' debe ser un objeto.")

            if "template" in raw_definition:
                normalized[str(key)] = dict(raw_definition)
                continue

            variants = raw_definition.get("templates")
            if not isinstance(variants, list) or not variants or not all(
                isinstance(variant, str) and variant.strip() for variant in variants
            ):
                raise ValueError(
                    f"La respuesta '{key}' debe declarar variantes no vacías."
                )
            normalized[str(key)] = {
                "template": variants[0],
                "required_values": raw_definition.get("required_values", []),
                "fallback": safe_fallback,
            }
        return normalized

    @staticmethod
    def _load_config(source: str | Path | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(source, Mapping):
            data = dict(source)
        elif isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise FileNotFoundError(
                    f"No existe el catálogo de plantillas de respuesta: {path}"
                )
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise TypeError(f"Se esperaba un objeto JSON en {path}")
        else:
            raise TypeError("templates debe ser una ruta o un diccionario")
        return data

    def _validate_config(self) -> None:
        if not isinstance(self._templates, dict) or not self._templates:
            raise ValueError("response_templates.json debe contener 'templates'.")
        if not isinstance(self._direct_responses, dict) or not self._direct_responses:
            raise ValueError(
                "response_templates.json debe contener "
                "'direct_response_by_intent_and_subintent'."
            )
        if self._fallback_template not in self._templates:
            raise ValueError("La plantilla fallback declarada no existe.")

        for template_key, raw_definition in self._templates.items():
            if not isinstance(raw_definition, Mapping):
                raise ValueError(
                    f"La plantilla '{template_key}' debe ser un objeto."
                )
            definition = dict(raw_definition)
            if set(definition) != {"template", "required_values", "fallback"}:
                raise ValueError(
                    f"La plantilla '{template_key}' no coincide con el contrato."
                )
            template = str(definition["template"])
            fallback = str(definition["fallback"])
            required_values = definition["required_values"]
            if not template.strip() or not fallback.strip():
                raise ValueError(
                    f"La plantilla '{template_key}' requiere template y fallback."
                )
            if not isinstance(required_values, list) or not all(
                isinstance(value, str) and value for value in required_values
            ):
                raise ValueError(
                    f"La plantilla '{template_key}' tiene required_values inválido."
                )
            placeholders = {
                name for _, name, _, _ in Formatter().parse(template) if name
            }
            if placeholders != set(required_values):
                raise ValueError(
                    f"La plantilla '{template_key}' no sincroniza placeholders "
                    "y required_values."
                )
            fallback_placeholders = {
                name for _, name, _, _ in Formatter().parse(fallback) if name
            }
            if fallback_placeholders:
                raise ValueError(
                    f"El fallback de '{template_key}' no debe requerir valores."
                )

        for pair, template_key in self._direct_responses.items():
            if str(template_key) not in self._templates:
                raise ValueError(
                    f"La respuesta directa '{pair}' referencia una plantilla inexistente."
                )

    def render(
        self,
        resolution: IntentResolution,
        values: Mapping[str, Any] | None = None,
    ) -> RenderedResponse:
        if not isinstance(resolution, IntentResolution):
            raise TypeError("resolution debe ser IntentResolution")
        if values is not None and not isinstance(values, Mapping):
            raise TypeError("values debe ser un diccionario")

        if resolution.clarification_message:
            return RenderedResponse(
                text=resolution.clarification_message,
                source="conversation_action_rules",
                template_key=resolution.question_key or resolution.intervention_mode,
            )

        pair = (
            f"{resolution.intent}.{resolution.subintent}"
            if resolution.intent and resolution.subintent
            else ""
        )
        template_key = str(
            self._direct_responses.get(pair, self._fallback_template)
        )
        definition = self._templates[template_key]
        render_values = self._resolution_values(resolution)
        render_values.update(dict(values or {}))
        required_values = tuple(str(value) for value in definition["required_values"])
        missing_values = tuple(
            value
            for value in required_values
            if render_values.get(value) is None or render_values.get(value) == ""
        )
        if missing_values:
            return RenderedResponse(
                text=str(definition["fallback"]),
                source="response_templates",
                template_key=template_key,
                missing_values=missing_values,
                used_fallback=True,
            )

        return RenderedResponse(
            text=str(definition["template"]).format_map(render_values),
            source="response_templates",
            template_key=template_key,
        )

    @staticmethod
    def _resolution_values(resolution: IntentResolution) -> dict[str, Any]:
        values: dict[str, Any] = {}
        entity_value_by_field = {
            "product": {"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"},
            "preparation": {"PREPARACION"},
            "category": {"CATEGORIA"},
            "day": {"DIA_SEMANA", "FECHA_RELATIVA"},
        }
        for field, entity_types in entity_value_by_field.items():
            entity = next(
                (
                    item
                    for item in resolution.entities
                    if item.get("entity_type") in entity_types
                ),
                None,
            )
            if entity:
                values[field] = entity.get("canonical") or entity.get("text")
        return values

    @property
    def config(self) -> dict[str, Any]:
        return self._config
