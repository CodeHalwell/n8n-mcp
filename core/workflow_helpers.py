"""Helper functions for building n8n workflows programmatically.

These utilities simplify common workflow patterns and reduce boilerplate code.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from core.specs import NodeSpec, ConnectionSpec, WorkflowSpec


class WorkflowBuilder:
    """Fluent API for building n8n workflows.

    Example:
        builder = WorkflowBuilder("My Workflow")
        builder.add_webhook("Trigger", "/my-webhook", "POST")
        builder.add_http_request("API Call", "https://api.example.com")
        builder.add_slack("Notify", "#alerts", "{{$json.message}}")
        builder.connect("Trigger", "API Call")
        builder.connect("API Call", "Notify")
        workflow_spec = builder.build()
    """

    def __init__(self, name: str, description: Optional[str] = None):
        """
        Initialize a workflow builder.

        Args:
            name: The workflow name
            description: Optional workflow description
        """
        self.name = name
        self.description = description
        self._nodes: List[NodeSpec] = []
        self._connections: List[ConnectionSpec] = []

    def add_node(
        self,
        name: str,
        node_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        position: Optional[List[int]] = None,
    ) -> "WorkflowBuilder":
        """
        Add a generic node to the workflow.

        Args:
            name: Node name
            node_type: Node type (e.g., "n8n-nodes-base.webhook")
            parameters: Node parameters
            position: Optional [x, y] position

        Returns:
            Self for chaining
        """
        node = NodeSpec(
            name=name,
            type=node_type,
            parameters=parameters or {},
            position=position or [250, len(self._nodes) * 120],
        )
        self._nodes.append(node)
        return self

    def add_webhook(
        self,
        name: str,
        path: str,
        method: str = "POST",
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        """
        Add a webhook trigger node.

        Args:
            name: Node name
            path: Webhook path
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional parameters

        Returns:
            Self for chaining
        """
        params = {
            "path": path,
            "httpMethod": method,
            "responseMode": "onReceived",
            **kwargs,
        }
        return self.add_node(name, "n8n-nodes-base.webhook", params)

    def add_http_request(
        self,
        name: str,
        url: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        """
        Add an HTTP Request node.

        Args:
            name: Node name
            url: Request URL
            method: HTTP method
            **kwargs: Additional parameters (headers, body, etc.)

        Returns:
            Self for chaining
        """
        params = {
            "url": url,
            "method": method,
            **kwargs,
        }
        return self.add_node(name, "n8n-nodes-base.httpRequest", params)

    def add_slack(
        self,
        name: str,
        channel: str,
        message: str,
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        """
        Add a Slack node for posting messages.

        Args:
            name: Node name
            channel: Slack channel (e.g., "#general")
            message: Message text (supports n8n expressions)
            **kwargs: Additional parameters

        Returns:
            Self for chaining
        """
        params = {
            "resource": "message",
            "operation": "post",
            "channel": channel,
            "text": message,
            **kwargs,
        }
        return self.add_node(name, "n8n-nodes-base.slack", params)

    def add_email(
        self,
        name: str,
        to: str,
        subject: str,
        message: str,
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        """
        Add an Email Send node.

        Args:
            name: Node name
            to: Recipient email address
            subject: Email subject
            message: Email body
            **kwargs: Additional parameters

        Returns:
            Self for chaining
        """
        params = {
            "toEmail": to,
            "subject": subject,
            "message": message,
            **kwargs,
        }
        return self.add_node(name, "n8n-nodes-base.emailSend", params)

    def add_if_condition(
        self,
        name: str,
        field: str,
        operation: str = "equal",
        value: Any = None,
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        """
        Add an IF node for conditional branching.

        Args:
            name: Node name
            field: Field to check (e.g., "={{$json.status}}")
            operation: Comparison operation (equal, notEqual, contains, etc.)
            value: Value to compare against
            **kwargs: Additional parameters

        Returns:
            Self for chaining
        """
        params = {
            "conditions": {
                "string": [
                    {
                        "value1": field,
                        "operation": operation,
                        "value2": value,
                    }
                ]
            },
            **kwargs,
        }
        return self.add_node(name, "n8n-nodes-base.if", params)

    def add_function(
        self,
        name: str,
        javascript_code: str,
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        """
        Add a Function node for custom JavaScript.

        Args:
            name: Node name
            javascript_code: JavaScript code to execute
            **kwargs: Additional parameters

        Returns:
            Self for chaining
        """
        params = {
            "functionCode": javascript_code,
            **kwargs,
        }
        return self.add_node(name, "n8n-nodes-base.function", params)

    def add_set(
        self,
        name: str,
        values: Dict[str, Any],
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        """
        Add a Set node for transforming data.

        Args:
            name: Node name
            values: Dictionary of field names to values/expressions
            **kwargs: Additional parameters

        Returns:
            Self for chaining
        """
        params = {
            "values": {
                "string": [
                    {"name": key, "value": value}
                    for key, value in values.items()
                ]
            },
            **kwargs,
        }
        return self.add_node(name, "n8n-nodes-base.set", params)

    def connect(
        self,
        from_node: str,
        to_node: str,
        output: str = "main",
        branch: int = 0,
        index: int = 0,
    ) -> "WorkflowBuilder":
        """
        Connect two nodes.

        Args:
            from_node: Source node name
            to_node: Target node name
            output: Output type (default: "main")
            branch: Branch index for IF/Switch nodes (default: 0)
            index: Output index (default: 0)

        Returns:
            Self for chaining
        """
        connection = ConnectionSpec(
            fromNode=from_node,
            toNode=to_node,
            output=output,
            branch=branch,
            index=index,
        )
        self._connections.append(connection)
        return self

    def connect_on_error(
        self,
        from_node: str,
        error_handler: str,
    ) -> "WorkflowBuilder":
        """
        Connect a node's error output to an error handler.

        Args:
            from_node: Source node name
            error_handler: Error handler node name

        Returns:
            Self for chaining
        """
        return self.connect(from_node, error_handler, output="error")

    def build(self) -> WorkflowSpec:
        """
        Build the final workflow specification.

        Returns:
            WorkflowSpec ready for validation and creation
        """
        return WorkflowSpec(
            name=self.name,
            description=self.description,
            nodes=self._nodes,
            connections=self._connections,
        )


def create_simple_webhook_workflow(
    name: str,
    webhook_path: str,
    action_node_type: str,
    action_params: Dict[str, Any],
) -> WorkflowSpec:
    """
    Create a simple webhook → action workflow.

    Args:
        name: Workflow name
        webhook_path: Webhook path
        action_node_type: Type of action node (e.g., "n8n-nodes-base.slack")
        action_params: Parameters for the action node

    Returns:
        WorkflowSpec ready for creation

    Example:
        spec = create_simple_webhook_workflow(
            name="Slack Alert",
            webhook_path="/alert",
            action_node_type="n8n-nodes-base.slack",
            action_params={
                "resource": "message",
                "operation": "post",
                "channel": "#alerts",
                "text": "Alert: {{$json.message}}",
            },
        )
    """
    builder = WorkflowBuilder(name)
    builder.add_webhook("Webhook", webhook_path, "POST")
    builder.add_node("Action", action_node_type, action_params)
    builder.connect("Webhook", "Action")
    return builder.build()


def create_conditional_workflow(
    name: str,
    trigger_node: NodeSpec,
    condition_field: str,
    condition_operation: str,
    condition_value: Any,
    true_branch_node: NodeSpec,
    false_branch_node: NodeSpec,
) -> WorkflowSpec:
    """
    Create a workflow with conditional branching (if/then/else).

    Args:
        name: Workflow name
        trigger_node: Trigger node spec
        condition_field: Field to evaluate
        condition_operation: Comparison operation
        condition_value: Value to compare against
        true_branch_node: Node to execute if condition is true
        false_branch_node: Node to execute if condition is false

    Returns:
        WorkflowSpec ready for creation

    Example:
        trigger = NodeSpec(
            name="Webhook",
            type="n8n-nodes-base.webhook",
            parameters={"path": "/check", "httpMethod": "POST"},
        )
        urgent_handler = NodeSpec(
            name="Urgent Alert",
            type="n8n-nodes-base.slack",
            parameters={"channel": "#urgent", "text": "URGENT: {{$json.message}}"},
        )
        normal_handler = NodeSpec(
            name="Normal Log",
            type="n8n-nodes-base.httpRequest",
            parameters={"url": "https://log.example.com", "method": "POST"},
        )
        spec = create_conditional_workflow(
            name="Priority Router",
            trigger_node=trigger,
            condition_field="={{$json.priority}}",
            condition_operation="equal",
            condition_value="high",
            true_branch_node=urgent_handler,
            false_branch_node=normal_handler,
        )
    """
    builder = WorkflowBuilder(name)
    builder._nodes.append(trigger_node)
    builder.add_if_condition(
        "Condition",
        field=condition_field,
        operation=condition_operation,
        value=condition_value,
    )
    builder._nodes.append(true_branch_node)
    builder._nodes.append(false_branch_node)

    # Connect trigger → condition
    builder.connect(trigger_node.name, "Condition")

    # Connect condition → branches (branch 0 = true, branch 1 = false)
    builder.connect("Condition", true_branch_node.name, branch=0)
    builder.connect("Condition", false_branch_node.name, branch=1)

    return builder.build()
