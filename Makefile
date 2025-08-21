.PHONY: sync run ui test

sync:
	uv sync

run:
	uv run uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000

ui:
	uv run python ui_gradio/app.py

test:
	uv run pytest -q
