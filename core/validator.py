from __future__ import annotations

from typing import Any, Dict, List, Set

from core.specs import WorkflowSpec, NodeSpec, ConnectionSpec


SUPPORTED_NODE_TYPES = {
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


def validate_workflow(spec: WorkflowSpec, existing_names: List[str] | None = None, overwrite: bool = False) -> List[str]:
	errors: List[str] = []
	if not spec.name:
		errors.append("workflow.name is required")
	if not spec.nodes:
		errors.append("workflow.nodes must be non-empty")
	if not spec.connections:
		errors.append("workflow.connections must be non-empty")

	# uniqueness check
	if existing_names and spec.name in existing_names and not overwrite:
		errors.append("workflow.name must be unique or overwrite allowed")

	node_names: Set[str] = {n.name for n in spec.nodes}
	for conn in spec.connections:
		if conn.fromNode not in node_names or conn.toNode not in node_names:
			errors.append(f"connection references missing nodes: {conn.fromNode} -> {conn.toNode}")
		if conn.fromNode == conn.toNode:
			errors.append(f"self-connection not allowed by default: {conn.fromNode}")

	# node types and required params minimal checks
	for node in spec.nodes:
		if node.type not in SUPPORTED_NODE_TYPES:
			errors.append(f"unsupported node.type: {node.type}")
		else:
			_missing = _required_params_missing(node)
			if _missing:
				errors.append(f"node {node.name} missing required parameters: {', '.join(sorted(_missing))}")

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
	elif node.type == "n8n-nodes-base.slack":
		if "resource" not in node.parameters or "operation" not in node.parameters:
			missing.extend([k for k in ("resource", "operation") if k not in node.parameters])
	elif node.type == "n8n-nodes-base.discord":
		if "resource" not in node.parameters or "operation" not in node.parameters:
			missing.extend([k for k in ("resource", "operation") if k not in node.parameters])
	elif node.type == "n8n-nodes-base.postgres":
		if "operation" not in node.parameters:
			missing.append("operation")
	elif node.type == "n8n-nodes-base.notion":
		if "resource" not in node.parameters or "operation" not in node.parameters:
			missing.extend([k for k in ("resource", "operation") if k not in node.parameters])
	elif node.type == "n8n-nodes-base.airtable":
		if "operation" not in node.parameters:
			missing.append("operation")
	return missing