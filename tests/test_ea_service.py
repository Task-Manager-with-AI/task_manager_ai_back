import platform

import pytest

from app.services.ea_service import EnterpriseArchitectService


def test_generate_diagram_sequence_uses_ea_only(monkeypatch, tmp_path):
    service = EnterpriseArchitectService("modelo.eapx")
    called = {"ea": 0, "mermaid": 0}

    def fake_generate_via_ea(architecture_data, output_path):
        called["ea"] += 1
        return str(output_path)

    def fake_generate_via_mermaid(architecture_data, output_path):
        called["mermaid"] += 1
        return "should-not-happen"

    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(service, "_generate_via_ea", fake_generate_via_ea)
    monkeypatch.setattr(service, "_generate_via_mermaid", fake_generate_via_mermaid)

    output = service.generate_diagram(
        {
            "diagram_type": "sequence",
            "participants": [{"name": "A", "type": "actor"}, {"name": "B", "type": "lifeline"}],
            "messages": [{"from": "A", "to": "B", "message": "ping", "kind": "sync"}],
        },
        tmp_path / "sequence.png",
    )

    assert called == {"ea": 1, "mermaid": 0}
    assert output.endswith("sequence.png")


def test_generate_diagram_sequence_failure_raises_clear_error(monkeypatch, tmp_path):
    service = EnterpriseArchitectService("modelo.eapx")

    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        service,
        "_generate_via_ea",
        lambda architecture_data, output_path: (_ for _ in ()).throw(Exception("COM down")),
    )

    with pytest.raises(Exception, match="Sequence diagram generation requires Enterprise Architect COM"):
        service.generate_diagram(
            {
                "diagram_type": "sequence",
                "participants": [{"name": "A", "type": "actor"}, {"name": "B", "type": "lifeline"}],
                "messages": [{"from": "A", "to": "B", "message": "ping", "kind": "sync"}],
            },
            tmp_path / "sequence.png",
        )


def test_generate_diagram_class_falls_back_to_mermaid(monkeypatch, tmp_path):
    service = EnterpriseArchitectService("modelo.eapx")

    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        service,
        "_generate_via_ea",
        lambda architecture_data, output_path: (_ for _ in ()).throw(Exception("EA unavailable")),
    )
    monkeypatch.setattr(service, "_generate_via_mermaid", lambda architecture_data, output_path: "fallback.png")

    output = service.generate_diagram(
        {
            "diagram_type": "class",
            "elements": [],
            "relationships": [],
        },
        tmp_path / "class.png",
    )

    assert output == "fallback.png"


def test_dispatch_ea_generation_routes_sequence_to_sequence_handler(monkeypatch, tmp_path):
    service = EnterpriseArchitectService("modelo.eapx")

    monkeypatch.setattr(
        service,
        "_generate_sequence_via_ea",
        lambda repository, project_interface, package, architecture_data, output_path: "sequence.png",
    )
    monkeypatch.setattr(
        service,
        "_generate_static_via_ea",
        lambda repository, project_interface, package, architecture_data, output_path: "static.png",
    )

    output = service._dispatch_ea_generation(
        repository=object(),
        project_interface=object(),
        package=object(),
        architecture_data={"diagram_type": "sequence"},
        output_path=tmp_path / "sequence.png",
    )

    assert output == "sequence.png"


def test_build_sequence_layout_scopes_nested_fragments_to_involved_participants():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_sequence_layout(
        participants=[
            {"name": "Usuario", "type": "actor"},
            {"name": "Frontend", "type": "boundary"},
            {"name": "Backend", "type": "control"},
            {"name": "BaseDatos", "type": "entity"},
        ],
        messages=[
            {"from": "Usuario", "to": "Frontend", "message": "ingresarCredenciales()", "kind": "sync"},
            {"from": "Frontend", "to": "Backend", "message": "login()", "kind": "sync"},
            {"from": "Backend", "to": "BaseDatos", "message": "buscarUsuario()", "kind": "async"},
            {"from": "BaseDatos", "to": "Backend", "message": "usuario()", "kind": "return"},
        ],
        fragments=[
            {"type": "loop", "label": "Reintentos", "start_message_index": 1, "end_message_index": 2},
            {"type": "alt", "label": "[credenciales validas]", "start_message_index": 2, "end_message_index": 4},
        ],
    )

    loop_box, alt_box = layout["fragment_boxes"]
    assert loop_box["left"] < alt_box["left"]
    assert loop_box["right"] < layout["right_edge"]
    assert alt_box["right"] > loop_box["right"]
    assert alt_box["top"] > loop_box["top"]


def test_map_sequence_participant_type_uses_clean_lifelines_for_non_actors():
    service = EnterpriseArchitectService("modelo.eapx")

    assert service._map_sequence_participant_type("actor") == ("Actor", "")
    assert service._map_sequence_participant_type("control") == ("Object", "Lifeline")
    assert service._map_sequence_participant_type("entity") == ("Object", "Lifeline")
