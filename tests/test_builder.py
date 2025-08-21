from builder.models import WorkflowSpec, NodeSpec, ConnectionSpec, validate_workflow

def test_minimal_webhook_http():
    spec = WorkflowSpec(
        name="Webhook to HTTP",
        nodes=[
            NodeSpec(id="Webhook", name="Webhook", type="n8n-nodes-base.webhook", parameters={"path": "test", "httpMethod": "POST"}),
            NodeSpec(id="HTTPRequest", name="HTTP Request", type="n8n-nodes-base.httpRequest", parameters={"url": "https://example.com", "method": "GET"}),
        ],
        connections=[ConnectionSpec(source="Webhook", target="HTTPRequest")],
    )
    n8n = validate_workflow(spec)
    assert n8n.name == spec.name
    assert "Webhook" in n8n.connections
    assert n8n.connections["Webhook"]["main"][0]["node"] == "HTTPRequest"
