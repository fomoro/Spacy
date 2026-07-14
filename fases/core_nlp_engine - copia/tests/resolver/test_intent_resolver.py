
from pathlib import Path
import unittest

from src.infrastructure import (
    EntityRulerService,
    TextNormalizer,
    PhraseMatcherService,
    MatcherService,
    LemmaService,
)
from src.application import (
    IntentEngine,
    IntentResolver,
    LinguisticParser,
)

ROOT = Path(__file__).resolve().parents[2]


class IntentResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        normalizer = TextNormalizer(ROOT / "resources" / "nlp" / "normalizer_config.json")
        phrase = PhraseMatcherService(ROOT / "resources" / "menu" / "menu_catalog.json")
        matcher = MatcherService(ROOT / "resources" / "nlp" / "matcher_patterns.json", phrase)
        lemmas = LemmaService(ROOT / "resources" / "nlp" / "lemma_signals.json")
        ruler = EntityRulerService(ROOT / "resources" / "nlp" / "entity_ruler_patterns.json")
        parser = LinguisticParser(normalizer, phrase, matcher, lemmas, ruler)
        resolver = IntentResolver(ROOT / "resources" / "nlp" / "resolver_config.json")
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

    def test_unknown_requests_clarification(self):
        result = self.resolve("xyzdesconocido")
        self.assertTrue(result.requires_clarification)
        self.assertEqual(result.status, "unknown")

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


if __name__ == "__main__":
    unittest.main()
