"""Pruebas de orquestación de LinguisticParser."""

from pathlib import Path
import unittest

from src.infrastructure import EntityRulerService, LemmaService, MatcherService, PhraseMatcherService, TextNormalizer
from src.application import LinguisticParser

ROOT = Path(__file__).resolve().parents[2]


class LinguisticParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        normalizer = TextNormalizer(ROOT / "resources" / "nlp" / "normalizer_config.json")
        phrase = PhraseMatcherService(ROOT / "resources" / "menu" / "menu_catalog.json")
        matcher = MatcherService(ROOT / "resources" / "nlp" / "matcher_patterns.json", phrase)
        lemmas = LemmaService(ROOT / "resources" / "nlp" / "lemma_signals.json")
        ruler = EntityRulerService(ROOT / "resources" / "nlp" / "entity_ruler_patterns.json")
        cls.pipeline = LinguisticParser(normalizer, phrase, matcher, lemmas, ruler)

    def test_integrated_price_analysis(self):
        result = self.pipeline.analyze("cuanto balen la mojarra frita")
        self.assertIn("valen", result.normalized_text)
        self.assertTrue(result.phrase_matcher["entities"])
        self.assertTrue(result.lemmas["evidence"])

    def test_pipeline_does_not_resolve_final_intent(self):
        result = self.pipeline.analyze("Quiero saber cuánto vale la mojarra")
        payload = result.to_dict()
        self.assertNotIn("final_intent", payload)
        self.assertIn("matcher", payload)
        self.assertIn("lemmas", payload)
        self.assertIn("entity_ruler", payload)


if __name__ == "__main__":
    unittest.main()
