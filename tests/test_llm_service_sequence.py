import asyncio
import json

import pytest

from app.services import llm_service


def test_parse_architecture_prompt_sequence_empty_prompt_returns_empty_structure():
    result = asyncio.run(llm_service.parse_architecture_prompt("   ", "sequence"))

    assert result == {
        "participants": [],
        "messages": [],
        "fragments": [],
        "activations": [],
    }


def test_parse_architecture_prompt_sequence_normalizes_llm_output(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "participants": [
                    {"name": " Usuario Web ", "type": "actor"},
                    {"name": "Auth Service"},
                    {"name": "BaseDatos", "type": "entity"},
                ],
                "messages": [
                    {
                        "from": "usuario web",
                        "to": "Auth Service",
                        "message": "login()",
                    },
                    {
                        "from": "Auth Service",
                        "to": "BaseDatos",
                        "message": "buscarUsuario()",
                        "kind": "async",
                    },
                    {
                        "from": "Auth Service",
                        "to": "Auth Service",
                        "message": "validarFormato()",
                        "kind": "sync",
                    },
                    {
                        "from": "BaseDatos",
                        "to": "Auth Service",
                        "message": "usuario",
                        "kind": "return",
                    },
                ],
                "fragments": [
                    {
                        "type": "alt",
                        "guard": "[credenciales validas]",
                        "start_message_index": 1,
                        "end_message_index": 4,
                    }
                ],
                "activations": [
                    {
                        "participant": "Auth Service",
                        "start_message_index": 1,
                        "end_message_index": 4,
                    }
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    result = asyncio.run(
        llm_service.parse_architecture_prompt(
            "Usuario inicia sesion y el backend consulta la base de datos",
            "sequence",
        )
    )

    assert result["participants"] == [
        {"name": "Usuario Web", "type": "actor"},
        {"name": "Auth Service", "type": "lifeline"},
        {"name": "BaseDatos", "type": "entity"},
    ]
    assert result["messages"][0]["kind"] == "sync"
    assert result["messages"][1]["kind"] == "async"
    assert result["messages"][2]["from"] == "Auth Service"
    assert result["messages"][2]["to"] == "Auth Service"
    assert result["messages"][3]["kind"] == "return"
    assert result["fragments"][0]["type"] == "alt"
    assert result["fragments"][0]["label"] == "[credenciales validas]"
    assert result["activations"][0]["participant"] == "Auth Service"


def test_parse_architecture_prompt_sequence_rejects_insufficient_structure(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "participants": [{"name": "SoloUno", "type": "actor"}],
                "messages": [],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    with pytest.raises(ValueError, match="at least 2 participants and 1 message"):
        asyncio.run(llm_service.parse_architecture_prompt("flujo insuficiente", "sequence"))
