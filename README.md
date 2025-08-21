## MCP-Based n8n Workflow Builder

This repo provides an MCP server exposing tools to build, validate, deploy, manage, and execute n8n workflows via the official n8n REST API. An optional Gradio UI enables human-friendly creation and deployment.

### Quickstart

1. Copy `.env.template` to `.env` and fill values.
2. Create a virtual environment and install dependencies:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
3. Connectivity check and run tests:
```bash
pytest -q
```
4. Run MCP server over stdio:
```bash
python -m mcp_server
```
5. (Optional) Run UI:
```bash
ENABLE_UI=true python -m ui.app
```

### Structure
- `core/`: builder, validator, config, logging
- `client/`: n8n REST API client
- `mcp/`: MCP server exposing tools
- `ui/`: optional Gradio app
- `templates/`: canonical JSON templates
- `tests/`: unit + integration
- `docker/`: containerization
- `scripts/`: helpers

### Security
- Secrets come from environment variables. No secrets in code or logs.
- Requests are rate-limited.
- Audit logs for create/update/activate/deactivate/execute.

See `docs/` and inline docstrings for more details.
