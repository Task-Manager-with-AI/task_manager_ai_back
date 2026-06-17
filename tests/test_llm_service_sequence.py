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


def test_parse_architecture_prompt_sequence_merges_overlapping_alt_fragments(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "participants": [
                    {"name": "Usuario", "type": "actor"},
                    {"name": "Backend", "type": "control"},
                    {"name": "BaseDatos", "type": "entity"},
                ],
                "messages": [
                    {"from": "Usuario", "to": "Backend", "message": "login()", "kind": "sync"},
                    {"from": "Backend", "to": "BaseDatos", "message": "buscarUsuario()", "kind": "sync"},
                    {"from": "BaseDatos", "to": "Backend", "message": "usuario()", "kind": "return"},
                    {"from": "Backend", "to": "Usuario", "message": "ok()", "kind": "return"},
                    {"from": "Backend", "to": "Usuario", "message": "errorCredenciales()", "kind": "return"},
                ],
                "fragments": [
                    {
                        "type": "alt",
                        "label": "Credenciales validas",
                        "start_message_index": 2,
                        "end_message_index": 4,
                    },
                    {
                        "type": "alt",
                        "label": "Credenciales invalidas",
                        "start_message_index": 2,
                        "end_message_index": 5,
                    },
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    result = asyncio.run(llm_service.parse_architecture_prompt("login con exito o error", "sequence"))

    assert len(result["fragments"]) == 1
    assert result["fragments"][0]["type"] == "alt"
    assert result["fragments"][0]["start_message_index"] == 2
    assert result["fragments"][0]["end_message_index"] == 5
    assert result["fragments"][0]["label"] == "Alternativas"
    assert len(result["fragments"][0]["branches"]) == 2
    assert result["fragments"][0]["branches"][0]["label"] == "Credenciales validas"
    assert result["fragments"][0]["branches"][1]["label"] == "Credenciales invalidas"


def test_parse_architecture_prompt_sequence_expands_alt_when_it_only_covers_return_messages(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "participants": [
                    {"name": "Usuario", "type": "actor"},
                    {"name": "Frontend", "type": "boundary"},
                    {"name": "Backend", "type": "control"},
                    {"name": "BaseDatos", "type": "entity"},
                ],
                "messages": [
                    {"from": "Usuario", "to": "Frontend", "message": "ingresarCredenciales()", "kind": "sync"},
                    {"from": "Frontend", "to": "Backend", "message": "login()", "kind": "sync"},
                    {"from": "Backend", "to": "Backend", "message": "validarFormato()", "kind": "sync"},
                    {"from": "Backend", "to": "BaseDatos", "message": "buscarUsuario()", "kind": "sync"},
                    {"from": "BaseDatos", "to": "Backend", "message": "datosUsuario()", "kind": "return"},
                    {"from": "Backend", "to": "Frontend", "message": "ok()", "kind": "return"},
                    {"from": "Backend", "to": "Frontend", "message": "errorCredenciales()", "kind": "return"},
                ],
                "fragments": [
                    {
                        "type": "alt",
                        "label": "Credenciales validas",
                        "start_message_index": 6,
                        "end_message_index": 6,
                    },
                    {
                        "type": "alt",
                        "label": "Credenciales invalidas",
                        "start_message_index": 7,
                        "end_message_index": 7,
                    },
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    result = asyncio.run(llm_service.parse_architecture_prompt("login con ramas de exito y error", "sequence"))

    assert len(result["fragments"]) == 1
    assert result["fragments"][0]["type"] == "alt"
    assert result["fragments"][0]["start_message_index"] == 4
    assert result["fragments"][0]["end_message_index"] == 7


def test_parse_architecture_prompt_sequence_expands_alt_to_decision_context_for_mixed_branch_messages(monkeypatch):
    async def fake_call_llm(prompt: str, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "participants": [
                    {"name": "Usuario", "type": "actor"},
                    {"name": "Frontend", "type": "boundary"},
                    {"name": "Backend", "type": "control"},
                    {"name": "BaseDatos", "type": "entity"},
                ],
                "messages": [
                    {"from": "Usuario", "to": "Frontend", "message": "ingresarCredenciales()", "kind": "sync"},
                    {"from": "Frontend", "to": "Backend", "message": "solicitarLogin()", "kind": "sync"},
                    {"from": "Backend", "to": "Backend", "message": "validarFormato()", "kind": "sync"},
                    {"from": "Backend", "to": "BaseDatos", "message": "buscarUsuario()", "kind": "sync"},
                    {"from": "BaseDatos", "to": "Backend", "message": "usuarioEncontrado()", "kind": "return"},
                    {"from": "Backend", "to": "Backend", "message": "verificarPassword()", "kind": "sync"},
                    {"from": "Backend", "to": "Backend", "message": "generarToken()", "kind": "sync"},
                    {"from": "Backend", "to": "Frontend", "message": "respuestaExito()", "kind": "return"},
                    {"from": "Backend", "to": "Frontend", "message": "respuestaError()", "kind": "return"},
                    {"from": "Frontend", "to": "Usuario", "message": "mostrarError()", "kind": "sync"},
                ],
                "fragments": [
                    {
                        "type": "alt",
                        "label": "Credenciales validas",
                        "start_message_index": 8,
                        "end_message_index": 8,
                    },
                    {
                        "type": "alt",
                        "label": "Credenciales invalidas",
                        "start_message_index": 9,
                        "end_message_index": 10,
                    },
                ],
            }
        )

    monkeypatch.setattr(llm_service, "_call_llm", fake_call_llm)

    result = asyncio.run(llm_service.parse_architecture_prompt("login con ramas de exito y error", "sequence"))

    assert len(result["fragments"]) == 1
    assert result["fragments"][0]["start_message_index"] == 4
    assert result["fragments"][0]["end_message_index"] == 10
