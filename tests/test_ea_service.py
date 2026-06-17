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


def test_generate_diagram_activity_uses_ea_only(monkeypatch, tmp_path):
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
            "diagram_type": "activity",
            "nodes": [
                {"id": "inicio", "name": "Inicio", "type": "initial"},
                {"id": "procesar", "name": "Procesar", "type": "action"},
                {"id": "fin", "name": "Fin", "type": "final"},
            ],
            "flows": [
                {"from": "inicio", "to": "procesar", "label": ""},
                {"from": "procesar", "to": "fin", "label": ""},
            ],
        },
        tmp_path / "activity.png",
    )

    assert called == {"ea": 1, "mermaid": 0}
    assert output.endswith("activity.png")


def test_generate_diagram_component_uses_ea_only(monkeypatch, tmp_path):
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
            "diagram_type": "component",
            "layers": ["client", "gateway"],
            "components": [
                {"id": "cliente", "name": "Cliente Web", "stereotype": "frontend", "layer": "client"},
                {"id": "gateway", "name": "API Gateway", "stereotype": "gateway", "layer": "gateway"},
            ],
            "dependencies": [
                {"from": "cliente", "to": "gateway", "label": "HTTPS"},
            ],
        },
        tmp_path / "component.png",
    )

    assert called == {"ea": 1, "mermaid": 0}
    assert output.endswith("component.png")


def test_generate_diagram_deployment_uses_ea_only(monkeypatch, tmp_path):
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
            "diagram_type": "deployment",
            "nodes": [
                {"id": "cliente", "name": "Cliente Web", "type": "external_node"},
                {"id": "backend", "name": "Backend Server", "type": "node"},
            ],
            "artifacts": [
                {"id": "api", "name": "Backend API", "type": "service", "nodeId": "backend"},
            ],
            "connections": [
                {"from": "cliente", "to": "backend", "label": "HTTPS"},
            ],
        },
        tmp_path / "deployment.png",
    )

    assert called == {"ea": 1, "mermaid": 0}
    assert output.endswith("deployment.png")


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


def test_generate_diagram_activity_failure_raises_clear_error(monkeypatch, tmp_path):
    service = EnterpriseArchitectService("modelo.eapx")

    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        service,
        "_generate_via_ea",
        lambda architecture_data, output_path: (_ for _ in ()).throw(Exception("COM down")),
    )

    with pytest.raises(Exception, match="Activity diagram generation requires Enterprise Architect COM"):
        service.generate_diagram(
            {
                "diagram_type": "activity",
                "nodes": [
                    {"id": "inicio", "name": "Inicio", "type": "initial"},
                    {"id": "procesar", "name": "Procesar", "type": "action"},
                    {"id": "fin", "name": "Fin", "type": "final"},
                ],
                "flows": [
                    {"from": "inicio", "to": "procesar", "label": ""},
                    {"from": "procesar", "to": "fin", "label": ""},
                ],
            },
            tmp_path / "activity.png",
        )


def test_generate_diagram_component_failure_raises_clear_error(monkeypatch, tmp_path):
    service = EnterpriseArchitectService("modelo.eapx")

    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        service,
        "_generate_via_ea",
        lambda architecture_data, output_path: (_ for _ in ()).throw(Exception("COM down")),
    )

    with pytest.raises(Exception, match="Component diagram generation requires Enterprise Architect COM"):
        service.generate_diagram(
            {
                "diagram_type": "component",
                "layers": ["client", "gateway"],
                "components": [
                    {"id": "cliente", "name": "Cliente Web", "stereotype": "frontend", "layer": "client"},
                    {"id": "gateway", "name": "API Gateway", "stereotype": "gateway", "layer": "gateway"},
                ],
                "dependencies": [
                    {"from": "cliente", "to": "gateway", "label": "HTTPS"},
                ],
            },
            tmp_path / "component.png",
        )


