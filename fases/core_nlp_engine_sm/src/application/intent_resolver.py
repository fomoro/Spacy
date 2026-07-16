
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, TYPE_CHECKING
from collections import defaultdict
import json
import math
import re

if TYPE_CHECKING:
    from src.application.linguistic_parser import LinguisticEvidenceBundle


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
    intervention_mode: str
    missing_slots: tuple[str, ...]
    question_key: str | None
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
            "intervention_mode": self.intervention_mode,
            "missing_slots": list(self.missing_slots),
            "question_key": self.question_key,
            "candidates": [item.to_dict() for item in self.candidates],
            "entities": list(self.entities),
            "extraction": self.extraction,
            "applied_rules": list(self.applied_rules),
        }


class IntentResolver:
    """Combina Matcher, PhraseMatcher, lemas y contexto.

    El resolutor selecciona intención y subintención o solicita aclaración.
    No consulta precios, inventario, horarios ni genera la respuesta comercial.
    """

    def __init__(
        self,
        config: str | Path | Mapping[str, Any],
        conversation_action_rules: str | Path | Mapping[str, Any] | None = None,
    ) -> None:
        self._config = self._load_config(config)
        self._conversation_action_rules = self._load_conversation_action_rules(
            conversation_action_rules,
            resolver_source=config,
            resolver_config=self._config,
        )
        self._thresholds = self._config["thresholds"]
        self._multipliers = self._config["source_multipliers"]
        self._priorities = self._config["intent_priorities"]

    @staticmethod
    def _load_config(source: str | Path | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(source, Mapping):
            data = dict(source)
        elif isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise FileNotFoundError(f"No existe la configuración del resolutor: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise TypeError(f"Se esperaba un objeto JSON en {path}")
        else:
            raise TypeError("config debe ser una ruta o un diccionario")
        data = data.get("resolver", data)
        if not isinstance(data.get("thresholds"), dict):
            raise ValueError("La configuración debe contener 'thresholds'.")
        return data

    @staticmethod
    def _load_conversation_action_rules(
        source: str | Path | Mapping[str, Any] | None,
        *,
        resolver_source: str | Path | Mapping[str, Any],
        resolver_config: Mapping[str, Any],
    ) -> dict[str, Any]:
        selected = source
        if selected is None and isinstance(resolver_source, (str, Path)):
            resolver_path = Path(resolver_source)
            candidate = resolver_path.parent / "conversation_action_rules.json"
            if candidate.is_file():
                selected = candidate

        if isinstance(selected, Mapping):
            data = dict(selected)
        elif isinstance(selected, (str, Path)):
            path = Path(selected)
            if not path.is_file():
                raise FileNotFoundError(f"No existen las reglas de acción conversacional: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise TypeError(f"Se esperaba un objeto JSON en {path}")
        elif selected is None:
            legacy = resolver_config.get("clarification_messages", {})
            return {
                "conversation_actions": {
                    "needs_user_clarification": {"requires_clarification_compat": True}
                },
                "rules_by_intent_and_subintent": {},
                "questions": {
                    key: {"template": value}
                    for key, value in legacy.items()
                    if isinstance(value, str)
                },
            }
        else:
            raise TypeError(
                "conversation_action_rules debe ser una ruta, un diccionario o None"
            )

        questions = data.get("questions")
        if not isinstance(questions, dict):
            raise ValueError(
                "Las reglas de acción conversacional deben contener 'questions'."
            )

        for key in (
            "conversation_actions",
            "rules_by_intent_and_subintent",
            "questions",
        ):
            if not isinstance(data.get(key), dict):
                raise ValueError(
                    f"Las reglas de acción conversacional deben contener '{key}'."
                )
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
        self._add_entity_ruler_evidence(payload, scores, reasons)
        self._apply_context_rules(payload, context, scores, reasons, applied_rules)
        self._apply_priority_rules(payload, context, scores, reasons, applied_rules)

        candidates = self._build_candidates(scores, reasons)
        entities = tuple(self._all_entities(payload))
        extraction = dict(payload.get("matcher", {}).get("extraction", {}))

        if not candidates or candidates[0].score < float(self._thresholds["minimum_score"]):
            mode = "out_of_scope"
            return IntentResolution(
                intent=None,
                subintent=None,
                confidence=0.0,
                status="unknown",
                requires_clarification=self._mode_requires_clarification(mode),
                clarification_reason="out_of_scope",
                clarification_message=self._question("out_of_scope", payload),
                intervention_mode=mode,
                missing_slots=(),
                question_key="out_of_scope",
                candidates=tuple(candidates[:5]),
                entities=entities,
                extraction=extraction,
                applied_rules=tuple(applied_rules),
            )

        top = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        policy = self._policy(top)
        close = (
            second is not None
            and (top.intent, top.subintent) != (second.intent, second.subintent)
            and second.score >= float(self._thresholds["minimum_score"])
            and top.score - second.score < float(self._thresholds["clarification_margin"])
        )

        identity_required = policy.get("requires_identity_verification") is True
        identity_verified = context.get("identity_verified") is True
        if identity_required and not identity_verified:
            mode = "needs_identity_verification"
            question_key = str(
                policy.get("identity_question", "identity_verification_required")
            )
            applied_rules.append("POLICY_IDENTITY_VERIFICATION")
            return IntentResolution(
                intent=top.intent,
                subintent=top.subintent,
                confidence=self._confidence(top.score, second.score if second else 0.0),
                status=mode,
                requires_clarification=self._mode_requires_clarification(mode),
                clarification_reason=mode,
                clarification_message=self._question(question_key, payload),
                intervention_mode=mode,
                missing_slots=(),
                question_key=question_key,
                candidates=tuple(candidates[:5]),
                entities=entities,
                extraction=extraction,
                applied_rules=tuple(applied_rules),
            )

        missing_slots, missing_key = self._missing_slots(top, payload, context)
        if missing_slots:
            mode = self._policy(top).get("on_missing", "needs_user_clarification")
            reason = f"missing:{','.join(missing_slots)}"
            return IntentResolution(
                intent=top.intent,
                subintent=top.subintent,
                confidence=self._confidence(top.score, second.score if second else 0.0),
                status=str(mode),
                requires_clarification=self._mode_requires_clarification(str(mode)),
                clarification_reason=reason,
                clarification_message=self._question(missing_key, payload),
                intervention_mode=str(mode),
                missing_slots=missing_slots,
                question_key=missing_key,
                candidates=tuple(candidates[:5]),
                entities=entities,
                extraction=extraction,
                applied_rules=tuple(applied_rules),
            )

        if close and not self._top_has_priority_override(applied_rules, top):
            mode = "needs_user_clarification"
            return IntentResolution(
                intent=top.intent,
                subintent=top.subintent,
                confidence=self._confidence(top.score, second.score),
                status="ambiguous",
                requires_clarification=self._mode_requires_clarification(mode),
                clarification_reason="close_candidates",
                clarification_message=self._question("close_candidates", payload),
                intervention_mode=mode,
                missing_slots=(),
                question_key="close_candidates",
                candidates=tuple(candidates[:5]),
                entities=entities,
                extraction=extraction,
                applied_rules=tuple(applied_rules),
            )

        complete_mode = policy.get("on_complete")
        if complete_mode:
            question_key = policy.get("complete_question")
            mode = str(complete_mode)
            return IntentResolution(
                intent=top.intent,
                subintent=top.subintent,
                confidence=self._confidence(top.score, second.score if second else 0.0),
                status=mode,
                requires_clarification=self._mode_requires_clarification(mode),
                clarification_reason=mode,
                clarification_message=self._question(question_key, payload),
                intervention_mode=mode,
                missing_slots=(),
                question_key=str(question_key) if question_key else None,
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
            intervention_mode="resolved",
            missing_slots=(),
            question_key=None,
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
        entities = payload.get("phrase_matcher", {}).get("entities", [])
        for entity in entities:
            entity_type = entity.get("entity_type")
            entity_id = entity.get("entity_id")
            if entity_type == "SERVICIO" and entity_id == "menu_pdf" and any(
                other is not entity
                and (
                    (
                        int(other.get("start_char", 0)) <= int(entity.get("start_char", 0))
                        and int(other.get("end_char", 0)) >= int(entity.get("end_char", 0))
                        and (
                            int(other.get("start_char", 0)) < int(entity.get("start_char", 0))
                            or int(other.get("end_char", 0)) > int(entity.get("end_char", 0))
                        )
                    )
                    or (
                        int(other.get("start_char", 0)) >= int(entity.get("end_char", 0))
                        and str(payload.get("normalized_text", ""))[
                            int(entity.get("end_char", 0)):int(other.get("start_char", 0))
                        ].strip() == ""
                    )
                )
                for other in entities
            ):
                continue
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

    def _add_entity_ruler_evidence(self, payload, scores, reasons) -> None:
        evidence_map = self._config.get("entity_ruler_evidence", {})
        multiplier = float(self._multipliers.get("phrase", 1.0))
        for entity in payload.get("entity_ruler", {}).get("entities", []):
            entity_type = entity.get("entity_type")
            entity_id = entity.get("entity_id")
            for item in evidence_map.get(entity_type, []):
                self._add(
                    scores, reasons, item["intent"], item["subintent"],
                    float(item["weight"]) * multiplier,
                    "EntityRuler", f"{entity_type}:{entity_id}"
                )

    def _apply_context_rules(self, payload, context, scores, reasons, applied_rules) -> None:
        entities = self._all_entities(payload)
        entity_ids = {item.get("entity_id") for item in entities}
        text = str(payload.get("normalized_text", ""))

        if "ultimo_elemento" in entity_ids and "otra vez" in text:
            if context.get("menu_enviado_previamente") or context.get("menu_pdf_ultima_fecha_envio"):
                self._add(scores, reasons, "menu", "reenviar_menu", 0.62, "Context", "menu_previamente_enviado")
                applied_rules.append("CTX_MENU_REENVIO")

        if "pedido_previo" in entity_ids and context.get("pedido_anterior"):
            self._add(
                scores, reasons, "pedido", "repetir_pedido", 0.62,
                "Context", "pedido_anterior"
            )
            applied_rules.append("CTX_PEDIDO_PREVIO")

        if "direccion_previa" in entity_ids and context.get("direccion_previa"):
            self._add(
                scores, reasons, "domicilio", "usar_direccion_previa", 0.58,
                "Context", "direccion_previa"
            )
            applied_rules.append("CTX_DIRECCION_PREVIA")

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
        entities = self._all_entities(payload)
        entity_types = {item.get("entity_type") for item in entities}
        entity_ids = {item.get("entity_id") for item in entities}
        extraction = payload.get("matcher", {}).get("extraction", {})

        products = [
            item for item in entities
            if item.get("entity_type") in {"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"}
        ]
        if len(products) >= 2 and any(word in text for word in (" más ", " menos ", " o ", "compar")):
            self._add(scores, reasons, "catalogo", "comparar_productos", 0.7, "PriorityRule", "explicit_product_comparison")
            applied_rules.append("PRIORITY_PRODUCT_COMPARISON")

        if "PREPARACION" in entity_types and re.search(r"^[¿?¡!\s]*(?:qué|que)\s+es\b", text):
            self._add(scores, reasons, "catalogo", "consultar_definicion_preparacion", 0.38, "PriorityRule", "definition_question")
            applied_rules.append("PRIORITY_PREPARATION_DEFINITION")

        if (
            "PREPARACION" in entity_types
            and extraction.get("has_negation")
            and re.search(r"^[¿?¡!\s]*(?:cuál|cual|qué|que)\b", text)
        ):
            self._add(scores, reasons, "catalogo", "consultar_preparacion", 0.32, "PriorityRule", "preparation_question_over_modification")
            applied_rules.append("PRIORITY_PREPARATION_QUERY")

        if "reserva" in entity_ids and any(word in text for word in ("cuesta", "costo", "valor", "precio")):
            self._add(scores, reasons, "reserva_evento", "consultar_reserva", 0.55, "PriorityRule", "reservation_conditions")
            applied_rules.append("PRIORITY_RESERVATION_CONDITIONS")

        if products and any(item.get("entity_type") in {"DIA_SEMANA", "FECHA_RELATIVA"} for item in entities):
            if any(word in text for word in ("hay", "tiene", "tienen", "queda", "quedan", "disponible")):
                self._add(scores, reasons, "catalogo", "consultar_disponibilidad_producto", 0.42, "PriorityRule", "temporal_availability")
                applied_rules.append("PRIORITY_TEMPORAL_AVAILABILITY")

        payment_methods = [item for item in entities if item.get("entity_type") == "MEDIO_PAGO"]
        if len(payment_methods) >= 2 and any(word in text for word in ("parte", "mitad", "otra", "combinar")):
            self._add(scores, reasons, "pago", "consultar_pago_mixto", 0.55, "PriorityRule", "multiple_payment_methods")
            applied_rules.append("PRIORITY_MIXED_PAYMENT")

        explicit_sensitive_entities = [
            item for item in entities
            if item.get("entity_type") == "ALERGENO"
            and not any(
                item.get("start_char") == product.get("start_char")
                and item.get("end_char") == product.get("end_char")
                for product in products
            )
        ]
        if explicit_sensitive_entities and products and any(
            word in text for word in ("contiene", "tiene", "lleva", "trae")
        ):
            self._add(scores, reasons, "seguridad_alimentaria", "consultar_alergenos", 1.7, "PriorityRule", "allergen_content")
            applied_rules.append("PRIORITY_ALLERGEN_CONTENT")

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

        delivery_status_markers = any(
            marker in text
            for marker in (
                "estado del domicilio", "estado de mi pedido", "estado del pedido",
                "seguimiento del pedido", "rastrear el pedido", "dónde va mi pedido",
                "donde va mi pedido", "ya salió mi pedido", "ya salio mi pedido",
            )
        )
        if delivery_status_markers:
            self._add(
                scores, reasons, "domicilio", "consultar_estado_domicilio", 0.86,
                "PriorityRule", "explicit_delivery_status"
            )
            applied_rules.append("PRIORITY_DELIVERY_STATUS")

        delivery_request = (
            any(
                marker in text
                for marker in (
                    "envíen el pedido", "envien el pedido", "manden el pedido",
                    "mándeme el pedido", "mandeme el pedido", "lleven el pedido",
                    "despachen el pedido", "solicitar el domicilio",
                )
            )
            and not delivery_status_markers
        )
        if delivery_request:
            self._add(
                scores, reasons, "domicilio", "solicitar_domicilio", 0.78,
                "PriorityRule", "explicit_delivery_request"
            )
            applied_rules.append("PRIORITY_DELIVERY_REQUEST")

        if "direccion_previa" in entity_ids or any(
            marker in text
            for marker in (
                "misma dirección", "misma direccion", "dirección anterior",
                "direccion anterior",
            )
        ):
            self._add(
                scores, reasons, "domicilio", "usar_direccion_previa", 0.96,
                "PriorityRule", "explicit_previous_address"
            )
            applied_rules.append("PRIORITY_PREVIOUS_ADDRESS")

        if (
            "primera consulta" in text
            and any(marker in text for marker in ("qué ofrece", "que ofrece", "términos generales", "terminos generales"))
        ):
            self._add(
                scores, reasons, "menu", "consultar_menu_general", 0.72,
                "PriorityRule", "first_contact_general_menu"
            )
            applied_rules.append("PRIORITY_MENU_GENERAL_FIRST_CONTACT")

        if (
            any(marker in text for marker in ("repetir", "repita", "lo mismo"))
            and any(marker in text for marker in ("pedido", "vez pasada", "pedido anterior"))
        ):
            self._add(
                scores, reasons, "pedido", "repetir_pedido", 0.74,
                "PriorityRule", "explicit_repeat_order"
            )
            applied_rules.append("PRIORITY_REPEAT_ORDER")

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

    def _policy(self, top: CandidateScore) -> dict[str, Any]:
        key = f"{top.intent}.{top.subintent}"
        policy = self._conversation_action_rules.get(
            "rules_by_intent_and_subintent", {}
        ).get(key, {})
        return dict(policy) if isinstance(policy, Mapping) else {}

    def _missing_slots(
        self,
        top: CandidateScore,
        payload: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> tuple[tuple[str, ...], str | None]:
        policy = self._policy(top)
        if not policy:
            return (), None

        available = self._available_slots(payload, context)
        missing: list[str] = [
            str(slot)
            for slot in policy.get("required_slots", [])
            if str(slot) not in available
        ]
        for raw_group in policy.get("required_any", []):
            group = [str(slot) for slot in raw_group]
            if group and not available.intersection(group):
                missing.append("|".join(group))

        if not missing:
            return (), None
        questions = policy.get("question_by_slot", {})
        first = missing[0]
        question_key = questions.get(first)
        if question_key is None and "|" in first:
            question_key = questions.get("|".join(first.split("|")))
        return tuple(missing), str(question_key) if question_key else "no_evidence"

    def _available_slots(
        self,
        payload: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> set[str]:
        entities = self._all_entities(payload)
        types = {item.get("entity_type") for item in entities}
        extraction = payload.get("matcher", {}).get("extraction", {})
        quantities = extraction.get("quantities", [])
        text = str(payload.get("normalized_text", "")).casefold()
        available: set[str] = set()

        if types.intersection({"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"}):
            available.add("product")
        if "PREPARACION" in types:
            available.add("preparation")
        if quantities:
            available.add("quantity")
        if types.intersection({"DIA_SEMANA", "FECHA_RELATIVA"}):
            available.add("date")
        if "MOMENTO_DIA" in types or re.search(
            r"\b(?:a|para)\s+la(?:s)?\s+(?:una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|\d{1,2})(?:\s|$)",
            text,
        ):
            available.add("time")
        if "MEDIO_PAGO" in types:
            available.add("payment_method")
        if types.intersection({"ALERGENO", "INGREDIENTE"}):
            available.add("allergen")
        if types.intersection({"ALERGENO", "INGREDIENTE"}) or any(
            marker in text
            for marker in (
                "vegetarian", "vegetariano", "vegetariana", "vegan", "vegano",
                "vegana", "sin carne", "sin mariscos", "sin camarón", "sin camaron",
            )
        ):
            available.add("dietary_restriction")
        if types.intersection({"INGREDIENTE", "ALERGENO", "PREPARACION"}) or (
            extraction.get("has_negation") and "PRODUCTO_BASE" in types
        ):
            available.add("modification_target")
        if quantities and any(
            marker in text
            for marker in ("persona", "mesa", "reserva", "evento", "espacio", "almuerzo", "pedidos")
        ):
            available.add("party_size")
        if extraction.get("monetary_values") or context.get("budget"):
            available.add("budget")
        if context.get("producto_activo"):
            available.add("product")
        if context.get("pedido_anterior"):
            available.add("order")
        if context.get("pedido_activo"):
            available.add("order")
        if context.get("direccion_previa"):
            available.add("delivery_address")
        for context_key, slot in (
            ("delivery_address", "delivery_address"),
            ("delivery_zone", "delivery_zone"),
            ("customer_name", "customer_name"),
            ("phone", "phone"),
            ("order_id", "order_id"),
            ("reservation_id", "reservation_id"),
            ("invoice_data", "invoice_data"),
        ):
            if context.get(context_key):
                available.add(slot)
        return available

    def _confidence(self, top_score: float, second_score: float) -> float:
        if top_score <= 0:
            return 0.0
        margin = max(0.0, top_score - second_score)
        raw = 1.0 - math.exp(-(0.9 * top_score + 0.7 * margin))
        return min(float(self._thresholds.get("maximum_confidence", 0.99)), max(0.0, raw))

    def _mode_requires_clarification(self, mode: str) -> bool:
        if mode == "resolved":
            return False
        config = self._conversation_action_rules.get("conversation_actions", {}).get(
            mode, {}
        )
        return bool(config.get("requires_clarification_compat", True))

    def _question(
        self,
        question_key: str | None,
        payload: Mapping[str, Any],
    ) -> str | None:
        if not question_key:
            return None
        item = self._conversation_action_rules.get("questions", {}).get(question_key)
        if not isinstance(item, Mapping):
            legacy = self._config.get("clarification_messages", {})
            return str(legacy.get(question_key, legacy.get("no_evidence", ""))) or None

        template = str(item.get("template", ""))
        fallback = str(item.get("fallback", ""))
        product = next(
            (
                str(entity.get("canonical") or entity.get("text"))
                for entity in self._all_entities(payload)
                if entity.get("entity_type") in {"PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"}
            ),
            "",
        )
        values = {"product": product}
        try:
            rendered = template.format(**values)
        except (KeyError, ValueError):
            rendered = fallback
        if not product and "{product}" in template:
            rendered = fallback
        return rendered or fallback or None

    @staticmethod
    def _all_entities(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [
            *payload.get("phrase_matcher", {}).get("entities", []),
            *payload.get("entity_ruler", {}).get("entities", []),
        ]

    @staticmethod
    def _top_has_priority_override(applied_rules: list[str], top: CandidateScore) -> bool:
        if top.intent == "seguridad_alimentaria" and "PRIORITY_SAFETY_FIRST" in applied_rules:
            return True
        if top.intent == "precio" and any(rule in applied_rules for rule in ("PRIORITY_PRICE_OVER_WANT", "PRIORITY_BUDGET")):
            return True
        if top.intent == "menu" and any(
            rule in applied_rules
            for rule in (
                "PRIORITY_MENU_REENVIO",
                "PRIORITY_MENU_GENERAL_FIRST_CONTACT",
            )
        ):
            return True
        if top.subintent == "consultar_reserva" and "PRIORITY_RESERVATION_CONDITIONS" in applied_rules:
            return True
        if top.subintent == "consultar_definicion_preparacion" and "PRIORITY_PREPARATION_DEFINITION" in applied_rules:
            return True
        if top.subintent == "consultar_disponibilidad_producto" and "PRIORITY_TEMPORAL_AVAILABILITY" in applied_rules:
            return True
        if top.subintent == "consultar_preparacion" and "PRIORITY_PREPARATION_QUERY" in applied_rules:
            return True
        return False

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    @property
    def conversation_action_rules(self) -> dict[str, Any]:
        return self._conversation_action_rules
