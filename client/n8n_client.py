from __future__ import annotations

import httpx
from typing import Any, Dict, List, Optional, Union

from core.config import Settings


class N8nClient:
	def __init__(self, settings: Settings) -> None:
		self._base_url = f"{settings.n8n_api_url}/api/v1"
		self._headers = {"X-N8N-API-KEY": settings.n8n_api_key}
		self._client = httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=30.0)

	async def close(self) -> None:
		await self._client.aclose()

	async def health(self) -> Dict[str, Any]:
		resp = await self._client.get("/health")
		resp.raise_for_status()
		return resp.json()

	async def list_workflows(self) -> List[Dict[str, Any]]:
		resp = await self._client.get("/workflows")
		resp.raise_for_status()
		return resp.json().get("data", [])

	async def get_workflow(self, workflow_id: Union[str, int]) -> Dict[str, Any]:
		resp = await self._client.get(f"/workflows/{workflow_id}")
		resp.raise_for_status()
		return resp.json().get("data") or resp.json()

	async def create_workflow(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
		resp = await self._client.post("/workflows", json=workflow_json)
		resp.raise_for_status()
		return resp.json()

	async def update_workflow(self, workflow_id: Union[str, int], patch: Dict[str, Any]) -> Dict[str, Any]:
		resp = await self._client.patch(f"/workflows/{workflow_id}", json=patch)
		resp.raise_for_status()
		return resp.json()

	async def set_activation(self, workflow_id: Union[str, int], active: bool) -> Dict[str, Any]:
		endpoint = "activate" if active else "deactivate"
		resp = await self._client.post(f"/workflows/{workflow_id}/{endpoint}")
		resp.raise_for_status()
		return resp.json()