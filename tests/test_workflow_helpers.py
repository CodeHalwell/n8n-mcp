"""Test workflow builder helpers."""
import pytest
from core.workflow_helpers import (
    WorkflowBuilder,
    create_simple_webhook_workflow,
    create_conditional_workflow,
)
from core.specs import NodeSpec


def test_workflow_builder_basic():
    """Test basic workflow builder functionality."""
    builder = WorkflowBuilder("Test Workflow")

    assert builder.name == "Test Workflow"
    assert builder.description is None
    assert len(builder._nodes) == 0
    assert len(builder._connections) == 0


def test_workflow_builder_add_generic_node():
    """Test adding a generic node."""
    builder = WorkflowBuilder("Test")
    builder.add_node("MyNode", "n8n-nodes-base.httpRequest", {"url": "https://example.com"})

    assert len(builder._nodes) == 1
    node = builder._nodes[0]
    assert node.name == "MyNode"
    assert node.type == "n8n-nodes-base.httpRequest"
    assert node.parameters["url"] == "https://example.com"


def test_workflow_builder_add_webhook():
    """Test adding a webhook node."""
    builder = WorkflowBuilder("Test")
    builder.add_webhook("Trigger", "/my-webhook", "POST")

    assert len(builder._nodes) == 1
    node = builder._nodes[0]
    assert node.name == "Trigger"
    assert node.type == "n8n-nodes-base.webhook"
    assert node.parameters["path"] == "/my-webhook"
    assert node.parameters["httpMethod"] == "POST"


def test_workflow_builder_add_http_request():
    """Test adding an HTTP request node."""
    builder = WorkflowBuilder("Test")
    builder.add_http_request("API Call", "https://api.example.com", "GET")

    assert len(builder._nodes) == 1
    node = builder._nodes[0]
    assert node.name == "API Call"
    assert node.type == "n8n-nodes-base.httpRequest"
    assert node.parameters["url"] == "https://api.example.com"
    assert node.parameters["method"] == "GET"


def test_workflow_builder_add_slack():
    """Test adding a Slack node."""
    builder = WorkflowBuilder("Test")
    builder.add_slack("Notify", "#general", "Hello World")

    assert len(builder._nodes) == 1
    node = builder._nodes[0]
    assert node.name == "Notify"
    assert node.type == "n8n-nodes-base.slack"
    assert node.parameters["channel"] == "#general"
    assert node.parameters["text"] == "Hello World"
    assert node.parameters["resource"] == "message"
    assert node.parameters["operation"] == "post"


def test_workflow_builder_add_email():
    """Test adding an email node."""
    builder = WorkflowBuilder("Test")
    builder.add_email("Send Email", "user@example.com", "Test Subject", "Test Body")

    assert len(builder._nodes) == 1
    node = builder._nodes[0]
    assert node.name == "Send Email"
    assert node.type == "n8n-nodes-base.emailSend"
    assert node.parameters["toEmail"] == "user@example.com"
    assert node.parameters["subject"] == "Test Subject"
    assert node.parameters["message"] == "Test Body"


def test_workflow_builder_add_if_condition():
    """Test adding an IF condition node."""
    builder = WorkflowBuilder("Test")
    builder.add_if_condition("Check Status", "={{$json.status}}", "equal", "success")

    assert len(builder._nodes) == 1
    node = builder._nodes[0]
    assert node.name == "Check Status"
    assert node.type == "n8n-nodes-base.if"
    assert "conditions" in node.parameters


def test_workflow_builder_add_function():
    """Test adding a Function node."""
    code = "return [{json: {result: 'processed'}}];"
    builder = WorkflowBuilder("Test")
    builder.add_function("Process", code)

    assert len(builder._nodes) == 1
    node = builder._nodes[0]
    assert node.name == "Process"
    assert node.type == "n8n-nodes-base.function"
    assert node.parameters["functionCode"] == code


