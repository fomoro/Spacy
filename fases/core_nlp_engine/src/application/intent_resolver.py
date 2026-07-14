from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, TYPE_CHECKING
from collections import defaultdict
import json
import math

if TYPE_CHECKING:
    from .linguistic_parser import LinguisticEvidenceBundle


@dataclass(frozen=True)
class CandidateScore:
    intent: str
    subintent: str
    score: float
    priority: int
    reasons: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "subintent": self.subintent,
            "score": round(self.score, 4),
            "priority": self.priority,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class IntentResolution:
    intent: str | None
    subintent: str | None
    confidence: float
    status: str
    requires_clarification: bool
    clarification_reason: str | None
    clarification_message: str | None
    candidates: tuple[CandidateScore, ...]
    entities: tuple[dict[str, Any], ...]
    extraction: dict[str, Any]
    applied_rules: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "subintent": self.subintent,
            "confidence": round(self.confidence, 4),
            "status": self.status,
            "requires_clarification": self.requires_clarification,
            "clarification_reason": self.clarification_reason,
            "clarification_message": self.clarification_message,
            "candidates": [item.to_dict() for item in self.candidates],
            "entities": list(self.entities),
            "extraction": self.extraction,
            "applied_rules": list(self.applied_rules),
        }


class IntentResolver:
    """Combina Matcher, PhraseMatcher, lemas, EntityRuler y contexto.

    El resolutor selecciona intención y subintención o solicita aclaración.
    No consulta precios, inventario, horarios ni genera la respuesta comercial.
    """

    def __init__(self, config: str | Path | dict[str, Any]) -> None:
        if isinstance(config, (str, Path)):
            self._config_path = Path(config)
            self._config = self._load_config(self._config_path)
        elif isinstance(config, dict):
            self._config_path = None
            self._config = config.get("resolver", config)
        else:
            raise TypeError("config debe ser str, Path o dict[str, Any]")
            
        self._thresholds = self._config["thresholds"]
        self._multipliers = self._config["source_multipliers"]
        self._priorities = self._config["intent_priorities"]

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"No existe la configuración del resolutor: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        data = data.get("resolver", data)
        if not isinstance(data.get("thresholds"), dict):
            raise ValueError("La configuración debe contener 'thresholds'.")
        return data

    def resolve(
        self,
        bundle: LinguisticEvidenceBundle | Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> IntentResolution:
        payload = bundle.to_dict() if hasattr(bundle, "to_dict") else dict(bundle)
        context = dict(context or {})
        scores: dict[tuple[str, str], float] = defaultdict(float)
        reasons: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        applied_rules: list[str] = []

        self._add_matcher_evidence(payload, scores, reasons)
        self._add_lemma_evidence(payload, scores, reasons)
        self._add_phrase_evidence(payload, scores, reasons)
        self._apply_context_rules(payload, context, scores, reasons, applied_rules)
        self._apply_priority_rules(payload, context, scores, reasons, applied_rules)

        candidates = self._build_candidates(scores, reasons)
        entities = tuple(payload.get("phrase_matcher", {}).get("entities", []))
        extraction = dict(payload.get("matcher", {}).get("extraction", {}))

        if not candidates or candidates[0].score < float(self._thresholds["minimum_score"]):
            return IntentResolution(
                intent=None,
                subintent=None,
                confidence=0.0,
                status="unknown",
                requires_clarification=True,
                clarification_reason="no_evidence",
                clarification_message=self._message("no_evidence"),
                candidates=tuple(candidates[:5]),
                entities=entities,
                extraction=extraction,
                applied_rules=tuple(applied_rules),
            )

        top = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        close = (
            second is not None
            and top.intent != second.intent
            and top.score - second.score < float(self._thresholds["clarification_margin"])
        )

        missing_reason = self._missing_requirement(top, payload, context)
        if missing_reason:
            return IntentResolution(
                intent=top.intent,
                subintent=top.subintent,
                confidence=self._confidence(top.score, second.score if second else 0.0),
                status="needs_clarification",
                requires_clarification=True,
                clarification_reason=missing_reason,
                clarification_message=self._message(missing_reason),
                candidates=tuple(candidates[:5]),
                entities=entities,
                extraction=extraction,
                applied_rules=tuple(applied_rules),
            )

        if close and not self._top_has_priority_override(applied_rules, top):
            return IntentResolution(
                intent=top.intent,
                subintent=top.subintent,
                confidence=self._confidence(top.score, second.score),
                status="ambiguous",
                requires_clarification=True,
                clarification_reason="close_candidates",
                clarification_message=self._message("close_candidates"),
                candidates=tuple(candidates[:5]),
                entities=entities,
                extraction=extraction,
                applied_rules=tuple(applied_rules),
            )

        return IntentResolution(
            intent=top.intent,
            subintent=top.subintent,
            confidence=self._confidence(top.score, second.score if second else 0.0),
            status="resolved",
            requires_clarification=False,
            clarification_reason=None,
            clarification_message=None,
            candidates=tuple(candidates[:5]),
            entities=entities,
            extraction=extraction,
            applied_rules=tuple(applied_rules),
        )

    def _add(self, scores, reasons, intent, subintent, weight, source, detail) -> None:
        key = (str(intent), str(subintent))
        value = max(0.0, float(weight))
        scores[key] += value
        reasons[key].append({"source": source, "weight": round(value, 4), "detail": detail})

    def _add_matcher_evidence(self, payload, scores, reasons) -> None:
        multiplier = float(self._multipliers.get("matcher", 1.0))
        for item in payload.get("matcher", {}).get("evidence", []):
            self._add(
                scores, reasons, item["intent"], item["subintent"],
                float(item["weight"]) * multiplier,
                "Matcher", item.get("rule_id", "matcher_rule")
            )

    def _add_lemma_evidence(self, payload, scores, reasons) -> None:
        for item in payload.get("lemmas", {}).get("evidence", []):
            source = str(item.get("source", "surface"))
            multiplier_key = f"lemma_{source}"
            multiplier = float(self._multipliers.get(multiplier_key, 0.5))
            self._add(
                scores, reasons, item["intent"], item["subintent"],
                float(item["weight"]) * multiplier,
                f"Lemma:{source}", item.get("lemma", item.get("matched_text", ""))
            )

    def _add_phrase_evidence(self, payload, scores, reasons) -> None:
        phrase_map = self._config.get("phrase_evidence", {})
        service_map = self._config.get("service_entity_map", {})
        multiplier = float(self._multipliers.get("phrase", 1.0))
        for entity in payload.get("phrase_matcher", {}).get("entities", []):
            entity_type = entity.get("entity_type")
            entity_id = entity.get("entity_id")
            if entity_type == "SERVICIO" and entity_id in service_map:
                item = service_map[entity_id]
                self._add(
                    scores, reasons, item["intent"], item["subintent"],
                    float(item["weight"]) * multiplier,
                    "PhraseMatcher", f"SERVICIO:{entity_id}"
                )
            for item in phrase_map.get(entity_type, []):
                self._add(
                    scores, reasons, item["intent"], item["subintent"],
                    float(item["weight"]) * multiplier,
                    "PhraseMatcher", f"{entity_type}:{entity_id}"
                )

    def _apply_context_rules(self, payload, context, scores, reasons, applied_rules) -> None:
        entities = payload.get("phrase_matcher", {}).get("entities", [])
        entity_ids = {item.get("entity_id") for item in entities}
        text = str(payload.get("normalized_text", ""))

        if "ultimo_elemento" in entity_ids and "otra vez" in text:
            if context.get("menu_enviado_previamente") or context.get("menu_pdf_ultima_fecha_envio"):
                self._add(scores, reasons, "menu", "reenviar_menu", 0.62, "Context", "menu_previamente_enviado")
                applied_rules.append("CTX_MENU_REENVIO")

        if any(item.get("entity_type") == "REFERENCIA_CONTEXTUAL" for item in entities):
            product = context.get("producto_activo")
            if product:
                self._add(scores, reasons, "pedido", "seleccionar_preparacion", 0.16, "Context", f"producto_activo:{product}")
                applied_rules.append("CTX_PRODUCTO_ACTIVO")

        quantities = payload.get("matcher", {}).get("extraction", {}).get("quantities", [])
        if quantities and context.get("producto_activo"):
            self._add(scores, reasons, "pedido", "indicar_cantidad", 0.34, "Context", "cantidad_con_producto_activo")
            applied_rules.append("CTX_CANTIDAD_PRODUCTO")

    def _apply_priority_rules(self, payload, context, scores, reasons, applied_rules) -> None:
        text = str(payload.get("normalized_text", ""))
        entities = payload.get("phrase_matcher", {}).get("entities", [])
        entity_types = {item.get("entity_type") for item in entities}
        extraction = payload.get("matcher", {}).get("extraction", {})

        if "ALERGENO" in entity_types and any(word in text for word in ("alérg", "alerg", "intoler", "contamin")):
            subintent = "consultar_contaminacion_cruzada" if "contamin" in text or "utensilio" in text or "aceite" in text else "consultar_alergenos"
            self._add(scores, reasons, "seguridad_alimentaria", subintent, 0.75, "PriorityRule", "safety_first")
            applied_rules.append("PRIORITY_SAFETY_FIRST")

        price_markers = any(word in text for word in ("cuánto", "cuanto", "precio", "vale", "valen", "cuesta", "cuestan"))
        product_present = bool(entity_types.intersection({"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"}))
        if price_markers and product_present:
            self._add(scores, reasons, "precio", "consultar_precio_producto", 0.48, "PriorityRule", "explicit_price_with_product")
            applied_rules.append("PRIORITY_PRICE_OVER_WANT")

        money = extraction.get("monetary_values", [])
        budget_markers = any(word in text for word in ("barato", "económico", "economico", "presupuesto", "lucas"))
        if money or budget_markers:
            if any(word in text for word in ("qué puedo", "que puedo", "recomienda", "barato", "económico", "economico")):
                self._add(scores, reasons, "precio", "solicitar_recomendacion_por_presupuesto", 0.52, "PriorityRule", "budget_recommendation")
                applied_rules.append("PRIORITY_BUDGET")

        if extraction.get("has_negation") and ("INGREDIENTE" in entity_types or "PREPARACION" in entity_types):
            self._add(scores, reasons, "pedido", "solicitar_modificacion", 0.48, "PriorityRule", "negation_modification")
            applied_rules.append("PRIORITY_NEGATION_MODIFICATION")

        if "otra vez" in text and (context.get("menu_enviado_previamente") or context.get("menu_pdf_ultima_fecha_envio")):
            self._add(scores, reasons, "menu", "reenviar_menu", 0.58, "PriorityRule", "explicit_again_with_menu_history")
            applied_rules.append("PRIORITY_MENU_REENVIO")

    def _build_candidates(self, scores, reasons) -> list[CandidateScore]:
        candidates = [
            CandidateScore(
                intent=key[0],
                subintent=key[1],
                score=value,
                priority=int(self._priorities.get(key[0], 0)),
                reasons=tuple(reasons[key]),
            )
            for key, value in scores.items()
            if value > 0
        ]
        candidates.sort(key=lambda item: (-item.score, -item.priority, item.intent, item.subintent))
        return candidates

    def _missing_requirement(self, top: CandidateScore, payload, context) -> str | None:
        entities = payload.get("phrase_matcher", {}).get("entities", [])
        types = {item.get("entity_type") for item in entities}
        extraction = payload.get("matcher", {}).get("extraction", {})
        key = f"{top.intent}.{top.subintent}"

        if key == "precio.consultar_precio_producto" and not types.intersection({"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"}):
            return "missing_product"
        if key == "catalogo.consultar_detalle_producto" and not types.intersection({"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"}):
            return "missing_product"
        if key == "catalogo.consultar_preparacion_producto" and "PREPARACION" not in types:
            return "missing_preparation"
        if key == "pedido.indicar_cantidad" and not context.get("producto_activo"):
            return "missing_context"
        if key == "pedido.seleccionar_preparacion" and not context.get("producto_activo") and not types.intersection({"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"}):
            return "missing_context"
        if key == "seguridad_alimentaria.consultar_alergenos" and not types.intersection({"ALERGENO", "INGREDIENTE"}):
            return "safety_confirmation"
        return None

    def _confidence(self, top_score: float, second_score: float) -> float:
        if top_score <= 0:
            return 0.0
        margin = max(0.0, top_score - second_score)
        raw = 1.0 - math.exp(-(0.9 * top_score + 0.7 * margin))
        return min(float(self._thresholds.get("maximum_confidence", 0.99)), max(0.0, raw))

    def _message(self, reason: str) -> str:
        return str(self._config.get("clarification_messages", {}).get(reason, self._config["clarification_messages"]["no_evidence"]))

    @staticmethod
    def _top_has_priority_override(applied_rules: list[str], top: CandidateScore) -> bool:
        if top.intent == "seguridad_alimentaria" and "PRIORITY_SAFETY_FIRST" in applied_rules:
            return True
        if top.intent == "precio" and any(rule in applied_rules for rule in ("PRIORITY_PRICE_OVER_WANT", "PRIORITY_BUDGET")):
            return True
        if top.intent == "menu" and "PRIORITY_MENU_REENVIO" in applied_rules:
            return True
        return False

    @property
    def config(self) -> dict[str, Any]:
        return self._config
