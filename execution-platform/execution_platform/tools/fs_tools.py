from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any

class WorkspaceSandbox:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, rel_path: str) -> Path:
        p = (self.root / rel_path).resolve()
        if not str(p).startswith(str(self.root)):
            raise ValueError("path escapes workspace root")
        return p

    def fs_write(self, args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        path = args.get("path")
        content = args.get("content", "")
        if not path:
            raise ValueError("path required")
        dest = self._resolve(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "bytes": len(content)}

    def fs_read(self, args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        path = args.get("path")
        if not path:
            raise ValueError("path required")
        src = self._resolve(path)
        if not src.exists():
            raise FileNotFoundError("not found")
        data = src.read_text(encoding="utf-8")
        return {"ok": True, "content": data}
