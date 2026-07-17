from pathlib import Path
"""Pruebas unitarias de MatcherService."""

import unittest

from src.infrastructure import TextNormalizerService, MatcherService

ROOT = Path(__file__).resolve().parents[2]


class MatcherServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.normalizer = TextNormalizerService(ROOT / "src" / "infrastructure" / "resources" / "text_normalizer_service_config.json")
        cls.matcher = MatcherService(
            ROOT / "src" / "infrastructure" / "resources" / "matcher_service_config.json"
        )

    def analyze_text(self, text: str):
        normalized = self.normalizer.normalize(text).normalized
        return self.matcher.analyze(normalized)

    @staticmethod
    def has_signal(result, rule_id: str) -> bool:
        return any(item.rule_id == rule_id for item in result.signals)

    def test_price(self):
        res = self.analyze_text("¿Cuánto vale la mojarra frita?")
        self.assertTrue(self.has_signal(res, "PRICE_Q_WH"))

    def test_order(self):
        res = self.analyze_text("Quiero una mojarra frita")
        self.assertTrue(self.has_signal(res, "ORDER_WANT_PRODUCT"))

    def test_payment(self):
        res = self.analyze_text("¿Reciben Nequi?")
        self.assertTrue(self.has_signal(res, "PAYMENT_QUERY"))

    def test_reservation(self):
        res = self.analyze_text("Quiero reservar una mesa para seis")
        self.assertTrue(self.has_signal(res, "RESERVATION_REQUEST"))

    def test_allergy_priority(self):
        res = self.analyze_text("Soy alérgica al camarón")
        self.assertTrue(self.has_signal(res, "ALLERGY_QUERY"))

    def test_modification(self):
        res = self.analyze_text("Quiero la trucha sin ajo")
        self.assertTrue(self.has_signal(res, "MODIFICATION_REMOVE"))
        self.assertTrue(res.extraction.has_negation)

    def test_budget(self):
        res = self.analyze_text("¿Qué puedo pedir con veinte lucas?")
        self.assertIn(20000, res.extraction.monetary_values)

    def test_quantity(self):
        res = self.analyze_text("Quiero dos mojarras")
        self.assertIn(2, res.extraction.quantities)

    def test_empty(self):
        res = self.analyze_text("   ")
        self.assertEqual(res.signals, ())


if __name__ == "__main__":
    unittest.main()
