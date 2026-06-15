from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_generate_diagram_rejects_invalid_type():
    response = client.post(
        "/api/v1/ea/generate",
        json={"prompt": "hola", "diagram_type": "component"},
    )

    assert response.status_code == 400
    assert "Unsupported diagram_type" in response.json()["detail"]


def test_generate_sequence_diagram_success(monkeypatch):
    async def fake_parse_architecture_prompt(prompt: str, diagram_type: str):
        return {
            "participants": [
                {"name": "Usuario", "type": "actor"},
                {"name": "Backend", "type": "control"},
            ],
            "messages": [
                {"from": "Usuario", "to": "Backend", "message": "login()", "kind": "sync"}
            ],
            "fragments": [],
            "activations": [],
        }

    class FakeService:
        def __init__(self, model_path: str):
            self.model_path = model_path

        def generate_diagram(self, architecture_data, output_path):
            return str(output_path)

    monkeypatch.setattr("app.api.v1.ea.parse_architecture_prompt", fake_parse_architecture_prompt)
    monkeypatch.setattr("app.api.v1.ea.EnterpriseArchitectService", FakeService)

    response = client.post(
        "/api/v1/ea/generate",
        json={"prompt": "Usuario inicia sesión", "diagram_type": "sequence"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["url"].endswith(".png")


def test_generate_sequence_diagram_returns_clear_server_error(monkeypatch):
    async def fake_parse_architecture_prompt(prompt: str, diagram_type: str):
        return {
            "participants": [
                {"name": "Usuario", "type": "actor"},
                {"name": "Backend", "type": "control"},
            ],
            "messages": [
                {"from": "Usuario", "to": "Backend", "message": "login()", "kind": "sync"}
            ],
            "fragments": [],
            "activations": [],
        }

    class FakeService:
        def __init__(self, model_path: str):
            self.model_path = model_path

        def generate_diagram(self, architecture_data, output_path):
            raise Exception("Sequence diagram generation requires Enterprise Architect COM and failed: COM down")

    monkeypatch.setattr("app.api.v1.ea.parse_architecture_prompt", fake_parse_architecture_prompt)
    monkeypatch.setattr("app.api.v1.ea.EnterpriseArchitectService", FakeService)

    response = client.post(
        "/api/v1/ea/generate",
        json={"prompt": "Usuario inicia sesión", "diagram_type": "sequence"},
    )

    assert response.status_code == 500
    assert "Sequence diagram generation requires Enterprise Architect COM" in response.json()["detail"]
