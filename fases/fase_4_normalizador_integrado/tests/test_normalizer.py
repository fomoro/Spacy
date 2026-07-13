from pathlib import Path
import unittest

from src.infrastructure.json_loader import load_normalizer_config
from src.nlp.normalizer import TextNormalizer


ROOT = Path(__file__).resolve().parents[1]


class TextNormalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.normalizer = TextNormalizer(load_normalizer_config(ROOT / "resources" / "normalizer"))

    def test_typo_domicilio(self) -> None:
        result = self.normalizer.normalize("tiene domi")
        self.assertEqual("tiene domicilio", result.normalized)

    def test_typo_price(self) -> None:
        result = self.normalizer.normalize("me regala una mojarra")
        self.assertEqual("por favor me da una mojarra", result.normalized)

    def test_preserves_negation(self) -> None:
        result = self.normalizer.normalize("Sin ajo, por favor")
        self.assertIn("sin ajo", result.normalized)

    def test_monetary_slang(self) -> None:
        result = self.normalizer.normalize("qué puedo pedir con veinte lucas")
        self.assertEqual((20000,), result.monetary_values)

    def test_replacement_uses_boundaries(self) -> None:
        result = self.normalizer.normalize("hay y ayer")
        self.assertEqual("hay y ayer", result.normalized)

    def test_keeps_original(self) -> None:
        result = self.normalizer.normalize("  MENÚ  ")
        self.assertEqual("  MENÚ  ", result.original)
        self.assertEqual("menú", result.normalized)

    def test_none_rejected(self) -> None:
        with self.assertRaises(TypeError):
            self.normalizer.normalize(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
