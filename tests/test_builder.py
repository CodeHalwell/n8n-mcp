from __future__ import annotations

from core.specs import WorkflowSpec, NodeSpec, ConnectionSpec
from core.builder import WorkflowBuilder


def test_minimal_webhook_http() -> None:
    spec = WorkflowSpec(
        name="Webhook to HTTP",
        nodes=[
            NodeSpec(
                name="Webhook",
                type="n8n-nodes-base.webhook",
                parameters={"path": "test", "httpMethod": "POST"},
            ),
            NodeSpec(
                name="HTTP Request",
                type="n8n-nodes-base.httpRequest",
                parameters={"url": "https://example.com", "method": "GET"},
            ),
        ],
        connections=[ConnectionSpec(fromNode="Webhook", toNode="HTTP Request")],
    )
    builder = WorkflowBuilder()
    wf = builder.build(spec)
    assert wf["name"] == spec.name
    assert "Webhook" in wf["connections"]
    conn = wf["connections"]["Webhook"]["main"][0][0]
    assert conn["node"] == "HTTP Request"
    assert conn["type"] == "main"
    assert conn["index"] == 0
