## n8n-mcp: MCP server + n8n workflow builder

This project provides:
- A small, secure MCP-style HTTP server exposing tools to create/update/list/activate/execute n8n workflows.
- A minimal n8n API client.
- A workflow builder with schema checks and templates for a few core nodes.
- An optional Gradio UI for humans.

### Repo layout

- `mcp_server/` FastAPI app exposing tool-like endpoints under `/tools/*`.
- `n8n_client/` Lightweight n8n REST API client wrapper.
- `builder/` Pydantic models, validators, and a tiny workflow builder.
- `ui_gradio/` Optional Gradio UI for preview/validate/deploy.
- `infra/` Dockerfile and docker-compose.
- `tests/` Minimal unit tests.

### Environment

Copy `.env.template` to `.env` and populate:

```
N8N_API_URL=https://n8n.example.com/api/v1
N8N_API_KEY=xxxx
N8N_ENV=staging
HTTP_TIMEOUT=30
```

### Quickstart (local with uv)

1) Install uv if not present:

```
pip install uv
```

2) Sync dependencies:

```
uv sync
```

3) Run the MCP server:

```
uv run uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000
```

4) Optional Gradio UI:

```
uv run python ui_gradio/app.py
```

### Docker

```
docker build -t n8n-mcp -f infra/Dockerfile .
docker run --rm -p 8000:8000 --env-file .env n8n-mcp
```

Or with compose:

```
docker compose -f infra/docker-compose.yml up --build
```

### Endpoints (tools)

- POST `/tools/create_workflow` { spec, dry_run, commit }
- POST `/tools/update_workflow` { workflow_id, spec, dry_run, commit }
- GET `/tools/list_workflows`
- GET `/tools/get_workflow/{id}`
- POST `/tools/activate_workflow` { id }
- POST `/tools/deactivate_workflow` { id }
- POST `/tools/execute_workflow` { id, payload? }

Inputs are strongly typed via Pydantic models; set `dry_run=true` to only validate and preview JSON.

### Notes

- Start with minimal node coverage: Webhook, Cron, HTTP Request, Code, IF.
- Add more nodes by exporting example workflows from n8n and codifying minimal params.

### Testing

```
uv run pytest -q
```

### Security & Ops

- API base URL and key are read from env vars.
- Keep separate staging vs prod n8n instances via env.
- Rate limit and auth sit in front of this server if internet-facing.
