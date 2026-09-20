import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.mcp_service import parse_mcp_tool_result, OfficialGrafanaMCPBridge

class DummyTextContent:
    def __init__(self, text: str):
        self.text = text

class DummyDataContent:
    def __init__(self, data: dict):
        self.data = data

class DummyResult:
    def __init__(self, content=None, isError=False):
        self.content = content or []
        self.isError = isError

def test_parse_mcp_tool_result_single_text_json():
    res = DummyResult(content=[DummyTextContent('{"status": "success", "val": 42}')])
    parsed = parse_mcp_tool_result(res)
    assert parsed == {"status": "success", "val": 42}

def test_parse_mcp_tool_result_single_text_plain():
    res = DummyResult(content=[DummyTextContent("raw string response")])
    parsed = parse_mcp_tool_result(res)
    assert parsed == "raw string response"

def test_parse_mcp_tool_result_is_error():
    res = DummyResult(content=[DummyTextContent("Query timed out or failed")], isError=True)
    parsed = parse_mcp_tool_result(res)
    assert parsed["status"] == "error"
    assert parsed["error"] == "Query timed out or failed"

def test_parse_mcp_tool_result_structured_content():
    res = DummyResult(content=[DummyDataContent({"subsystem": "DRM", "status": "FAILOVER"})])
    parsed = parse_mcp_tool_result(res)
    assert parsed == {"subsystem": "DRM", "status": "FAILOVER"}

def test_parse_mcp_tool_result_multiple_content_blocks():
    res = DummyResult(content=[
        DummyTextContent('{"part": 1}'),
        DummyTextContent('{"part": 2}')
    ])
    parsed = parse_mcp_tool_result(res)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0] == {"part": 1}
    assert parsed[1] == {"part": 2}

def test_parse_mcp_tool_result_empty():
    res = DummyResult(content=[])
    parsed = parse_mcp_tool_result(res)
    assert parsed == {}

@pytest.mark.asyncio
async def test_mcp_bridge_session_reuse():
    bridge = OfficialGrafanaMCPBridge()
    mock_session = AsyncMock()
    mock_tool = MagicMock()
    mock_tool.name = "query_prometheus"
    mock_tool.description = "prom query"
    mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])
    
    # Pre-populate session
    bridge._session = mock_session
    
    tools1 = await bridge.list_official_tools()
    tools2 = await bridge.list_official_tools()
    
    assert len(tools1) == 1
    assert tools1[0]["name"] == "query_prometheus"
    assert mock_session.list_tools.call_count == 2
    # Verify session instance remained the same
    assert bridge._session is mock_session

@pytest.mark.asyncio
async def test_mcp_bridge_timeout_handling():
    bridge = OfficialGrafanaMCPBridge()
    bridge.call_timeout = 0.05
    
    mock_session = AsyncMock()
    async def slow_call(*args, **kwargs):
        await asyncio.sleep(0.2)
        return DummyResult(content=[DummyTextContent("ok")])
    
    mock_session.call_tool.side_effect = slow_call
    bridge._session = mock_session
    
    res = await bridge.call_official_tool("query_prometheus", {"expr": "up"})
    assert res is None
    # Verify session was reset upon timeout
    assert bridge._session is None

@pytest.mark.asyncio
async def test_mcp_bridge_reconnect_after_failure():
    bridge = OfficialGrafanaMCPBridge()
    
    # 1. Faulty session that raises BrokenPipeError
    faulty_session = AsyncMock()
    faulty_session.call_tool.side_effect = BrokenPipeError("Stdio channel closed")
    bridge._session = faulty_session
    
    res = await bridge.call_official_tool("query_loki_logs", {"logql": "{app='test'}"})
    assert res is None
    # Session reset
    assert bridge._session is None
    
    # 2. Re-supply working session
    working_session = AsyncMock()
    working_session.call_tool.return_value = DummyResult(content=[DummyTextContent('{"status": "ok"}')])
    bridge._session = working_session
    
    res2 = await bridge.call_official_tool("query_loki_logs", {"logql": "{app='test'}"})
    assert res2 == {"status": "ok"}
