import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.mcp_service import official_mcp_bridge
from services.grafana_client import grafana_client

def pytest_configure(config):
    config.addinivalue_line("markers", "grafana_live: marks tests as requiring live Grafana Cloud credentials")

import asyncio

@pytest.fixture(autouse=True)
def cleanup_bridges_after_test():
    """Ensures subprocess pipes and HTTP clients are cleanly closed after each test."""
    yield
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(official_mcp_bridge.close())
        loop.run_until_complete(grafana_client.close())
        loop.close()
    except Exception:
        pass
