from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# Data contracts

class Position(BaseModel):
    x: float
    y: float

class NodeSpec(BaseModel):
    id: str
    name: str
    type: str
    typeVersion: int = 1
    parameters: Dict[str, Any] = Field(default_factory=dict)
    credentials: Optional[Dict[str, Dict[str, Any]]] = None
    position: Optional[Position] = None

class ConnectionRef(BaseModel):
    node: str
    type: Literal["main"] = "main"
    index: int = 0

# Note: We keep ConnectionRef for reference, but N8NWorkflow stores raw dicts to match n8n JSON

class ConnectionSpec(BaseModel):
    source: str
    target: str
    output: str = "main"
    index: int = 0

class WorkflowSpec(BaseModel):
    name: str
    nodes: List[NodeSpec]
    connections: List[ConnectionSpec]
    settings: Dict[str, Any] = Field(default_factory=dict)

class N8NWorkflow(BaseModel):
    name: str
    nodes: List[NodeSpec]
    connections: Dict[str, Dict[str, List[Dict[str, Any]]]]
    settings: Dict[str, Any] = Field(default_factory=dict)
    # Structure validated by builder and type hints

# Builder helpers

class WorkflowBuilder:
    def __init__(self, spec: WorkflowSpec):
        self.spec = spec

    def to_n8n(self) -> N8NWorkflow:
        node_ids = {n.id for n in self.spec.nodes}
        # connections dict shape
        conn_dict: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for c in self.spec.connections:
            if c.source not in node_ids or c.target not in node_ids:
                raise ValueError(f"Connection references unknown node: {c.source} -> {c.target}")
            conn_dict.setdefault(c.source, {}).setdefault(c.output, []).append(
                {"node": c.target, "type": "main", "index": c.index}
            )
        return N8NWorkflow(
            name=self.spec.name,
            nodes=self.spec.nodes,
            connections=conn_dict,
            settings=self.spec.settings,
        )

# Minimal node parameter schema validators (handwritten)

def validate_webhook_node(node: NodeSpec):
    params = node.parameters or {}
    required = ["path", "httpMethod"]
    for r in required:
        if r not in params:
            raise ValueError(f"Webhook node '{node.name}' missing required param '{r}'")


def validate_cron_node(node: NodeSpec):
    params = node.parameters or {}
    if "rule" not in params and "triggerTimes" not in params:
        raise ValueError("Cron node requires 'rule' or 'triggerTimes'")


def validate_http_request(node: NodeSpec):
    params = node.parameters or {}
    if "url" not in params or "method" not in params:
        raise ValueError("HTTP Request node requires 'url' and 'method'")


NODE_VALIDATORS = {
    "n8n-nodes-base.webhook": validate_webhook_node,
    "n8n-nodes-base.cron": validate_cron_node,
    "n8n-nodes-base.httpRequest": validate_http_request,
}


def validate_nodes(nodes: list[NodeSpec]):
    for node in nodes:
        fn = NODE_VALIDATORS.get(node.type)
        if fn:
            fn(node)


def validate_workflow(spec: WorkflowSpec) -> N8NWorkflow:
    if not spec.nodes:
        raise ValueError("Workflow must have at least one node")
    validate_nodes(spec.nodes)
    builder = WorkflowBuilder(spec)
    return builder.to_n8n()
