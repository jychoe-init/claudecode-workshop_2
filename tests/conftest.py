from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workshop_core.local_api import LabServer, LocalStore


@pytest.fixture
def service(tmp_path):
    store = LocalStore(tmp_path / "api.sqlite3")
    store.register("participant-token-a", "p001")
    store.register("participant-token-b", "p002")
    server = LabServer(("127.0.0.1", 0), store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(3)
