from pathlib import Path
import unittest

from src.infrastructure import TextNormalizer, PhraseMatcherService, MatcherService, LemmaService
from src.application import LinguisticParser

ROOT = Path(__file__).resolve().parents[2]


class EvidencePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        normalizer = TextNormalizer(ROOT / "resources" / "rules_config.json")
        phrase = PhraseMatcherService(ROOT / "resources" / "menu_catalog.json")
        matcher = MatcherService(ROOT / "resources" / "rules_config.json", phrase)
        lemmas = LemmaService(ROOT / "resources" / "rules_config.json")
        cls.pipeline = LinguisticParser(normalizer, phrase, matcher, lemmas)

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


if __name__ == "__main__":
    unittest.main()
