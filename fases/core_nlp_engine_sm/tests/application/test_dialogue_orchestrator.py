"""Pruebas unitarias del director puro DialogueOrchestrator."""

import unittest
from unittest.mock import Mock

from src.application import DialogueOrchestrator


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

    def test_rejects_missing_dependencies(self):
        cases = (
            ("parser", (None, Mock(), Mock(), Mock())),
            ("evidence_mapper", (Mock(), None, Mock(), Mock())),
            ("resolver", (Mock(), Mock(), None, Mock())),
            ("response_renderer", (Mock(), Mock(), Mock(), None)),
        )

        for dependency, arguments in cases:
            with self.subTest(dependency=dependency):
                with self.assertRaisesRegex(ValueError, f"{dependency} es obligatorio"):
                    DialogueOrchestrator(*arguments)


if __name__ == "__main__":
    unittest.main()
