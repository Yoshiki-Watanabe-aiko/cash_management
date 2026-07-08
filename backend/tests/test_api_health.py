def test_health_check_returns_ok_when_db_reachable(client):
    """DB疎通確認込みの/healthエンドポイントが正常時にstatus=okを返す。"""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
