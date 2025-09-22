from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Union, cast

from mcp.server import Server, stdio_server
from mcp.types import TextContent, Tool

from client.n8n_client import N8nClient
from core.builder import WorkflowBuilder
from core.config import Settings
from core.logging import audit_log, configure_logging
from core.rate_limiter import RateLimiter
from core.specs import WorkflowSpec
from core.validator import validate_workflow


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
            workflow_id = _workflow_id(target)
            response = await client.update_workflow(workflow_id, workflow_json)
        else:
            response = await client.create_workflow(workflow_json)

        if options.get("activate"):
            await client.set_activation(_workflow_id(response), True)

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
        workflow_id = _workflow_id(workflow)
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
        full = await client.get_workflow(_workflow_id(workflow))
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
        workflow_id = _workflow_id(workflow)
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
        full = await client.get_workflow(_workflow_id(workflow))
        full["name"] = f"{full.get('name')}{suffix}"
        full.pop("id", None)
        response = await client.create_workflow(full)
        audit_log(
            "duplicate_workflow",
            actor="mcp",
            details={"src": _workflow_id(workflow), "new": response.get("id")},
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
        workflow_id = _workflow_id(workflow)
        response = await client.execute_workflow(workflow_id, payload or {})
        audit_log(
            "execute_workflow",
            actor="mcp",
            details={"id": workflow_id, "payload": payload},
        )
        return {"workflow": response}


ToolHandler = Callable[[Dict[str, Any]], Awaitable[List[TextContent]]]
_tool_registry: Dict[str, tuple[ToolHandler, Dict[str, Any], str]] = {}


def _workflow_id(workflow: Dict[str, Any]) -> Union[str, int]:
    identifier = workflow.get("id")
    if isinstance(identifier, (str, int)):
        return identifier
    raise ValueError("workflow response missing id")


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
        await _health_check(_settings)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(runner())
