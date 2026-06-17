import asyncio
import json

import pytest

from app.services import llm_service


def test_parse_architecture_prompt_component_empty_prompt_returns_empty_structure():
    result = asyncio.run(llm_service.parse_architecture_prompt("   ", "component"))

    assert result == {
        "layers": list(llm_service.COMPONENT_LAYERS),
        "components": [],
        "dependencies": [],
    }


def test_parse_architecture_prompt_component_normalizes_components_and_dependencies(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "components": [
                    {"name": " Cliente Web ", "stereotype": "frontend", "layer": "client"},
                    {"name": "API Gateway"},
                    {"name": "Servicio Pedidos", "stereotype": "service", "interfaces": {"provided": ["PedidosAPI"]}},
                ],
                "dependencies": [
                    {"from": "cliente web", "to": "api gateway", "label": "HTTPS"},
                    {"from": "API Gateway", "to": "Servicio Pedidos", "label": "crear pedido"},
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    result = asyncio.run(llm_service.parse_architecture_prompt("arquitectura por componentes", "component"))

    assert result["components"][0]["name"] == "Cliente Web"
    assert result["components"][1]["stereotype"] == "gateway"
    assert result["components"][1]["layer"] == "gateway"
    assert result["components"][2]["interfaces"]["provided"] == ["PedidosAPI"]
    assert len(result["dependencies"]) == 2


def test_parse_architecture_prompt_component_rejects_invalid_dependency_references(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "components": [
                    {"name": "Cliente Web", "stereotype": "frontend"},
                    {"name": "API Gateway", "stereotype": "gateway"},
                ],
                "dependencies": [
                    {"from": "Cliente Web", "to": "Servicio Fantasma"},
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    with pytest.raises(ValueError, match="unknown components"):
        asyncio.run(llm_service.parse_architecture_prompt("dependencia invalida", "component"))


def test_parse_architecture_prompt_component_rejects_insufficient_structure(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "components": [
                    {"name": "Solo Uno", "stereotype": "component"},
                ],
                "dependencies": [],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    with pytest.raises(ValueError, match="at least 2 components and 1 dependency"):
        asyncio.run(llm_service.parse_architecture_prompt("insuficiente", "component"))
