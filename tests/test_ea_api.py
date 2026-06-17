from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_generate_diagram_rejects_invalid_type():
    response = client.post(
        "/api/v1/ea/generate",
        json={"prompt": "hola", "diagram_type": "invalid_type"},
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


def test_generate_activity_diagram_success(monkeypatch):
    async def fake_parse_architecture_prompt(prompt: str, diagram_type: str):
        return {
            "nodes": [
                {"id": "inicio", "name": "Inicio", "type": "initial"},
                {"id": "procesar", "name": "Procesar", "type": "action"},
                {"id": "fin", "name": "Fin", "type": "final"},
            ],
            "flows": [
                {"from": "inicio", "to": "procesar", "label": ""},
                {"from": "procesar", "to": "fin", "label": ""},
            ],
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
        json={"prompt": "flujo de actividad", "diagram_type": "activity"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_generate_activity_diagram_returns_clear_server_error(monkeypatch):
    async def fake_parse_architecture_prompt(prompt: str, diagram_type: str):
        return {
            "nodes": [
                {"id": "inicio", "name": "Inicio", "type": "initial"},
                {"id": "procesar", "name": "Procesar", "type": "action"},
                {"id": "fin", "name": "Fin", "type": "final"},
            ],
            "flows": [
                {"from": "inicio", "to": "procesar", "label": ""},
                {"from": "procesar", "to": "fin", "label": ""},
            ],
        }

    class FakeService:
        def __init__(self, model_path: str):
            self.model_path = model_path

        def generate_diagram(self, architecture_data, output_path):
            raise Exception("Activity diagram generation requires Enterprise Architect COM and failed: COM down")

    monkeypatch.setattr("app.api.v1.ea.parse_architecture_prompt", fake_parse_architecture_prompt)
    monkeypatch.setattr("app.api.v1.ea.EnterpriseArchitectService", FakeService)

    response = client.post(
        "/api/v1/ea/generate",
        json={"prompt": "flujo de actividad", "diagram_type": "activity"},
    )

    assert response.status_code == 500
    assert "Activity diagram generation requires Enterprise Architect COM" in response.json()["detail"]


def test_generate_component_diagram_success(monkeypatch):
    async def fake_parse_architecture_prompt(prompt: str, diagram_type: str):
        return {
            "layers": ["client", "gateway"],
            "components": [
                {"id": "cliente", "name": "Cliente Web", "stereotype": "frontend", "layer": "client", "interfaces": {"provided": [], "required": []}},
                {"id": "gateway", "name": "API Gateway", "stereotype": "gateway", "layer": "gateway", "interfaces": {"provided": [], "required": []}},
            ],
            "dependencies": [
                {"from": "cliente", "to": "gateway", "label": "HTTPS"},
            ],
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
        json={"prompt": "arquitectura por componentes", "diagram_type": "component"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_generate_component_diagram_returns_clear_server_error(monkeypatch):
    async def fake_parse_architecture_prompt(prompt: str, diagram_type: str):
        return {
            "layers": ["client", "gateway"],
            "components": [
                {"id": "cliente", "name": "Cliente Web", "stereotype": "frontend", "layer": "client", "interfaces": {"provided": [], "required": []}},
                {"id": "gateway", "name": "API Gateway", "stereotype": "gateway", "layer": "gateway", "interfaces": {"provided": [], "required": []}},
            ],
            "dependencies": [
                {"from": "cliente", "to": "gateway", "label": "HTTPS"},
            ],
        }

    class FakeService:
        def __init__(self, model_path: str):
            self.model_path = model_path

        def generate_diagram(self, architecture_data, output_path):
            raise Exception("Component diagram generation requires Enterprise Architect COM and failed: COM down")

    monkeypatch.setattr("app.api.v1.ea.parse_architecture_prompt", fake_parse_architecture_prompt)
    monkeypatch.setattr("app.api.v1.ea.EnterpriseArchitectService", FakeService)

    response = client.post(
        "/api/v1/ea/generate",
        json={"prompt": "arquitectura por componentes", "diagram_type": "component"},
    )

    assert response.status_code == 500
    assert "Component diagram generation requires Enterprise Architect COM" in response.json()["detail"]


def test_generate_deployment_diagram_success(monkeypatch):
    async def fake_parse_architecture_prompt(prompt: str, diagram_type: str):
        return {
            "nodes": [
                {"id": "cliente", "name": "Cliente Web", "type": "external_node", "environment": "", "parentId": ""},
                {"id": "backend", "name": "Backend Server", "type": "node", "environment": "Produccion", "parentId": ""},
            ],
            "artifacts": [
                {"id": "api", "name": "Backend API", "type": "service", "nodeId": "backend"},
            ],
            "connections": [
                {"from": "cliente", "to": "backend", "label": "HTTPS"},
            ],
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
        json={"prompt": "infraestructura de despliegue", "diagram_type": "deployment"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_generate_deployment_diagram_returns_clear_server_error(monkeypatch):
    async def fake_parse_architecture_prompt(prompt: str, diagram_type: str):
        return {
            "nodes": [
                {"id": "cliente", "name": "Cliente Web", "type": "external_node", "environment": "", "parentId": ""},
                {"id": "backend", "name": "Backend Server", "type": "node", "environment": "Produccion", "parentId": ""},
            ],
            "artifacts": [
                {"id": "api", "name": "Backend API", "type": "service", "nodeId": "backend"},
            ],
            "connections": [
                {"from": "cliente", "to": "backend", "label": "HTTPS"},
            ],
        }

    class FakeService:
        def __init__(self, model_path: str):
            self.model_path = model_path

        def generate_diagram(self, architecture_data, output_path):
            raise Exception("Deployment diagram generation requires Enterprise Architect COM and failed: COM down")

    monkeypatch.setattr("app.api.v1.ea.parse_architecture_prompt", fake_parse_architecture_prompt)
    monkeypatch.setattr("app.api.v1.ea.EnterpriseArchitectService", FakeService)

    response = client.post(
        "/api/v1/ea/generate",
        json={"prompt": "infraestructura de despliegue", "diagram_type": "deployment"},
    )

    assert response.status_code == 500
    assert "Deployment diagram generation requires Enterprise Architect COM" in response.json()["detail"]
