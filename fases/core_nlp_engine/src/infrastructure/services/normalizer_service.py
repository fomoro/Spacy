from __future__ import annotations

from dataclasses import dataclass, asdict
import re
import unicodedata
from typing import Any, Iterable


@dataclass(frozen=True)
class Transformation:
    rule: str
    before: str
    after: str


@dataclass(frozen=True)
class NormalizationResult:
    original: str
    normalized: str
    transformations: tuple[Transformation, ...]
    monetary_values: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["transformations"] = [asdict(item) for item in self.transformations]
        data["monetary_values"] = list(self.monetary_values)
        return data


class TextNormalizer:
    """Normalización controlada para español colombiano.

    Responsabilidad: reducir variaciones superficiales sin inferir intención,
    producto ni reglas de negocio.
    """

    _QUOTE_TRANSLATION = str.maketrans({
        "“": '"', "”": '"', "„": '"', "’": "'", "‘": "'", "`": "'"
    })

    def __init__(self, config: dict[str, Any] | str | Path) -> None:
        from pathlib import Path
        if isinstance(config, (str, Path)):
            import json
            config_path = Path(config)
            with config_path.open("r", encoding="utf-8") as f:
                full_config = json.load(f)
            config = full_config.get("normalizer", full_config)

        if not isinstance(config, dict):
            raise TypeError("config debe ser un diccionario o una ruta de archivo JSON")
            
        self._options = config.get("options", {})
        self._phrase_replacements = self._prepare_replacements(
            config.get("phrase_replacements", {})
        )
        self._word_replacements = self._prepare_replacements(
            config.get("orthographic_replacements", {})
        )
        self._monetary_slang = {
            str(key).lower(): int(value)
            for key, value in config.get("monetary_slang", {}).items()
        }

    @staticmethod
    def _prepare_replacements(values: dict[str, str]) -> tuple[tuple[str, str], ...]:
        if not isinstance(values, dict):
            raise TypeError("Los reemplazos deben ser un diccionario")
        pairs = [(str(source).strip().lower(), str(target).strip().lower())
                 for source, target in values.items() if str(source).strip()]
        return tuple(sorted(pairs, key=lambda item: len(item[0]), reverse=True))

    @staticmethod
    def _replace_bounded(text: str, source: str, target: str) -> tuple[str, bool]:
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", re.IGNORECASE)
        replaced, count = pattern.subn(target, text)
        return replaced, count > 0

    def normalize(self, text: str) -> NormalizationResult:
        if text is None:
            raise TypeError("text no puede ser None")
        if not isinstance(text, str):
            raise TypeError("text debe ser una cadena")

        original = text
        current = text
        changes: list[Transformation] = []

        unicode_form = self._options.get("unicode_form", "NFC")
        normalized_unicode = unicodedata.normalize(unicode_form, current)
        if normalized_unicode != current:
            changes.append(Transformation("unicode", current, normalized_unicode))
            current = normalized_unicode

        if self._options.get("normalize_quotes", True):
            changed = current.translate(self._QUOTE_TRANSLATION)
            if changed != current:
                changes.append(Transformation("quotes", current, changed))
                current = changed

        if self._options.get("lowercase", True):
            changed = current.lower()
            if changed != current:
                changes.append(Transformation("lowercase", current, changed))
                current = changed

        for source, target in self._phrase_replacements:
            changed, applied = self._replace_bounded(current, source, target)
            if applied and changed != current:
                changes.append(Transformation(f"phrase:{source}", current, changed))
                current = changed

        for source, target in self._word_replacements:
            changed, applied = self._replace_bounded(current, source, target)
            if applied and changed != current:
                changes.append(Transformation(f"alias:{source}", current, changed))
                current = changed

        if self._options.get("normalize_punctuation_spacing", True):
            changed = re.sub(r"\s+([,.;:!?])", r"\1", current)
            changed = re.sub(r"([,.;:!?])(?!\s|$)", r"\1 ", changed)
            if changed != current:
                changes.append(Transformation("punctuation_spacing", current, changed))
                current = changed

        if self._options.get("collapse_whitespace", True):
            changed = re.sub(r"\s+", " ", current)
            if changed != current:
                changes.append(Transformation("whitespace", current, changed))
                current = changed

        if self._options.get("strip_outer_whitespace", True):
            changed = current.strip()
            if changed != current:
                changes.append(Transformation("strip", current, changed))
                current = changed

        monetary_values = tuple(self._extract_monetary_slang(current))
        return NormalizationResult(original, current, tuple(changes), monetary_values)

    def _extract_monetary_slang(self, text: str) -> Iterable[int]:
        number_words = {
            "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
            "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
            "diez": 10, "once": 11, "doce": 12, "quince": 15,
            "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50
        }
        slang = "|".join(re.escape(key) for key in self._monetary_slang)
        if not slang:
            return []
        pattern = re.compile(rf"\b(?P<amount>\d+|{'|'.join(number_words)})\s+(?P<unit>{slang})\b")
        values: list[int] = []
        for match in pattern.finditer(text):
            raw_amount = match.group("amount")
            amount = int(raw_amount) if raw_amount.isdigit() else number_words[raw_amount]
            values.append(amount * self._monetary_slang[match.group("unit")])
        return values
