from __future__ import annotations

from typing import Dict, List, Optional, Set

from core.specs import NodeSpec, WorkflowSpec


class ValidationError(Exception):
    pass


def validate_workflow(
    spec: WorkflowSpec,
    existing_names: Optional[List[str]] = None,
    overwrite: bool = False,
    strict_node_validation: bool = False,
    available_node_types: Optional[Set[str]] = None,
) -> List[str]:
    """
    Validate a workflow specification.

    Args:
        spec: The workflow specification to validate
        existing_names: List of existing workflow names to check for duplicates
        overwrite: Whether overwriting existing workflows is allowed
        strict_node_validation: If True, validate against available_node_types
        available_node_types: Set of node types available in the n8n instance

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: List[str] = []

    # Basic validation
    if not spec.name:
        errors.append("workflow.name is required")
    if not spec.nodes:
        errors.append("workflow.nodes must be non-empty")

    # Allow workflows without connections (single node workflows)
    # But validate connections if they exist

    if existing_names and spec.name in existing_names and not overwrite:
        errors.append("workflow.name must be unique or overwrite allowed")

    node_names: Set[str] = {node.name for node in spec.nodes}

    # Validate node names are unique
    if len(node_names) != len(spec.nodes):
        errors.append("node names must be unique within a workflow")

    # Validate connections
    for conn in spec.connections:
        if conn.fromNode not in node_names or conn.toNode not in node_names:
            errors.append(
                f"connection references missing nodes: {conn.fromNode} -> {conn.toNode}"
            )
        if conn.fromNode == conn.toNode:
            errors.append(f"self-connection not allowed: {conn.fromNode}")

    # Validate nodes
    for node in spec.nodes:
        # Only validate node types if strict validation is enabled
        if strict_node_validation and available_node_types:
            if node.type not in available_node_types:
                errors.append(
                    f"node.type '{node.type}' not available in n8n instance. "
                    f"Node: {node.name}"
                )

        # Basic node validation - ensure required fields are present
        if not node.name:
            errors.append("node.name is required for all nodes")
        if not node.type:
            errors.append(f"node.type is required for node: {node.name}")

        # Validate parameters exist (but don't validate specific params)
        if node.parameters is None:
            errors.append(f"node.parameters should be a dict for node: {node.name}")

    return errors


def get_node_info(node_type: str) -> Optional[Dict[str, str]]:
    """
    Get basic information about a node type.

    This is a simple helper that provides hints for common node types.
    For comprehensive information, use the n8n API or documentation.

    Returns:
        Dictionary with 'description' and 'docs_url' or None
    """
    # Common node information for reference
    common_nodes = {
        "n8n-nodes-base.webhook": {
            "description": "Receives data via webhook HTTP endpoint",
            "docs_url": "https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/"
        },
        "n8n-nodes-base.httpRequest": {
            "description": "Makes HTTP requests to any URL",
            "docs_url": "https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/"
        },
        "n8n-nodes-base.code": {
            "description": "Run custom JavaScript or Python code",
            "docs_url": "https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.code/"
        },
        "n8n-nodes-base.set": {
            "description": "Set values on items",
            "docs_url": "https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.set/"
        },
        "n8n-nodes-base.if": {
            "description": "Conditional routing of items",
            "docs_url": "https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if/"
        },
        "n8n-nodes-base.switch": {
            "description": "Route items to different branches based on rules",
            "docs_url": "https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.switch/"
        },
    }
    return common_nodes.get(node_type)
