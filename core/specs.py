from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NodeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None
    name: str
    type: str
    typeVersion: int = 1
    parameters: Dict[str, Any] = Field(default_factory=dict)
    credentials: Optional[Dict[str, Any]] = None
    position: Optional[List[int]] = None


class ConnectionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fromNode: str
    toNode: str
    output: Literal["main"] = "main"
    index: int = 0

    @field_validator("index")
    @classmethod
    def validate_index(cls, value: int) -> int:
        if value < 0:
            raise ValueError("index must be >= 0")
        return value


class WorkflowSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: Optional[str] = None
    nodes: List[NodeSpec]
    connections: List[ConnectionSpec]
    settings: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