def test_generate_diagram_deployment_failure_raises_clear_error(monkeypatch, tmp_path):
    service = EnterpriseArchitectService("modelo.eapx")

    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        service,
        "_generate_via_ea",
        lambda architecture_data, output_path: (_ for _ in ()).throw(Exception("COM down")),
    )

    with pytest.raises(Exception, match="Deployment diagram generation requires Enterprise Architect COM"):
        service.generate_diagram(
            {
                "diagram_type": "deployment",
                "nodes": [
                    {"id": "cliente", "name": "Cliente Web", "type": "external_node"},
                    {"id": "backend", "name": "Backend Server", "type": "node"},
                ],
                "artifacts": [
                    {"id": "api", "name": "Backend API", "type": "service", "nodeId": "backend"},
                ],
                "connections": [
                    {"from": "cliente", "to": "backend", "label": "HTTPS"},
                ],
            },
            tmp_path / "deployment.png",
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


def test_dispatch_ea_generation_routes_activity_to_activity_handler(monkeypatch, tmp_path):
    service = EnterpriseArchitectService("modelo.eapx")

    monkeypatch.setattr(
        service,
        "_generate_activity_via_ea",
        lambda repository, project_interface, package, architecture_data, output_path: "activity.png",
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
        architecture_data={"diagram_type": "activity"},
        output_path=tmp_path / "activity.png",
    )

    assert output == "activity.png"


def test_dispatch_ea_generation_routes_component_to_component_handler(monkeypatch, tmp_path):
    service = EnterpriseArchitectService("modelo.eapx")

    monkeypatch.setattr(
        service,
        "_generate_component_via_ea",
        lambda repository, project_interface, package, architecture_data, output_path: "component.png",
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
        architecture_data={"diagram_type": "component"},
        output_path=tmp_path / "component.png",
    )

    assert output == "component.png"


def test_dispatch_ea_generation_routes_deployment_to_deployment_handler(monkeypatch, tmp_path):
    service = EnterpriseArchitectService("modelo.eapx")

    monkeypatch.setattr(
        service,
        "_generate_deployment_via_ea",
        lambda repository, project_interface, package, architecture_data, output_path: "deployment.png",
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
        architecture_data={"diagram_type": "deployment"},
        output_path=tmp_path / "deployment.png",
    )

    assert output == "deployment.png"


def test_build_deployment_layout_places_scene_roles_in_expected_regions():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_deployment_layout(
        nodes=[
            {"id": "cliente", "name": "Cliente / Navegador", "type": "external_node"},
            {"id": "web", "name": "Servidor Web", "type": "node"},
            {"id": "app", "name": "Servidor de Aplicaciones", "type": "node"},
            {"id": "db", "name": "Base de Datos", "type": "database_node"},
            {"id": "pagos", "name": "Pasarela de Pago Externa", "type": "external_node"},
        ],
        artifacts=[
            {"id": "api", "name": "Backend API", "type": "service", "nodeId": "app"},
            {"id": "worker", "name": "Worker", "type": "service", "nodeId": "app"},
            {"id": "auth", "name": "Auth", "type": "service", "nodeId": "app"},
        ],
    )

    assert layout["nodes"]["cliente"]["left"] < layout["nodes"]["web"]["left"] < layout["nodes"]["app"]["left"] < layout["nodes"]["db"]["left"]
    assert layout["nodes"]["pagos"]["top"] >= service.DEPLOYMENT_LOWER_ROW_Y
    assert layout["nodes"]["app"]["height"] > layout["nodes"]["web"]["height"]
    assert layout["nodes"]["pagos"]["left"] >= layout["nodes"]["app"]["left"]


def test_build_deployment_layout_keeps_generic_nodes_when_web_nodes_exist():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_deployment_layout(
        nodes=[
            {"id": "web", "name": "Servidor Web", "type": "node"},
            {"id": "cache", "name": "Servidor Cache", "type": "node"},
            {"id": "db", "name": "Base de Datos", "type": "database_node"},
        ],
        artifacts=[
            {"id": "nginx", "name": "Nginx", "type": "service", "nodeId": "web"},
            {"id": "redis", "name": "Redis", "type": "service", "nodeId": "cache"},
        ],
    )

    assert "cache" in layout["nodes"]
    assert layout["nodes"]["cache"]["left"] > layout["nodes"]["web"]["left"]


def test_build_deployment_layout_avoids_overlap_between_left_column_and_app_column():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_deployment_layout(
        nodes=[
            {"id": "cliente", "name": "Cliente / Navegador", "type": "external_node"},
            {"id": "web", "name": "Servidor Web", "type": "node"},
            {"id": "app_server", "name": "Servidor de Aplicaciones", "type": "node"},
            {"id": "runtime", "name": "JVM", "type": "execution_environment"},
            {"id": "db", "name": "Base de Datos", "type": "database_node"},
        ],
        artifacts=[
            {"id": "api", "name": "Backend API", "type": "service", "nodeId": "runtime"},
            {"id": "worker", "name": "Worker", "type": "service", "nodeId": "runtime"},
        ],
    )

    web_right = layout["nodes"]["web"]["left"] + layout["nodes"]["web"]["width"]
    leftmost_app = min(layout["nodes"]["app_server"]["left"], layout["nodes"]["runtime"]["left"])
    assert web_right <= leftmost_app


def test_build_deployment_layout_pushes_database_after_rightmost_app_node():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_deployment_layout(
        nodes=[
            {"id": "web", "name": "Servidor Web", "type": "node"},
            {"id": "runtime", "name": "JVM", "type": "execution_environment"},
            {"id": "app_server", "name": "Servidor de Aplicaciones", "type": "node"},
            {"id": "db", "name": "Base de Datos", "type": "database_node"},
        ],
        artifacts=[
            {"id": "api", "name": "Backend API", "type": "service", "nodeId": "runtime"},
            {"id": "worker", "name": "Worker", "type": "service", "nodeId": "runtime"},
        ],
    )

    rightmost_app = max(
        layout["nodes"]["runtime"]["left"] + layout["nodes"]["runtime"]["width"],
        layout["nodes"]["app_server"]["left"] + layout["nodes"]["app_server"]["width"],
    )
    assert layout["nodes"]["db"]["left"] >= rightmost_app


def test_compact_deployment_scene_collapses_runtime_into_app_host():
    service = EnterpriseArchitectService("modelo.eapx")

    nodes, artifacts, connections = service._compact_deployment_scene(
        nodes=[
            {"id": "web", "name": "Servidor Web", "type": "node"},
            {"id": "app_server", "name": "Servidor de Aplicaciones", "type": "node", "environment": ""},
            {"id": "runtime", "name": "JVM", "type": "execution_environment", "parentId": "app_server"},
            {"id": "db", "name": "Base de Datos", "type": "database_node"},
        ],
        artifacts=[
            {"id": "api", "name": "Backend API", "type": "service", "nodeId": "runtime"},
            {"id": "worker", "name": "Worker", "type": "service", "nodeId": "runtime"},
        ],
        connections=[
            {"from": "web", "to": "runtime", "label": "HTTP"},
            {"from": "runtime", "to": "db", "label": "JDBC"},
        ],
    )

    assert {node["id"] for node in nodes} == {"web", "app_server", "db"}
    assert all(artifact["nodeId"] == "app_server" for artifact in artifacts)
    assert {tuple(connection.values()) for connection in connections} == {
        ("web", "app_server", "HTTP"),
        ("app_server", "db", "JDBC"),
    }
    app_server = next(node for node in nodes if node["id"] == "app_server")
    assert "JVM" in app_server["environment"]


def test_compact_deployment_scene_moves_frontend_artifact_from_client_to_web_host():
    service = EnterpriseArchitectService("modelo.eapx")

    nodes, artifacts, connections = service._compact_deployment_scene(
        nodes=[
            {"id": "cliente", "name": "Cliente Web", "type": "external_node"},
            {"id": "web", "name": "Servidor Web Nginx", "type": "node"},
            {"id": "app_server", "name": "Servidor de Aplicaciones", "type": "node"},
        ],
        artifacts=[
            {"id": "frontend", "name": "Frontend Web", "type": "artifact", "nodeId": "cliente"},
            {"id": "api", "name": "Backend API", "type": "service", "nodeId": "app_server"},
        ],
        connections=[
            {"from": "cliente", "to": "web", "label": "HTTPS"},
            {"from": "web", "to": "app_server", "label": "HTTP"},
        ],
    )

    frontend = next(artifact for artifact in artifacts if artifact["id"] == "frontend")
    assert frontend["nodeId"] == "web"
    assert {node["id"] for node in nodes} == {"cliente", "web", "app_server"}
    assert connections == [
        {"from": "cliente", "to": "web", "label": "HTTPS"},
        {"from": "web", "to": "app_server", "label": "HTTP"},
    ]


def test_deployment_node_spec_maps_types_to_visual_ea_elements():
    service = EnterpriseArchitectService("modelo.eapx")

    assert service._deployment_node_spec("device") == ("Device", "")
    assert service._deployment_node_spec("node") == ("Node", "")
    assert service._deployment_node_spec("execution_environment") == ("Node", "application server")
    assert service._deployment_node_spec("database_node") == ("Node", "database server")


def test_deployment_visual_stereotype_uses_expressive_server_labels():
    service = EnterpriseArchitectService("modelo.eapx")

    assert service._deployment_visual_stereotype({"type": "node", "name": "Servidor Web"}, "web") == "web server"
    assert service._deployment_visual_stereotype({"type": "node", "name": "Backend API"}, "app") == "application server"
    assert service._deployment_visual_stereotype({"type": "database_node", "name": "PostgreSQL"}, "database") == "database server"
    assert service._deployment_visual_stereotype({"type": "external_node", "name": "Pasarela Pago"}, "external_integration") == "external system"
    assert service._deployment_visual_stereotype({"type": "node", "name": "Servidor Notificaciones"}, "notification") == "notification server"


def test_deployment_visual_role_treats_servidor_de_aplicaciones_as_app():
    service = EnterpriseArchitectService("modelo.eapx")

    assert service._deployment_visual_role(
        {"type": "node", "name": "Servidor de Aplicaciones"},
        0,
    ) == "app"


def test_deployment_visual_element_spec_promotes_browser_clients_to_device():
    service = EnterpriseArchitectService("modelo.eapx")

    assert service._deployment_visual_element_spec(
        {"type": "external_node", "name": "Cliente Web / Navegador"},
        "client",
    ) == ("Device", "device")


def test_build_deployment_scene_connections_promotes_artifact_links_to_host_nodes():
    service = EnterpriseArchitectService("modelo.eapx")

    scene_connections = service._build_deployment_scene_connections(
        nodes=[
            {"id": "cliente", "name": "Cliente Web", "type": "external_node"},
            {"id": "runtime", "name": "JVM", "type": "execution_environment"},
            {"id": "db", "name": "PostgreSQL", "type": "database_node"},
            {"id": "pagos", "name": "Pasarela Pago", "type": "external_node"},
        ],
        artifacts=[
            {"id": "api", "name": "Backend API", "type": "service", "nodeId": "runtime"},
            {"id": "worker", "name": "Worker", "type": "service", "nodeId": "runtime"},
        ],
        connections=[
            {"from": "cliente", "to": "api", "label": "HTTPS"},
            {"from": "api", "to": "db", "label": "JDBC"},
            {"from": "worker", "to": "pagos", "label": "REST / HTTPS"},
        ],
    )

    assert scene_connections == [
        {"from": "cliente", "to": "runtime", "label": "HTTPS"},
        {"from": "runtime", "to": "db", "label": "JDBC"},
        {"from": "runtime", "to": "pagos", "label": "REST / HTTPS"},
    ]


def test_build_deployment_scene_connections_deduplicates_promoted_pairs_and_merges_labels():
    service = EnterpriseArchitectService("modelo.eapx")

    scene_connections = service._build_deployment_scene_connections(
        nodes=[
            {"id": "runtime", "name": "JVM", "type": "execution_environment"},
            {"id": "externo", "name": "Servicio Externo", "type": "external_node"},
        ],
        artifacts=[
            {"id": "api", "name": "Backend API", "type": "service", "nodeId": "runtime"},
            {"id": "worker", "name": "Worker", "type": "service", "nodeId": "runtime"},
        ],
        connections=[
            {"from": "api", "to": "externo", "label": "REST / HTTPS"},
            {"from": "worker", "to": "externo", "label": "AMQP"},
            {"from": "runtime", "to": "externo", "label": "REST / HTTPS"},
        ],
    )

    assert scene_connections == [
        {"from": "runtime", "to": "externo", "label": "REST / HTTPS | AMQP"}
    ]


def test_build_component_layout_places_components_by_layer_column():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_component_layout(
        components=[
            {"id": "cliente", "name": "Cliente Web", "stereotype": "frontend", "layer": "client"},
            {"id": "gateway", "name": "API Gateway", "stereotype": "gateway", "layer": "gateway"},
            {"id": "pedidos", "name": "Servicio Pedidos", "stereotype": "service", "layer": "service"},
        ],
        layers=["client", "gateway", "service"],
    )

    assert layout["cliente"]["left"] < layout["gateway"]["left"] < layout["pedidos"]["left"]


def test_build_component_notes_includes_basic_interfaces():
    service = EnterpriseArchitectService("modelo.eapx")

    notes = service._build_component_notes(
        {
            "interfaces": {
                "provided": ["PedidosAPI"],
                "required": ["PagosAPI"],
            }
        }
    )

    assert "PedidosAPI" in notes
    assert "PagosAPI" in notes


def test_activity_element_spec_maps_node_types_to_expected_ea_elements():
    service = EnterpriseArchitectService("modelo.eapx")

    assert service._activity_element_spec("initial") == ("StateNode", 100)
    assert service._activity_element_spec("final") == ("StateNode", 101)
    assert service._activity_element_spec("action") == ("Action", None)
    assert service._activity_element_spec("decision") == ("Decision", None)
    assert service._activity_element_spec("fork") == ("Synchronization", None)
    assert service._activity_element_spec("join") == ("Synchronization", None)
    assert service._activity_element_spec("object") == ("Object", None)


def test_build_activity_layout_places_branch_nodes_outside_center_column():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_activity_layout(
        nodes=[
            {"id": "inicio", "name": "Inicio", "type": "initial"},
            {"id": "validar", "name": "Validar pedido", "type": "action"},
            {"id": "stock", "name": "Hay stock", "type": "decision"},
            {"id": "pagar", "name": "Procesar pago", "type": "action"},
            {"id": "sin_stock", "name": "Mostrar sin stock", "type": "action"},
            {"id": "fin_ok", "name": "Fin ok", "type": "final"},
            {"id": "fin_error", "name": "Fin error", "type": "final"},
        ],
        flows=[
            {"from": "inicio", "to": "validar", "label": ""},
            {"from": "validar", "to": "stock", "label": ""},
            {"from": "stock", "to": "pagar", "label": "[Sí]"},
            {"from": "stock", "to": "sin_stock", "label": "[No]"},
            {"from": "pagar", "to": "fin_ok", "label": ""},
            {"from": "sin_stock", "to": "fin_error", "label": ""},
        ],
    )

    assert layout["sin_stock"]["center_x"] == service.ACTIVITY_LEFT_X
    assert layout["pagar"]["center_x"] == service.ACTIVITY_CENTER_X


def test_build_activity_layout_places_loopback_branch_between_decision_and_reentry():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_activity_layout(
        nodes=[
            {"id": "inicio", "name": "Inicio", "type": "initial"},
            {"id": "seleccionar_pago", "name": "Seleccionar metodo de pago", "type": "action"},
            {"id": "procesar_pago", "name": "Procesar pago", "type": "action"},
            {"id": "decision_pago", "name": "Pago aprobado", "type": "decision"},
            {"id": "generar_orden", "name": "Generar orden", "type": "action"},
            {"id": "mostrar_error", "name": "Mostrar error", "type": "action"},
            {"id": "reintentar_pago", "name": "Reintentar pago", "type": "action"},
            {"id": "fin", "name": "Fin", "type": "final"},
        ],
        flows=[
            {"from": "inicio", "to": "seleccionar_pago", "label": ""},
            {"from": "seleccionar_pago", "to": "procesar_pago", "label": ""},
            {"from": "procesar_pago", "to": "decision_pago", "label": ""},
            {"from": "decision_pago", "to": "generar_orden", "label": "[Sí]"},
            {"from": "decision_pago", "to": "mostrar_error", "label": "[No]"},
            {"from": "mostrar_error", "to": "reintentar_pago", "label": ""},
            {"from": "reintentar_pago", "to": "procesar_pago", "label": "[Reintentar]"},
            {"from": "generar_orden", "to": "fin", "label": ""},
        ],
    )

    assert layout["mostrar_error"]["center_x"] == service.ACTIVITY_LEFT_X
    assert layout["reintentar_pago"]["center_x"] == service.ACTIVITY_LEFT_X
    assert layout["mostrar_error"]["top_y"] < layout["decision_pago"]["top_y"]
    assert layout["reintentar_pago"]["top_y"] < layout["decision_pago"]["top_y"]
    assert layout["reintentar_pago"]["top_y"] > layout["seleccionar_pago"]["top_y"]


def test_build_activity_layout_uses_outer_lane_when_left_branches_overlap_vertically():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_activity_layout(
        nodes=[
            {"id": "inicio", "name": "Inicio", "type": "initial"},
            {"id": "seleccionar", "name": "Seleccionar", "type": "action"},
            {"id": "decision_stock", "name": "Hay stock", "type": "decision"},
            {"id": "sin_stock", "name": "Sin stock", "type": "action"},
            {"id": "fin_sin_stock", "name": "Fin sin stock", "type": "final"},
            {"id": "metodo_pago", "name": "Metodo de pago", "type": "action"},
            {"id": "procesar_pago", "name": "Procesar pago", "type": "action"},
            {"id": "decision_pago", "name": "Pago aprobado", "type": "decision"},
            {"id": "mostrar_error", "name": "Mostrar error", "type": "action"},
            {"id": "reintentar_pago", "name": "Reintentar pago", "type": "action"},
            {"id": "fin_ok", "name": "Fin ok", "type": "final"},
        ],
        flows=[
            {"from": "inicio", "to": "seleccionar", "label": ""},
            {"from": "seleccionar", "to": "decision_stock", "label": ""},
            {"from": "decision_stock", "to": "sin_stock", "label": "[No]"},
            {"from": "sin_stock", "to": "fin_sin_stock", "label": ""},
            {"from": "decision_stock", "to": "metodo_pago", "label": "[Sí]"},
            {"from": "metodo_pago", "to": "procesar_pago", "label": ""},
            {"from": "procesar_pago", "to": "decision_pago", "label": ""},
            {"from": "decision_pago", "to": "mostrar_error", "label": "[No]"},
            {"from": "mostrar_error", "to": "reintentar_pago", "label": ""},
            {"from": "reintentar_pago", "to": "metodo_pago", "label": "[Reintentar]"},
            {"from": "decision_pago", "to": "fin_ok", "label": "[Sí]"},
        ],
    )

    assert layout["sin_stock"]["center_x"] == service.ACTIVITY_LEFT_X
    assert layout["mostrar_error"]["center_x"] == service.ACTIVITY_LEFT_OUTER_X
    assert layout["reintentar_pago"]["center_x"] == service.ACTIVITY_LEFT_OUTER_X


def test_build_activity_layout_uses_lane_centers_for_v2_nodes():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_activity_layout(
        nodes=[
            {"id": "inicio", "name": "Inicio", "type": "initial", "lane": "Cliente"},
            {"id": "validar", "name": "Validar solicitud", "type": "action", "lane": "Sistema"},
            {"id": "fork", "name": "Procesos paralelos", "type": "fork", "lane": "Sistema"},
            {"id": "obj", "name": "Orden", "type": "object", "lane": "Pasarela"},
            {"id": "join", "name": "Sincronizar", "type": "join", "lane": "Sistema"},
            {"id": "fin", "name": "Fin", "type": "final", "lane": "Cliente"},
        ],
        flows=[
            {"from": "inicio", "to": "validar", "label": ""},
            {"from": "validar", "to": "fork", "label": ""},
            {"from": "fork", "to": "obj", "label": ""},
            {"from": "obj", "to": "join", "label": ""},
            {"from": "join", "to": "fin", "label": ""},
        ],
        lanes=["Cliente", "Sistema", "Pasarela"],
    )

    assert layout["inicio"]["center_x"] < layout["validar"]["center_x"]
    assert layout["obj"]["center_x"] > layout["validar"]["center_x"]
    assert layout["fork"]["center_x"] == layout["validar"]["center_x"]


def test_activity_node_dimensions_support_v2_shapes():
    service = EnterpriseArchitectService("modelo.eapx")

    assert service._activity_node_dimensions("fork") == (
        service.ACTIVITY_SYNC_WIDTH,
        service.ACTIVITY_SYNC_HEIGHT,
    )
    assert service._activity_node_dimensions("join") == (
        service.ACTIVITY_SYNC_WIDTH,
        service.ACTIVITY_SYNC_HEIGHT,
    )
    assert service._activity_node_dimensions("object") == (
        service.ACTIVITY_OBJECT_WIDTH,
        service.ACTIVITY_OBJECT_HEIGHT,
    )


def test_build_activity_layout_spreads_parallel_fork_branches_in_same_lane():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_activity_layout(
        nodes=[
            {"id": "inicio", "name": "Inicio", "type": "initial", "lane": "Cliente"},
            {"id": "confirmar", "name": "Confirmar pedido", "type": "action", "lane": "Cliente"},
            {"id": "fork", "name": "Validaciones en paralelo", "type": "fork", "lane": "Sistema"},
            {"id": "stock", "name": "Validar stock", "type": "action", "lane": "Sistema"},
            {"id": "fraude", "name": "Calcular fraude", "type": "action", "lane": "Sistema"},
            {"id": "join", "name": "Join", "type": "join", "lane": "Sistema"},
            {"id": "fin", "name": "Fin", "type": "final", "lane": "Cliente"},
        ],
        flows=[
            {"from": "inicio", "to": "confirmar", "label": ""},
            {"from": "confirmar", "to": "fork", "label": ""},
            {"from": "fork", "to": "stock", "label": ""},
            {"from": "fork", "to": "fraude", "label": ""},
            {"from": "stock", "to": "join", "label": ""},
            {"from": "fraude", "to": "join", "label": ""},
            {"from": "join", "to": "fin", "label": ""},
        ],
        lanes=["Cliente", "Sistema"],
    )

    assert layout["stock"]["center_x"] != layout["fraude"]["center_x"]
    assert layout["stock"]["top_y"] == layout["fraude"]["top_y"]


def test_build_activity_layout_offsets_decision_branches_that_share_same_lane():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_activity_layout(
        nodes=[
            {"id": "inicio", "name": "Inicio", "type": "initial", "lane": "Cliente"},
            {"id": "evaluar", "name": "Evaluar solicitud", "type": "action", "lane": "Sistema"},
            {"id": "decision", "name": "Solicitud viable?", "type": "decision", "lane": "Sistema"},
            {"id": "rechazo", "name": "Notificar rechazo", "type": "action", "lane": "Sistema"},
            {"id": "continuar", "name": "Generar solicitud de aprobacion", "type": "action", "lane": "Sistema"},
            {"id": "fin", "name": "Fin", "type": "final", "lane": "Cliente"},
        ],
        flows=[
            {"from": "inicio", "to": "evaluar", "label": ""},
            {"from": "evaluar", "to": "decision", "label": ""},
            {"from": "decision", "to": "rechazo", "label": "[No]"},
            {"from": "decision", "to": "continuar", "label": "[Si]"},
            {"from": "rechazo", "to": "fin", "label": ""},
            {"from": "continuar", "to": "fin", "label": ""},
        ],
        lanes=["Cliente", "Sistema"],
    )

    assert layout["rechazo"]["center_x"] != layout["continuar"]["center_x"]
    assert layout["continuar"]["center_x"] == layout["evaluar"]["center_x"]


def test_build_activity_layout_skips_empty_branch_paths_without_crashing():
    service = EnterpriseArchitectService("modelo.eapx")

    layout = service._build_activity_layout(
        nodes=[
            {"id": "inicio", "name": "Inicio", "type": "initial", "lane": "Cliente"},
            {"id": "validar", "name": "Validar", "type": "action", "lane": "Sistema"},
            {"id": "decision", "name": "Continuar?", "type": "decision", "lane": "Sistema"},
            {"id": "fin", "name": "Fin", "type": "final", "lane": "Cliente"},
        ],
        flows=[
            {"from": "inicio", "to": "validar", "label": ""},
            {"from": "validar", "to": "decision", "label": ""},
            {"from": "decision", "to": "fin", "label": "[Si]"},
            {"from": "decision", "to": "validar", "label": "[No]"},
        ],
        lanes=["Cliente", "Sistema"],
    )

    assert layout["decision"]["center_x"] == layout["validar"]["center_x"]
    assert layout["fin"]["center_x"] == layout["inicio"]["center_x"]


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


def test_format_sequence_fragment_label_keeps_alt_headers_compact_for_multiple_branches():
    service = EnterpriseArchitectService("modelo.eapx")

    assert (
        service._format_sequence_fragment_label(
            {
                "type": "alt",
                "label": "Credenciales validas / Credenciales invalidas",
                "branches": [
                    {"label": "Credenciales validas"},
                    {"label": "Credenciales invalidas"},
                ],
            }
        )
        == "alt"
    )


def test_build_sequence_fragment_notes_keeps_branch_conditions_out_of_title():
    service = EnterpriseArchitectService("modelo.eapx")

    notes = service._build_sequence_fragment_notes(
        {
            "type": "alt",
            "branches": [
                {"label": "[Credenciales validas]"},
                {"label": "[Credenciales invalidas]"},
            ],
        }
    )

    assert "[Credenciales validas]" in notes
    assert "[Credenciales invalidas]" in notes


def test_build_sequence_layout_uses_alt_branch_participants_to_keep_box_compact():
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
            {"from": "Frontend", "to": "Backend", "message": "solicitarLogin()", "kind": "sync"},
            {"from": "Backend", "to": "BaseDatos", "message": "buscarUsuario()", "kind": "sync"},
            {"from": "BaseDatos", "to": "Backend", "message": "usuarioEncontrado()", "kind": "return"},
            {"from": "Backend", "to": "Backend", "message": "verificarPassword()", "kind": "sync"},
            {"from": "Backend", "to": "Frontend", "message": "respuestaExito()", "kind": "return"},
            {"from": "Backend", "to": "Frontend", "message": "respuestaError()", "kind": "return"},
            {"from": "Frontend", "to": "Usuario", "message": "mostrarError()", "kind": "sync"},
        ],
        fragments=[
            {
                "type": "alt",
                "label": "Alternativas",
                "start_message_index": 3,
                "end_message_index": 8,
                "branches": [
                    {"label": "Credenciales validas", "start_message_index": 5, "end_message_index": 6},
                    {"label": "Credenciales invalidas", "start_message_index": 7, "end_message_index": 8},
                ],
            }
        ],
    )

    alt_box = layout["fragment_boxes"][0]
    assert alt_box["right"] < layout["right_edge"]


