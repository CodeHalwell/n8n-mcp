from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional, Union

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from client.n8n_client import N8nClient
from core.builder import WorkflowBuilder
from core.config import Settings
from core.specs import WorkflowSpec
from core.validator import validate_workflow
from mcp_server.utils import get_workflow_by_identifier, workflow_id_or_raise


app = FastAPI(title="n8n-mcp")
_settings = Settings.load_from_env()
_builder = WorkflowBuilder()


class CreateWorkflowRequest(BaseModel):
    spec: WorkflowSpec
    dry_run: bool = True
    commit: bool = False
    activate: bool = False


class UpdateWorkflowRequest(BaseModel):
    identifier: str
    patch: Dict[str, Any]


class ExecuteWorkflowRequest(BaseModel):
    identifier: str
    payload: Optional[Dict[str, Any]] = None


def _client() -> N8nClient:
    return N8nClient(_settings)


@asynccontextmanager
async def n8n_client_manager() -> AsyncIterator[N8nClient]:
    """FastAPI dependency for managing N8nClient lifecycle."""
    client = _client()
    try:
        yield client
    finally:
        await client.close()


def _workflow_id(workflow: Dict[str, Any]) -> Union[str, int]:
    """Legacy wrapper for backward compatibility."""
    return workflow_id_or_raise(
        workflow, 
        lambda msg: HTTPException(status_code=502, detail=msg)
    )


@app.get("/health")
async def health(client: N8nClient = Depends(n8n_client_manager)) -> Dict[str, Any]:
    info = await client.health()
    return {"status": "ok", "info": info}


@app.post("/tools/create_workflow")
async def create_workflow(
    req: CreateWorkflowRequest,
    client: N8nClient = Depends(n8n_client_manager)
) -> Dict[str, Any]:
    spec = req.spec
    errors = validate_workflow(spec)
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    workflow_json = _builder.build(spec)
    if req.dry_run and not req.commit:
        return {"validated": True, "workflow": workflow_json}

    existing = await client.list_workflows()
    existing_names = [wf.get("name") for wf in existing]
    if spec.name in existing_names:
        raise HTTPException(status_code=409, detail="workflow name already exists")
    created = await client.create_workflow(workflow_json)
    if req.activate:
        await client.set_activation(_workflow_id(created), True)
    return {"validated": True, "workflow": created}


@app.post("/tools/update_workflow")
async def update_workflow(
    req: UpdateWorkflowRequest,
    client: N8nClient = Depends(n8n_client_manager)
) -> Dict[str, Any]:
    workflow = await get_workflow_by_identifier(client, req.identifier)
    updated = await client.update_workflow(_workflow_id(workflow), req.patch)
    return {"updated": updated}


@app.get("/tools/list_workflows")
async def list_workflows(client: N8nClient = Depends(n8n_client_manager)) -> Dict[str, Any]:
    workflows = await client.list_workflows()
    return {"workflows": workflows}


@app.get("/tools/get_workflow/{identifier}")
async def get_workflow(
    identifier: str,
    client: N8nClient = Depends(n8n_client_manager)
) -> Dict[str, Any]:
    workflow = await get_workflow_by_identifier(client, identifier)
    full = await client.get_workflow(_workflow_id(workflow))
    return {"workflow": full}


@app.post("/tools/execute_workflow")
async def execute_workflow(
    req: ExecuteWorkflowRequest,
    client: N8nClient = Depends(n8n_client_manager)
) -> Dict[str, Any]:
    workflow = await get_workflow_by_identifier(client, req.identifier)
    result = await client.execute_workflow(_workflow_id(workflow), req.payload or {})
    return {"result": result}
