"""Pruebas unitarias de la fachada IntentEngine."""

import unittest
from unittest.mock import Mock

from src.application import IntentEngine


class IntentEngineTests(unittest.TestCase):
    def test_coordinates_parser_and_resolver(self):
        evidence = Mock(name="evidence")
        resolution = Mock(name="resolution")
        parser = Mock()
        resolver = Mock()
        parser.analyze.return_value = evidence
        resolver.resolve.return_value = resolution
        engine = IntentEngine(parser, resolver)

        result = engine.analyze("¿Cuánto vale la mojarra?", {"producto_activo": "mojarra"})

        parser.analyze.assert_called_once_with("¿Cuánto vale la mojarra?")
        resolver.resolve.assert_called_once_with(evidence, {"producto_activo": "mojarra"})
        self.assertIs(result.evidence, evidence)
        self.assertIs(result.resolution, resolution)

    def test_rejects_missing_parser(self):
        with self.assertRaisesRegex(ValueError, "parser es obligatorio"):
            IntentEngine(None, Mock())

    def test_rejects_missing_resolver(self):
        with self.assertRaisesRegex(ValueError, "resolver es obligatorio"):
            IntentEngine(Mock(), None)


if __name__ == "__main__":
    unittest.main()
