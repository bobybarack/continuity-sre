import os
import sys
from pathlib import Path
import pytest
import asyncio

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# Configure fast verification thresholds for snappy automated testing
os.environ.setdefault("CONTINUITY_VERIFY_TIMEOUT_SEC", "0.3")
os.environ.setdefault("CONTINUITY_VERIFY_POLL_INTERVAL_SEC", "0.05")

from services.mcp_service import official_mcp_bridge
from services.grafana_client import grafana_client
from services.chaos import chaos_manager
from services.transaction_manager import transaction_manager

def pytest_configure(config):
    config.addinivalue_line("markers", "grafana_live: marks tests as requiring live Grafana Cloud credentials")

@pytest.fixture(autouse=True)
def reset_state_per_test():
    """Resets chaos and transaction ledger state between tests without killing subprocess sessions."""
    yield
    try:
        chaos_manager.reset_to_normal()
        transaction_manager.clear()
    except Exception:
        pass

@pytest.fixture(scope="session", autouse=True)
def cleanup_bridges_session():
    """Ensures subprocess pipes and HTTP clients are cleanly closed after the test session completes."""
    yield
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(official_mcp_bridge.close())
        loop.run_until_complete(grafana_client.close())
        loop.close()
    except Exception:
        pass
