from __future__ import annotations

from core.specs import WorkflowSpec, NodeSpec, ConnectionSpec
from core.builder import WorkflowBuilder


def test_minimal_webhook_http() -> None:
    spec = WorkflowSpec(
        name="Webhook to HTTP",
        nodes=[
            NodeSpec(
                name="Webhook",
                type="n8n-nodes-base.webhook",
                parameters={"path": "test", "httpMethod": "POST"},
            ),
            NodeSpec(
                name="HTTP Request",
                type="n8n-nodes-base.httpRequest",
                parameters={"url": "https://example.com", "method": "GET"},
            ),
        ],
        connections=[ConnectionSpec(fromNode="Webhook", toNode="HTTP Request")],
    )
    builder = WorkflowBuilder()
    wf = builder.build(spec)
    assert wf["name"] == spec.name
    assert "Webhook" in wf["connections"]
    conn = wf["connections"]["Webhook"]["main"][0][0]
    assert conn["node"] == "HTTP Request"
    assert conn["type"] == "main"
    assert conn["index"] == 0


def test_multiple_connections_single_branch() -> None:
    """Test that multiple outgoing connections are aggregated into branch 0."""
    spec = WorkflowSpec(
        name="Multi-output workflow",
        nodes=[
            NodeSpec(
                name="Start",
                type="n8n-nodes-base.webhook",
                parameters={"path": "start"},
            ),
            NodeSpec(
                name="Node A",
                type="n8n-nodes-base.httpRequest",
                parameters={"url": "https://a.com"},
            ),
            NodeSpec(
                name="Node B", 
                type="n8n-nodes-base.httpRequest",
                parameters={"url": "https://b.com"},
            ),
            NodeSpec(
                name="Node C",
                type="n8n-nodes-base.httpRequest", 
                parameters={"url": "https://c.com"},
            ),
        ],
        connections=[
            ConnectionSpec(fromNode="Start", toNode="Node A"),
            ConnectionSpec(fromNode="Start", toNode="Node B"),
            ConnectionSpec(fromNode="Start", toNode="Node C"),
        ],
    )
    
    builder = WorkflowBuilder()
    wf = builder.build(spec)
    
    # Verify connections structure
    assert "Start" in wf["connections"]
    assert "main" in wf["connections"]["Start"]
    
    # Should have exactly one branch (index 0)
    branches = wf["connections"]["Start"]["main"]
    assert len(branches) == 1, "All connections should be in branch 0"
    
    # Branch 0 should contain all three connections
    branch_0 = branches[0]
    assert len(branch_0) == 3, "Branch 0 should contain all 3 connections"
    
    # Verify all target nodes are present
    target_nodes = {conn["node"] for conn in branch_0}
    assert target_nodes == {"Node A", "Node B", "Node C"}
    
    # Verify all connections have correct properties
    for conn in branch_0:
        assert conn["type"] == "main"
        assert conn["index"] == 0


def test_connections_from_different_outputs() -> None:
    """Test connections from different outputs create separate output arrays."""
    spec = WorkflowSpec(
        name="Multi-output types",
        nodes=[
            NodeSpec(
                name="Switch",
                type="n8n-nodes-base.switch",
                parameters={},
            ),
            NodeSpec(
                name="Main Path",
                type="n8n-nodes-base.httpRequest",
                parameters={"url": "https://main.com"},
            ),
            NodeSpec(
                name="Alt Path",
                type="n8n-nodes-base.httpRequest",
                parameters={"url": "https://alt.com"},
            ),
        ],
        connections=[
            ConnectionSpec(fromNode="Switch", toNode="Main Path", output="main"),
            ConnectionSpec(fromNode="Switch", toNode="Alt Path", output="fallback"),
        ],
    )
    
    builder = WorkflowBuilder()
    wf = builder.build(spec)
    
    # Verify separate outputs
    assert "Switch" in wf["connections"]
    switch_conns = wf["connections"]["Switch"]
    assert "main" in switch_conns
    assert "fallback" in switch_conns
    
    # Each output should have one branch with one connection
    assert len(switch_conns["main"]) == 1
    assert len(switch_conns["main"][0]) == 1
    assert switch_conns["main"][0][0]["node"] == "Main Path"
    
    assert len(switch_conns["fallback"]) == 1
    assert len(switch_conns["fallback"][0]) == 1
    assert switch_conns["fallback"][0][0]["node"] == "Alt Path"
