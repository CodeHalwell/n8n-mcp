from __future__ import annotations

from typing import Any, Dict, List

from core.specs import NodeSpec, WorkflowSpec


class WorkflowBuilder:
    def __init__(self) -> None:
        pass

    def build(self, spec: WorkflowSpec) -> Dict[str, Any]:
        nodes = [self._node_to_json(node) for node in spec.nodes]
        name_to_index = {node.name: idx for idx, node in enumerate(spec.nodes)}

        connections: Dict[str, Dict[str, List[List[Dict[str, Any]]]]] = {}
        for conn in spec.connections:
            from_idx = name_to_index.get(conn.fromNode)
            to_idx = name_to_index.get(conn.toNode)
            if from_idx is None or to_idx is None:
                raise ValueError(f"Connection refers to unknown node: {conn}")

            from_name = spec.nodes[from_idx].name
            connection_entry = {
                "node": spec.nodes[to_idx].name,
                "type": conn.output,
                "index": conn.index,
            }
            # Ensure a single branch list (index 0) per from_name/output, then append entries to that branch
            outs = connections.setdefault(from_name, {}).setdefault(conn.output, [])
            if not outs:
                outs.append([])  # create branch 0
            outs[0].append(connection_entry)

        workflow: Dict[str, Any] = {
            "name": spec.name,
            "nodes": nodes,
            "connections": connections,
            "settings": spec.settings or {},
            "active": False,
            "tags": spec.tags or [],
        }
        if spec.description:
            workflow["description"] = spec.description
        return workflow

    def _node_to_json(self, node: NodeSpec) -> Dict[str, Any]:
        node_json: Dict[str, Any] = {
            "parameters": node.parameters,
            "id": node.id or "",
            "name": node.name,
            "type": node.type,
            "typeVersion": node.typeVersion,
            "position": node.position or [0, 0],
        }
        if node.credentials:
            node_json["credentials"] = node.credentials
        return node_json
