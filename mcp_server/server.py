from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Union, cast

from mcp.server import Server, stdio_server
from mcp.types import TextContent, Tool

from client.n8n_client import N8nClient
from core.builder import WorkflowBuilder
from core.cache import node_type_cache
from core.config import Settings
from core.logging import audit_log, configure_logging
from core.metrics import metrics_collector
from core.rate_limiter import RateLimiter
from core.specs import WorkflowSpec
from core.validator import validate_workflow
from mcp_server.utils import workflow_id_or_raise


server = Server("n8n-workflow-builder")
_settings = Settings.load_from_env()
configure_logging(_settings.log_level, _settings.audit_log_path)
rate_limiter = RateLimiter(_settings.rate_limit_per_minute)
_builder = WorkflowBuilder()


@asynccontextmanager
async def _client() -> AsyncIterator[N8nClient]:
    client = N8nClient(_settings)
    try:
        yield client
    finally:
        await client.close()


async def _health_check(settings: Settings) -> Dict[str, Any]:
    async with _client() as client:
        info = await client.health()
        server_version = info.get("version") or info.get("data", {}).get("version")
        payload: Dict[str, Any] = {"ok": True, "server_version": server_version}
        if settings.n8n_version and server_version and settings.n8n_version != server_version:
            payload["warning"] = {
                "type": "version_mismatch",
                "configured": settings.n8n_version,
                "server": server_version,
            }
        return payload


async def get_circuit_breaker_stats_action() -> Dict[str, Any]:
    """Get circuit breaker statistics for monitoring."""
    async with _client() as client:
        stats = client.get_circuit_breaker_stats()
        return stats


async def reset_circuit_breaker_action() -> Dict[str, Any]:
    """Manually reset the circuit breaker to closed state."""
    async with _client() as client:
        client.reset_circuit_breaker()
        audit_log("reset_circuit_breaker", actor="mcp", details={})
        return {"status": "reset", "message": "Circuit breaker has been reset to CLOSED state"}


async def get_metrics_action() -> Dict[str, Any]:
    """Get current metrics summary."""
    return metrics_collector.get_summary()


async def get_health_status_action() -> Dict[str, Any]:
    """Get health status with checks."""
    health = metrics_collector.check_health()
    return health.to_dict()


async def reset_metrics_action() -> Dict[str, Any]:
    """Reset all metrics."""
    metrics_collector.reset()
    audit_log("reset_metrics", actor="mcp", details={})
    return {"status": "reset", "message": "All metrics have been reset"}


async def validate_workflow_action(workflow_json: Dict[str, Any]) -> Dict[str, Any]:
    spec = WorkflowSpec(**workflow_json)
    errors = validate_workflow(spec)
    return {"errors": errors}


