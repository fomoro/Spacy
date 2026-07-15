"""Compone respuestas a partir de plantillas y datos ya validados."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class ResponseComposer:
    """Presenta datos sin resolver intenciones ni consultar sistemas de negocio.

    La clase no conserva valores de la conversación. En particular, los datos
    personales deben llegar ya autorizados y redactados cuando corresponda.
    """

    def __init__(
        self,
        templates: str | Path | Mapping[str, Any],
        business_profile: str | Path | Mapping[str, Any],
    ) -> None:
        template_resource = self._load_resource(templates, "plantillas de respuesta")
        business_resource = self._load_resource(business_profile, "perfil del negocio")
        self._templates = template_resource.get("templates", template_resource)
        self._restaurant = business_resource.get("restaurant", business_resource)
        if not isinstance(self._templates, dict) or not self._templates:
            raise ValueError("El recurso debe contener un catálogo 'templates'.")
        if not isinstance(self._restaurant, dict) or not self._restaurant:
            raise ValueError("El recurso debe contener un objeto 'restaurant'.")

    @staticmethod
    def _load_resource(
        source: str | Path | Mapping[str, Any],
        resource_name: str,
    ) -> dict[str, Any]:
        if isinstance(source, Mapping):
            return dict(source)
        if not isinstance(source, (str, Path)):
            raise TypeError(f"{resource_name} debe ser una ruta o un diccionario")
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"No existe el recurso de {resource_name}: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError(f"Se esperaba un objeto JSON en {path}")
        return data

    def render(
        self,
        template_key: str,
        values: Mapping[str, Any] | None = None,
    ) -> str:
        """Renderiza una plantilla; los datos comerciales dinámicos los aporta el llamador."""
        template = self._templates.get(template_key)
        if not isinstance(template, str):
            raise KeyError(f"No existe la plantilla de respuesta '{template_key}'.")
        variables = self._business_defaults()
        variables.update(dict(values or {}))
        try:
            return template.format_map(variables)
        except KeyError as exc:
            missing = str(exc.args[0])
            raise ValueError(
                f"Falta el valor '{missing}' para la plantilla '{template_key}'."
            ) from exc

    def _business_defaults(self) -> dict[str, str]:
        address = self._restaurant.get("address", {})
        payment_methods = [
            str(value).replace("_", " ")
            for value in self._restaurant.get("payment_methods", [])
        ]
        return {
            "restaurant_name": str(self._restaurant.get("name", "")),
            "restaurant_description": str(self._restaurant.get("description", "")),
            "address": ", ".join(
                value
                for value in (
                    str(address.get("street", "")),
                    str(address.get("neighborhood", "")),
                )
                if value
            ),
            "city": str(address.get("city", "")),
            "payment_methods": ", ".join(payment_methods),
        }
