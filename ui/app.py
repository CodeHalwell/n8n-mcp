from __future__ import annotations

import json
import os
import asyncio
import gradio as gr

from core.config import Settings
from core.specs import WorkflowSpec
from core.validator import validate_workflow
from core.builder import WorkflowBuilder
from client.n8n_client import N8nClient

settings = Settings.load_from_env()


async def _deploy(spec_json: str, activate: bool) -> str:
	client = N8nClient(settings)
	try:
		spec = WorkflowSpec.model_validate_json(spec_json)
		builder = WorkflowBuilder()
		payload = builder.build(spec)
		resp = await client.create_workflow(payload)
		if activate:
			await client.set_activation(resp.get("id"), True)
		return json.dumps({"status": "ok", "id": resp.get("id"), "name": resp.get("name")})
	finally:
		await client.close()


def ui() -> gr.Blocks:
	with gr.Blocks(title="n8n Builder") as demo:
		with gr.Row():
			with gr.Column():
				template = gr.Dropdown(["webhook-code-http", "cron-http-if-slack", "webhook-http-postgres", "cron-http-notion"], label="Template")
				params = gr.Textbox(label="Template Params (JSON)", value="{}")
				activate = gr.Checkbox(label="Activate after deploy", value=False)
				validate_btn = gr.Button("Validate")
				deploy_btn = gr.Button("Deploy")
			with gr.Column():
				preview = gr.Code(label="Workflow JSON Preview", language="json")
				status = gr.Markdown("Ready")

			def build_preview(template_id: str, params_json: str) -> str:
				# In a real impl, expand template by id with params
				return json.dumps({"name": template_id, "nodes": [], "connections": []}, indent=2)

			async def do_validate(preview_json: str) -> str:
				try:
					spec = WorkflowSpec.model_validate_json(preview_json)
					errors = validate_workflow(spec)
					return "No errors" if not errors else "\n".join(errors)
				except Exception as e:
					return f"Validation exception: {e}"

			async def do_deploy(preview_json: str, activate_flag: bool) -> str:
				try:
					return await _deploy(preview_json, activate_flag)
				except Exception as e:
					return json.dumps({"status": "error", "message": str(e)})

			template.change(build_preview, inputs=[template, params], outputs=[preview])
			params.change(build_preview, inputs=[template, params], outputs=[preview])
			validate_btn.click(do_validate, inputs=[preview], outputs=[status])
			deploy_btn.click(do_deploy, inputs=[preview, activate], outputs=[status])

	return demo


if __name__ == "__main__":
	demo = ui()
	demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))