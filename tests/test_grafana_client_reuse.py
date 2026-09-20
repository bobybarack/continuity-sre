import pytest
import asyncio
import sys
import httpx
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.grafana_client import GrafanaCloudClient

@pytest.mark.asyncio
async def test_grafana_client_instance_reused_across_requests():
    client_wrapper = GrafanaCloudClient()
    
    # 1. First client fetch
    client1 = await client_wrapper.get_client()
    assert client1 is not None
    assert not client1.is_closed
    
    # 2. Second client fetch must return the exact same object
    client2 = await client_wrapper.get_client()
    assert client2 is client1
    
    # Clean up
    await client_wrapper.close()

@pytest.mark.asyncio
async def test_grafana_client_close_happens_cleanly():
    client_wrapper = GrafanaCloudClient()
    
    client = await client_wrapper.get_client()
    assert not client.is_closed
    
    # Close client
    await client_wrapper.close()
    assert client.is_closed
    assert client_wrapper._client is None
    
    # Calling close again should not raise errors
    await client_wrapper.close()

@pytest.mark.asyncio
async def test_grafana_client_retry_logic_works():
    client_wrapper = GrafanaCloudClient()
    client_wrapper.max_retries = 3
    client_wrapper.retry_delay_sec = 0.01
    
    attempts = 0
    
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(503, text="Service Temporarily Unavailable")
        return httpx.Response(200, json={"status": "recovered"})
    
    transport = httpx.MockTransport(handler)
    mock_http_client = httpx.AsyncClient(transport=transport)
    client_wrapper._client = mock_http_client
    
    res = await client_wrapper._execute_with_retry("GET", "http://test-grafana/api/datasources")
    assert res.status_code == 200
    assert res.json() == {"status": "recovered"}
    assert attempts == 3
    
    await client_wrapper.close()
