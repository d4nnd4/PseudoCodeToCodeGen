"""

Este es el módulo de persistencia en disco: generated/<lenguaje>/<id>_<slug>.<ext> + index.json .
con el historial de transformación.

Acá se podría incluir logs, pero es mejor separarlo en un módulo aparte.

"""

import json
import re
import threading
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .languages import LANGUAGES


def slugify(text: str, max_len: int = 40) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text[:max_len].rstrip("_") or "programa"


class Storage:
    def __init__(self, root: Path):
        self.root = root
        self.index_path = root / "index.json"
        self._lock = threading.Lock()
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write_index([])

    def _read_index(self) -> list[dict]:
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_index(self, items: list[dict]) -> None:
        tmp = self.index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.index_path)

    def save(self, *, name: str, language: str, pseudocode: str, code: str, model: str) -> dict:
        lang = LANGUAGES[language]
        item_id = uuid.uuid4().hex[:10]
        slug = slugify(name)
        rel_path = Path(language) / f"{item_id}_{slug}.{lang.extension}"
        abs_path = self.root / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(code, encoding="utf-8")

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        item = {
            "id": item_id,
            "name": name,
            "language": language,
            "path": rel_path.as_posix(),
            "pseudocode": pseudocode,
            "model": model,
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            items = self._read_index()
            items.insert(0, item)
            self._write_index(items)
        return item

    def list(self) -> list[dict]:
        return self._read_index()

    def get(self, item_id: str) -> dict | None:
        item = next((i for i in self._read_index() if i["id"] == item_id), None)
        if item is None:
            return None
        path = self.root / item["path"]
        return {**item, "code": path.read_text(encoding="utf-8") if path.exists() else ""}

    def file_path(self, item_id: str) -> Path | None:
        item = next((i for i in self._read_index() if i["id"] == item_id), None)
        return (self.root / item["path"]) if item else None

    def update_code(self, item_id: str, code: str) -> dict | None:
        with self._lock:
            items = self._read_index()
            item = next((i for i in items if i["id"] == item_id), None)
            if item is None:
                return None
            (self.root / item["path"]).write_text(code, encoding="utf-8")
            item["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._write_index(items)
        return {**item, "code": code}

    def delete(self, item_id: str) -> bool:
        with self._lock:
            items = self._read_index()
            item = next((i for i in items if i["id"] == item_id), None)
            if item is None:
                return False
            (self.root / item["path"]).unlink(missing_ok=True)
            self._write_index([i for i in items if i["id"] != item_id])
        return True
