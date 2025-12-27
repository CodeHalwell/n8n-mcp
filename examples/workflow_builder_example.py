"""Example usage of the WorkflowBuilder helper API.

This demonstrates how to use the fluent API to build workflows programmatically.
"""

from core.workflow_helpers import (
    WorkflowBuilder,
    create_simple_webhook_workflow,
    create_conditional_workflow,
)
from core.specs import NodeSpec


def example_simple_workflow():
    """Build a simple webhook → HTTP request → Slack workflow."""
    builder = (
        WorkflowBuilder("GitHub Webhook Handler")
        .add_webhook("GitHub Trigger", "/github-webhook", "POST")
        .add_http_request(
            "Fetch User Info",
            "https://api.github.com/users/={{$json.user.login}}",
            method="GET",
        )
        .add_slack(
            "Post to Slack",
            "#github-notifications",
            "New event from {{$json.user.login}}",
        )
        .connect("GitHub Trigger", "Fetch User Info")
        .connect("Fetch User Info", "Post to Slack")
    )

    workflow_spec = builder.build()
    print(f"Created workflow: {workflow_spec.name}")
    print(f"Nodes: {len(workflow_spec.nodes)}")
    print(f"Connections: {len(workflow_spec.connections)}")
    return workflow_spec


def example_conditional_workflow():
    """Build a workflow with conditional branching."""
    builder = (
        WorkflowBuilder("Priority Alert Router", description="Routes alerts by priority")
        .add_webhook("Alert Trigger", "/alert", "POST")
        .add_if_condition(
            "Check Priority",
            field="={{$json.priority}}",
            operation="equal",
            value="high",
        )
        .add_slack("Urgent Channel", "#urgent", "🚨 HIGH PRIORITY: {{$json.message}}")
        .add_slack("Normal Channel", "#general", "ℹ️  Info: {{$json.message}}")
        .connect("Alert Trigger", "Check Priority")
        .connect("Check Priority", "Urgent Channel", branch=0)  # True branch
        .connect("Check Priority", "Normal Channel", branch=1)  # False branch
    )

    workflow_spec = builder.build()
    print(f"Created conditional workflow: {workflow_spec.name}")
    return workflow_spec


def example_error_handling():
    """Build a workflow with error handling."""
    builder = (
        WorkflowBuilder("API Call with Error Handler")
        .add_webhook("Start", "/trigger", "POST")
        .add_http_request(
            "Call External API",
            "https://api.example.com/data",
            method="POST",
        )
        .add_slack("Success Notification", "#success", "✅ API call succeeded!")
        .add_slack("Error Alert", "#errors", "❌ API call failed: {{$json.error.message}}")
        .connect("Start", "Call External API")
        .connect("Call External API", "Success Notification")  # Success path
        .connect_on_error("Call External API", "Error Alert")  # Error path
    )

    workflow_spec = builder.build()
    print(f"Created workflow with error handling: {workflow_spec.name}")
    return workflow_spec


def example_data_transformation():
    """Build a workflow with data transformation."""
    builder = (
        WorkflowBuilder("Data Processor")
        .add_webhook("Receive Data", "/process", "POST")
        .add_function(
            "Transform Data",
            javascript_code="""
// Transform the input data
const input = items[0].json;
const output = {
  processedAt: new Date().toISOString(),
  originalData: input,
  summary: `Processed ${Object.keys(input).length} fields`
};
return [{json: output}];
""",
        )
        .add_set(
            "Add Metadata",
            values={
                "status": "completed",
                "timestamp": "={{$now}}",
                "source": "n8n-workflow",
            },
        )
        .add_http_request(
            "Save to Database",
            "https://db.example.com/records",
            method="POST",
        )
        .connect("Receive Data", "Transform Data")
        .connect("Transform Data", "Add Metadata")
        .connect("Add Metadata", "Save to Database")
    )

    workflow_spec = builder.build()
    print(f"Created data transformation workflow: {workflow_spec.name}")
    return workflow_spec


def example_helper_functions():
    """Use pre-built helper functions for common patterns."""

    # Simple webhook → action workflow
    simple_spec = create_simple_webhook_workflow(
        name="Quick Slack Alert",
        webhook_path="/quick-alert",
        action_node_type="n8n-nodes-base.slack",
        action_params={
            "resource": "message",
            "operation": "post",
            "channel": "#alerts",
            "text": "Alert received: {{$json.message}}",
        },
    )
    print(f"Created simple workflow using helper: {simple_spec.name}")

    # Conditional workflow
    trigger = NodeSpec(
        name="Email Trigger",
        type="n8n-nodes-base.emailReadImap",
        parameters={"mailbox": "INBOX"},
    )
    urgent_action = NodeSpec(
        name="Urgent Slack Alert",
        type="n8n-nodes-base.slack",
        parameters={
            "resource": "message",
            "operation": "post",
            "channel": "#urgent",
            "text": "URGENT EMAIL: {{$json.subject}}",
        },
    )
    normal_action = NodeSpec(
        name="Normal Email Processing",
        type="n8n-nodes-base.httpRequest",
        parameters={"url": "https://api.example.com/process-email", "method": "POST"},
    )

    conditional_spec = create_conditional_workflow(
        name="Email Priority Router",
        trigger_node=trigger,
        condition_field="={{$json.subject}}",
        condition_operation="contains",
        condition_value="URGENT",
        true_branch_node=urgent_action,
        false_branch_node=normal_action,
    )
    print(f"Created conditional workflow using helper: {conditional_spec.name}")

    return simple_spec, conditional_spec


if __name__ == "__main__":
    print("=" * 60)
    print("Workflow Builder Examples")
    print("=" * 60)
    print()

    print("Example 1: Simple Workflow")
    print("-" * 60)
    example_simple_workflow()
    print()

    print("Example 2: Conditional Workflow")
    print("-" * 60)
    example_conditional_workflow()
    print()

    print("Example 3: Error Handling")
    print("-" * 60)
    example_error_handling()
    print()

    print("Example 4: Data Transformation")
    print("-" * 60)
    example_data_transformation()
    print()

    print("Example 5: Helper Functions")
    print("-" * 60)
    example_helper_functions()
    print()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
