def test_ai_status_endpoint(client):
    response = client.get("/api/v1/ai/status")
    assert response.status_code == 200
    data = response.json()
    assert data["busy"] is False
    assert data["queue_length"] == 0
    assert data["current_task"] is None
