from __future__ import annotations

from typing import List, Set

from core.specs import NodeSpec, WorkflowSpec


SUPPORTED_NODE_TYPES: Set[str] = {
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.cron",
    "n8n-nodes-base.if",
    "n8n-nodes-base.switch",
    "n8n-nodes-base.function",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.slack",
    "n8n-nodes-base.discord",
    "n8n-nodes-base.postgres",
    "n8n-nodes-base.notion",
    "n8n-nodes-base.airtable",
}


class ValidationError(Exception):
    pass


def validate_workflow(
    spec: WorkflowSpec,
    existing_names: List[str] | None = None,
    overwrite: bool = False,
) -> List[str]:
    errors: List[str] = []
    if not spec.name:
        errors.append("workflow.name is required")
    if not spec.nodes:
        errors.append("workflow.nodes must be non-empty")
    if not spec.connections:
        errors.append("workflow.connections must be non-empty")

    if existing_names and spec.name in existing_names and not overwrite:
        errors.append("workflow.name must be unique or overwrite allowed")

    node_names: Set[str] = {node.name for node in spec.nodes}
    for conn in spec.connections:
        if conn.fromNode not in node_names or conn.toNode not in node_names:
            errors.append(
                f"connection references missing nodes: {conn.fromNode} -> {conn.toNode}"
            )
        if conn.fromNode == conn.toNode:
            errors.append(f"self-connection not allowed by default: {conn.fromNode}")

    for node in spec.nodes:
        if node.type not in SUPPORTED_NODE_TYPES:
            errors.append(f"unsupported node.type: {node.type}")
        else:
            missing = _required_params_missing(node)
            if missing:
                errors.append(
                    f"node {node.name} missing required parameters: {', '.join(sorted(missing))}"
                )

    return errors


def _required_params_missing(node: NodeSpec) -> List[str]:
    missing: List[str] = []
    if node.type == "n8n-nodes-base.webhook":
        for key in ("path", "httpMethod"):
            if key not in node.parameters:
                missing.append(key)
    elif node.type == "n8n-nodes-base.cron":
        if "triggerTimes" not in node.parameters:
            missing.append("triggerTimes")
    elif node.type == "n8n-nodes-base.if":
        if "conditions" not in node.parameters:
            missing.append("conditions")
    elif node.type == "n8n-nodes-base.function":
        if "functionCode" not in node.parameters:
            missing.append("functionCode")
    elif node.type == "n8n-nodes-base.httpRequest":
        for key in ("url", "method"):
            if key not in node.parameters:
                missing.append(key)
    elif node.type in {"n8n-nodes-base.slack", "n8n-nodes-base.discord"}:
        for key in ("resource", "operation"):
            if key not in node.parameters:
                missing.append(key)
    elif node.type == "n8n-nodes-base.postgres":
        if "operation" not in node.parameters:
            missing.append("operation")
    elif node.type == "n8n-nodes-base.notion":
        for key in ("resource", "operation"):
            if key not in node.parameters:
                missing.append(key)
    elif node.type == "n8n-nodes-base.airtable":
        if "operation" not in node.parameters:
            missing.append("operation")
    return missing
