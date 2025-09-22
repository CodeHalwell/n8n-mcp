# n8n-MCP Workflow Builder

**ALWAYS** follow these instructions first before falling back to additional search or bash commands. Only gather additional context if the information here is incomplete or found to be in error.

This repository provides an MCP (Model Context Protocol) server that exposes tools to build, validate, deploy, manage, and execute n8n workflows via the official n8n REST API. It includes optional Gradio UI components for human-friendly workflow creation and deployment.

## Working Effectively

### Environment Setup
Set up the development environment with these **VALIDATED** commands:

```bash
# Copy environment template and configure
cp .env.template .env
# Edit .env to set N8N_API_URL and N8N_API_KEY for full functionality

# Create virtual environment (takes ~10 seconds)
python3 -m venv .venv --upgrade-deps

# Install dependencies (takes ~60 seconds, NEVER CANCEL)
source .venv/bin/activate
pip install -r requirements.txt
```

**TIMEOUT WARNING**: Set timeout to 180+ seconds for dependency installation. NEVER CANCEL the pip install process.

### Project Structure
- `core/`: Core workflow builder, validator, config, logging, rate limiting
- `client/`: n8n REST API client library  
- `mcp_server/`: MCP server exposing workflow tools over stdio/HTTP
- `ui/`: Gradio UI application (requires n8n connectivity)
- `ui_gradio/`: Alternative Gradio UI (legacy, has import issues)
- `templates/`: Canonical JSON workflow templates
- `tests/`: Unit and integration tests
- `scripts/`: Helper scripts including bootstrap.sh
- `infra/`: Docker containerization files

### Build and Test

**Run tests** (takes ~1 second, always run this first):
```bash
source .venv/bin/activate
pytest -q
```

**Lint code** (ruff is fast, pylint has style issues):
```bash
source .venv/bin/activate
ruff check --exclude .venv --exclude get-pip.py .  # Fast, passes cleanly
PYTHONPATH=. mypy core/                            # Type checking, takes ~2 seconds
# Note: pylint has many tab/indentation style issues, use ruff instead
```

**Environment validation without n8n connectivity**:
```bash
source .venv/bin/activate
PYTHONPATH=. python -c "
from core.specs import WorkflowSpec, NodeSpec
from core.builder import WorkflowBuilder
spec = WorkflowSpec(name='Test', nodes=[NodeSpec(name='Test Node', type='n8n-nodes-base.webhook', parameters={'path': 'test'})], connections=[])
builder = WorkflowBuilder()
result = builder.build(spec)
print('Core functionality works:', result.get('name'))
"
```

### Running Applications

**MCP Server** (requires valid N8N_API_URL and N8N_API_KEY in .env):
```bash
source .venv/bin/activate
python -m mcp_server                    # Stdio mode
# OR
uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000  # HTTP mode
```

**Gradio UI** (requires valid n8n configuration):
```bash
source .venv/bin/activate
ENABLE_UI=true python -m ui.app         # Port 7860 by default
```

**Using alternative package manager** (if uv is available):
```bash
uv sync                                 # Install dependencies
uv run pytest -q                       # Run tests  
uv run uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000  # Run server
uv run python ui_gradio/app.py          # Run alternative UI
```

## Validation Scenarios

**ALWAYS** test these scenarios after making changes:

1. **Core workflow building** (works without n8n connectivity):
   ```bash
   source .venv/bin/activate
   PYTHONPATH=. python -c "from core.builder import WorkflowBuilder; print('Builder import works')"
   ```

2. **Test suite validation**:
   ```bash
   source .venv/bin/activate
   pytest -v  # All 6 tests should pass
   ```

3. **Configuration loading** (requires .env setup):
   ```bash
   source .venv/bin/activate  
   PYTHONPATH=. N8N_API_URL=http://test N8N_API_KEY=test python -c "from core.config import Settings; print('Config works')"
   ```

4. **Template validation**:
   ```bash
   source .venv/bin/activate
   ls templates/*.json  # Should show workflow templates
   ```

## Common Development Tasks

### Before Committing Changes
**ALWAYS** run these checks (total time ~5 seconds):
```bash
source .venv/bin/activate
ruff check --exclude .venv --exclude get-pip.py .  # Lint check
pytest -q                                          # Test suite
PYTHONPATH=. mypy core/                            # Type checking
```

### Adding New Workflow Templates
- Place JSON templates in `templates/` directory
- Update `templates/index.json` if needed
- Test template loading via core builder

### Working with MCP Tools
- MCP server exposes workflow tools over stdio protocol
- Test MCP functionality requires valid n8n API credentials
- Use `mcp_server.app:app` for HTTP mode testing

### Debugging Import Issues
If you encounter `ModuleNotFoundError`:
```bash
# Always set PYTHONPATH for running scripts
source .venv/bin/activate
PYTHONPATH=. python your_script.py
```

## Known Issues and Workarounds

- **pylint reports many style issues**: Code uses tabs instead of spaces. Use `ruff` for linting instead.
- **ui_gradio has import errors**: Use `ui/app.py` for UI functionality instead.
- **MCP server requires valid credentials**: Core functionality can be tested without n8n connectivity.
- **Two package managers**: Project supports both pip/venv and uv. Use pip/venv if uv is not available.

## Timing Expectations

- **Tests**: ~1 second (6 tests)
- **Dependency installation**: ~60 seconds (NEVER CANCEL, set 180+ second timeout)  
- **Virtual environment creation**: ~10 seconds
- **Linting with ruff**: <1 second
- **Type checking with mypy**: ~2 seconds
- **Complete validation suite**: ~2 seconds total
- **Core functionality validation**: <1 second

## Environment Variables

Required for full functionality (set in `.env`):
- `N8N_API_URL`: n8n instance URL (e.g., `https://your-n8n.example.com`)
- `N8N_API_KEY`: n8n API authentication key
- `N8N_VERSION`: Target n8n version (optional, default: `1.64.0`)

Optional configuration:
- `LOG_LEVEL`: Logging level (default: `info`)
- `ENABLE_UI`: Enable UI components (default: `false`)
- `RATE_LIMIT`: Rate limiting per minute (default: `60`)
- `AUDIT_LOG_PATH`: Path for audit logging

## Quick Reference Commands

**Full development setup from scratch**:
```bash
cp .env.template .env  # Edit as needed
python3 -m venv .venv --upgrade-deps
source .venv/bin/activate  
pip install -r requirements.txt
pytest -q
```

**Validate changes before commit**:
```bash
source .venv/bin/activate
ruff check --exclude .venv --exclude get-pip.py . && pytest -q && PYTHONPATH=. mypy core/
```

**Test core functionality without n8n**:
```bash
source .venv/bin/activate
PYTHONPATH=. python -c "from core.builder import WorkflowBuilder; from core.specs import WorkflowSpec, NodeSpec; print('Core validation passed')"
```