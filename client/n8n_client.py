from __future__ import annotations

import httpx
from typing import Any, Dict, List, Optional, Union, cast

from core.config import Settings


class N8nClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = f"{settings.n8n_api_url}/api/v1"
        self._headers = {"X-N8N-API-KEY": settings.n8n_api_key}
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    # Health & Info
    async def health(self) -> Dict[str, Any]:
        resp = await self._client.get("/health")
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())

    # Workflows
    async def list_workflows(self) -> List[Dict[str, Any]]:
        resp = await self._client.get("/workflows")
        resp.raise_for_status()
        data = cast(Dict[str, Any], resp.json())
        raw = data.get("data", [])
        return [cast(Dict[str, Any], item) for item in raw]

    async def get_workflow(self, workflow_id: Union[str, int]) -> Dict[str, Any]:
        resp = await self._client.get(f"/workflows/{workflow_id}")
        resp.raise_for_status()
        payload = cast(Dict[str, Any], resp.json())
        inner = payload.get("data")
        if isinstance(inner, dict):
            return inner
        return payload

    async def create_workflow(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        resp = await self._client.post("/workflows", json=workflow_json)
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())

    async def update_workflow(
        self, workflow_id: Union[str, int], patch: Dict[str, Any]
    ) -> Dict[str, Any]:
        resp = await self._client.patch(f"/workflows/{workflow_id}", json=patch)
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())

    async def delete_workflow(self, workflow_id: Union[str, int]) -> Dict[str, Any]:
        resp = await self._client.delete(f"/workflows/{workflow_id}")
        resp.raise_for_status()
        return {"status": "deleted", "id": workflow_id}

    async def set_activation(
        self, workflow_id: Union[str, int], active: bool
    ) -> Dict[str, Any]:
        endpoint = "activate" if active else "deactivate"
        resp = await self._client.post(f"/workflows/{workflow_id}/{endpoint}")
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())

    async def execute_workflow(
        self, workflow_id: Union[str, int], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        resp = await self._client.post(
            f"/workflows/{workflow_id}/run",
            json=payload,
        )
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())

    # Executions
    async def list_executions(
        self, workflow_id: Optional[Union[str, int]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List workflow executions, optionally filtered by workflow_id."""
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = str(workflow_id)
        resp = await self._client.get("/executions", params=params)
        resp.raise_for_status()
        data = cast(Dict[str, Any], resp.json())
        raw = data.get("data", [])
        return [cast(Dict[str, Any], item) for item in raw]

    async def get_execution(self, execution_id: Union[str, int]) -> Dict[str, Any]:
        """Get detailed information about a specific execution."""
        resp = await self._client.get(f"/executions/{execution_id}")
        resp.raise_for_status()
        payload = cast(Dict[str, Any], resp.json())
        inner = payload.get("data")
        if isinstance(inner, dict):
            return inner
        return payload

    async def delete_execution(self, execution_id: Union[str, int]) -> Dict[str, Any]:
        """Delete an execution."""
        resp = await self._client.delete(f"/executions/{execution_id}")
        resp.raise_for_status()
        return {"status": "deleted", "id": execution_id}

    # Credentials
    async def list_credentials(self, credential_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all credentials, optionally filtered by type."""
        params = {}
        if credential_type:
            params["type"] = credential_type
        resp = await self._client.get("/credentials", params=params)
        resp.raise_for_status()
        data = cast(Dict[str, Any], resp.json())
        raw = data.get("data", [])
        return [cast(Dict[str, Any], item) for item in raw]

    async def get_credential(self, credential_id: Union[str, int]) -> Dict[str, Any]:
        """Get a specific credential (without sensitive data)."""
        resp = await self._client.get(f"/credentials/{credential_id}")
        resp.raise_for_status()
        payload = cast(Dict[str, Any], resp.json())
        inner = payload.get("data")
        if isinstance(inner, dict):
            return inner
        return payload

    async def create_credential(self, credential_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new credential."""
        resp = await self._client.post("/credentials", json=credential_data)
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())

    async def update_credential(
        self, credential_id: Union[str, int], credential_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing credential."""
        resp = await self._client.patch(f"/credentials/{credential_id}", json=credential_data)
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())

    async def delete_credential(self, credential_id: Union[str, int]) -> Dict[str, Any]:
        """Delete a credential."""
        resp = await self._client.delete(f"/credentials/{credential_id}")
        resp.raise_for_status()
        return {"status": "deleted", "id": credential_id}

    # Node Types
    async def list_node_types(self) -> List[Dict[str, Any]]:
        """List all available node types in the n8n instance."""
        resp = await self._client.get("/node-types")
        resp.raise_for_status()
        data = cast(Dict[str, Any], resp.json())
        raw = data.get("data", [])
        return [cast(Dict[str, Any], item) for item in raw]

    async def get_node_type(self, node_type: str) -> Dict[str, Any]:
        """Get detailed information about a specific node type."""
        # URL encode the node type name
        encoded_type = node_type.replace(".", "%2E")
        resp = await self._client.get(f"/node-types/{encoded_type}")
        resp.raise_for_status()
        payload = cast(Dict[str, Any], resp.json())
        inner = payload.get("data")
        if isinstance(inner, dict):
            return inner
        return payload

    # Tags
    async def list_tags(self) -> List[Dict[str, Any]]:
        """List all tags."""
        resp = await self._client.get("/tags")
        resp.raise_for_status()
        data = cast(Dict[str, Any], resp.json())
        raw = data.get("data", [])
        return [cast(Dict[str, Any], item) for item in raw]

    async def create_tag(self, name: str) -> Dict[str, Any]:
        """Create a new tag."""
        resp = await self._client.post("/tags", json={"name": name})
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())