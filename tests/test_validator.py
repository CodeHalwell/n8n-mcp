from __future__ import annotations

from core.specs import WorkflowSpec, NodeSpec, ConnectionSpec
from core.validator import validate_workflow


def test_missing_name() -> None:
    spec = WorkflowSpec(name="", nodes=[], connections=[])
    errors = validate_workflow(spec)
    assert any("workflow.name is required" in e for e in errors)


def test_basic_webhook_flow_validates() -> None:
    spec = WorkflowSpec(
        name="t",
        nodes=[
            NodeSpec(
                name="Webhook",
                type="n8n-nodes-base.webhook",
                parameters={"path": "p", "httpMethod": "POST"},
            ),
            NodeSpec(
                name="Code",
                type="n8n-nodes-base.function",
                parameters={"functionCode": "return items;"},
            ),
        ],
        connections=[ConnectionSpec(fromNode="Webhook", toNode="Code")],
    )
    errors = validate_workflow(spec)
    assert errors == []