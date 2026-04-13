from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import CompareRequest, ResearchRunRequest, WorkspaceRequest
from app.service import QuantResearchService


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
service = QuantResearchService()

app = FastAPI(title="Quant Research Lab")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/system")
def system() -> dict[str, object]:
    return service.system_status()


@app.get("/api/scenarios")
def scenarios() -> list[dict[str, object]]:
    return service.list_scenarios()


@app.get("/api/public-datasets")
def public_datasets() -> list[dict[str, object]]:
    return service.list_public_datasets()


@app.get("/api/public-resources")
def public_resources() -> list[dict[str, str]]:
    return service.list_public_resources()


@app.get("/api/platform")
def platform() -> dict[str, object]:
    return service.platform()


@app.get("/api/workspaces")
def workspaces() -> list[dict[str, object]]:
    return service.list_workspaces()


@app.post("/api/workspaces")
def create_workspace(request: WorkspaceRequest) -> dict[str, object]:
    return service.create_workspace(name=request.name, description=request.description)


@app.get("/api/overview")
def overview() -> dict[str, object]:
    return service.overview()


@app.get("/api/runs")
def list_runs() -> list[dict[str, object]]:
    return service.list_runs()


@app.post("/api/runs")
def create_run(request: ResearchRunRequest) -> dict[str, object]:
    try:
        return service.run_research(
            scenario_id=request.scenario_id,
            seed=request.seed,
            workspace_id=request.workspace_id,
            label=request.label,
            dataset_id=request.dataset_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown scenario or run: {exc}") from exc


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    try:
        return service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc


@app.post("/api/runs/{run_id}/replay")
def replay_run(run_id: str) -> dict[str, object]:
    try:
        return service.replay_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc


@app.post("/api/compare")
def compare_runs(request: CompareRequest) -> dict[str, object]:
    try:
        return service.compare_runs(request.run_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {exc}") from exc


@app.get("/api/artifacts/{run_id}/{artifact_name}")
def get_artifact(run_id: str, artifact_name: str) -> FileResponse:
    try:
        run = service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
    artifact_path = run["artifacts"].get(artifact_name)
    if artifact_path is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_name}")
    return FileResponse(artifact_path)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
