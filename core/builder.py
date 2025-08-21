from __future__ import annotations

from typing import Any, Dict, List

from core.specs import WorkflowSpec, NodeSpec, ConnectionSpec


class WorkflowBuilder:
	def __init__(self) -> None:
		pass

	def build(self, spec: WorkflowSpec) -> Dict[str, Any]:
		# Map NodeSpec to n8n node JSON.
		nodes = [self._node_to_json(node) for node in spec.nodes]
		connections: Dict[str, Dict[str, List[List[int]]]] = {}
		name_to_index = {n.name: i for i, n in enumerate(spec.nodes)}
		for conn in spec.connections:
			from_idx = name_to_index[conn.fromNode]
			to_idx = name_to_index[conn.toNode]
			from_name = spec.nodes[from_idx].name
			to_name = spec.nodes[to_idx].name
			connections.setdefault(from_name, {}).setdefault(conn.output, []).append([to_idx, conn.index])

		workflow: Dict[str, Any] = {
			"name": spec.name,
			"nodes": nodes,
			"connections": connections,
			"settings": spec.settings or {},
			"active": False,
			"tags": spec.tags or [],
		}
		return workflow

	def _node_to_json(self, node: NodeSpec) -> Dict[str, Any]:
		return {
			"parameters": node.parameters,
			"id": node.id or "",
			"name": node.name,
			"type": node.type,
			"typeVersion": node.typeVersion,
			"position": node.position or [0, 0],
			**({"credentials": node.credentials} if node.credentials else {}),
		}