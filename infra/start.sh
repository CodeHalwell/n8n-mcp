#!/bin/sh
set -e
uv run uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000
