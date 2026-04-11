from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4


class JsonRepository:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.runs_path = self.base_dir / "runs.json"
        self.workspaces_path = self.base_dir / "workspaces.json"
        self.artifacts_dir = self.base_dir / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_seed_files()

    def _ensure_seed_files(self) -> None:
        if not self.workspaces_path.exists():
            self.workspaces_path.write_text(
                json.dumps(
                    [
                        {
                            "workspace_id": "core-lab",
                            "name": "Core Lab",
                            "description": "Default workspace for the public quant research lab.",
                        }
                    ],
                    indent=2,
                )
            )
        if not self.runs_path.exists():
            self.runs_path.write_text("[]")

    def _read_json(self, path: Path) -> list[dict[str, Any]]:
        return json.loads(path.read_text())

    def _write_json(self, path: Path, payload: list[dict[str, Any]]) -> None:
        path.write_text(json.dumps(payload, indent=2, default=str))

    def list_workspaces(self) -> list[dict[str, Any]]:
        return self._read_json(self.workspaces_path)

    def create_workspace(self, name: str, description: str) -> dict[str, Any]:
        payload = self._read_json(self.workspaces_path)
        workspace = {
            "workspace_id": f"ws-{uuid4().hex[:10]}",
            "name": name,
            "description": description,
        }
        payload.append(workspace)
        self._write_json(self.workspaces_path, payload)
        return workspace

    def list_runs(self) -> list[dict[str, Any]]:
        return sorted(self._read_json(self.runs_path), key=lambda item: item["created_at"], reverse=True)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return next((item for item in self._read_json(self.runs_path) if item["run_id"] == run_id), None)

    def create_run(self, run: dict[str, Any]) -> dict[str, Any]:
        payload = self._read_json(self.runs_path)
        payload.append(run)
        self._write_json(self.runs_path, payload)
        return run

    def update_run(self, run_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        payload = self._read_json(self.runs_path)
        updated = None
        for item in payload:
            if item["run_id"] == run_id:
                item.update(updates)
                updated = item
                break
        if updated is None:
            raise KeyError(run_id)
        self._write_json(self.runs_path, payload)
        return updated

    def get_artifact_dir(self, run_id: str) -> Path:
        path = self.artifacts_dir / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path
