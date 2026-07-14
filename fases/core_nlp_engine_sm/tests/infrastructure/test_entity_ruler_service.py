"""Pruebas unitarias de EntityRulerService."""

from pathlib import Path
import unittest

from src.infrastructure import EntityRulerService


ROOT = Path(__file__).resolve().parents[2]


class EntityRulerServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = EntityRulerService(ROOT / "resources" / "nlp" / "entity_ruler_patterns.json")

    def test_detects_weekday_and_context_reference(self):
        result = self.service.analyze("el lunes mándamelo otra vez")
        pairs = {(item.entity_type, item.entity_id) for item in result.entities}
        self.assertIn(("DIA_SEMANA", "lunes"), pairs)
        self.assertIn(("REFERENCIA_CONTEXTUAL", "ultimo_elemento"), pairs)

    def test_annotates_doc_in_place(self):
        doc = self.service.nlp.make_doc("la misma")
        annotated = self.service.annotate(doc)
        self.assertIs(annotated, doc)
        self.assertEqual(doc.ents[0].ent_id_, "ultimo_producto")

    def test_accepts_section_dictionary(self):
        service = EntityRulerService({
            "patterns": [{"label": "PRUEBA", "pattern": "hola", "id": "saludo"}]
        })
        result = service.analyze("hola")
        self.assertEqual(result.entities[0].entity_id, "saludo")


if __name__ == "__main__":
    unittest.main()
