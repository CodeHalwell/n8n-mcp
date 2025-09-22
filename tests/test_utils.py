"""Tests for mcp_server.utils module."""
from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from mcp_server.utils import get_workflow_by_identifier, workflow_id_or_raise


class TestWorkflowIdOrRaise:
    """Test workflow_id_or_raise function."""

    def test_valid_string_id(self) -> None:
        """Test with valid string ID."""
        workflow = {"id": "test-id", "name": "Test Workflow"}
        result = workflow_id_or_raise(workflow)
        assert result == "test-id"

    def test_valid_int_id(self) -> None:
        """Test with valid integer ID.""" 
        workflow = {"id": 123, "name": "Test Workflow"}
        result = workflow_id_or_raise(workflow)
        assert result == 123

    def test_missing_id_default_error(self) -> None:
        """Test missing ID with default ValueError."""
        workflow = {"name": "Test Workflow"}
        with pytest.raises(ValueError, match="workflow response missing id"):
            workflow_id_or_raise(workflow)

    def test_none_id_default_error(self) -> None:
        """Test None ID with default ValueError."""
        workflow = {"id": None, "name": "Test Workflow"}
        with pytest.raises(ValueError, match="workflow response missing id"):
            workflow_id_or_raise(workflow)

    def test_custom_error_function(self) -> None:
        """Test with custom error function (HTTPException)."""
        workflow = {"name": "Test Workflow"}
        
        def make_http_error(msg: str) -> HTTPException:
            return HTTPException(status_code=502, detail=msg)
        
        with pytest.raises(HTTPException) as exc_info:
            workflow_id_or_raise(workflow, make_http_error)
        
        assert exc_info.value.status_code == 502
        assert exc_info.value.detail == "workflow response missing id"


class TestGetWorkflowByIdentifier:
    """Test get_workflow_by_identifier function."""

    @pytest.mark.asyncio
    async def test_find_by_id(self) -> None:
        """Test finding workflow by ID."""
        workflows = [
            {"id": "123", "name": "Workflow A"},
            {"id": "456", "name": "Workflow B"},
        ]
        
        client = AsyncMock()
        client.list_workflows.return_value = workflows
        
        result = await get_workflow_by_identifier(client, "123")
        assert result == {"id": "123", "name": "Workflow A"}
        client.list_workflows.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name(self) -> None:
        """Test finding workflow by name."""
        workflows = [
            {"id": "123", "name": "Workflow A"},
            {"id": "456", "name": "Workflow B"},
        ]
        
        client = AsyncMock()
        client.list_workflows.return_value = workflows
        
        result = await get_workflow_by_identifier(client, "Workflow B")
        assert result == {"id": "456", "name": "Workflow B"}
        client.list_workflows.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_string_id(self) -> None:
        """Test finding workflow by string representation of ID."""
        workflows = [
            {"id": 123, "name": "Workflow A"},  # numeric ID
            {"id": "456", "name": "Workflow B"},
        ]
        
        client = AsyncMock()
        client.list_workflows.return_value = workflows
        
        result = await get_workflow_by_identifier(client, "123")
        assert result == {"id": 123, "name": "Workflow A"}

    @pytest.mark.asyncio
    async def test_workflow_not_found(self) -> None:
        """Test workflow not found raises HTTPException."""
        workflows = [
            {"id": "123", "name": "Workflow A"},
        ]
        
        client = AsyncMock()
        client.list_workflows.return_value = workflows
        
        with pytest.raises(HTTPException) as exc_info:
            await get_workflow_by_identifier(client, "nonexistent")
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "workflow not found"

    @pytest.mark.asyncio 
    async def test_empty_workflow_list(self) -> None:
        """Test empty workflow list raises HTTPException."""
        client = AsyncMock()
        client.list_workflows.return_value = []
        
        with pytest.raises(HTTPException) as exc_info:
            await get_workflow_by_identifier(client, "any")
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "workflow not found"