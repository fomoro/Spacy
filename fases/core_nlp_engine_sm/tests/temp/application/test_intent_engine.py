"""Pruebas unitarias de la fachada IntentEngine."""

import unittest
from unittest.mock import Mock

from src.temp import IntentEngine


class IntentEngineTests(unittest.TestCase):
    def test_coordinates_parser_and_resolver(self):
        evidence = Mock(name="evidence")
        resolution = Mock(name="resolution")
        parser = Mock()
        resolver = Mock()
        renderer = Mock()
        parser.analyze.return_value = evidence
        resolver.resolve.return_value = resolution
        response = Mock(name="response")
        renderer.render.return_value = response
        engine = IntentEngine(parser, resolver, renderer)

        result = engine.analyze(
            "¿Cuánto vale la mojarra?",
            {"producto_activo": "mojarra"},
            {"price": "$35.000"},
        )

        parser.analyze.assert_called_once_with("¿Cuánto vale la mojarra?")
        resolver.resolve.assert_called_once_with(evidence, {"producto_activo": "mojarra"})
        renderer.render.assert_called_once_with(resolution, {"price": "$35.000"})
        self.assertIs(result.evidence, evidence)
        self.assertIs(result.resolution, resolution)
        self.assertIs(result.response, response)

    def test_rejects_missing_parser(self):
        with self.assertRaisesRegex(ValueError, "parser es obligatorio"):
            IntentEngine(None, Mock(), Mock())

    def test_rejects_missing_resolver(self):
        with self.assertRaisesRegex(ValueError, "resolver es obligatorio"):
            IntentEngine(Mock(), None, Mock())

    def test_rejects_missing_response_renderer(self):
        with self.assertRaisesRegex(ValueError, "response_renderer es obligatorio"):
            IntentEngine(Mock(), Mock(), None)


if __name__ == "__main__":
    unittest.main()
