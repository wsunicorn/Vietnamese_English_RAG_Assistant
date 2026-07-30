import os

os.environ["AUTO_CREATE_TABLES"] = "false"

from fastapi.testclient import TestClient

from app.main import app


def test_healthz():
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_realtime_websocket_connects():
    with TestClient(app) as client, client.websocket_connect("/ws/realtime") as websocket:
        event = websocket.receive_json()

    assert event["type"] == "connected"
