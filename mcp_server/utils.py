"""Shared utilities for MCP server modules."""
from __future__ import annotations

from typing import Any, Callable, Dict, Union

from fastapi import HTTPException

from client.n8n_client import N8nClient


def workflow_id_or_raise(
    workflow: Dict[str, Any],
    raise_fn: Callable[[str], Exception] = ValueError,
) -> Union[str, int]:
    """Extract workflow ID from workflow dict with configurable error handling.
    
    Args:
        workflow: Workflow dict from n8n API
        raise_fn: Function to create exception with error message
        
    Returns:
        Workflow ID as string or int
        
    Raises:
        Exception created by raise_fn if ID is missing or invalid
    """
    identifier = workflow.get("id")
    if isinstance(identifier, (str, int)):
        return identifier
    raise raise_fn("workflow response missing id")


async def get_workflow_by_identifier(client: N8nClient, identifier: str) -> Dict[str, Any]:
    """Find workflow by ID or name.
    
    Args:
        client: N8n client instance
        identifier: Workflow ID or name to search for
        
    Returns:
        Workflow dict from n8n API
        
    Raises:
        HTTPException: 404 if workflow not found
    """
    workflows = await client.list_workflows()
    workflow = next(
        (
            wf
            for wf in workflows
            if str(wf.get("id")) == identifier or wf.get("name") == identifier
        ),
        None,
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="workflow not found")
    return workflow