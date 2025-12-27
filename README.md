## MCP-Based n8n Workflow Builder

A comprehensive MCP (Model Context Protocol) server for building, managing, and executing **any n8n workflow** via the n8n REST API. This tool removes all node type restrictions and provides full access to your n8n instance's capabilities.

### Key Features

🚀 **Universal Node Support** - Create workflows with ANY n8n node type (no restrictions!)
🔌 **Comprehensive API Coverage** - Workflows, credentials, executions, and node type management
🌲 **Complex Workflows** - Full support for branching (IF/Switch), error workflows, and multi-path flows
📊 **Execution Monitoring** - Track workflow runs, view results, and manage execution history
🔐 **Credential Management** - Securely manage n8n credentials programmatically
🎯 **Smart Validation** - Dynamic validation against your n8n instance's available nodes
📝 **Audit Logging** - Complete audit trail of all operations
⚡ **Rate Limiting** - Built-in protection for your n8n instance
🏎️ **High Performance** - Connection pooling, retry logic, and bulk operations ✨ NEW
🔗 **Webhook URLs** - Automatically retrieve webhook endpoints ✨ NEW
🛡️ **Circuit Breaker** - Automatic failure detection and recovery ✨ NEW
💾 **Node Type Caching** - 1-hour cache for faster node type lookups ✨ NEW
📊 **Metrics & Monitoring** - Real-time metrics, health checks, and observability ✨ NEW

### MCP Tools Available (28 Total)

**Workflow Management:**
- `validate_workflow` - Validate workflow specs offline
- `list_workflows` - List with filtering (name, active status)
- `create_workflow` - Create with dry-run, auto-activate, overwrite
- `get_workflow` - Fetch full workflow JSON
- `update_workflow` - Partial updates by ID or name
- `delete_workflow` - Remove workflows
- `activate_workflow` - Enable/disable workflows
- `duplicate_workflow` - Clone with custom suffix
- `execute_workflow` - Trigger with custom payload
- `get_webhook_urls` - Get webhook URLs for a workflow ✨ NEW
- `bulk_activate_workflows` - Activate/deactivate multiple workflows in parallel ✨ NEW
- `bulk_delete_workflows` - Delete multiple workflows in parallel ✨ NEW

**Execution Monitoring:**
- `list_executions` - View execution history (filter by workflow)
- `get_execution` - Get detailed execution data & results
- `delete_execution` - Clean up execution history

**Credential Management:**
- `list_credentials` - List all credentials (filter by type)
- `get_credential` - View credential details (sensitive data redacted)
- `create_credential` - Add new credentials
- `update_credential` - Modify existing credentials
- `delete_credential` - Remove credentials

**Node Discovery:**
- `list_node_types` - Get all available node types in your instance
- `get_node_type` - Get detailed node documentation and parameters

**System Monitoring:**
- `get_circuit_breaker_stats` - Monitor API health and circuit breaker state ✨ NEW
- `reset_circuit_breaker` - Manually reset circuit breaker after n8n recovery ✨ NEW
- `get_metrics` - Comprehensive metrics (requests, latency, errors, cache) ✨ NEW
- `get_health_status` - Overall health checks with detailed status ✨ NEW
- `reset_metrics` - Reset all collected metrics ✨ NEW

### Quickstart

1. **Configure your n8n connection:**
```bash
cp .env.template .env
# Edit .env with your n8n URL and API key
```

2. **Install dependencies:**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

3. **Run MCP server:**
```bash
python -m mcp_server  # Runs health check then starts server
```

4. **Use with any MCP client** (Claude Desktop, etc.)

### Example: Create a Complex Workflow

```json
{
  "name": "Advanced Email Processor",
  "nodes": [
    {
      "name": "Email Trigger",
      "type": "n8n-nodes-base.emailReadImap",
      "parameters": {
        "mailbox": "INBOX",
        "options": {}
      }
    },
    {
      "name": "Check Priority",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{$json.subject}}",
              "operation": "contains",
              "value2": "URGENT"
            }
          ]
        }
      }
    },
    {
      "name": "Slack Alert",
      "type": "n8n-nodes-base.slack",
      "parameters": {
        "resource": "message",
        "operation": "post",
        "channel": "#urgent",
        "text": "Urgent email: {{$json.subject}}"
      }
    },
    {
      "name": "Save to Database",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "operation": "insert",
        "table": "emails"
      }
    }
  ],
  "connections": [
    {"fromNode": "Email Trigger", "toNode": "Check Priority"},
    {"fromNode": "Check Priority", "toNode": "Slack Alert", "branch": 0},
    {"fromNode": "Check Priority", "toNode": "Save to Database", "branch": 1}
  ]
}
```

