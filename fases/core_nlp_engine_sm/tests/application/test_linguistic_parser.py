"""Pruebas de orquestación de LinguisticParser."""

from pathlib import Path
import unittest

from src.infrastructure import EntityRulerService, LemmaService, MatcherService, PhraseMatcherService, TextNormalizerService
from src.application import LinguisticParser

ROOT = Path(__file__).resolve().parents[2]


class LinguisticParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        normalizer = TextNormalizerService(ROOT / "resources" / "config" / "infrastructure_nlp" / "text_normalizer_service_config.json")
        phrase = PhraseMatcherService(
            ROOT
            / "resources"
            / "config"
            / "infrastructure_nlp"
            / "phrase_matcher_service_config.json"
        )
        matcher = MatcherService(ROOT / "resources" / "config" / "infrastructure_nlp" / "matcher_service_config.json", phrase)
        lemmas = LemmaService(ROOT / "resources" / "config" / "infrastructure_nlp" / "lemma_service_config.json")
        ruler = EntityRulerService(ROOT / "resources" / "config" / "infrastructure_nlp" / "entity_ruler_service_config.json")
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
