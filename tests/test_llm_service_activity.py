import asyncio
import json

import pytest

from app.services import llm_service


def test_parse_architecture_prompt_activity_empty_prompt_returns_empty_structure():
    result = asyncio.run(llm_service.parse_architecture_prompt("   ", "activity"))

    assert result == {
        "lanes": [],
        "nodes": [],
        "flows": [],
    }


def test_parse_architecture_prompt_activity_normalizes_nodes_and_flows(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "nodes": [
                    {"name": " Inicio ", "type": "initial"},
                    {"id": "seleccionar productos", "name": "Seleccionar productos", "type": "action"},
                    {"name": "Hay stock?", "type": "decision"},
                    {"name": "Fin compra", "type": "final"},
                ],
                "flows": [
                    {"from": "Inicio", "to": "seleccionar productos"},
                    {"from": "seleccionar productos", "to": "Hay stock?"},
                    {"from": "Hay stock?", "to": "Fin compra", "label": "[Sí]"},
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    result = asyncio.run(
        llm_service.parse_architecture_prompt("flujo simple de compra", "activity")
    )

    assert result["nodes"] == [
        {"id": "inicio", "name": "Inicio", "type": "initial", "lane": ""},
        {"id": "seleccionar_productos", "name": "Seleccionar productos", "type": "action", "lane": ""},
        {"id": "hay_stock", "name": "Hay stock?", "type": "decision", "lane": ""},
        {"id": "fin_compra", "name": "Fin compra", "type": "final", "lane": ""},
    ]
    assert result["flows"][2]["label"] == "[Sí]"


def test_parse_architecture_prompt_activity_decision_keeps_branch_labels(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "nodes": [
                    {"name": "Inicio", "type": "initial"},
                    {"name": "Procesar pago", "type": "action"},
                    {"name": "Pago aprobado", "type": "decision"},
                    {"name": "Generar orden", "type": "action"},
                    {"name": "Mostrar error", "type": "action"},
                    {"name": "Fin", "type": "final"},
                ],
                "flows": [
                    {"from": "Inicio", "to": "Procesar pago"},
                    {"from": "Procesar pago", "to": "Pago aprobado"},
                    {"from": "Pago aprobado", "to": "Generar orden", "label": "[Sí]"},
                    {"from": "Pago aprobado", "to": "Mostrar error", "label": "[No]"},
                    {"from": "Generar orden", "to": "Fin"},
                    {"from": "Mostrar error", "to": "Fin"},
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    result = asyncio.run(llm_service.parse_architecture_prompt("pago aprobado o rechazado", "activity"))

    assert any(node["type"] == "decision" for node in result["nodes"])
    assert {flow["label"] for flow in result["flows"] if flow["label"]} == {"[Sí]", "[No]"}


def test_parse_architecture_prompt_activity_preserves_v2_lanes_and_extended_node_types(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "lanes": ["Cliente", "Sistema", "PasarelaPago"],
                "nodes": [
                    {"name": "Inicio", "type": "initial", "lane": "Cliente"},
                    {"name": "Preparar pedido", "type": "action", "lane": "Sistema"},
                    {"name": "Validaciones paralelas", "type": "fork", "lane": "Sistema"},
                    {"name": "Pago", "type": "object", "lane": "PasarelaPago"},
                    {"name": "Sincronizar", "type": "join", "lane": "Sistema"},
                    {"name": "Fin", "type": "final", "lane": "Cliente"},
                ],
                "flows": [
                    {"from": "Inicio", "to": "Preparar pedido"},
                    {"from": "Preparar pedido", "to": "Validaciones paralelas"},
                    {"from": "Validaciones paralelas", "to": "Pago"},
                    {"from": "Pago", "to": "Sincronizar"},
                    {"from": "Sincronizar", "to": "Fin"},
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    result = asyncio.run(llm_service.parse_architecture_prompt("flujo paralelo con lanes", "activity"))

    assert result["lanes"] == ["Cliente", "Sistema", "PasarelaPago"]
    assert [node["type"] for node in result["nodes"]] == [
        "initial",
        "action",
        "fork",
        "object",
        "join",
        "final",
    ]
    assert result["nodes"][2]["lane"] == "Sistema"
    assert result["nodes"][3]["lane"] == "PasarelaPago"


def test_parse_architecture_prompt_activity_rejects_invalid_flow_references(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "nodes": [
                    {"name": "Inicio", "type": "initial"},
                    {"name": "Fin", "type": "final"},
                ],
                "flows": [
                    {"from": "Inicio", "to": "Nodo inexistente"},
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    with pytest.raises(ValueError, match="unknown nodes"):
        asyncio.run(llm_service.parse_architecture_prompt("flujo invalido", "activity"))


def test_parse_architecture_prompt_activity_rejects_missing_required_nodes(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "nodes": [
                    {"name": "Procesar", "type": "action"},
                    {"name": "Fin", "type": "final"},
                ],
                "flows": [
                    {"from": "Procesar", "to": "Fin"},
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    with pytest.raises(ValueError, match="at least 1 initial node, 1 final node and 1 flow"):
        asyncio.run(llm_service.parse_architecture_prompt("sin nodo inicial", "activity"))
