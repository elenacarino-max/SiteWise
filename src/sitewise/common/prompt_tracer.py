"""
Módulo prompt_tracer.py: Registro persistente de prompts y respuestas de los agentes
para depuración y auditoría.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any


def _serializar_dato(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _serializar_dato(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serializar_dato(item) for item in obj]
    if hasattr(obj, "model_dump"):
        return _serializar_dato(obj.model_dump())
    if hasattr(obj, "__dict__"):
        return {
            k: _serializar_dato(v)
            for k, v in obj.__dict__.items()
            if not k.startswith("_")
        }
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
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