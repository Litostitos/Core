import pytest
from app import app, db, Store

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
        yield client

def test_create_store(client):
    response = client.post("/store", json={"name": "TestStore"})
    assert response.status_code == 201
    assert response.get_json()["name"] == "TestStore"

def test_get_stores(client):
    client.post("/store", json={"name": "TestStore"})
    response = client.get("/store")
    assert response.status_code == 200
    assert any(store["name"] == "TestStore" for store in response.get_json()["stores"])

