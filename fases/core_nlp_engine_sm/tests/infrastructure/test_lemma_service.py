from pathlib import Path
"""Pruebas unitarias de LemmaService."""

import unittest

from src.infrastructure import LemmaService

ROOT = Path(__file__).resolve().parents[2]


class LemmaServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = LemmaService(ROOT / "resources" / "nlp" / "lemma_signals.json")

    def test_price_inflection_uses_canonical_lemma(self):
        result = self.service.analyze("¿Cuánto cuesta la mojarra?")
        self.assertTrue(any(item.lemma == "costar" for item in result.evidence))
        self.assertTrue(any(
            item.intent == "precio"
            and item.subintent == "consultar_precio_producto"
            for item in result.evidence
        ))

    def test_order_evidence(self):
        result = self.service.analyze("Quiero pedir una trucha")
        self.assertTrue(any(item.lemma == "querer" for item in result.evidence))
        self.assertTrue(any(item.lemma == "pedir" for item in result.evidence))

    def test_recommendation(self):
        result = self.service.analyze("¿Qué me recomienda?")
        self.assertTrue(any(
            item.subintent == "solicitar_recomendacion"
            for item in result.evidence
        ))

    def test_allergy_has_high_weight(self):
        result = self.service.analyze("Soy alérgica al camarón")
        evidence = [
            item for item in result.evidence
            if item.subintent == "consultar_alergenos"
        ]
        self.assertTrue(evidence)
        self.assertGreaterEqual(evidence[0].weight, 0.4)

    def test_social_thanks(self):
        result = self.service.analyze("gracias")
        self.assertTrue(any(item.subintent == "agradecer" for item in result.evidence))

    def test_unknown_word_remains_surface(self):
        result = self.service.analyze("xyzdesconocido")
        self.assertEqual(result.tokens[0].lemma, "xyzdesconocido")
        self.assertFalse(result.evidence)

    def test_empty_text(self):
        result = self.service.analyze("   ")
        self.assertFalse(result.tokens)
        self.assertFalse(result.evidence)

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            self.service.analyze(None)


if __name__ == "__main__":
    unittest.main()
