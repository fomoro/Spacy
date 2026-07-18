"""Pruebas unitarias del director puro DialogueOrchestrator."""

import unittest
from unittest.mock import Mock

from src.temp import DialogueOrchestrator


class DialogueOrchestratorTests(unittest.TestCase):
    def test_coordinates_each_pipeline_stage_independently(self):
        parsed_bundle = Mock(name="parsed_bundle")
        evidence = Mock(name="evidence")
        resolution = Mock(name="resolution")
        response = Mock(name="response")
        parser = Mock()
        evidence_mapper = Mock()
        resolver = Mock()
        renderer = Mock()

        parser.analyze.return_value = parsed_bundle
        evidence_mapper.map_bundle.return_value = evidence
        resolver.resolve.return_value = resolution
        renderer.render.return_value = response

        orchestrator = DialogueOrchestrator(
            parser,
            evidence_mapper,
            resolver,
            renderer,
        )
        result = orchestrator.analyze(
            "¿Cuánto vale la mojarra?",
            {"producto_activo": "mojarra"},
            {"price": "$35.000"},
        )

        parser.analyze.assert_called_once_with("¿Cuánto vale la mojarra?")
        evidence_mapper.map_bundle.assert_called_once_with(parsed_bundle)
        resolver.resolve.assert_called_once_with(
            evidence,
            {"producto_activo": "mojarra"},
        )
        renderer.render.assert_called_once_with(resolution, {"price": "$35.000"})
        self.assertIs(result.evidence, evidence)
        self.assertIs(result.resolution, resolution)
        self.assertIs(result.response, response)

    def test_rejects_missing_parser(self):
        with self.assertRaisesRegex(ValueError, "parser es obligatorio"):
            DialogueOrchestrator(None, Mock(), Mock(), Mock())

    def test_rejects_missing_evidence_mapper(self):
        with self.assertRaisesRegex(ValueError, "evidence_mapper es obligatorio"):
            DialogueOrchestrator(Mock(), None, Mock(), Mock())

    def test_rejects_missing_resolver(self):
        with self.assertRaisesRegex(ValueError, "resolver es obligatorio"):
            DialogueOrchestrator(Mock(), Mock(), None, Mock())

    def test_rejects_missing_response_renderer(self):
        with self.assertRaisesRegex(ValueError, "response_renderer es obligatorio"):
            DialogueOrchestrator(Mock(), Mock(), Mock(), None)


if __name__ == "__main__":
    unittest.main()
