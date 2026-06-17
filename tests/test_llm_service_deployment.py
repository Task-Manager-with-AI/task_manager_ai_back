import asyncio

import pytest

from app.services import llm_service


def test_parse_architecture_prompt_deployment_empty_prompt_returns_empty_structure():
    result = asyncio.run(llm_service.parse_architecture_prompt("   ", "deployment"))

    assert result == {"nodes": [], "artifacts": [], "connections": []}


def test_parse_architecture_prompt_deployment_normalizes_nodes_artifacts_and_connections(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False):
        return """
        {
          "nodes": [
            {"id": "cliente", "name": "Cliente Web", "type": "external_node"},
            {"id": "server", "name": "Backend Server", "type": "node", "environment": "Produccion"},
            {"id": "runtime", "name": "JVM", "type": "execution_environment", "parentId": "server"}
          ],
          "artifacts": [
            {"id": "api", "name": "Backend API", "type": "service", "nodeId": "runtime"}
          ],
          "connections": [
            {"from": "cliente", "to": "api", "label": "HTTPS"}
          ]
        }
        """

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    result = asyncio.run(llm_service.parse_architecture_prompt("despliegue basico", "deployment"))

    assert len(result["nodes"]) == 3
    assert result["artifacts"][0]["nodeId"] == "runtime"
    assert result["connections"][0]["to"] == "api"


def test_parse_architecture_prompt_deployment_rejects_invalid_artifact_node_references(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False):
        return """
        {
          "nodes": [
            {"id": "backend", "name": "Backend Server", "type": "node"},
            {"id": "db", "name": "Base de Datos", "type": "database_node"}
          ],
          "artifacts": [
            {"id": "api", "name": "Backend API", "type": "service", "nodeId": "runtime_inexistente"}
          ],
          "connections": [
            {"from": "backend", "to": "db", "label": "TCP"}
          ]
        }
        """

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    with pytest.raises(ValueError, match="artifacts referencing unknown nodes"):
        asyncio.run(llm_service.parse_architecture_prompt("referencia invalida", "deployment"))


def test_parse_architecture_prompt_deployment_rejects_insufficient_structure(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False):
        return """
        {
          "nodes": [
            {"id": "backend", "name": "Backend Server", "type": "node"}
          ],
          "artifacts": [
            {"id": "api", "name": "Backend API", "type": "service", "nodeId": "backend"}
          ],
          "connections": []
        }
        """

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    with pytest.raises(ValueError, match="requires at least 2 nodes, 1 artifact or service, and 1 connection"):
        asyncio.run(llm_service.parse_architecture_prompt("insuficiente", "deployment"))
