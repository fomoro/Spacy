from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"No existe el archivo JSON: {file_path}")
    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido en {file_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise TypeError(f"Se esperaba un objeto JSON en {file_path}")
    return data


def load_normalizer_config(config_dir: str | Path) -> dict[str, Any]:
    dir_path = Path(config_dir)
    if not dir_path.is_dir():
        raise FileNotFoundError(f"No existe el directorio de configuración: {dir_path}")

    files_to_load = {
        "metadata": "metadata.json",
        "options": "options.json",
        "orthographic_replacements": "orthographic_replacements.json",
        "phrase_replacements": "phrase_replacements.json",
        "monetary_slang": "monetary_slang.json",
        "non_semantic_tokens": "non_semantic_tokens.json",
        "rules": "rules.json"
    }

    config: dict[str, Any] = {}
    for key, filename in files_to_load.items():
        file_path = dir_path / filename
        if not file_path.is_file():
            raise FileNotFoundError(f"Falta el archivo de configuración requerido: {file_path}")

        try:
            with file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido en {file_path}: {exc}") from exc

        config[key] = data

    return config

