"""Pruebas de validación para intents_and_subintents.json."""

import unittest
from tests.json_validators.utils.base_validator import load, taxonomy_pairs

class IntentsValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.taxonomy = load("intents_and_subintents.json")
        cls.valid_pairs = taxonomy_pairs(cls.taxonomy)

    def test_metadata_structure(self):
        taxonomy_metadata = self.taxonomy.get("metadata", {})
        expected_taxonomy_metadata = {
            "schema_version",
            "purpose",
            "language",
            "intent_count",
            "intent_subintent_pair_count",
            "slot_count",
        }
        self.assertIsInstance(taxonomy_metadata, dict, "metadata debe ser un diccionario.")
        self.assertEqual(set(taxonomy_metadata), expected_taxonomy_metadata, "metadata no coincide con el contrato mínimo.")
        
        self.assertEqual(
            taxonomy_metadata.get("intent_count"), 
            len(self.taxonomy.get("intents", {})), 
            "intent_count es incorrecto."
        )
        self.assertEqual(
            taxonomy_metadata.get("intent_subintent_pair_count"), 
            len(self.valid_pairs), 
            "intent_subintent_pair_count es incorrecto."
        )

    def test_intent_and_subintent_descriptions(self):
        for intent_id, intent in self.taxonomy.get("intents", {}).items():
            desc = str(intent.get("description", "")).strip()
            self.assertTrue(desc, f"'{intent_id}' requiere descripción.")
            
            for subintent_id, sub_desc in intent.get("subintents", {}).items():
                self.assertIsInstance(sub_desc, str)
                self.assertTrue(sub_desc.strip(), f"'{intent_id}.{subintent_id}' requiere descripción.")

    def test_resolver_settings(self):
        resolver_settings = self.taxonomy.get("resolver_settings", {})
        thresholds = resolver_settings.get("thresholds", {})
        multipliers = resolver_settings.get("source_multipliers", {})
        
        self.assertEqual(set(resolver_settings), {"thresholds", "source_multipliers"}, "resolver_settings no coincide con el contrato.")
        self.assertEqual(
            set(thresholds), 
            {"minimum_score", "clarification_margin", "maximum_confidence"}, 
            "thresholds no coincide con el contrato."
        )
        self.assertEqual(
            set(multipliers), 
            {"matcher", "lemma_spacy", "lemma_catalog_fallback", "lemma_surface", "phrase_matcher", "entity_ruler"}, 
            "source_multipliers no coincide con el contrato."
        )

    def test_tie_break_priority(self):
        for intent_id, intent in self.taxonomy.get("intents", {}).items():
            priority = intent.get("tie_break_priority")
            self.assertIsInstance(priority, int, f"'{intent_id}' requiere tie_break_priority entero.")
            self.assertNotIsInstance(priority, bool, f"'{intent_id}' requiere tie_break_priority entero (no booleano).")

    def test_legacy_keys_removed(self):
        for legacy_key in ("required_entities", "clarification_messages", "phrase_evidence", "service_entity_map", "entity_ruler_evidence"):
            self.assertNotIn(legacy_key, self.taxonomy, f"Resolver: '{legacy_key}' pertenece a otro recurso de aplicación.")

    def test_slots_structure(self):
        slots = self.taxonomy.get("slots", {})
        taxonomy_metadata = self.taxonomy.get("metadata", {})
        self.assertIsInstance(slots, dict)
        self.assertTrue(slots, "Slots: 'slots' debe ser un objeto no vacío.")
        self.assertEqual(taxonomy_metadata.get("slot_count"), len(slots), f"metadata.slot_count debe ser {len(slots)}.")
        
        valid_slot_fields = {"description", "classification"}
        valid_classifications = {
            "operational", "personal_data", "sensitive_personal_data",
            "financial_data", "linked_identifier", "tax_data",
        }
        for slot_id, definition in slots.items():
            self.assertIsInstance(definition, dict, f"Slots: '{slot_id}' debe ser un objeto.")
            unexpected = set(definition) - valid_slot_fields
            self.assertFalse(unexpected, f"Slots: '{slot_id}' contiene campos desconocidos: {unexpected}")
            self.assertTrue(str(definition.get("description", "")).strip(), f"Slots: '{slot_id}' requiere una descripción.")
            
            classification = definition.get("classification")
            self.assertIn(classification, valid_classifications, f"Slots: '{slot_id}' usa clasificación desconocida '{classification}'.")
