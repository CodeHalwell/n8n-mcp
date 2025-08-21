from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, Result

from core.config import Settings
from core.logging import configure_logging, audit_log
from core.specs import WorkflowSpec
from core.validator import validate_workflow
from core.builder import WorkflowBuilder
from core.rate_limiter import RateLimiter
from client.n8n_client import N8nClient


server = Server("n8n-workflow-builder")
settings = Settings.load_from_env()
configure_logging(settings.log_level, settings.audit_log_path)
rate_limiter = RateLimiter(settings.rate_limit_per_minute)


async def _health_check() -> Dict[str, Any]:
	client = N8nClient(settings)
	try:
		info = await client.health()
		server_version = info.get("version") or info.get("data", {}).get("version")
		warn = None
		if settings.n8n_version and server_version and settings.n8n_version != server_version:
			warn = {
				"warning": "version_mismatch",
				"configured": settings.n8n_version,
				"server": server_version,
			}
		return {"ok": True, "server_version": server_version, **({"warning": warn} if warn else {})}
	finally:
		await client.close()


@server.tool()
async def validate_workflow_tool(workflow_json: Dict[str, Any]) -> Result:
	rate_limiter.check("mcp")
	spec = WorkflowSpec(**workflow_json)
	errors = validate_workflow(spec)
	return Result(content=[{"type": "text", "text": json.dumps({"errors": errors})}])


@server.tool()
async def list_workflows_tool(filters: Optional[Dict[str, Any]] = None) -> Result:
	rate_limiter.check("mcp")
	filters = filters or {}
	client = N8nClient(settings)
	try:
		workflows = await client.list_workflows()
		name_contains = filters.get("name_contains")
		active = filters.get("active")
		if name_contains:
			workflows = [w for w in workflows if name_contains.lower() in (w.get("name", "").lower())]
		if active is not None:
			workflows = [w for w in workflows if bool(w.get("active")) == bool(active)]
		return Result(content=[{"type": "text", "text": json.dumps({"data": workflows})}])
	finally:
		await client.close()


@server.tool()
async def create_workflow_tool(spec: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Result:
	rate_limiter.check("mcp")
	options = options or {}
	client = N8nClient(settings)
	try:
		# pre-validate
		existing = await client.list_workflows()
		existing_names = [w.get("name") for w in existing]
		spec_model = WorkflowSpec(**spec)
		errors = validate_workflow(spec_model, existing_names=existing_names, overwrite=bool(options.get("overwrite_if_exists")))
		if errors:
			return Result(content=[{"type": "text", "text": json.dumps({"errors": errors})}])

		builder = WorkflowBuilder()
		workflow_json = builder.build(spec_model)
		if options.get("tags"):
			workflow_json["tags"] = options.get("tags")

		if options.get("dry_run"):
			return Result(content=[{"type": "text", "text": json.dumps({"dry_run": True, "workflow": workflow_json})}])

		# create or overwrite
		if spec_model.name in existing_names and options.get("overwrite_if_exists"):
			wf = next(w for w in existing if w.get("name") == spec_model.name)
			resp = await client.update_workflow(wf.get("id"), workflow_json)
		else:
			resp = await client.create_workflow(workflow_json)

		if options.get("activate"):
			await client.set_activation(resp.get("id"), True)

		audit_log("create_workflow", actor="mcp", details={"name": spec_model.name, "id": resp.get("id")})
		return Result(content=[{"type": "text", "text": json.dumps(resp)}])
	finally:
		await client.close()


@server.tool()
async def update_workflow_tool(identifier: str, patch: Dict[str, Any]) -> Result:
	rate_limiter.check("mcp")
	client = N8nClient(settings)
	try:
		workflows = await client.list_workflows()
		wf = next((w for w in workflows if str(w.get("id")) == identifier or w.get("name") == identifier), None)
		if not wf:
			return Result(error=f"workflow {identifier} not found")
		resp = await client.update_workflow(wf.get("id"), patch)
		audit_log("update_workflow", actor="mcp", details={"id": wf.get("id")})
		return Result(content=[{"type": "text", "text": json.dumps(resp)}])
	finally:
		await client.close()


@server.tool()
async def get_workflow_tool(identifier: str) -> Result:
	rate_limiter.check("mcp")
	client = N8nClient(settings)
	try:
		workflows = await client.list_workflows()
		wf = next((w for w in workflows if str(w.get("id")) == identifier or w.get("name") == identifier), None)
		if not wf:
			return Result(error=f"workflow {identifier} not found")
		full = await client.get_workflow(wf.get("id"))
		return Result(content=[{"type": "text", "text": json.dumps(full)}])
	finally:
		await client.close()


@server.tool()
async def activate_workflow_tool(identifier: str, active: bool) -> Result:
	rate_limiter.check("mcp")
	client = N8nClient(settings)
	try:
		workflows = await client.list_workflows()
		wf = next((w for w in workflows if str(w.get("id")) == identifier or w.get("name") == identifier), None)
		if not wf:
			return Result(error=f"workflow {identifier} not found")
		resp = await client.set_activation(wf.get("id"), active)
		audit_log("activate_workflow", actor="mcp", details={"id": wf.get("id"), "active": active})
		return Result(content=[{"type": "text", "text": json.dumps(resp)}])
	finally:
		await client.close()


@server.tool()
async def duplicate_workflow_tool(identifier: str, suffix: str) -> Result:
	rate_limiter.check("mcp")
	client = N8nClient(settings)
	try:
		workflows = await client.list_workflows()
		wf = next((w for w in workflows if str(w.get("id")) == identifier or w.get("name") == identifier), None)
		if not wf:
			return Result(error=f"workflow {identifier} not found")
		full = await client.get_workflow(wf.get("id"))
		full["name"] = f"{full.get('name')}{suffix}"
		full.pop("id", None)
		resp = await client.create_workflow(full)
		audit_log("duplicate_workflow", actor="mcp", details={"src": wf.get("id"), "new": resp.get("id")})
		return Result(content=[{"type": "text", "text": json.dumps(resp)}])
	finally:
		await client.close()


@server.tool()
async def execute_workflow_tool(identifier: str, payload: Optional[Dict[str, Any]] = None) -> Result:
	rate_limiter.check("mcp")
	# Minimal placeholder: users should trigger via webhook for webhook flows
	return Result(content=[{"type": "text", "text": json.dumps({"status": "not_implemented", "hint": "Trigger via webhook/manual run"})}])

	client = N8nClient(settings)
	try:
		workflows = await client.list_workflows()
		wf = next((w for w in workflows if str(w.get("id")) == identifier or w.get("name") == identifier), None)
		if not wf:
			return Result(error=f"workflow {identifier} not found")
		# Attempt to execute the workflow
		resp = await client.execute_workflow(wf.get("id"), payload or {})
		audit_log("execute_workflow", actor="mcp", details={"id": wf.get("id"), "payload": payload})
		return Result(content=[{"type": "text", "text": json.dumps(resp)}])
	except Exception as e:
		return Result(error=f"Failed to execute workflow {identifier}: {e}")
	finally:
		await client.close()
def main() -> None:
	# Startup health check
	loop = asyncio.get_event_loop()
	try:
		health = loop.run_until_complete(_health_check())
		if not health.get("ok"):
			raise SystemExit("n8n health check failed")
	except Exception as e:
		raise SystemExit(f"n8n health check failed: {e}")
	server.run_stdio()


if __name__ == "__main__":
	main()