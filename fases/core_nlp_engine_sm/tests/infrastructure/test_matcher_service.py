from pathlib import Path
"""Pruebas unitarias de MatcherService."""

import unittest

from src.infrastructure import TextNormalizer, PhraseMatcherService, MatcherService

ROOT = Path(__file__).resolve().parents[2]


class MatcherServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.normalizer = TextNormalizer(ROOT / "resources" / "nlp" / "normalizer_config.json")
        cls.phrase_matcher = PhraseMatcherService(
            ROOT / "resources" / "menu" / "menu_catalog.json"
        )
        cls.matcher = MatcherService(
            ROOT / "resources" / "nlp" / "matcher_patterns.json",
            cls.phrase_matcher
        )

    def analyze_text(self, text: str):
        normalized = self.normalizer.normalize(text).normalized
        return self.matcher.analyze(normalized)

    def has_subintent(self, result, subintent: str) -> bool:
        return any(x.subintent == subintent for x in result.evidence)

    def test_price(self):
        res = self.analyze_text("¿Cuánto vale la mojarra frita?")
        self.assertTrue(self.has_subintent(res, "consultar_precio_producto"))

    def test_order(self):
        res = self.analyze_text("Quiero una mojarra frita")
        self.assertTrue(self.has_subintent(res, "iniciar_pedido"))

    def test_payment(self):
        res = self.analyze_text("¿Reciben Nequi?")
        self.assertTrue(self.has_subintent(res, "consultar_medio_pago"))

    def test_reservation(self):
        res = self.analyze_text("Quiero reservar una mesa para seis")
        self.assertTrue(self.has_subintent(res, "solicitar_reserva"))

    def test_allergy_priority(self):
        res = self.analyze_text("Soy alérgica al camarón")
        self.assertTrue(self.has_subintent(res, "consultar_alergenos"))
        self.assertEqual(res.evidence[0].intent, "seguridad_alimentaria")

    def test_modification(self):
        res = self.analyze_text("Quiero la trucha sin ajo")
        self.assertTrue(self.has_subintent(res, "solicitar_modificacion"))
        self.assertTrue(res.extraction.has_negation)

    def test_budget(self):
        res = self.analyze_text("¿Qué puedo pedir con veinte lucas?")
        self.assertIn(20000, res.extraction.monetary_values)

    def test_quantity(self):
        res = self.analyze_text("Quiero dos mojarras")
        self.assertIn(2, res.extraction.quantities)

    def test_empty(self):
        res = self.analyze_text("   ")
        self.assertEqual(res.evidence, ())


if __name__ == "__main__":
    unittest.main()
