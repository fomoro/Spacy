"""Pruebas de selección y renderizado de respuestas resueltas."""

from pathlib import Path
import unittest

from src.temp import IntentResolution, ResponseRenderer


ROOT = Path(__file__).resolve().parents[3]


def resolution(
    *,
    intent: str | None,
    subintent: str | None,
    message: str | None = None,
    question_key: str | None = None,
    entities: tuple[dict, ...] = (),
) -> IntentResolution:
    return IntentResolution(
        intent=intent,
        subintent=subintent,
        confidence=0.9,
        status="resolved" if message is None else "needs_user_clarification",
        requires_clarification=message is not None,
        clarification_reason=None,
        clarification_message=message,
        intervention_mode=(
            "resolved" if message is None else "needs_user_clarification"
        ),
        missing_slots=(),
        question_key=question_key,
        candidates=(),
        entities=entities,
        extraction={},
        applied_rules=(),
    )


class ResponseRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.renderer = ResponseRenderer(
            ROOT
            / "src"
            / "temp"
            / "resources"
            / "intent_resolver"
            / "response_templates.json"
        )

    def test_preserves_conversation_action_message(self):
        result = self.renderer.render(
            resolution(
                intent="pedido",
                subintent="iniciar_pedido",
                message="¿Qué plato deseas pedir?",
                question_key="missing_order_product",
            )
        )

        self.assertEqual(result.text, "¿Qué plato deseas pedir?")
        self.assertEqual(result.source, "conversation_action_rules")
        self.assertEqual(result.template_key, "missing_order_product")

    def test_renders_direct_response_with_validated_values(self):
        result = self.renderer.render(
            resolution(
                intent="precio",
                subintent="consultar_precio_producto",
                entities=(
                    {
                        "entity_type": "PRODUCTO_ESPECIFICO",
                        "canonical": "Mojarra frita",
                    },
                ),
            ),
            {"price": "$35.000"},
        )

        self.assertEqual(
            result.text,
            "¡Claro! Te cuento que el precio de Mojarra frita es de $35.000.",
        )
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.template_key, "product_price")

    def test_uses_safe_fallback_when_business_data_is_missing(self):
        result = self.renderer.render(
            resolution(
                intent="precio",
                subintent="consultar_precio_producto",
            )
        )

        self.assertTrue(result.used_fallback)
        self.assertEqual(result.missing_values, ("product", "price"))
        self.assertNotIn("{", result.text)

    def test_renders_static_social_response(self):
        result = self.renderer.render(
            resolution(intent="social", subintent="agradecer")
        )

        self.assertEqual(
            result.text,
            "¡Con muchísimo gusto! ¿Te puedo colaborar con alguna otra cosita?",
        )
        self.assertFalse(result.used_fallback)


if __name__ == "__main__":
    unittest.main()
