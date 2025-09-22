"""Tests for FastAPI dependency and client lifecycle management."""
from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server.app import n8n_client_manager


class TestN8nClientManager:
    """Test FastAPI dependency for N8nClient lifecycle."""

    @pytest.mark.asyncio
    async def test_client_lifecycle(self) -> None:
        """Test that client is properly created and closed."""
        mock_client = AsyncMock()
        
        with patch("mcp_server.app._client") as mock_client_factory:
            mock_client_factory.return_value = mock_client
            
            # Use the dependency
            async with n8n_client_manager() as client:
                assert client is mock_client
                # Client should not be closed yet
                mock_client.close.assert_not_called()
            
            # After exiting context, client should be closed
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_closed_on_exception(self) -> None:
        """Test that client is closed even if exception occurs."""
        mock_client = AsyncMock()
        
        with patch("mcp_server.app._client") as mock_client_factory:
            mock_client_factory.return_value = mock_client
            
            with pytest.raises(ValueError, match="test error"):
                async with n8n_client_manager() as client:
                    assert client is mock_client
                    # Simulate an error
                    raise ValueError("test error")
            
            # Client should still be closed despite the exception
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_close_exception_handling(self) -> None:
        """Test that exceptions during close don't propagate."""
        mock_client = AsyncMock()
        mock_client.close.side_effect = Exception("Close failed")
        
        with patch("mcp_server.app._client") as mock_client_factory:
            mock_client_factory.return_value = mock_client
            
            # Should not raise exception even if close fails
            async with n8n_client_manager() as client:
                assert client is mock_client
            
            mock_client.close.assert_called_once()