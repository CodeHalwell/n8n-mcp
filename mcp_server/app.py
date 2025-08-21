from __future__ import annotations
import json
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from builder.models import WorkflowSpec, validate_workflow
from builder.config import Settings
from n8n_client.client import N8NClient, N8NClientConfig, APIError

app = FastAPI(title="n8n-mcp")

class CreateWorkflowRequest(BaseModel):
    spec: WorkflowSpec
    dry_run: bool = True
    commit: bool = False

class UpdateWorkflowRequest(BaseModel):
    workflow_id: str
    spec: WorkflowSpec
    dry_run: bool = True
    commit: bool = False

class SimpleId(BaseModel):
    id: str

# Initialize client from env
settings = Settings.from_env()
client = N8NClient(N8NClientConfig(base_url=str(settings.n8n_api_url), api_key=settings.n8n_api_key, timeout=settings.http_timeout))

@app.get("/health")
def health():
    return {"status": "ok", "env": settings.n8n_env}

@app.post("/tools/create_workflow")
def create_workflow(req: CreateWorkflowRequest):
    try:
        n8n_json = validate_workflow(req.spec)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if req.dry_run and not req.commit:
    return {"validated": True, "n8n": n8n_json.model_dump()}  # type: ignore
    try:
        created = client.create_workflow(n8n_json.model_dump())
        return {"validated": True, "created": created}
    except APIError as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/tools/update_workflow")
def update_workflow(req: UpdateWorkflowRequest):
    try:
        n8n_json = validate_workflow(req.spec)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if req.dry_run and not req.commit:
    return {"validated": True, "n8n": n8n_json.model_dump()}  # type: ignore
    try:
        updated = client.update_workflow(req.workflow_id, n8n_json.model_dump())
        return {"validated": True, "updated": updated}
    except APIError as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/tools/list_workflows")
def list_workflows():
    try:
        return client.list_workflows()
    except APIError as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/tools/get_workflow/{workflow_id}")
def get_workflow(workflow_id: str):
    try:
        return client.get_workflow(workflow_id)
    except APIError as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/tools/activate_workflow")
def activate_workflow(body: SimpleId):
    try:
        return client.activate_workflow(body.id, True)
    except APIError as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/tools/deactivate_workflow")
def deactivate_workflow(body: SimpleId):
    try:
        return client.activate_workflow(body.id, False)
    except APIError as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/tools/execute_workflow")
def execute_workflow(body: Dict[str, Any]):
    try:
        workflow_id = body.get("id")
        payload = body.get("payload")
        if not workflow_id:
            raise HTTPException(status_code=400, detail="Missing 'id'")
        return client.execute_workflow(workflow_id, payload)
    except APIError as e:
        raise HTTPException(status_code=502, detail=str(e))
