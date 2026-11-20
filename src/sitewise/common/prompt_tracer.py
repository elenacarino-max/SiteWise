"""
Módulo prompt_tracer.py: Registro persistente de prompts y respuestas de los agentes
para depuración y auditoría.
"""

import json
import os
from datetime import UTC, datetime
from typing import Any

MAX_SERIALIZE_DEPTH = 15


def _es_mock(obj: Any) -> bool:
    cls = type(obj)
    return cls.__module__.startswith("unittest.mock") or hasattr(obj, "_mock_name")


def _serializar_dato(
    obj: Any,
    _depth: int = 0,
    _seen: set[int] | None = None,
) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if _es_mock(obj):
        nombre = getattr(obj, "_mock_name", None) or type(obj).__name__
        return f"<Mock:{nombre}>"
    if _depth >= MAX_SERIALIZE_DEPTH:
        return str(obj)

    if _seen is None:
        _seen = set()
    obj_id = id(obj)
    if obj_id in _seen:
        return "<CircularRef>"

    if isinstance(obj, dict):
        _seen.add(obj_id)
        try:
            return {
                str(k): _serializar_dato(v, _depth + 1, _seen)
                for k, v in obj.items()
            }
        finally:
            _seen.discard(obj_id)

    if isinstance(obj, (list, tuple)):
        _seen.add(obj_id)
        try:
            return [_serializar_dato(item, _depth + 1, _seen) for item in obj]
        finally:
            _seen.discard(obj_id)

    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        dumped = obj.model_dump()
        if not _es_mock(dumped):
            _seen.add(obj_id)
            try:
                return _serializar_dato(dumped, _depth + 1, _seen)
            finally:
                _seen.discard(obj_id)

    if hasattr(obj, "__dict__"):
        _seen.add(obj_id)
        try:
            return {
                k: _serializar_dato(v, _depth + 1, _seen)
                for k, v in obj.__dict__.items()
                if not k.startswith("_")
            }
        finally:
            _seen.discard(obj_id)

    return str(obj)


def guardar_traza_prompt(
    componente: str,
    model: str,
    messages: list[Any],
    response: Any = None,
    extra: dict[str, Any] | None = None,
    trace_file: str | None = None,
) -> None:
    """Guarda una entrada JSONL con los mensajes enviados al LLM y su respuesta."""
    ruta = trace_file or os.getenv("SITEWISE_PROMPTS_FILE", "logs/prompts_trace.jsonl")
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    registro: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "componente": componente,
        "model": model,
        "messages": _serializar_dato(messages),
    }
    if response is not None:
        registro["response"] = _serializar_dato(response)
    if extra:
        registro["extra"] = _serializar_dato(extra)

    with open(ruta, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")