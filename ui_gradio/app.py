from __future__ import annotations
import json
import os
import gradio as gr
from pydantic import BaseModel
from builder.models import WorkflowSpec, validate_workflow
from builder.config import Settings
from n8n_client.client import N8NClient, N8NClientConfig

settings = Settings.from_env()
client = N8NClient(N8NClientConfig(base_url=str(settings.n8n_api_url), api_key=settings.n8n_api_key, timeout=settings.http_timeout))

class DeployOptions(BaseModel):
    dry_run: bool = True
    commit: bool = False
    activate: bool = False


def build_and_deploy(spec_json: str, dry_run: bool, commit: bool, activate: bool):
    try:
        spec = WorkflowSpec.model_validate_json(spec_json)
        n8n_wf = validate_workflow(spec)
    except Exception as e:
        return gr.update(value=f"Validation error: {e}"), gr.update(value="{}")

    if dry_run and not commit:
        return gr.update(value="Validated (dry run)."), gr.update(value=json.dumps(n8n_wf.model_dump(), indent=2))

    created = client.create_workflow(n8n_wf.model_dump())
    msg = f"Created workflow with id {created.get('id')}"
    if activate:
        client.activate_workflow(str(created.get("id")), True)
        msg += ", activated"
    return gr.update(value=msg), gr.update(value=json.dumps(created, indent=2))


def app_factory():
    with gr.Blocks(title="n8n MCP Builder") as demo:
        gr.Markdown("# n8n MCP Builder")
        with gr.Row():
            spec = gr.Textbox(label="WorkflowSpec JSON", lines=20, value=json.dumps({
                "name": "Webhook to HTTP",
                "nodes": [
                    {
                        "id": "Webhook",
                        "name": "Webhook",
                        "type": "n8n-nodes-base.webhook",
                        "typeVersion": 1,
                        "parameters": {"path": "test", "httpMethod": "POST"},
                        "position": {"x": 0, "y": 0}
                    },
                    {
                        "id": "HTTPRequest",
                        "name": "HTTP Request",
                        "type": "n8n-nodes-base.httpRequest",
                        "typeVersion": 1,
                        "parameters": {"method": "GET", "url": "https://example.com"},
                        "position": {"x": 300, "y": 0}
                    }
                ],
                "connections": [
                    {"source": "Webhook", "target": "HTTPRequest"}
                ],
                "settings": {}
            }, indent=2))
        with gr.Row():
            dry = gr.Checkbox(label="Dry Run", value=True)
            commit = gr.Checkbox(label="Commit", value=False)
            activate = gr.Checkbox(label="Activate", value=False)
        with gr.Row():
            out_msg = gr.Textbox(label="Status")
            out_json = gr.Textbox(label="Result JSON", lines=20)
        go = gr.Button("Validate/Deploy")
        go.click(build_and_deploy, inputs=[spec, dry, commit, activate], outputs=[out_msg, out_json])
    return demo

if __name__ == "__main__":
    demo = app_factory()
    demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))
