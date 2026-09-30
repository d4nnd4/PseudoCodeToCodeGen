"""

Cliente pequeño para Ollama (API /api/chat) con streaming limitado.

"""

import json
import re
from collections.abc import AsyncIterator

import httpx

from .config import settings

FENCE_RE = re.compile(r"```[\w+-]*\s*\n(.*?)(?:```|$)", re.DOTALL)


class LLMError(RuntimeError):
    pass


async def stream_chat(system: str, user: str) -> AsyncIterator[str]:
    """Hace el streaming de los tokens generados por el modelo en medio de la ejecución."""
    payload = {
        "model": settings.ollama_model,
        "stream": True,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"temperature": settings.ollama_temperature},
    }
    timeout = httpx.Timeout(settings.ollama_timeout, connect=10.0)
    try:
        async with httpx.AsyncClient(base_url=settings.ollama_url, timeout=timeout) as client:
            async with client.stream("POST", "/api/chat", json=payload) as resp:
                if resp.status_code != 200:
                    body = (await resp.aread()).decode(errors="replace")
                    raise LLMError(f"Ollama respondió {resp.status_code}: {body[:300]}")
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if "error" in chunk:
                        raise LLMError(chunk["error"])
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
    except httpx.HTTPError as exc:
        raise LLMError(f"No se pudo conectar con Ollama en {settings.ollama_url}: {exc}") from exc


async def health() -> dict:
    """
    Este async comprueba que Ollama responde y que el modelo configurado está descargado.
    
    Tener en cuenta que los health checks son necesarios para que el modelo responda correctamente, 
    y no se caiga cuando haya complicaciones.
    """
    try:
        async with httpx.AsyncClient(base_url=settings.ollama_url, timeout=5.0) as client:
            resp = await client.get("/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
    except httpx.HTTPError as exc:
        return {"ollama": False, "model": settings.ollama_model, "model_ready": False, "error": str(exc)}
    wanted = settings.ollama_model
    ready = any(m == wanted or m == f"{wanted}:latest" for m in models)
    return {"ollama": True, "model": wanted, "model_ready": ready, "available_models": models}


def clean_code(raw: str) -> str:
    """Quita fences de markdown y texto sobrante si el modelo no siguió las reglas."""
    text = raw.strip()
    match = FENCE_RE.search(text)
    if match:
        text = match.group(1)
    return text.strip("\n") + "\n"
