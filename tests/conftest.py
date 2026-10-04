from pathlib import Path
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugin/runtime"))
from workshop_lab.server import LabServer
from workshop_lab.store import Store


@pytest.fixture
def service(tmp_path):
    server = LabServer(("127.0.0.1", 0), Store(tmp_path / "lab.sqlite3"), "test-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(3)
