"""
Acá vive la API que se comunica con NGINX, Monaco y que entrega el streaming entre componentes de la app.

Intenté usar código que permita extender hacia más operaciones que se deseen incluir luego.
"""

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from . import llm
from .config import settings
from .languages import LANGUAGES, build_system_prompt, build_user_prompt
from .storage import Storage

app = FastAPI(title="Pseudo2Code API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = Storage(settings.generated_dir)


class GenerateRequest(BaseModel):
    pseudocode: str = Field(min_length=3, max_length=8000)
    language: str
    name: str | None = Field(default=None, max_length=80)


class UpdateRequest(BaseModel):
    code: str


_GENERIC_LINES = {"inicio", "begin", "start", "algoritmo", "programa", "proceso"}


def _default_name(pseudocode: str) -> str:
    """Primera línea con contenido real (ignora INICIO, ALGORITMO, etc.)."""
    lines = [l.strip() for l in pseudocode.splitlines() if l.strip()]
    for line in lines:
        if line.lower().rstrip(":") not in _GENERIC_LINES:
            return line
    return lines[0] if lines else "programa"


def _ndjson(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"


@app.get("/api/health")
async def health():
    return await llm.health()


@app.get("/api/languages")
def languages():
    return [
        {"id": l.id, "label": l.label, "extension": l.extension, "monaco": l.monaco}
        for l in LANGUAGES.values()
    ]


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    """Genera código en streaming (NDJSON).

    Eventos: {"type":"token","content":...} ... {"type":"done","item":{...}}
    o {"type":"error","message":...}
    """
    lang = LANGUAGES.get(req.language)
    if lang is None:
        raise HTTPException(400, f"Lenguaje no soportado: {req.language}")

    system = build_system_prompt(lang)
    user = build_user_prompt(req.pseudocode, lang)
    name = (req.name or _default_name(req.pseudocode))[:80]

    async def event_stream():
        raw = []
        try:
            async for token in llm.stream_chat(system, user):
                raw.append(token)
                yield _ndjson({"type": "token", "content": token})
        except llm.LLMError as exc:
            yield _ndjson({"type": "error", "message": str(exc)})
            return

        code = llm.clean_code("".join(raw))
        item = storage.save(
            name=name,
            language=lang.id,
            pseudocode=req.pseudocode,
            code=code,
            model=settings.ollama_model,
        )
        yield _ndjson({"type": "done", "item": {**item, "code": code}})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.get("/api/history")
def history():
    return storage.list()


@app.get("/api/history/{item_id}")
def get_item(item_id: str):
    item = storage.get(item_id)
    if item is None:
        raise HTTPException(404, "No encontrado")
    return item


@app.put("/api/history/{item_id}")
def update_item(item_id: str, req: UpdateRequest):
    item = storage.update_code(item_id, req.code)
    if item is None:
        raise HTTPException(404, "No encontrado")
    return item


@app.delete("/api/history/{item_id}", status_code=204)
def delete_item(item_id: str):
    if not storage.delete(item_id):
        raise HTTPException(404, "No encontrado")


@app.get("/api/history/{item_id}/download")
def download(item_id: str):
    path = storage.file_path(item_id)
    if path is None or not path.exists():
        raise HTTPException(404, "No encontrado")
    return FileResponse(path, filename=path.name, media_type="text/plain")
