from __future__ import annotations

from typing import Any, Dict

import pytest
from pytest import MonkeyPatch


@pytest.mark.asyncio
async def test_execute_workflow_tool_runs_client(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("N8N_API_URL", "https://example.com")
    monkeypatch.setenv("N8N_API_KEY", "dummy")

    from importlib import reload
    from mcp_server import server

    reload(server)

    calls: Dict[str, object] = {}

    class DummyClient:
        def __init__(self, settings: object) -> None:  # pragma: no cover - simple holder
            calls["settings"] = settings

        async def list_workflows(self) -> list[Dict[str, str]]:
            return [{"id": "1", "name": "Example"}]

        async def execute_workflow(
            self, workflow_id: str, payload: Dict[str, Any]
        ) -> Dict[str, str]:
            calls["executed"] = (workflow_id, payload)
            return {"status": "ok"}

        async def close(self) -> None:
            calls["closed"] = True

    monkeypatch.setattr(server, "N8nClient", DummyClient)

    result = await server.execute_workflow_action("Example", {"foo": "bar"})
    assert calls["executed"] == ("1", {"foo": "bar"})
    assert calls.get("closed") is True

    assert result["workflow"]["status"] == "ok"
