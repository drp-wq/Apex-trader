import pytest
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ONLINE"


def test_api_safety():
    res = client.get("/safety")
    assert res.status_code == 200
    data = res.json()
    assert data["dry_run"] is True
    assert data["auto_execute"] is False
    assert data["production_enabled"] is False


def test_api_paper_account_and_order():
    res_acc = client.get("/paper/account")
    assert res_acc.status_code == 200
    assert res_acc.json()["balance"] >= 0.0

    # Submit valid paper order (500 distance * 0.01 qty = $5 risk = 1% of 500)
    order_payload = {
        "symbol": "BTCUSDT",
        "direction": "BUY",
        "price": 50000.0,
        "stop_loss": 49500.0,
        "take_profit": 51500.0,
        "quantity": 0.01
    }
    res_ord = client.post("/paper/order", json=order_payload)
    assert res_ord.status_code == 200
    assert res_ord.json()["status"] == "FILLED"

    # Verify in positions
    res_pos = client.get("/paper/positions")
    assert "BTCUSDT" in res_pos.json()


def test_api_emergency_flatten():
    # Flatten BTC position
    res_flat = client.post("/paper/flatten", json={"BTCUSDT": 50500.0})
    assert res_flat.status_code == 200
    assert res_flat.json()["status"] == "FLATTENED"

    res_pos = client.get("/paper/positions")
    assert "BTCUSDT" not in res_pos.json()
