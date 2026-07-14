"""Migración idempotente de los recursos lingüísticos separados.

Conserva el contenido comercial existente, corrige colisiones evidentes y añade
patrones que ya forman parte del contrato conversacional del proyecto.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
RESOURCE_PATHS = {
    "intent_taxonomy.json": RESOURCES / "nlp" / "intent_taxonomy.json",
    "normalizer_config.json": RESOURCES / "nlp" / "normalizer_config.json",
    "matcher_patterns.json": RESOURCES / "nlp" / "matcher_patterns.json",
    "lemma_signals.json": RESOURCES / "nlp" / "lemma_signals.json",
    "entity_ruler_patterns.json": RESOURCES / "nlp" / "entity_ruler_patterns.json",
    "resolver_config.json": RESOURCES / "nlp" / "resolver_config.json",
    "menu_catalog.json": RESOURCES / "menu" / "menu_catalog.json",
    "menu_offerings.json": RESOURCES / "menu" / "menu_offerings.json",
}


def load(name: str) -> dict[str, Any]:
    return json.loads(RESOURCE_PATHS[name].read_text(encoding="utf-8"))


def save(name: str, data: dict[str, Any]) -> None:
    RESOURCE_PATHS[name].write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def merge_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        entity_id = str(item["id"])
        if entity_id not in merged:
            merged[entity_id] = dict(item)
            merged[entity_id]["phrases"] = list(item.get("phrases", []))
            continue
        target = merged[entity_id]
        target["phrases"] = unique(target["phrases"] + item.get("phrases", []))
        if item.get("menu_sections"):
            target["menu_sections"] = unique(
                target.get("menu_sections", []) + item["menu_sections"]
            )
    return list(merged.values())


def refine_menu() -> None:
    menu = load("menu_catalog.json")
    menu["metadata"].update({
        "schema_version": "3.0.0",
        "domain": "restaurante_colombiano_de_comida_de_mar",
        "ownership": "vocabulario_comercial_estable",
        "excludes": [
            "referencias_contextuales",
            "fechas_y_dias",
            "actos_de_habla_e_intenciones",
        ],
    })
    types = menu["entity_types"]
    types.pop("FECHA_RELATIVA", None)

    for group in types.values():
        group["items"] = merge_items(group.get("items", []))

    specific = types["PRODUCTO_ESPECIFICO"]["items"]
    by_id = {item["id"]: item for item in specific}
    executive_to_base = {
        "filete_a_la_marinera_ejecutivo": "filete_a_la_marinera",
        "arroz_con_camaron_ejecutivo": "arroz_con_camaron",
        "cazuela_de_mariscos_ejecutiva": "cazuela_de_mariscos",
        "filete_al_ajillo_ejecutivo": "filete_al_ajillo",
        "mojarra_frita_ejecutiva": "mojarra_frita",
        "arroz_a_la_marinera_ejecutivo": "arroz_a_la_marinera",
        "trucha_a_la_plancha_ejecutiva": "trucha_a_la_plancha",
        "trucha_a_la_marinera_ejecutiva": "trucha_a_la_marinera",
        "viudo_de_mapara_ejecutivo": "viudo_de_mapara",
    }
    for executive_id, base_id in executive_to_base.items():
        executive = by_id.get(executive_id)
        base = by_id.get(base_id)
        if not executive or not base:
            continue
        base["phrases"] = unique(base.get("phrases", []) + executive.get("phrases", []))
        base["menu_sections"] = unique(
            base.get("menu_sections", ["carta"]) + ["almuerzos_ejecutivos"]
        )
    specific = [
        item for item in specific
        if item["id"] not in executive_to_base and item["id"] != "de_camarones"
    ]
    special_sierra = next(
        (item for item in specific if item["id"] == "sierra_frita_especial"), None
    )
    if special_sierra:
        special_sierra["phrases"] = [
            phrase for phrase in special_sierra.get("phrases", [])
            if phrase.casefold() != "sierra frita"
        ]
        special_sierra["menu_sections"] = ["carta"]
    if not any(item["id"] == "sierra_frita" for item in specific):
        specific.append({
            "id": "sierra_frita",
            "canonical": "Sierra frita",
            "phrases": ["sierra frita"],
            "menu_sections": ["almuerzos_ejecutivos"],
        })
    filete_salsa = next(
        (item for item in specific if item["id"] == "filete_o_bagre_en_salsa"), None
    )
    if filete_salsa:
        filete_salsa["canonical"] = "Filete o bagre en salsa de camarones"
        filete_salsa["phrases"] = unique(filete_salsa.get("phrases", []) + [
            "filete o bagre en salsa de camarones",
            "filete o bagre en salsa de camarón",
        ])
    for item in specific:
        item.setdefault("menu_sections", ["carta"])
    types["PRODUCTO_ESPECIFICO"]["items"] = specific

    canonical_names = {
        "camaron": "Camarón",
        "langostino": "Langostino",
        "mapara": "Mapará",
        "mariscos": "Mariscos",
        "mojarra": "Mojarra",
        "pargo_rojo": "Pargo rojo",
        "robalo": "Róbalo",
        "salmon": "Salmón",
    }
    for item in types["PRODUCTO_BASE"]["items"]:
        item["canonical"] = canonical_names.get(item["id"], item["canonical"])

    payment_items = types["MEDIO_PAGO"]["items"]
    if not any(item["id"] == "tarjeta" for item in payment_items):
        payment_items.append({
            "id": "tarjeta",
            "canonical": "Tarjeta",
            "phrases": ["tarjeta", "con tarjeta"],
            "ambiguity": "requiere precisar débito o crédito solo si la operación lo exige",
        })

    categories = {item["id"]: item for item in types["CATEGORIA"]["items"]}
    if "pescados_precio_fijo" in categories:
        categories["pescados_precio_fijo"]["phrases"] = [
            "pescados a precio fijo", "pescado a precio fijo"
        ]
    if "pescados_segun_tamano" in categories:
        categories["pescados_segun_tamano"]["phrases"] = [
            "pescados según tamaño", "pescados por tamaño",
            "pescado según tamaño", "pescado por tamaño",
        ]

    save("menu_catalog.json", menu)


def refine_matcher() -> None:
    config = load("matcher_patterns.json")
    config["metadata"].update({
        "schema_version": "2.0.0",
        "taxonomy": "intent_taxonomy.json",
        "ownership": "estructuras_tokenizadas_y_extraccion_sintactica",
    })
    patterns = config["patterns"]
    by_id = {item["id"]: item for item in patterns}

    if "AVAILABILITY_PRODUCT" in by_id:
        by_id["AVAILABILITY_PRODUCT"]["pattern"] = [
            {"LOWER": {"IN": ["disponible", "disponibles", "queda", "quedan"]}},
            {"LOWER": {"IN": ["el", "la", "los", "las"]}, "OP": "?"},
            {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"]}, "OP": "+"},
        ]
    if "ORDER_WANT_PRODUCT" in by_id:
        verbs = by_id["ORDER_WANT_PRODUCT"]["pattern"][0]["LOWER"]["IN"]
        by_id["ORDER_WANT_PRODUCT"]["pattern"][0]["LOWER"]["IN"] = [
            word for word in verbs if word not in {"anota", "anotar", "anote"}
        ]
    if "MENU_REQUEST" in by_id:
        by_id["MENU_REQUEST"]["pattern"][-1] = {"ENT_ID": "menu_pdf", "OP": "+"}
    if "DELIVERY_QUERY" in by_id:
        by_id["DELIVERY_QUERY"]["pattern"][0] = {"ENT_ID": "domicilio", "OP": "+"}
    if "ALLERGY_QUERY" in by_id:
        by_id["ALLERGY_QUERY"]["pattern"][-1] = {
            "ENT_TYPE": {"IN": ["ALERGENO", "INGREDIENTE", "PRODUCTO_BASE"]},
            "OP": "+",
        }
    if "QUANTITY_ONLY" in by_id:
        by_id["QUANTITY_ONLY"]["full_text_only"] = True
    if "MENU_RETRY" in by_id:
        by_id["MENU_RETRY"]["pattern"][0]["OP"] = "+"
        retry_words = by_id["MENU_RETRY"]["pattern"][0]["LOWER"]["IN"]
        by_id["MENU_RETRY"]["pattern"][0]["LOWER"]["IN"] = unique(
            retry_words + ["reenvíala", "reenvíalo", "reenvíame"]
        )
    if "MENU_REQUEST" in by_id:
        by_id["MENU_REQUEST"]["pattern"][0].pop("OP", None)

    additions = [
        {
            "id": "CATALOG_PRODUCT_OFFER",
            "intent": "catalogo", "subintent": "consultar_producto", "weight": 0.5,
            "pattern": [
                {"LOWER": {"IN": ["hay", "maneja", "manejan", "ofrece", "ofrecen", "tiene", "tienen"]}},
                {"LOWER": {"IN": ["el", "la", "los", "las", "algo", "algún", "algun"]}, "OP": "?"},
                {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"]}, "OP": "+"},
            ],
        },
        {
            "id": "AVAILABILITY_TEMPORAL", "intent": "catalogo",
            "subintent": "consultar_disponibilidad_producto", "weight": 0.58,
            "pattern": [
                {"LOWER": {"IN": ["hoy", "ahora", "todavía", "todavia"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["hay", "queda", "quedan", "tiene", "tienen"]}},
                {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"]}, "OP": "+"},
            ],
        },
        {
            "id": "AVAILABILITY_PRODUCT_TRAILING", "intent": "catalogo",
            "subintent": "consultar_disponibilidad_producto", "weight": 0.76,
            "pattern": [
                {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"]}, "OP": "+"},
                {"LOWER": {"IN": ["está", "esta", "están", "estan"]}, "OP": "?"},
                {"LOWER": {"IN": ["disponible", "disponibles", "queda", "quedan"]}},
            ],
        },
        {
            "id": "AVAILABILITY_SPECIFIC_EXISTENCE", "intent": "catalogo",
            "subintent": "consultar_disponibilidad_producto", "weight": 0.7,
            "pattern": [
                {"LOWER": "hay"},
                {"ENT_TYPE": "PRODUCTO_ESPECIFICO", "OP": "+"},
            ],
        },
        {
            "id": "PREPARATION_SEARCH", "intent": "catalogo",
            "subintent": "consultar_preparacion", "weight": 0.54,
            "pattern": [
                {"LOWER": {"IN": ["cuál", "cual", "cuáles", "cuales", "qué", "que", "algo"]}},
                {"OP": "*"},
                {"ENT_TYPE": "PREPARACION", "OP": "+"},
            ],
        },
        {
            "id": "PREPARATION_DEFINITION", "intent": "catalogo",
            "subintent": "consultar_definicion_preparacion", "weight": 0.6,
            "pattern": [
                {"LOWER": {"IN": ["qué", "que"]}},
                {"LOWER": {"IN": ["es", "significa", "quiere"]}, "OP": "?"},
                {"LOWER": "decir", "OP": "?"},
                {"ENT_TYPE": "PREPARACION", "OP": "+"},
            ],
        },
        {
            "id": "PRODUCT_COMPARISON", "intent": "catalogo",
            "subintent": "comparar_productos", "weight": 0.78,
            "pattern": [
                {"LOWER": {"IN": ["cuál", "cual", "compare", "comparar"]}},
                {"OP": "*"},
                {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"]}, "OP": "+"},
                {"LOWER": {"IN": ["o", "y", "con"]}},
                {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"]}, "OP": "+"},
            ],
        },
        {
            "id": "PRODUCT_DETAIL_CONTENT", "intent": "catalogo",
            "subintent": "consultar_detalle_producto", "weight": 0.62,
            "pattern": [
                {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"]}, "OP": "+"},
                {"OP": "*"},
                {"LOWER": {"IN": ["contiene", "trae", "tiene", "viene", "lleva"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["acompañamiento", "acompañamientos", "bebida", "espina", "espinas"]}, "OP": "?"},
            ],
        },
        {
            "id": "PREPARATION_PRODUCT_VERBAL", "intent": "catalogo",
            "subintent": "consultar_preparacion_producto", "weight": 0.7,
            "pattern": [
                {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"]}, "OP": "+"},
                {"LOWER": {"IN": ["la", "lo", "se"]}, "OP": "?"},
                {"LOWER": {"IN": ["hace", "hacen", "prepara", "preparan", "puede", "pueden"]}},
                {"LOWER": {"IN": ["hacer", "preparar"]}, "OP": "?"},
                {"ENT_TYPE": "PREPARACION", "OP": "+"},
            ],
        },
        {
            "id": "CATEGORY_DIETARY_RESTRICTION", "intent": "catalogo",
            "subintent": "consultar_categoria_por_restriccion", "weight": 0.82,
            "pattern": [
                {"LOWER": {"IN": ["qué", "que", "cuál", "cual", "tienen", "hay"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["sin", "vegetariano", "vegetariana", "vegano", "vegana"]}},
                {"ENT_TYPE": {"IN": ["ALERGENO", "INGREDIENTE", "PRODUCTO_BASE"]}, "OP": "*"},
            ],
        },
        {
            "id": "MENU_GENERAL", "intent": "menu",
            "subintent": "consultar_menu_general", "weight": 0.48,
            "pattern": [
                {"LOWER": {"IN": ["qué", "que"]}},
                {"LOWER": {"IN": ["hay", "ofrecen"]}},
            ],
        },
        {
            "id": "MENU_CHANGES", "intent": "menu",
            "subintent": "consultar_cambios_menu", "weight": 0.58,
            "pattern": [
                {"LOWER": {"IN": ["qué", "que"]}},
                {"LOWER": {"IN": ["cambió", "cambio", "cambiaron", "nuevo", "nueva"]}},
                {"LOWER": {"IN": ["del", "en"]}, "OP": "?"},
                {"LOWER": {"IN": ["menú", "menu", "carta"]}},
            ],
        },
        {
            "id": "MENU_RETRY_PERIPHRASTIC", "intent": "menu",
            "subintent": "reenviar_menu", "weight": 0.62,
            "requires_context": True,
            "pattern": [
                {"LOWER": {"IN": ["vuelva", "vuelvan"]}},
                {"LOWER": "y"},
                {"LOWER": {"IN": ["me", "lo", "la"]}, "OP": "*"},
                {"LOWER": {"IN": ["manda", "mande", "mandan", "envía", "envie"]}},
            ],
        },
        {
            "id": "ORDER_ADD_SINGLE", "intent": "pedido",
            "subintent": "agregar_producto_pedido", "weight": 0.63,
            "requires_context": True,
            "pattern": [
                {"LOWER": {"IN": ["agrega", "agregue", "anota", "anote", "añada", "adicione"]}},
                {"LOWER": {"IN": ["el", "la", "un", "una"]}, "OP": "?"},
                {"LIKE_NUM": True, "OP": "?"},
                {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"]}, "OP": "+"},
            ],
        },
        {
            "id": "ORDER_QUANTIFIED_PRODUCT", "intent": "pedido",
            "subintent": "agregar_productos_pedido", "weight": 0.72,
            "pattern": [
                {"LOWER": {"IN": ["dame", "deme", "manda", "mande", "necesito", "quiero"]}, "OP": "?"},
                {"LOWER": {"IN": ["dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "doce"]}},
                {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE"]}, "OP": "+"},
            ],
        },
        {
            "id": "ORDER_GROUP_START", "intent": "pedido",
            "subintent": "iniciar_pedido_grupal", "weight": 0.58,
            "pattern": [
                {"LOWER": {"IN": ["necesito", "quiero", "requiero"]}},
                {"OP": "*"},
                {"LOWER": "para"},
                {"LIKE_NUM": True},
                {"LOWER": {"IN": ["personas", "platos", "almuerzos", "pedidos"]}},
            ],
        },
        {
            "id": "ORDER_REPEAT", "intent": "pedido",
            "subintent": "repetir_pedido", "weight": 0.66,
            "requires_context": True,
            "pattern": [
                {"LOWER": {"IN": ["deme", "dame", "quiero", "repita", "repíteme", "repite"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["mismo", "misma", "siempre", "anterior", "pasada"]}},
            ],
        },
        {
            "id": "ORDER_SELECT_PREPARATION", "intent": "pedido",
            "subintent": "seleccionar_preparacion", "weight": 0.6,
            "requires_context": True,
            "pattern": [
                {"LOWER": {"IN": ["lo", "la", "uno", "una"]}},
                {"LOWER": {"IN": ["quiero", "deme", "dame"]}, "OP": "?"},
                {"ENT_TYPE": "PREPARACION", "OP": "+"},
            ],
        },
        {
            "id": "ORDER_SELECT_PREPARATION_COMMAND", "intent": "pedido",
            "subintent": "seleccionar_preparacion", "weight": 0.6,
            "requires_context": True,
            "pattern": [
                {"LOWER": {"IN": ["quiero", "deme", "dame"]}},
                {"ENT_TYPE": "PREPARACION", "OP": "+"},
            ],
        },
        {
            "id": "PRICE_GENERAL", "intent": "precio",
            "subintent": "consultar_precios_generales", "weight": 0.5,
            "pattern": [{"LOWER": {"IN": ["precios", "precio", "tarifas", "valores"]}}],
        },
        {
            "id": "PAYMENT_MIXED", "intent": "pago",
            "subintent": "consultar_pago_mixto", "weight": 1.25,
            "pattern": [
                {"LOWER": {"IN": ["parte", "mitad"]}},
                {"OP": "*"},
                {"ENT_TYPE": "MEDIO_PAGO", "OP": "+"},
                {"LOWER": "y"},
                {"OP": "*"},
                {"ENT_TYPE": "MEDIO_PAGO", "OP": "+"},
            ],
        },
        {
            "id": "DELIVERY_GROUP", "intent": "domicilio",
            "subintent": "consultar_domicilio_grupal", "weight": 0.72,
            "pattern": [
                {"LOWER": {"IN": ["tiempo", "demora", "entrega", "domicilio"]}},
                {"OP": "*"},
                {"LIKE_NUM": True},
                {"LOWER": {"IN": ["pedidos", "almuerzos", "personas"]}},
            ],
        },
        {
            "id": "DELIVERY_PREVIOUS_ADDRESS", "intent": "domicilio",
            "subintent": "usar_direccion_previa", "weight": 0.72,
            "requires_context": True,
            "pattern": [
                {"LOWER": {"IN": ["manda", "mande", "envía", "envie"]}, "OP": "?"},
                {"OP": "*"},
                {"LOWER": {"IN": ["misma", "anterior"]}},
                {"LOWER": {"IN": ["dirección", "direccion"]}},
            ],
        },
        {
            "id": "INVOICE_QUERY", "intent": "operacion",
            "subintent": "consultar_facturacion", "weight": 0.6,
            "pattern": [
                {"LOWER": {"IN": ["envían", "envian", "expiden", "manejan", "necesito", "requiere", "requiero"]}, "OP": "?"},
                {"ENT_ID": "factura_electronica", "OP": "+"},
            ],
        },
        {
            "id": "PACKAGING_QUERY", "intent": "operacion",
            "subintent": "consultar_empaque", "weight": 0.58,
            "pattern": [
                {"LOWER": {"IN": ["empacar", "empacan", "marcar", "marcan", "separar", "separan"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["pedido", "pedidos", "nombre", "nombres"]}},
            ],
        },
        {
            "id": "SCHEDULED_ORDER", "intent": "operacion",
            "subintent": "consultar_pedido_programado", "weight": 0.6,
            "pattern": [
                {"LOWER": {"IN": ["programar", "programarlo", "entregar", "llegar", "lleguen"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["hora", "una", "dos", "mediodía", "mediodia"]}},
            ],
        },
        {
            "id": "PARKING_QUERY", "intent": "horario_ubicacion",
            "subintent": "consultar_parqueadero", "weight": 0.58,
            "pattern": [
                {"LOWER": {"IN": ["hay", "tiene", "tienen", "costo", "cuesta"]}, "OP": "?"},
                {"ENT_ID": "parqueadero", "OP": "+"},
            ],
        },
        {
            "id": "INSTALLATION_QUERY", "intent": "horario_ubicacion",
            "subintent": "consultar_instalacion", "weight": 0.55,
            "pattern": [
                {"LOWER": {"IN": ["hay", "tiene", "tienen"]}},
                {"LOWER": {"IN": ["baño", "bano", "baños", "banos", "rampa", "terraza"]}},
            ],
        },
        {
            "id": "LOCATION_ADDRESS_REFERENCE", "intent": "horario_ubicacion",
            "subintent": "consultar_ubicacion", "weight": 0.52,
            "pattern": [
                {"LOWER": {"IN": ["dirección", "direccion", "ubicación", "ubicacion"]}},
                {"LOWER": {"IN": ["es", "queda"]}, "OP": "?"},
                {"LOWER": {"IN": ["misma", "igual", "siempre"]}, "OP": "?"},
            ],
        },
        {
            "id": "RECOMMENDATION_QUALITY", "intent": "recomendacion",
            "subintent": "solicitar_recomendacion", "weight": 0.56,
            "pattern": [
                {"LOWER": {"IN": ["qué", "que", "cuál", "cual"]}},
                {"LOWER": {"IN": ["plato", "opción", "opcion"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["llena", "rinde", "rápido", "rapido", "suave", "recomendable"]}},
            ],
        },
        {
            "id": "RECOMMENDATION_BY_ALLERGY", "intent": "recomendacion",
            "subintent": "solicitar_recomendacion_por_alergia", "weight": 0.92,
            "pattern": [
                {"LOWER": {"IN": ["alérgico", "alérgica", "alergico", "alergica", "intolerante"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["qué", "que"]}},
                {"LOWER": "puedo"},
                {"LOWER": {"IN": ["pedir", "comer"]}},
            ],
        },
        {
            "id": "RECOMMENDATION_BY_RESTRICTION", "intent": "recomendacion",
            "subintent": "solicitar_recomendacion_por_restriccion", "weight": 0.86,
            "pattern": [
                {"LOWER": {"IN": ["cuál", "cual", "qué", "que"]}},
                {"LOWER": {"IN": ["plato", "opción", "opcion"]}},
                {"LOWER": {"IN": ["no", "sin"]}},
                {"LOWER": {"IN": ["lleva", "tiene", "contiene"]}, "OP": "?"},
                {"ENT_TYPE": {"IN": ["ALERGENO", "INGREDIENTE", "PRODUCTO_BASE"]}, "OP": "+"},
            ],
        },
        {
            "id": "ALLERGEN_CONTENT", "intent": "seguridad_alimentaria",
            "subintent": "consultar_alergenos", "weight": 0.82,
            "pattern": [
                {"ENT_TYPE": {"IN": ["PRODUCTO_ESPECIFICO", "PRODUCTO_BASE", "PREPARACION", "INGREDIENTE"]}, "OP": "+"},
                {"OP": "*"},
                {"LOWER": {"IN": ["contiene", "trae", "tiene", "lleva"]}},
                {"OP": "*"},
                {"ENT_TYPE": "ALERGENO", "OP": "+"},
            ],
        },
        {
            "id": "ALLERGEN_OPEN_QUERY", "intent": "seguridad_alimentaria",
            "subintent": "consultar_alergenos", "weight": 0.72,
            "pattern": [
                {"LOWER": {"IN": ["qué", "que", "cuál", "cual"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["tiene", "tienen", "lleva", "llevan", "contiene", "contienen"]}},
                {"ENT_TYPE": "ALERGENO", "OP": "+"},
            ],
        },
        {
            "id": "MODIFICATION_ADAPT", "intent": "pedido",
            "subintent": "solicitar_modificacion", "weight": 0.7,
            "pattern": [
                {"LOWER": {"IN": ["adaptar", "adapta", "adapten", "cambiar", "cambie"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["sin", "con"]}},
                {"ENT_TYPE": {"IN": ["ALERGENO", "INGREDIENTE", "PRODUCTO_BASE"]}, "OP": "+"},
            ],
        },
        {
            "id": "RESERVATION_CONDITIONS", "intent": "reserva_evento",
            "subintent": "consultar_reserva", "weight": 0.58,
            "pattern": [
                {"LOWER": {"IN": ["reserva", "reservar"]}},
                {"OP": "*"},
                {"LOWER": {"IN": ["cuesta", "costo", "disponible", "privado", "privada"]}},
            ],
        },
        {
            "id": "EVENT_PROPOSAL", "intent": "reserva_evento",
            "subintent": "solicitar_evento", "weight": 0.62,
            "pattern": [
                {"LOWER": {"IN": ["necesito", "quiero", "solicito"]}},
                {"LOWER": {"IN": ["cotización", "cotizacion", "propuesta", "evento", "almuerzo"]}},
                {"OP": "*"},
                {"LOWER": "para"},
                {"LIKE_NUM": True},
                {"LOWER": "personas"},
            ],
        },
    ]

    addition_ids = {item["id"] for item in additions}
    patterns = [item for item in patterns if item["id"] not in addition_ids]
    patterns.extend(additions)
    config["patterns"] = patterns
    save("matcher_patterns.json", config)


def refine_lemmas() -> None:
    config = load("lemma_signals.json")
    config["metadata"].update({
        "schema_version": "2.0.0",
        "taxonomy": "intent_taxonomy.json",
        "ownership": "lemas_y_formas_flexionadas_como_evidencia_secundaria",
    })
    signals = config["signals"]
    by_lemma = {item["lemma"]: item for item in signals}
    additions = [
        ("disponer", ["disponible", "disponibles", "disponibilidad"], "catalogo", "consultar_disponibilidad_producto", 0.18),
        ("comparar", ["compara", "compare", "comparación"], "catalogo", "comparar_productos", 0.16),
        ("empacar", ["empaca", "empacan", "empaque", "empacado"], "operacion", "consultar_empaque", 0.18),
        ("marcar", ["marca", "marcan", "marcado", "etiquetar", "etiquetado"], "operacion", "consultar_empaque", 0.16),
        ("programar", ["programa", "programan", "programado", "programarlo"], "operacion", "consultar_pedido_programado", 0.18),
        ("repetir", ["repite", "repita", "repetir", "mismo", "misma"], "pedido", "repetir_pedido", 0.16),
        ("ubicar", ["ubica", "ubicado", "ubicados", "ubicación"], "horario_ubicacion", "consultar_ubicacion", 0.16),
    ]
    for lemma, forms, intent, subintent, weight in additions:
        evidence = {"intent": intent, "subintent": subintent, "weight": weight}
        if lemma in by_lemma:
            by_lemma[lemma]["forms"] = unique(by_lemma[lemma].get("forms", []) + forms)
            if evidence not in by_lemma[lemma].get("evidence", []):
                by_lemma[lemma].setdefault("evidence", []).append(evidence)
        else:
            item = {"lemma": lemma, "forms": unique([lemma] + forms), "evidence": [evidence]}
            signals.append(item)
            by_lemma[lemma] = item
    save("lemma_signals.json", config)


def refine_normalizer() -> None:
    config = load("normalizer_config.json")
    config["metadata"].update({
        "schema_version": "2.0.0",
        "ownership": "variacion_grafica_y_lexica_sin_inferencia_de_intencion",
    })
    config["orthographic_replacements"].update({
        "pesacado": "pescado",
        "mojaras": "mojarras",
        "mojara": "mojarra",
    })
    save("normalizer_config.json", config)


def refine_entity_ruler() -> None:
    config = load("entity_ruler_patterns.json")
    config["metadata"].update({
        "schema_version": "2.0.0",
        "ownership": "tiempo_y_referencias_que_requieren_contexto_conversacional",
        "excludes": ["productos", "ingredientes", "negacion_sintactica", "intenciones"],
    })
    patterns = [
        {"label": "DIA_SEMANA", "pattern": day, "id": day}
        for day in ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    ]
    patterns += [
        {"label": "FECHA_RELATIVA", "pattern": "hoy", "id": "hoy"},
        {"label": "FECHA_RELATIVA", "pattern": "mañana", "id": "manana"},
        {"label": "FECHA_RELATIVA", "pattern": "pasado mañana", "id": "pasado_manana"},
        {"label": "FECHA_RELATIVA", "pattern": "este fin de semana", "id": "fin_semana"},
        {"label": "MOMENTO_DIA", "pattern": "al mediodía", "id": "mediodia"},
        {"label": "MOMENTO_DIA", "pattern": "en la mañana", "id": "manana"},
        {"label": "MOMENTO_DIA", "pattern": "en la tarde", "id": "tarde"},
        {"label": "MOMENTO_DIA", "pattern": "en la noche", "id": "noche"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "ese", "id": "ultimo_producto"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "esa", "id": "ultimo_producto"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "el mismo", "id": "ultimo_producto"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "la misma", "id": "ultimo_producto"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "uno de esos", "id": "ultimo_producto"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "uno de esos", "id": "ultimo_elemento"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "lo de siempre", "id": "pedido_previo"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "la de siempre", "id": "pedido_previo"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "pedido anterior", "id": "pedido_previo"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "vez pasada", "id": "pedido_previo"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "misma dirección", "id": "direccion_previa"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "dirección de siempre", "id": "direccion_previa"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "otra vez", "id": "ultimo_elemento"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "de nuevo", "id": "ultimo_elemento"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "nuevamente", "id": "ultimo_elemento"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "la frita", "id": "preparacion_contextual"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "la de ajillo", "id": "preparacion_contextual"},
        {"label": "REFERENCIA_CONTEXTUAL", "pattern": "la de salsa", "id": "preparacion_contextual"},
    ]
    # Un mismo texto no puede tener dos ids en el mismo EntityRuler.
    seen: set[tuple[str, str]] = set()
    config["patterns"] = [
        item for item in patterns
        if not ((key := (item["label"], str(item["pattern"]))) in seen or seen.add(key))
    ]
    save("entity_ruler_patterns.json", config)


def refine_resolver() -> None:
    config = load("resolver_config.json")
    config["metadata"].update({
        "schema_version": "2.0.0",
        "taxonomy": "intent_taxonomy.json",
        "ownership": "ponderacion_prioridades_y_evidencia",
    })
    phrase = config["phrase_evidence"]
    phrase.pop("FECHA_RELATIVA", None)
    phrase.pop("DIA_SEMANA", None)
    phrase.pop("REFERENCIA_CONTEXTUAL", None)
    phrase["ALERGENO"] = []
    config["entity_ruler_evidence"] = {
        "DIA_SEMANA": [{
            "intent": "horario_ubicacion", "subintent": "consultar_horario", "weight": 0.06
        }],
        "FECHA_RELATIVA": [],
        "MOMENTO_DIA": [],
        "REFERENCIA_CONTEXTUAL": [],
    }
    config.pop("required_entities", None)
    config.pop("clarification_messages", None)
    save("resolver_config.json", config)


def main() -> None:
    refine_menu()
    refine_normalizer()
    refine_matcher()
    refine_lemmas()
    refine_entity_ruler()
    refine_resolver()


if __name__ == "__main__":
    main()
