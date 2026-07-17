from pathlib import Path
"""Pruebas unitarias de LemmaService."""

import unittest

from src.infrastructure import LemmaService

ROOT = Path(__file__).resolve().parents[2]


class LemmaServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = LemmaService(ROOT / "src" / "infrastructure" / "resources" / "lemma_service_config.json")

    def test_price_inflection_uses_canonical_lemma(self):
        result = self.service.analyze("¿Cuánto cuesta la mojarra?")
        self.assertTrue(any(item.lemma == "costar" for item in result.signals))

    def test_order_signals(self):
        result = self.service.analyze("Quiero pedir una trucha")
        self.assertTrue(any(item.lemma == "querer" for item in result.signals))
        self.assertTrue(any(item.lemma == "pedir" for item in result.signals))

    def test_recommendation(self):
        result = self.service.analyze("¿Qué me recomienda?")
        self.assertTrue(any(item.lemma == "recomendar" for item in result.signals))

    def test_allergy_is_neutral_signal_without_business_weight(self):
        result = self.service.analyze("Soy alérgica al camarón")
        signals = [item for item in result.signals if item.lemma == "alérgico"]
        self.assertTrue(signals)
        self.assertFalse(hasattr(signals[0], "intent"))
        self.assertFalse(hasattr(signals[0], "weight"))

    def test_social_thanks(self):
        result = self.service.analyze("gracias")
        self.assertTrue(any(item.lemma == "agradecer" for item in result.signals))

    def test_unknown_word_remains_surface(self):
        result = self.service.analyze("xyzdesconocido")
        self.assertEqual(result.tokens[0].lemma, "xyzdesconocido")
        self.assertFalse(result.signals)

    def test_empty_text(self):
        result = self.service.analyze("   ")
        self.assertFalse(result.tokens)
        self.assertFalse(result.signals)

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            self.service.analyze(None)


if __name__ == "__main__":
    unittest.main()
