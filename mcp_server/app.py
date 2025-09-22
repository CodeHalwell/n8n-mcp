from __future__ import annotations

from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from client.n8n_client import N8nClient
from core.builder import WorkflowBuilder
from core.config import Settings
from core.specs import WorkflowSpec
from core.validator import validate_workflow


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


def _workflow_id(workflow: Dict[str, Any]) -> Union[str, int]:
    identifier = workflow.get("id")
    if isinstance(identifier, (str, int)):
        return identifier
    raise HTTPException(status_code=502, detail="workflow id missing from n8n response")


@app.get("/health")
async def health() -> Dict[str, Any]:
    client = _client()
    try:
        info = await client.health()
        return {"status": "ok", "info": info}
    finally:
        await client.close()


@app.post("/tools/create_workflow")
async def create_workflow(req: CreateWorkflowRequest) -> Dict[str, Any]:
    spec = req.spec
    errors = validate_workflow(spec)
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    workflow_json = _builder.build(spec)
    if req.dry_run and not req.commit:
        return {"validated": True, "workflow": workflow_json}

    client = _client()
    try:
        existing = await client.list_workflows()
        existing_names = [wf.get("name") for wf in existing]
        if spec.name in existing_names:
            raise HTTPException(status_code=409, detail="workflow name already exists")
        created = await client.create_workflow(workflow_json)
        if req.activate:
            await client.set_activation(_workflow_id(created), True)
        return {"validated": True, "workflow": created}
    finally:
        await client.close()


@app.post("/tools/update_workflow")
async def update_workflow(req: UpdateWorkflowRequest) -> Dict[str, Any]:
    client = _client()
    try:
        workflows = await client.list_workflows()
        workflow = next(
            (
                wf
                for wf in workflows
                if str(wf.get("id")) == req.identifier or wf.get("name") == req.identifier
            ),
            None,
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="workflow not found")
        updated = await client.update_workflow(_workflow_id(workflow), req.patch)
        return {"updated": updated}
    finally:
        await client.close()


@app.get("/tools/list_workflows")
async def list_workflows() -> Dict[str, Any]:
    client = _client()
    try:
        workflows = await client.list_workflows()
        return {"workflows": workflows}
    finally:
        await client.close()


@app.get("/tools/get_workflow/{identifier}")
async def get_workflow(identifier: str) -> Dict[str, Any]:
    client = _client()
    try:
        workflows = await client.list_workflows()
        workflow = next(
            (
                wf
                for wf in workflows
                if str(wf.get("id")) == identifier or wf.get("name") == identifier
            ),
            None,
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="workflow not found")
        full = await client.get_workflow(_workflow_id(workflow))
        return {"workflow": full}
    finally:
        await client.close()


@app.post("/tools/execute_workflow")
async def execute_workflow(req: ExecuteWorkflowRequest) -> Dict[str, Any]:
    client = _client()
    try:
        workflows = await client.list_workflows()
        workflow = next(
            (
                wf
                for wf in workflows
                if str(wf.get("id")) == req.identifier or wf.get("name") == req.identifier
            ),
            None,
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="workflow not found")
        result = await client.execute_workflow(_workflow_id(workflow), req.payload or {})
        return {"result": result}
    finally:
        await client.close()