### Project Structure
- `core/` - Workflow builder, validator, config, logging, cache, circuit breaker, metrics, workflow helpers
- `client/` - n8n REST API client with full endpoint coverage
- `mcp_server/` - MCP server with 28 tools
- `ui/` - Optional Gradio web interface
- `templates/` - Example workflow templates
- `examples/` - Usage examples and patterns
- `tests/` - Comprehensive test suite (65+ tests, 100% passing)

### Testing

Run the test suite:
```bash
pytest tests/ -v
```

Test coverage includes:
- ✅ **Core modules**: Workflow builder, validator, utilities
- ✅ **Security**: Sensitive data redaction in audit logs
- ✅ **Reliability**: Circuit breaker pattern, rate limiting
- ✅ **Performance**: Caching with TTL support
- ✅ **MCP tools**: Tool registration and execution
- **65+ tests total** with comprehensive edge case coverage

### Workflow Builder API

Programmatically build workflows with a fluent, chainable API:

```python
from core.workflow_helpers import WorkflowBuilder

# Build a workflow fluently
workflow = (
    WorkflowBuilder("GitHub Alert System")
    .add_webhook("Trigger", "/github", "POST")
    .add_http_request("Fetch Data", "https://api.github.com/repos/={{$json.repo}}")
    .add_if_condition("Check Stars", "={{$json.stargazers_count}}", "greaterThan", 100)
    .add_slack("Trending Alert", "#trending", "🔥 Repo is trending!")
    .add_slack("Normal Log", "#activity", "New activity logged")
    .connect("Trigger", "Fetch Data")
    .connect("Fetch Data", "Check Stars")
    .connect("Check Stars", "Trending Alert", branch=0)  # True
    .connect("Check Stars", "Normal Log", branch=1)  # False
    .build()
)
```

**Supported Node Types:**
- `add_webhook()` - Webhook triggers
- `add_http_request()` - HTTP API calls
- `add_slack()` - Slack notifications
- `add_email()` - Email sending
- `add_if_condition()` - Conditional branching
- `add_function()` - Custom JavaScript
- `add_set()` - Data transformation
- `add_node()` - Any n8n node type

**Helper Functions:**
- `create_simple_webhook_workflow()` - Quick webhook → action workflows
- `create_conditional_workflow()` - If/then/else patterns

See `examples/workflow_builder_example.py` for complete examples.

### Advanced Features

**Complex Branching:**
```json
{
  "fromNode": "Switch",
  "toNode": "Path1",
  "branch": 0
},
{
  "fromNode": "Switch",
  "toNode": "Path2",
  "branch": 1
}
```

**Error Workflows:**
```json
{
  "fromNode": "HTTP Request",
  "toNode": "Error Handler",
  "output": "error"
}
```

**Dynamic Node Discovery:**
Query your instance for available nodes and get detailed documentation:
- Use `list_node_types()` to see all available nodes
- Use `get_node_type("n8n-nodes-base.gmail")` for specific node details

### Security
- ✅ All secrets via environment variables (never hardcoded)
- ✅ Automatic redaction of sensitive data in audit logs (passwords, API keys, tokens, etc.)
- ✅ Comprehensive test suite for security features
- ✅ Rate limiting (default: 60 requests/minute)
- ✅ API key authentication with n8n
- ✅ Audit trail for all destructive operations
- ✅ Security best practices documented in .env.template
- ✅ Recursive sanitization prevents credential leaks in nested objects

### Requirements
- Python 3.9+
- n8n instance with API access enabled
- n8n API key (generated in n8n Settings → API)

### Configuration

See `.env.template` for all options:
- `N8N_API_URL` - Your n8n instance URL
- `N8N_API_KEY` - Your n8n API key
- `N8N_VERSION` - Target n8n version (optional)
- `RATE_LIMIT` - Requests per minute (default: 60)
- `LOG_LEVEL` - Logging verbosity (default: info)

### What's New

This version removes ALL node type restrictions and adds:
- Support for **any n8n node type** (Gmail, Sheets, Airtable, custom nodes, etc.)
- Full credential management (list, create, update, delete)
- Execution monitoring and history
- Node type discovery and documentation
- Complex workflow branching (IF/Switch with multiple outputs)
- Error workflow support
- Dynamic validation against your n8n instance

### Documentation

For detailed usage examples and API documentation, see the inline docstrings and `/templates` directory for canonical workflow examples.