def test_build_sequence_layout_excludes_terminal_ui_actor_from_alt_width_when_possible():
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
            {"from": "Frontend", "to": "Backend", "message": "solicitarLogin()", "kind": "sync"},
            {"from": "Backend", "to": "BaseDatos", "message": "buscarUsuario()", "kind": "sync"},
            {"from": "BaseDatos", "to": "Backend", "message": "usuarioEncontrado()", "kind": "return"},
            {"from": "Backend", "to": "Backend", "message": "verificarPassword()", "kind": "sync"},
            {"from": "Backend", "to": "Frontend", "message": "respuestaExito()", "kind": "return"},
            {"from": "Backend", "to": "Frontend", "message": "respuestaError()", "kind": "return"},
            {"from": "Frontend", "to": "Usuario", "message": "mostrarError()", "kind": "sync"},
        ],
        fragments=[
            {
                "type": "alt",
                "label": "Alternativas",
                "start_message_index": 3,
                "end_message_index": 8,
                "branches": [
                    {"label": "Credenciales validas", "start_message_index": 5, "end_message_index": 6},
                    {"label": "Credenciales invalidas", "start_message_index": 7, "end_message_index": 8},
                ],
            }
        ],
    )

    alt_box = layout["fragment_boxes"][0]
    frontend_box = layout["participant_boxes"][1]
    assert alt_box["left"] >= frontend_box["left"] - 40


