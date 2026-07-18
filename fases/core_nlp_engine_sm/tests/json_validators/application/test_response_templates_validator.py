"""Pruebas de validación para response_templates.json."""

import unittest
from string import Formatter
from tests.json_validators.utils.base_validator import load, taxonomy_pairs

class ResponseTemplatesValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.taxonomy = load("intents_and_subintents.json")
        cls.valid_pairs = taxonomy_pairs(cls.taxonomy)
        
        cls.response_templates = load("response_templates.json")
        cls.responses = cls.response_templates.get("responses", {})
        cls.direct_responses = cls.response_templates.get("direct_response_by_intent_and_subintent", {})

    def test_top_level_fields(self):
        expected_fields = {
            "metadata",
            "responses",
            "direct_response_by_intent_and_subintent",
        }
        self.assertEqual(
            set(self.response_templates), 
            expected_fields, 
            "la raíz no coincide con el contrato de respuestas."
        )

    def test_metadata_structure(self):
        metadata = self.response_templates.get("metadata", {})
        expected_fields = {
            "schema_version",
            "purpose",
            "language",
            "response_count",
            "direct_response_pair_count",
        }
        self.assertIsInstance(metadata, dict)
        self.assertEqual(set(metadata), expected_fields, "metadata no coincide con el contrato.")
        
        self.assertTrue(str(metadata.get("purpose", "")).strip(), "metadata.purpose está vacío.")
        self.assertEqual(metadata.get("language"), "es-CO", "metadata.language debe ser 'es-CO'.")
        
        self.assertEqual(metadata.get("response_count"), len(self.responses), "metadata.response_count no coincide.")
        self.assertEqual(metadata.get("direct_response_pair_count"), len(self.direct_responses), "metadata.direct_response_pair_count no coincide.")

    def test_responses_structure(self):
        self.assertIsInstance(self.responses, dict)
        self.assertTrue(self.responses, "'responses' debe ser un objeto no vacío.")
        
        for template_key, definition in self.responses.items():
            self.assertIsInstance(definition, dict)
            self.assertEqual(set(definition), {"templates", "required_values"}, f"response '{template_key}' no coincide con el contrato.")
            
            variants = definition.get("templates")
            required_values = definition.get("required_values")
            
            self.assertIsInstance(variants, list)
            self.assertTrue(variants)
            self.assertTrue(all(isinstance(t, str) and t.strip() for t in variants), f"'{template_key}' debe tener templates no vacíos.")
            
            self.assertIsInstance(required_values, list)
            self.assertTrue(all(isinstance(v, str) and v for v in required_values), f"'{template_key}' tiene required_values inválido.")
            self.assertEqual(len(required_values), len(set(required_values)), f"'{template_key}' repite required_values.")
            
            for variant_index, template in enumerate(variants):
                try:
                    placeholders = {name for _, name, _, _ in Formatter().parse(template) if name}
                except ValueError as exc:
                    self.fail(f"formato inválido en '{template_key}' variante {variant_index}: {exc}.")
                
                self.assertEqual(
                    placeholders, 
                    set(required_values), 
                    f"'{template_key}' variante {variant_index} no sincroniza placeholders y required_values."
                )

    def test_safe_unknown_response_exists(self):
        self.assertIn("unknown", self.responses, "falta la respuesta segura 'unknown'.")

    def test_direct_responses_mapping(self):
        self.assertIsInstance(self.direct_responses, dict)
        
        for pair, template_key in self.direct_responses.items():
            self.assertIn(pair, self.valid_pairs, f"pareja desconocida '{pair}'.")
            self.assertIn(template_key, self.responses, f"'{pair}' referencia template desconocido '{template_key}'.")

    def test_unused_templates(self):
        referenced_templates = set(self.direct_responses.values()) | {"unknown"}
        unused_templates = sorted(set(self.responses) - referenced_templates)
        self.assertFalse(unused_templates, "templates sin uso: " + ", ".join(unused_templates))
