from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_routes_manifest():
    response = client.get('/manus-routes.json')
    assert response.status_code == 200
    assert any(route['path'] == '/app' for route in response.json()['routes'])