def test_build_sequence_activation_plan_infers_compact_entity_activation():
    service = EnterpriseArchitectService("modelo.eapx")

    plan = service._build_sequence_activation_plan(
        participants=[
            {"name": "Frontend", "type": "boundary"},
            {"name": "Backend", "type": "control"},
            {"name": "BaseDatos", "type": "entity"},
        ],
        messages=[
            {"from": "Frontend", "to": "Backend", "message": "login()", "kind": "sync"},
            {"from": "Backend", "to": "BaseDatos", "message": "buscarUsuario()", "kind": "sync"},
            {"from": "BaseDatos", "to": "Backend", "message": "usuario()", "kind": "return"},
            {"from": "Backend", "to": "Frontend", "message": "ok()", "kind": "return"},
        ],
        activations=[],
    )

    assert plan["BaseDatos"] == [
        {"start_message_index": 2, "end_message_index": 3, "source": "inferred", "participant_type": "entity"}
    ]


def test_build_sequence_message_state_flags_marks_entity_round_trip_activation():
    service = EnterpriseArchitectService("modelo.eapx")

    activation_plan = {
        "BaseDatos": [
            {"start_message_index": 2, "end_message_index": 3, "source": "inferred", "participant_type": "entity"}
        ],
        "Backend": [
            {"start_message_index": 1, "end_message_index": 4, "source": "inferred", "participant_type": "control"}
        ],
    }
    participant_types = {
        "Frontend": "boundary",
        "Backend": "control",
        "BaseDatos": "entity",
    }

    request_flags = service._build_sequence_message_state_flags(
        message_index=2,
        message={"from": "Backend", "to": "BaseDatos", "message": "buscarUsuario()", "kind": "sync"},
        activation_plan=activation_plan,
        participant_types=participant_types,
    )
    response_flags = service._build_sequence_message_state_flags(
        message_index=3,
        message={"from": "BaseDatos", "to": "Backend", "message": "usuario()", "kind": "return"},
        activation_plan=activation_plan,
        participant_types=participant_types,
    )

    assert "ForceActivation=1;" in request_flags
    assert "EndActivation=1;" in response_flags
    assert "StopActivation=1;" in response_flags