async def list_workflows_action(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    filters = filters or {}
    async with _client() as client:
        workflows = await client.list_workflows()
        name_contains = filters.get("name_contains")
        active = filters.get("active")
        if name_contains:
            workflows = [
                wf
                for wf in workflows
                if name_contains.lower() in (wf.get("name", "").lower())
            ]
        if active is not None:
            workflows = [
                wf for wf in workflows if bool(wf.get("active")) == bool(active)
            ]
        return {"data": workflows}


async def create_workflow_action(
    spec: Dict[str, Any], options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    options = options or {}
    spec_model = WorkflowSpec(**spec)

    async with _client() as client:
        existing = await client.list_workflows()
        existing_names = [
            cast(str, wf.get("name"))
            for wf in existing
            if isinstance(wf.get("name"), str)
        ]
        errors = validate_workflow(
            spec_model,
            existing_names=existing_names,
            overwrite=bool(options.get("overwrite_if_exists")),
        )
        if errors:
            return {"errors": errors}

        workflow_json = _builder.build(spec_model)
        if options.get("tags"):
            workflow_json["tags"] = options.get("tags")

        if options.get("dry_run"):
            return {"dry_run": True, "workflow": workflow_json}

        if spec_model.name in existing_names and options.get("overwrite_if_exists"):
            target = next(
                wf for wf in existing if wf.get("name") == spec_model.name
            )
            workflow_id = workflow_id_or_raise(target)
            response = await client.update_workflow(workflow_id, workflow_json)
        else:
            response = await client.create_workflow(workflow_json)

        if options.get("activate"):
            await client.set_activation(workflow_id_or_raise(response), True)

        audit_log(
            "create_workflow",
            actor="mcp",
            details={"name": spec_model.name, "id": response.get("id")},
        )
        return {"workflow": response}


async def update_workflow_action(identifier: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    async with _client() as client:
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
            raise ValueError(f"workflow {identifier} not found")
        workflow_id = workflow_id_or_raise(workflow)
        response = await client.update_workflow(workflow_id, patch)
        audit_log("update_workflow", actor="mcp", details={"id": workflow_id})
        return {"workflow": response}


async def get_workflow_action(identifier: str) -> Dict[str, Any]:
    async with _client() as client:
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
            raise ValueError(f"workflow {identifier} not found")
        full = await client.get_workflow(workflow_id_or_raise(workflow))
        return {"workflow": full}


async def activate_workflow_action(identifier: str, active: bool) -> Dict[str, Any]:
    async with _client() as client:
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
            raise ValueError(f"workflow {identifier} not found")
        workflow_id = workflow_id_or_raise(workflow)
        response = await client.set_activation(workflow_id, active)
        audit_log(
            "activate_workflow",
            actor="mcp",
            details={"id": workflow_id, "active": active},
        )
        return {"workflow": response}


async def duplicate_workflow_action(identifier: str, suffix: str) -> Dict[str, Any]:
    async with _client() as client:
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
            raise ValueError(f"workflow {identifier} not found")
        full = await client.get_workflow(workflow_id_or_raise(workflow))
        full["name"] = f"{full.get('name')}{suffix}"
        full.pop("id", None)
        response = await client.create_workflow(full)
        audit_log(
            "duplicate_workflow",
            actor="mcp",
            details={"src": workflow_id_or_raise(workflow), "new": response.get("id")},
        )
        return {"workflow": response}


async def execute_workflow_action(
    identifier: str, payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    async with _client() as client:
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
            raise ValueError(f"workflow {identifier} not found")
        workflow_id = workflow_id_or_raise(workflow)
        response = await client.execute_workflow(workflow_id, payload or {})
        audit_log(
            "execute_workflow",
            actor="mcp",
            details={"id": workflow_id, "payload": payload},
        )
        return {"workflow": response}


async def delete_workflow_action(identifier: str) -> Dict[str, Any]:
    async with _client() as client:
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
            raise ValueError(f"workflow {identifier} not found")
        workflow_id = workflow_id_or_raise(workflow)
        response = await client.delete_workflow(workflow_id)
        audit_log("delete_workflow", actor="mcp", details={"id": workflow_id})
        return response


async def get_webhook_urls_action(identifier: str) -> Dict[str, Any]:
    """Get all webhook URLs for a workflow."""
    async with _client() as client:
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
            raise ValueError(f"workflow {identifier} not found")

        full = await client.get_workflow(workflow_id_or_raise(workflow))

        # Find all webhook nodes
        webhook_nodes = [
            node for node in full.get("nodes", [])
            if node.get("type") == "n8n-nodes-base.webhook"
        ]

        # Build webhook URLs
        urls = []
        for node in webhook_nodes:
            path = node.get("parameters", {}).get("path", "")
            method = node.get("parameters", {}).get("httpMethod", "GET")

            # Construct the webhook URL
            # Format: {n8n_base_url}/webhook/{path}
            base_url = _settings.n8n_api_url.rstrip("/api/v1").rstrip("/")
            webhook_url = f"{base_url}/webhook/{path}"

            urls.append({
                "node_name": node.get("name"),
                "node_id": node.get("id"),
                "path": path,
                "method": method,
                "url": webhook_url,
            })

        return {
            "workflow_id": full.get("id"),
            "workflow_name": full.get("name"),
            "webhook_urls": urls,
            "count": len(urls),
        }


async def bulk_activate_workflows_action(
    identifiers: List[str], active: bool
) -> Dict[str, Any]:
    """Activate or deactivate multiple workflows in parallel."""
    tasks = [activate_workflow_action(identifier, active) for identifier in identifiers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = []
    failures = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failures.append({
                "identifier": identifiers[i],
                "error": str(result),
            })
        else:
            successes.append({
                "identifier": identifiers[i],
                "workflow_id": result.get("workflow", {}).get("id"),
            })

    return {
        "successes": successes,
        "failures": failures,
        "total": len(identifiers),
        "success_count": len(successes),
        "failure_count": len(failures),
    }


async def bulk_delete_workflows_action(identifiers: List[str]) -> Dict[str, Any]:
    """Delete multiple workflows in parallel."""
    tasks = [delete_workflow_action(identifier) for identifier in identifiers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = []
    failures = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failures.append({
                "identifier": identifiers[i],
                "error": str(result),
            })
        else:
            successes.append({
                "identifier": identifiers[i],
                "status": "deleted",
            })

    return {
        "successes": successes,
        "failures": failures,
        "total": len(identifiers),
        "success_count": len(successes),
        "failure_count": len(failures),
    }


# Execution actions
async def list_executions_action(
    workflow_id: Optional[str] = None, limit: int = 100
) -> Dict[str, Any]:
    async with _client() as client:
        executions = await client.list_executions(workflow_id, limit)
        return {"data": executions}


async def get_execution_action(execution_id: str) -> Dict[str, Any]:
    async with _client() as client:
        execution = await client.get_execution(execution_id)
        return {"execution": execution}


async def delete_execution_action(execution_id: str) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.delete_execution(execution_id)
        audit_log("delete_execution", actor="mcp", details={"id": execution_id})
        return response


# Credential actions
async def list_credentials_action(
    credential_type: Optional[str] = None
) -> Dict[str, Any]:
    async with _client() as client:
        credentials = await client.list_credentials(credential_type)
        return {"data": credentials}


async def get_credential_action(credential_id: str) -> Dict[str, Any]:
    async with _client() as client:
        credential = await client.get_credential(credential_id)
        return {"credential": credential}


async def create_credential_action(credential_data: Dict[str, Any]) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.create_credential(credential_data)
        audit_log(
            "create_credential",
            actor="mcp",
            details={"name": credential_data.get("name"), "type": credential_data.get("type")},
        )
        return {"credential": response}


async def update_credential_action(
    credential_id: str, credential_data: Dict[str, Any]
) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.update_credential(credential_id, credential_data)
        audit_log("update_credential", actor="mcp", details={"id": credential_id})
        return {"credential": response}


async def delete_credential_action(credential_id: str) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.delete_credential(credential_id)
        audit_log("delete_credential", actor="mcp", details={"id": credential_id})
        return response


# Node type actions
async def list_node_types_action() -> Dict[str, Any]:
    """List all available node types with caching."""
    # Check cache first
    cached = node_type_cache.get("node_types_list")
    if cached is not None:
        return {"data": cached, "cached": True}

    # Fetch from API if not cached
    async with _client() as client:
        node_types = await client.list_node_types()
        # Store in cache
        node_type_cache.set("node_types_list", node_types)
        return {"data": node_types, "cached": False}


async def get_node_type_action(node_type: str) -> Dict[str, Any]:
    """Get detailed node type information with caching."""
    cache_key = f"node_type:{node_type}"

    # Check cache first
    cached = node_type_cache.get(cache_key)
    if cached is not None:
        return {"node_type": cached, "cached": True}

    # Fetch from API if not cached
    async with _client() as client:
        node_type_info = await client.get_node_type(node_type)
        # Store in cache
        node_type_cache.set(cache_key, node_type_info)
        return {"node_type": node_type_info, "cached": False}


ToolHandler = Callable[[Dict[str, Any]], Awaitable[List[TextContent]]]
_tool_registry: Dict[str, tuple[ToolHandler, Dict[str, Any], str]] = {}


def register_tool(
    name: str, description: str, input_schema: Dict[str, Any]
) -> Callable[[ToolHandler], ToolHandler]:
    def decorator(func: ToolHandler) -> ToolHandler:
        _tool_registry[name] = (func, input_schema, description)
        return func

    return decorator


def _text_payload(payload: Dict[str, Any]) -> List[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload))]


@register_tool(
    "validate_workflow",
    "Validate an n8n workflow specification without touching n8n.",
    {
        "type": "object",
        "properties": {
            "workflow": {"type": "object"},
        },
        "required": ["workflow"],
    },
)
async def validate_workflow_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    workflow = arguments.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("workflow must be an object")
    return _text_payload(await validate_workflow_action(workflow))


@register_tool(
    "list_workflows",
    "List workflows available in the connected n8n instance.",
    {
        "type": "object",
        "properties": {
            "filters": {
                "type": "object",
                "properties": {
                    "name_contains": {"type": "string"},
                    "active": {"type": "boolean"},
                },
            }
        },
    },
)
async def list_workflows_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    filters = arguments.get("filters")
    if filters is not None and not isinstance(filters, dict):
        raise ValueError("filters must be an object if provided")
    return _text_payload(await list_workflows_action(filters))


@register_tool(
    "create_workflow",
    "Create or preview an n8n workflow from a structured specification.",
    {
        "type": "object",
        "properties": {
            "spec": {"type": "object"},
            "options": {"type": "object"},
        },
        "required": ["spec"],
    },
)
async def create_workflow_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    spec = arguments.get("spec")
    options = arguments.get("options")
    if not isinstance(spec, dict):
        raise ValueError("spec must be an object")
    if options is not None and not isinstance(options, dict):
        raise ValueError("options must be an object if provided")
    return _text_payload(await create_workflow_action(spec, options))


@register_tool(
    "update_workflow",
    "Apply a partial update to an existing workflow by id or name.",
    {
        "type": "object",
        "properties": {
            "identifier": {"type": "string"},
            "patch": {"type": "object"},
        },
        "required": ["identifier", "patch"],
    },
)
async def update_workflow_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    identifier = arguments.get("identifier")
    patch = arguments.get("patch")
    if not isinstance(identifier, str):
        raise ValueError("identifier must be a string")
    if not isinstance(patch, dict):
        raise ValueError("patch must be an object")
    return _text_payload(await update_workflow_action(identifier, patch))


@register_tool(
    "get_workflow",
    "Fetch the full JSON of a workflow by id or name.",
    {
        "type": "object",
        "properties": {
            "identifier": {"type": "string"},
        },
        "required": ["identifier"],
    },
)
async def get_workflow_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    identifier = arguments.get("identifier")
    if not isinstance(identifier, str):
        raise ValueError("identifier must be a string")
    return _text_payload(await get_workflow_action(identifier))


@register_tool(
    "activate_workflow",
    "Activate or deactivate a workflow.",
    {
        "type": "object",
        "properties": {
            "identifier": {"type": "string"},
            "active": {"type": "boolean"},
        },
        "required": ["identifier", "active"],
    },
)
async def activate_workflow_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    identifier = arguments.get("identifier")
    active = arguments.get("active")
    if not isinstance(identifier, str):
        raise ValueError("identifier must be a string")
    if not isinstance(active, bool):
        raise ValueError("active must be a boolean")
    return _text_payload(await activate_workflow_action(identifier, active))


@register_tool(
    "duplicate_workflow",
    "Duplicate a workflow with a suffix appended to its name.",
    {
        "type": "object",
        "properties": {
            "identifier": {"type": "string"},
            "suffix": {"type": "string"},
        },
        "required": ["identifier", "suffix"],
    },
)
async def duplicate_workflow_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    identifier = arguments.get("identifier")
    suffix = arguments.get("suffix")
    if not isinstance(identifier, str):
        raise ValueError("identifier must be a string")
    if not isinstance(suffix, str):
        raise ValueError("suffix must be a string")
    return _text_payload(await duplicate_workflow_action(identifier, suffix))


@register_tool(
    "execute_workflow",
    "Execute a workflow by id or name with an optional payload.",
    {
        "type": "object",
        "properties": {
            "identifier": {"type": "string"},
            "payload": {"type": "object"},
        },
        "required": ["identifier"],
    },
)
async def execute_workflow_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    identifier = arguments.get("identifier")
    payload = arguments.get("payload")
    if not isinstance(identifier, str):
        raise ValueError("identifier must be a string")
    if payload is not None and not isinstance(payload, dict):
        raise ValueError("payload must be an object if provided")
    return _text_payload(await execute_workflow_action(identifier, payload))


@register_tool(
    "delete_workflow",
    "Delete a workflow by id or name.",
    {
        "type": "object",
        "properties": {
            "identifier": {"type": "string"},
        },
        "required": ["identifier"],
    },
)
async def delete_workflow_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    identifier = arguments.get("identifier")
    if not isinstance(identifier, str):
        raise ValueError("identifier must be a string")
    return _text_payload(await delete_workflow_action(identifier))


@register_tool(
    "get_webhook_urls",
    "Get all webhook URLs for a workflow. Returns the full webhook endpoints that can be called.",
    {
        "type": "object",
        "properties": {
            "identifier": {"type": "string"},
        },
        "required": ["identifier"],
    },
)
async def get_webhook_urls_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    identifier = arguments.get("identifier")
    if not isinstance(identifier, str):
        raise ValueError("identifier must be a string")
    return _text_payload(await get_webhook_urls_action(identifier))


@register_tool(
    "bulk_activate_workflows",
    "Activate or deactivate multiple workflows in parallel for faster bulk operations.",
    {
        "type": "object",
        "properties": {
            "identifiers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of workflow IDs or names",
            },
            "active": {
                "type": "boolean",
                "description": "True to activate, False to deactivate",
            },
        },
        "required": ["identifiers", "active"],
    },
)
async def bulk_activate_workflows_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    identifiers = arguments.get("identifiers")
    active = arguments.get("active")
    if not isinstance(identifiers, list):
        raise ValueError("identifiers must be an array")
    if not isinstance(active, bool):
        raise ValueError("active must be a boolean")
    return _text_payload(await bulk_activate_workflows_action(identifiers, active))


@register_tool(
    "bulk_delete_workflows",
    "Delete multiple workflows in parallel. Use with caution - this cannot be undone.",
    {
        "type": "object",
        "properties": {
            "identifiers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of workflow IDs or names to delete",
            },
        },
        "required": ["identifiers"],
    },
)
async def bulk_delete_workflows_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    identifiers = arguments.get("identifiers")
    if not isinstance(identifiers, list):
        raise ValueError("identifiers must be an array")
    return _text_payload(await bulk_delete_workflows_action(identifiers))


# Execution tools
@register_tool(
    "list_executions",
    "List workflow executions, optionally filtered by workflow_id.",
    {
        "type": "object",
        "properties": {
            "workflow_id": {"type": "string"},
            "limit": {"type": "integer", "default": 100},
        },
    },
)
async def list_executions_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    workflow_id = arguments.get("workflow_id")
    limit = arguments.get("limit", 100)
    if workflow_id is not None and not isinstance(workflow_id, str):
        raise ValueError("workflow_id must be a string if provided")
    if not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    return _text_payload(await list_executions_action(workflow_id, limit))


@register_tool(
    "get_execution",
    "Get detailed information about a specific execution.",
    {
        "type": "object",
        "properties": {
            "execution_id": {"type": "string"},
        },
        "required": ["execution_id"],
    },
)
async def get_execution_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    execution_id = arguments.get("execution_id")
    if not isinstance(execution_id, str):
        raise ValueError("execution_id must be a string")
    return _text_payload(await get_execution_action(execution_id))


@register_tool(
    "delete_execution",
    "Delete an execution by id.",
    {
        "type": "object",
        "properties": {
            "execution_id": {"type": "string"},
        },
        "required": ["execution_id"],
    },
)
async def delete_execution_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    execution_id = arguments.get("execution_id")
    if not isinstance(execution_id, str):
        raise ValueError("execution_id must be a string")
    return _text_payload(await delete_execution_action(execution_id))


# Credential tools
@register_tool(
    "list_credentials",
    "List all credentials, optionally filtered by credential type.",
    {
        "type": "object",
        "properties": {
            "credential_type": {"type": "string"},
        },
    },
)
async def list_credentials_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    credential_type = arguments.get("credential_type")
    if credential_type is not None and not isinstance(credential_type, str):
        raise ValueError("credential_type must be a string if provided")
    return _text_payload(await list_credentials_action(credential_type))


@register_tool(
    "get_credential",
    "Get a specific credential by id (sensitive data will be redacted).",
    {
        "type": "object",
        "properties": {
            "credential_id": {"type": "string"},
        },
        "required": ["credential_id"],
    },
)
async def get_credential_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    credential_id = arguments.get("credential_id")
    if not isinstance(credential_id, str):
        raise ValueError("credential_id must be a string")
    return _text_payload(await get_credential_action(credential_id))


@register_tool(
    "create_credential",
    "Create a new credential with the specified data.",
    {
        "type": "object",
        "properties": {
            "credential_data": {"type": "object"},
        },
        "required": ["credential_data"],
    },
)
async def create_credential_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    credential_data = arguments.get("credential_data")
    if not isinstance(credential_data, dict):
        raise ValueError("credential_data must be an object")
    return _text_payload(await create_credential_action(credential_data))


@register_tool(
    "update_credential",
    "Update an existing credential.",
    {
        "type": "object",
        "properties": {
            "credential_id": {"type": "string"},
            "credential_data": {"type": "object"},
        },
        "required": ["credential_id", "credential_data"],
    },
)
async def update_credential_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    credential_id = arguments.get("credential_id")
    credential_data = arguments.get("credential_data")
    if not isinstance(credential_id, str):
        raise ValueError("credential_id must be a string")
    if not isinstance(credential_data, dict):
        raise ValueError("credential_data must be an object")
    return _text_payload(await update_credential_action(credential_id, credential_data))


@register_tool(
    "delete_credential",
    "Delete a credential by id.",
    {
        "type": "object",
        "properties": {
            "credential_id": {"type": "string"},
        },
        "required": ["credential_id"],
    },
)
async def delete_credential_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    credential_id = arguments.get("credential_id")
    if not isinstance(credential_id, str):
        raise ValueError("credential_id must be a string")
    return _text_payload(await delete_credential_action(credential_id))


# Node type tools
@register_tool(
    "list_node_types",
    "List all available node types in the n8n instance.",
    {
        "type": "object",
        "properties": {},
    },
)
async def list_node_types_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    return _text_payload(await list_node_types_action())


@register_tool(
    "get_node_type",
    "Get detailed information about a specific node type.",
    {
        "type": "object",
        "properties": {
            "node_type": {"type": "string"},
        },
        "required": ["node_type"],
    },
)
async def get_node_type_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    node_type = arguments.get("node_type")
    if not isinstance(node_type, str):
        raise ValueError("node_type must be a string")
    return _text_payload(await get_node_type_action(node_type))


# System monitoring tools
@register_tool(
    "get_circuit_breaker_stats",
    "Get circuit breaker statistics for monitoring n8n API health and preventing cascading failures.",
    {"type": "object", "properties": {}},
)
async def get_circuit_breaker_stats_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    return _text_payload(await get_circuit_breaker_stats_action())


@register_tool(
    "reset_circuit_breaker",
    "Manually reset the circuit breaker to closed state. Use when n8n service has recovered.",
    {"type": "object", "properties": {}},
)
async def reset_circuit_breaker_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    return _text_payload(await reset_circuit_breaker_action())


# Metrics and monitoring tools
@register_tool(
    "get_metrics",
    "Get comprehensive metrics including request rates, latency, error rates, and cache performance.",
    {"type": "object", "properties": {}},
)
async def get_metrics_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    return _text_payload(await get_metrics_action())


@register_tool(
    "get_health_status",
    "Check overall system health with detailed status checks for errors, latency, and cache.",
    {"type": "object", "properties": {}},
)
async def get_health_status_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    return _text_payload(await get_health_status_action())


@register_tool(
    "reset_metrics",
    "Reset all collected metrics. Use for testing or to clear historical data.",
    {"type": "object", "properties": {}},
)
async def reset_metrics_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    rate_limiter.check("mcp")
    return _text_payload(await reset_metrics_action())


# mypy struggles with dynamic decorator types exposed by the MCP library.
@server.list_tools()  # type: ignore[misc,no-untyped-call]
async def _list_tools() -> List[Tool]:
    return [
        Tool(name=name, description=desc, inputSchema=schema)
        for name, (_, schema, desc) in _tool_registry.items()
    ]


@server.call_tool()  # type: ignore[misc,no-untyped-call]
async def _call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    if name not in _tool_registry:
        raise ValueError(f"Unknown tool: {name}")
    handler, _, _ = _tool_registry[name]
    return await handler(arguments or {})


def main() -> None:
    async def runner() -> None:
        try:
            await _health_check(_settings)
        except Exception as e:
            raise SystemExit(f"n8n health check failed: {e}")

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(runner())
