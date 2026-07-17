"""Pruebas de resolución de intención y política conversacional."""

import json
from pathlib import Path
import unittest

from src.infrastructure import (
    EntityRulerService,
    TextNormalizerService,
    PhraseMatcherService,
    MatcherService,
    LemmaService,
)
from src.temp import (
    IntentEngine,
    IntentResolver,
    LinguisticParser,
)
from src.temp import LinguisticEvidenceMapper

ROOT = Path(__file__).resolve().parents[3]


class IntentResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        normalizer = TextNormalizerService(ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json")
        phrase = PhraseMatcherService(
            ROOT
            / "src"
            / "infrastructure"
            / "resources"
            / "phrase_matcher_service_config.json"
        )
        matcher = MatcherService(ROOT / "src" / "infrastructure" / "resources" / "matcher_service_config.json")
        lemmas = LemmaService(ROOT / "src" / "infrastructure" / "resources" / "lemma_service_config.json")
        ruler = EntityRulerService(ROOT / "src" / "infrastructure" / "resources" / "entity_ruler_service_config.json")
        evidence_mapper = LinguisticEvidenceMapper(ROOT / "src" / "temp" / "resources" / "intent_resolver" / "linguistic_evidence_mapping.json")
        parser = LinguisticParser(normalizer, phrase, matcher, lemmas, ruler, evidence_mapper)
        resolver = IntentResolver(
            ROOT / "src" / "temp" / "resources" / "intent_resolver"
        )
        cls.resolver = resolver
        cls.pipeline = IntentEngine(parser, resolver)

    def resolve(self, text, context=None):
        return self.pipeline.analyze(text, context).resolution

    def test_explicit_price_over_want(self):
        result = self.resolve("Quiero saber cuánto cuesta la mojarra")
        self.assertEqual(result.intent, "precio")
        self.assertEqual(result.subintent, "consultar_precio_producto")
        self.assertFalse(result.requires_clarification)

    def test_safety_first(self):
        result = self.resolve("Soy alérgica al camarón, ¿qué puedo pedir?")
        self.assertEqual(result.intent, "seguridad_alimentaria")
        self.assertEqual(result.subintent, "consultar_alergenos")

    def test_menu_request(self):
        result = self.resolve("Pásame el menú")
        self.assertEqual(result.intent, "menu")
        self.assertEqual(result.subintent, "solicitar_menu")

    def test_menu_resend_uses_context(self):
        result = self.resolve("Mándamelo otra vez", {"menu_enviado_previamente": True})
        self.assertEqual(result.intent, "menu")
        self.assertEqual(result.subintent, "reenviar_menu")
        self.assertIn("PRIORITY_MENU_REENVIO", result.applied_rules)

    def test_payment(self):
        result = self.resolve("¿Reciben Nequi?")
        self.assertEqual(result.intent, "pago")
        self.assertEqual(result.subintent, "consultar_medio_pago")

    def test_category(self):
        result = self.resolve("¿Qué arroces tienen?")
        self.assertEqual(result.intent, "catalogo")
        self.assertEqual(result.subintent, "consultar_categoria")

    def test_budget(self):
        result = self.resolve("¿Qué puedo pedir con veinte lucas?")
        self.assertEqual(result.intent, "precio")
        self.assertEqual(result.subintent, "solicitar_recomendacion_por_presupuesto")

    def test_negation_modification(self):
        result = self.resolve("Quiero la trucha sin ajo")
        self.assertEqual(result.intent, "pedido")
        self.assertEqual(result.subintent, "solicitar_modificacion")

    def test_unknown_is_out_of_scope_without_false_clarification(self):
        result = self.resolve("xyzdesconocido")
        self.assertFalse(result.requires_clarification)
        self.assertEqual(result.status, "unknown")
        self.assertEqual(result.intervention_mode, "out_of_scope")
        self.assertEqual(result.question_key, "out_of_scope")

    def test_standalone_greeting_and_farewell(self):
        greeting = self.resolve("Hola")
        farewell = self.resolve("Chao")
        self.assertEqual((greeting.intent, greeting.subintent), ("social", "saludar"))
        self.assertEqual(
            (farewell.intent, farewell.subintent), ("social", "despedirse")
        )

    def test_selects_pickup_as_fulfillment_method(self):
        result = self.resolve(
            "Quiero recoger el pedido directamente en el restaurante"
        )
        self.assertEqual(result.intent, "pedido")
        self.assertEqual(result.subintent, "seleccionar_modalidad_entrega")
        self.assertEqual(result.intervention_mode, "needs_transaction_confirmation")
        self.assertEqual(result.question_key, "confirm_fulfillment_method")

    def test_general_order_status_is_not_delivery_status(self):
        result = self.resolve(
            "Quiero consultar el estado de mi pedido para recoger"
        )
        self.assertEqual(result.intent, "pedido")
        self.assertEqual(result.subintent, "consultar_estado_pedido")
        self.assertEqual(result.intervention_mode, "needs_identity_verification")

    def test_cancel_order_requires_identity_before_confirmation(self):
        pending = self.resolve("Necesito cancelar el pedido que está activo")
        verified = self.resolve(
            "Necesito cancelar el pedido que está activo",
            {"identity_verified": True, "order_id": "order-test-1"},
        )
        self.assertEqual(pending.subintent, "cancelar_pedido")
        self.assertEqual(pending.intervention_mode, "needs_identity_verification")
        self.assertEqual(
            verified.intervention_mode, "needs_transaction_confirmation"
        )

    def test_modify_and_cancel_existing_reservation(self):
        change = self.resolve("Necesito modificar la reserva que ya tengo")
        cancellation = self.resolve("Necesito cancelar la reserva que ya tengo")
        self.assertEqual(change.subintent, "modificar_reserva")
        self.assertEqual(cancellation.subintent, "cancelar_reserva")
        self.assertEqual(change.intervention_mode, "needs_identity_verification")
        self.assertEqual(
            cancellation.intervention_mode, "needs_identity_verification"
        )

    def test_invoice_request_is_distinct_from_invoice_query(self):
        result = self.resolve(
            "Necesito que generen la factura electrónica de mi pedido"
        )
        self.assertEqual(result.intent, "operacion")
        self.assertEqual(result.subintent, "solicitar_factura")
        self.assertEqual(result.intervention_mode, "needs_identity_verification")

    def test_children_options_replace_generic_service_query(self):
        result = self.resolve("¿Tienen menú infantil?")
        self.assertEqual(result.intent, "catalogo")
        self.assertEqual(result.subintent, "consultar_opciones_infantiles")
        self.assertEqual(result.intervention_mode, "needs_business_lookup")

    def test_quantity_requires_context(self):
        result = self.resolve("dos")
        self.assertTrue(result.requires_clarification)

    def test_quantity_with_context(self):
        result = self.resolve("dos", {"producto_activo": "trucha"})
        self.assertEqual(result.intent, "pedido")
        self.assertEqual(result.subintent, "indicar_cantidad")
        self.assertFalse(result.requires_clarification)

    def test_result_contains_candidates(self):
        result = self.resolve("¿Cuánto vale el salmón?")
        self.assertTrue(result.candidates)
        self.assertGreater(result.confidence, 0.0)

    def test_incomplete_reservation_reports_missing_slots(self):
        result = self.resolve("Quiero reservar una mesa para cinco")
        self.assertEqual(result.intervention_mode, "needs_user_clarification")
        self.assertIn("date", result.missing_slots)
        self.assertIn("time", result.missing_slots)
        self.assertEqual(result.question_key, "missing_reservation_date")

    def test_order_uses_transaction_confirmation(self):
        result = self.resolve("Quiero una mojarra")
        self.assertEqual(result.intervention_mode, "needs_transaction_confirmation")
        self.assertTrue(result.requires_clarification)
        self.assertEqual(result.question_key, "confirm_order")

    def test_invoice_uses_business_lookup(self):
        result = self.resolve("¿Manejan factura electrónica?")
        self.assertEqual(result.intervention_mode, "needs_business_lookup")
        self.assertEqual(result.question_key, "invoice_business_lookup")

    def test_cross_contamination_requires_human_validation(self):
        result = self.resolve("¿El aceite se comparte con productos apanados?")
        self.assertEqual(result.intervention_mode, "needs_human_safety_validation")
        self.assertEqual(result.question_key, "cross_contamination_validation")

    def test_event_request_requires_human_assistance_after_collecting_data(self):
        result = self.resolve("Necesito un evento para veinte personas el viernes a las siete")
        self.assertEqual(result.intent, "reserva_evento")
        self.assertEqual(result.subintent, "solicitar_evento")
        self.assertEqual(result.intervention_mode, "needs_human_assistance")
        self.assertEqual(result.question_key, "event_human_assistance")

    def test_previous_order_requires_identity_verification(self):
        context = {"pedido_anterior": {"token": "pedido-tokenizado"}}
        result = self.resolve("Deme lo mismo de la vez pasada", context)
        self.assertEqual(result.intent, "pedido")
        self.assertEqual(result.subintent, "repetir_pedido")
        self.assertEqual(result.intervention_mode, "needs_identity_verification")
        self.assertEqual(result.question_key, "identity_verification_required")
        self.assertIn("POLICY_IDENTITY_VERIFICATION", result.applied_rules)

    def test_first_menu_consultation_does_not_trigger_identity_verification(self):
        result = self.resolve(
            "Es mi primera consulta y quisiera conocer, en términos generales, "
            "qué ofrece el restaurante; no quiero que reenvíen un documento anterior."
        )
        self.assertEqual(result.intent, "menu")
        self.assertEqual(result.subintent, "consultar_menu_general")
        self.assertEqual(result.intervention_mode, "resolved")

    def test_verified_identity_allows_previous_order_confirmation(self):
        context = {
            "identity_verified": True,
            "pedido_anterior": {"token": "pedido-tokenizado"},
        }
        result = self.resolve("Deme lo mismo de la vez pasada", context)
        self.assertEqual(result.intervention_mode, "needs_transaction_confirmation")
        self.assertEqual(result.question_key, "confirm_repeat_order")

    def test_previous_address_requires_identity_verification(self):
        context = {"direccion_previa": "direccion-tokenizada"}
        result = self.resolve("Envíelo a la misma dirección de antes", context)
        self.assertEqual(result.intent, "domicilio")
        self.assertEqual(result.subintent, "usar_direccion_previa")
        self.assertEqual(result.intervention_mode, "needs_identity_verification")

    def test_verified_identity_allows_previous_address_confirmation(self):
        context = {
            "identity_verified": True,
            "direccion_previa": "direccion-tokenizada",
        }
        result = self.resolve("Envíelo a la misma dirección de antes", context)
        self.assertEqual(result.intervention_mode, "needs_transaction_confirmation")
        self.assertEqual(result.question_key, "confirm_previous_address")

    def test_delivery_request_collects_order_before_address(self):
        result = self.resolve("Quiero que envíen el pedido a domicilio")
        self.assertEqual(result.intent, "domicilio")
        self.assertEqual(result.subintent, "solicitar_domicilio")
        self.assertEqual(result.intervention_mode, "needs_user_clarification")
        self.assertEqual(result.missing_slots, ("order", "delivery_address"))
        self.assertEqual(result.question_key, "missing_delivery_order")

    def test_delivery_request_with_active_order_asks_for_address(self):
        result = self.resolve(
            "Quiero que envíen el pedido a domicilio",
            {"pedido_activo": True},
        )
        self.assertEqual(result.missing_slots, ("delivery_address",))
        self.assertEqual(result.question_key, "missing_delivery_address")

    def test_complete_delivery_request_requires_transaction_confirmation(self):
        result = self.resolve(
            "Quiero que envíen el pedido a domicilio",
            {
                "pedido_activo": True,
                "delivery_address": "direccion-validada-tokenizada",
            },
        )
        self.assertEqual(result.intervention_mode, "needs_transaction_confirmation")
        self.assertEqual(result.question_key, "confirm_delivery")

    def test_delivery_status_requires_identity_verification(self):
        result = self.resolve("¿Dónde va mi pedido a domicilio?")
        self.assertEqual(result.intent, "domicilio")
        self.assertEqual(result.subintent, "consultar_estado_domicilio")
        self.assertEqual(result.intervention_mode, "needs_identity_verification")
        self.assertEqual(result.question_key, "identity_verification_required")

    def test_verified_delivery_status_requires_order_reference(self):
        result = self.resolve(
            "¿Dónde va mi pedido a domicilio?",
            {"identity_verified": True},
        )
        self.assertEqual(result.intervention_mode, "needs_user_clarification")
        self.assertEqual(result.missing_slots, ("order_id|order",))
        self.assertEqual(result.question_key, "missing_delivery_tracking_reference")

    def test_verified_delivery_status_uses_business_lookup(self):
        result = self.resolve(
            "¿Dónde va mi pedido a domicilio?",
            {
                "identity_verified": True,
                "order_id": "pedido-tokenizado",
            },
        )
        self.assertEqual(result.intervention_mode, "needs_business_lookup")
        self.assertEqual(result.question_key, "delivery_status_lookup")

    def test_personal_slots_are_accepted_only_from_validated_context(self):
        payload = {
            "normalized_text": "mi nombre es ana y mi teléfono es 3001234567",
            "phrase_matcher": {"entities": []},
            "entity_ruler": {"entities": []},
            "matcher": {"extraction": {"quantities": [], "monetary_values": []}},
        }
        without_context = self.resolver._available_slots(payload, {})
        self.assertNotIn("customer_name", without_context)
        self.assertNotIn("phone", without_context)

        with_context = self.resolver._available_slots(
            payload,
            {
                "customer_name": "Ana",
                "phone": "[REDACTED]",
                "order_id": "pedido-tokenizado",
                "reservation_id": "reserva-tokenizada",
                "invoice_data": {"status": "validated"},
            },
        )
        self.assertTrue(
            {"customer_name", "phone", "order_id", "reservation_id", "invoice_data"}
            <= with_context
        )

    def test_budget_and_delivery_address_slots_use_structured_evidence(self):
        payload = {
            "normalized_text": "tengo cincuenta mil",
            "phrase_matcher": {"entities": []},
            "entity_ruler": {"entities": []},
            "matcher": {
                "extraction": {
                    "quantities": [],
                    "monetary_values": [{"value": 50000, "currency": "COP"}],
                }
            },
        }
        available = self.resolver._available_slots(
            payload, {"direccion_previa": "direccion-tokenizada"}
        )
        self.assertIn("budget", available)
        self.assertIn("delivery_address", available)

    def test_accepts_runtime_resources_as_dictionaries(self):
        resource_directory = (
            ROOT / "src" / "temp" / "resources" / "intent_resolver"
        )
        conversation_rules = json.loads(
            (resource_directory / "conversation_action_rules.json").read_text(
                encoding="utf-8"
            )
        )
        intents = json.loads(
            (resource_directory / "intents_and_subintents.json").read_text(
                encoding="utf-8"
            )
        )
        data_fields = json.loads(
            (resource_directory / "conversation_data_fields.json").read_text(
                encoding="utf-8"
            )
        )
        resolver = IntentResolver(intents, conversation_rules, data_fields)
        self.assertIn("thresholds", resolver.resolver_settings)
        self.assertIn(
            "rules_by_intent_and_subintent", resolver.conversation_action_rules
        )
        self.assertIn("intents", resolver.intents_and_subintents)
        self.assertIn("slots", resolver.conversation_data_fields)

    def test_intent_dictionary_requires_other_runtime_resources(self):
        resource_directory = (
            ROOT / "src" / "temp" / "resources" / "intent_resolver"
        )
        intents = json.loads(
            (resource_directory / "intents_and_subintents.json").read_text(
                encoding="utf-8"
            )
        )
        rules = json.loads(
            (resource_directory / "conversation_action_rules.json").read_text(
                encoding="utf-8"
            )
        )
        with self.assertRaisesRegex(ValueError, "conversation_data_fields.json"):
            IntentResolver(intents, rules)

    def test_runtime_rejects_rules_outside_the_intent_catalog(self):
        resource_directory = (
            ROOT / "src" / "temp" / "resources" / "intent_resolver"
        )
        load = lambda name: json.loads(
            (resource_directory / name).read_text(encoding="utf-8")
        )
        rules = load("conversation_action_rules.json")
        intents = load("intents_and_subintents.json")
        fields = load("conversation_data_fields.json")
        rules["rules_by_intent_and_subintent"]["inexistente.no_declarada"] = {}

        with self.assertRaisesRegex(
            ValueError, "intención o subintención desconocida"
        ):
            IntentResolver(intents, rules, fields)

    def test_runtime_requires_priority_on_every_intent(self):
        resource_directory = (
            ROOT / "src" / "temp" / "resources" / "intent_resolver"
        )
        load = lambda name: json.loads(
            (resource_directory / name).read_text(encoding="utf-8")
        )
        intents = load("intents_and_subintents.json")
        rules = load("conversation_action_rules.json")
        fields = load("conversation_data_fields.json")
        del intents["intents"]["precio"]["tie_break_priority"]

        with self.assertRaisesRegex(ValueError, "tie_break_priority"):
            IntentResolver(intents, rules, fields)


if __name__ == "__main__":
    unittest.main()
