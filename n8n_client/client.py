from __future__ import annotations
from typing import Any, Dict, List, Optional
import requests
from pydantic import BaseModel

class APIError(Exception):
    pass

class N8NClientConfig(BaseModel):
    base_url: str
    api_key: str
    timeout: int = 30

class N8NClient:
    def __init__(self, config: N8NClientConfig):
        self.base_url = config.base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-N8N-API-KEY": config.api_key,
        })
        self.timeout = config.timeout

    # Workflows
    def create_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(f"{self.base_url}/workflows", json=workflow, timeout=self.timeout)
        if resp.status_code >= 400:
            raise APIError(f"create_workflow failed: {resp.status_code} {resp.text}")
        return resp.json()

    def update_workflow(self, workflow_id: str, workflow: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.patch(f"{self.base_url}/workflows/{workflow_id}", json=workflow, timeout=self.timeout)
        if resp.status_code >= 400:
            raise APIError(f"update_workflow failed: {resp.status_code} {resp.text}")
        return resp.json()

    def list_workflows(self, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = filter or {}
        resp = self.session.get(f"{self.base_url}/workflows", params=params, timeout=self.timeout)
        if resp.status_code >= 400:
            raise APIError(f"list_workflows failed: {resp.status_code} {resp.text}")
        return resp.json()

    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        resp = self.session.get(f"{self.base_url}/workflows/{workflow_id}", timeout=self.timeout)
        if resp.status_code >= 400:
            raise APIError(f"get_workflow failed: {resp.status_code} {resp.text}")
        return resp.json()

    def activate_workflow(self, workflow_id: str, active: bool = True) -> Dict[str, Any]:
        # n8n: POST /workflows/{id}/activate or deactivate; some versions patch 'active'
        path = "activate" if active else "deactivate"
        resp = self.session.post(f"{self.base_url}/workflows/{workflow_id}/{path}", timeout=self.timeout)
        if resp.status_code >= 400:
            raise APIError(f"activate/deactivate failed: {resp.status_code} {resp.text}")
        return resp.json() if resp.text else {"status": "ok"}

    def execute_workflow(self, workflow_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Some n8n versions support manual execution via /workflows/{id}/run or via /execute-webhook
        # Here we try a generic run endpoint; adjust as needed per n8n version.
        resp = self.session.post(f"{self.base_url}/workflows/{workflow_id}/run", json=payload or {}, timeout=self.timeout)
        if resp.status_code >= 400:
            raise APIError(f"execute_workflow failed: {resp.status_code} {resp.text}")
        return resp.json() if resp.text else {"status": "queued"}