def test_workflow_builder_add_set():
    """Test adding a Set node."""
    builder = WorkflowBuilder("Test")
    builder.add_set("Transform", {"field1": "value1", "field2": "={{$json.input}}"})

    assert len(builder._nodes) == 1
    node = builder._nodes[0]
    assert node.name == "Transform"
    assert node.type == "n8n-nodes-base.set"


def test_workflow_builder_connect_nodes():
    """Test connecting nodes."""
    builder = WorkflowBuilder("Test")
    builder.add_webhook("Start", "/test", "POST")
    builder.add_http_request("API", "https://example.com")
    builder.connect("Start", "API")

    assert len(builder._connections) == 1
    conn = builder._connections[0]
    assert conn.fromNode == "Start"
    assert conn.toNode == "API"
    assert conn.output == "main"
    assert conn.branch == 0


def test_workflow_builder_connect_on_error():
    """Test connecting error handlers."""
    builder = WorkflowBuilder("Test")
    builder.add_http_request("API", "https://example.com")
    builder.add_slack("Error Alert", "#errors", "Error occurred")
    builder.connect_on_error("API", "Error Alert")

    assert len(builder._connections) == 1
    conn = builder._connections[0]
    assert conn.fromNode == "API"
    assert conn.toNode == "Error Alert"
    assert conn.output == "error"


def test_workflow_builder_fluent_api():
    """Test fluent API chaining."""
    builder = (
        WorkflowBuilder("Chained Workflow")
        .add_webhook("Trigger", "/chain", "POST")
        .add_http_request("API1", "https://api1.example.com")
        .add_http_request("API2", "https://api2.example.com")
        .connect("Trigger", "API1")
        .connect("API1", "API2")
    )

    assert len(builder._nodes) == 3
    assert len(builder._connections) == 2


def test_workflow_builder_build():
    """Test building the final workflow spec."""
    builder = WorkflowBuilder("Final Workflow", description="Test workflow")
    builder.add_webhook("Start", "/test", "POST")
    builder.add_slack("End", "#test", "Done")
    builder.connect("Start", "End")

    spec = builder.build()

    assert spec.name == "Final Workflow"
    assert spec.description == "Test workflow"
    assert len(spec.nodes) == 2
    assert len(spec.connections) == 1


def test_create_simple_webhook_workflow():
    """Test simple webhook workflow helper."""
    spec = create_simple_webhook_workflow(
        name="Simple Alert",
        webhook_path="/alert",
        action_node_type="n8n-nodes-base.slack",
        action_params={
            "resource": "message",
            "operation": "post",
            "channel": "#alerts",
            "text": "Alert!",
        },
    )

    assert spec.name == "Simple Alert"
    assert len(spec.nodes) == 2
    assert len(spec.connections) == 1
    assert spec.nodes[0].type == "n8n-nodes-base.webhook"
    assert spec.nodes[1].type == "n8n-nodes-base.slack"


def test_create_conditional_workflow():
    """Test conditional workflow helper."""
    trigger = NodeSpec(
        name="Webhook",
        type="n8n-nodes-base.webhook",
        parameters={"path": "/priority", "httpMethod": "POST"},
    )
    urgent = NodeSpec(
        name="Urgent",
        type="n8n-nodes-base.slack",
        parameters={"channel": "#urgent", "text": "URGENT"},
    )
    normal = NodeSpec(
        name="Normal",
        type="n8n-nodes-base.slack",
        parameters={"channel": "#normal", "text": "Normal"},
    )

    spec = create_conditional_workflow(
        name="Priority Router",
        trigger_node=trigger,
        condition_field="={{$json.priority}}",
        condition_operation="equal",
        condition_value="high",
        true_branch_node=urgent,
        false_branch_node=normal,
    )

    assert spec.name == "Priority Router"
    assert len(spec.nodes) == 4  # trigger + condition + 2 branches
    assert len(spec.connections) == 3  # trigger→condition, condition→urgent, condition→normal

    # Check branching
    urgent_conn = next(c for c in spec.connections if c.toNode == "Urgent")
    assert urgent_conn.branch == 0  # True branch

    normal_conn = next(c for c in spec.connections if c.toNode == "Normal")
    assert normal_conn.branch == 1  # False branch
