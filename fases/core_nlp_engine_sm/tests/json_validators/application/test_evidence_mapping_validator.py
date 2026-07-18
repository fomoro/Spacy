"""Pruebas de validación para linguistic_evidence_mapping.json."""

import unittest
from tests.json_validators.utils.base_validator import load, taxonomy_pairs, evidence_pair

class EvidenceMappingValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.taxonomy = load("intents_and_subintents.json")
        cls.valid_pairs = taxonomy_pairs(cls.taxonomy)
        
        cls.evidence_mapping = load("linguistic_evidence_mapping.json")
        cls.matcher = load("matcher_service_config.json")
        cls.lemmas = load("lemma_service_config.json")

    def test_metadata_structure(self):
        metadata = self.evidence_mapping.get("metadata", {})
        expected_fields = {"schema_version", "purpose", "language"}
        self.assertIsInstance(metadata, dict)
        self.assertEqual(set(metadata), expected_fields, "metadata no coincide con el contrato mínimo.")
        self.assertTrue(str(metadata.get("purpose", "")).strip(), "metadata.purpose debe ser texto no vacío.")

    def test_top_level_fields(self):
        expected_fields = {
            "metadata",
            "matcher_signals",
            "lemma_signals",
            "phrase_entity_types",
            "service_entities",
            "entity_ruler_types",
        }
        self.assertEqual(
            set(self.evidence_mapping), 
            expected_fields, 
            "solo debe contener evidencia lingüística; no campos, preguntas ni acciones conversacionales."
        )

    def test_matcher_signals(self):
        matcher_mappings = self.evidence_mapping.get("matcher_signals", {})
        pattern_ids = {str(p.get("id", "")) for p in self.matcher.get("patterns", []) if p.get("id")}
        
        self.assertEqual(set(matcher_mappings), pattern_ids, "las señales Matcher no coinciden con sus patrones.")
        
        for rule_id, evidence in matcher_mappings.items():
            pair = evidence_pair(evidence)
            self.assertIn(pair, self.valid_pairs, f"Matcher '{rule_id}' referencia '{pair}' fuera de la taxonomía.")

    def test_lemma_signals(self):
        lemma_mappings = self.evidence_mapping.get("lemma_signals", {})
        lemma_ids = {str(s.get("lemma", "")) for s in self.lemmas.get("signals", []) if s.get("lemma")}
        
        self.assertEqual(set(lemma_mappings), lemma_ids, "las señales Lemma no coinciden con su catálogo.")
        
        for lemma_id, mappings in lemma_mappings.items():
            for evidence in mappings:
                pair = evidence_pair(evidence)
                self.assertIn(pair, self.valid_pairs, f"Lemma '{lemma_id}' referencia '{pair}' fuera de la taxonomía.")

    def test_entity_signals(self):
        mapped_entity_evidence = []
        for mapping_name in ("phrase_entity_types", "entity_ruler_types"):
            for items in self.evidence_mapping.get(mapping_name, {}).values():
                mapped_entity_evidence.extend(items)
        
        mapped_entity_evidence.extend(self.evidence_mapping.get("service_entities", {}).values())
        
        for evidence in mapped_entity_evidence:
            pair = evidence_pair(evidence)
            self.assertIn(pair, self.valid_pairs, f"Mapeo de entidades referencia '{pair}' fuera de la taxonomía.")
