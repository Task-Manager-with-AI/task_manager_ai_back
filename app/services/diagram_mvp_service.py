import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from app.core.config import settings

DiagramProvider = Literal["mermaid", "kroki"]
DiagramOutputFormat = Literal["png", "svg"]
DiagramSourceLanguage = Literal["mermaid", "plantuml"]


@dataclass
class DiagramRenderResult:
    provider: DiagramProvider
    source_language: DiagramSourceLanguage
    diagram_type: str
    source: str
    file_path: str
    output_format: DiagramOutputFormat
    render_time_ms: int


class DiagramMvpService:
    def __init__(
        self,
        public_root: str,
        kroki_base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.public_root = public_root
        self.kroki_base_url = (kroki_base_url or settings.KROKI_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.DIAGRAM_MVP_TIMEOUT_SECONDS

    def generate(
        self,
        architecture_data: Dict[str, Any],
        diagram_type: str,
        provider: DiagramProvider,
        output_format: DiagramOutputFormat = "png",
    ) -> DiagramRenderResult:
        if output_format not in ("png", "svg"):
            raise ValueError("Unsupported output_format. Supported values: png, svg.")

        source_language: DiagramSourceLanguage = "mermaid" if provider == "mermaid" else "plantuml"
        source = (
            generate_mermaid_source(architecture_data, diagram_type)
            if source_language == "mermaid"
            else generate_plantuml_source(architecture_data, diagram_type)
        )
        os.makedirs(self.public_root, exist_ok=True)

        filename = f"{provider}_{diagram_type}_{int(time.time() * 1000)}.{output_format}"
        output_path = os.path.join(self.public_root, filename)
        started = time.perf_counter()

        if provider == "mermaid":
            self._render_with_mermaid(source, output_path, output_format)
        elif provider == "kroki":
            self._render_with_kroki(source, output_path, output_format)
        else:
            raise ValueError("Unsupported provider. Supported values: mermaid, kroki.")

        return DiagramRenderResult(
            provider=provider,
            source_language=source_language,
            diagram_type=diagram_type,
            source=source,
            file_path=os.path.abspath(output_path),
            output_format=output_format,
            render_time_ms=int((time.perf_counter() - started) * 1000),
        )

    def _render_with_mermaid(
        self,
        source: str,
        output_path: str,
        output_format: DiagramOutputFormat,
    ) -> None:
        if shutil.which("mmdc"):
            self._render_with_mermaid_cli(source, output_path)
            return
        self._render_with_mermaid_ink(source, output_path, output_format)

    def _render_with_mermaid_cli(self, source: str, output_path: str) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False, encoding="utf-8") as handle:
            handle.write(source)
            source_path = handle.name

        try:
            subprocess.run(
                ["mmdc", "-i", source_path, "-o", output_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            raise RuntimeError(f"Mermaid CLI could not render the diagram: {detail}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Mermaid CLI timed out while rendering the diagram.") from exc
        finally:
            try:
                os.remove(source_path)
            except OSError:
                pass

    def _render_with_mermaid_ink(
        self,
        source: str,
        output_path: str,
        output_format: DiagramOutputFormat,
    ) -> None:
        encoded = urllib.parse.quote(base64.b64encode(source.encode("utf-8")).decode("ascii"))
        endpoint = "svg" if output_format == "svg" else "img"
        url = f"https://mermaid.ink/{endpoint}/{encoded}"
        self._download_rendered_file(url, output_path, "Mermaid.ink")

    def _render_with_kroki(
        self,
        source: str,
        output_path: str,
        output_format: DiagramOutputFormat,
    ) -> None:
        url = f"{self.kroki_base_url}/plantuml/{output_format}"
        payload = json.dumps({"diagram_source": source}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Accept": f"image/{output_format}",
                "Content-Type": "application/json",
                "User-Agent": "TaskManagerDiagramMVP/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                with open(output_path, "wb") as handle:
                    handle.write(response.read())
        except Exception as exc:
            raise RuntimeError(f"Kroki could not render the diagram: {exc}") from exc

    def _download_rendered_file(self, url: str, output_path: str, provider_name: str) -> None:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 Diagram MVP Renderer",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                with open(output_path, "wb") as handle:
                    handle.write(response.read())
        except Exception as exc:
            raise RuntimeError(f"{provider_name} could not render the diagram: {exc}") from exc


def generate_mermaid_source(architecture_data: Dict[str, Any], diagram_type: str) -> str:
    if diagram_type == "sequence":
        return _to_sequence_diagram(architecture_data)
    if diagram_type == "activity":
        return _to_activity_flowchart(architecture_data)
    if diagram_type == "component":
        return _to_component_flowchart(architecture_data)
    if diagram_type == "deployment":
        return _to_deployment_flowchart(architecture_data)
    if diagram_type == "use_case":
        return _to_use_case_flowchart(architecture_data)
    if diagram_type == "class":
        return _to_class_diagram(architecture_data)
    raise ValueError(
        "Unsupported diagram_type. Supported values: activity, class, component, deployment, sequence, use_case."
    )


def generate_plantuml_source(architecture_data: Dict[str, Any], diagram_type: str) -> str:
    if diagram_type == "sequence":
        return _to_plantuml_sequence_diagram(architecture_data)
    if diagram_type == "activity":
        return _to_plantuml_activity_diagram(architecture_data)
    if diagram_type == "component":
        return _to_plantuml_component_diagram(architecture_data)
    if diagram_type == "deployment":
        return _to_plantuml_deployment_diagram(architecture_data)
    if diagram_type == "use_case":
        return _to_plantuml_use_case_diagram(architecture_data)
    if diagram_type == "class":
        return _to_plantuml_class_diagram(architecture_data)
    raise ValueError(
        "Unsupported diagram_type. Supported values: activity, class, component, deployment, sequence, use_case."
    )


def public_url_for_file(
    file_path: str,
    request_base_url: str,
    public_root: str,
    public_url_dir: str = "diagrams/mvp",
) -> str:
    relative_path = os.path.relpath(file_path, public_root).replace(os.sep, "/")
    return f"{request_base_url.rstrip('/')}/public/{public_url_dir.strip('/')}/{relative_path}"


def _to_class_diagram(data: Dict[str, Any]) -> str:
    lines = ["classDiagram"]
    for element in data.get("elements", []):
        if not isinstance(element, dict):
            continue
        name = _safe_identifier(element.get("name"))
        if not name:
            continue
        lines.append(f"  class {name} {{")
        for attribute in element.get("attributes", []) or []:
            attr = _clean_label(attribute).replace("(", "").replace(")", "")
            if attr:
                lines.append(f"    {attr}")
        lines.append("  }")

    for relationship in data.get("relationships", []):
        if not isinstance(relationship, dict):
            continue
        source = _safe_identifier(relationship.get("source") or relationship.get("from"))
        target = _safe_identifier(relationship.get("target") or relationship.get("to"))
        if not source or not target:
            continue
        arrow = _class_relationship_arrow(relationship.get("type", "Association"))
        lines.append(f"  {source} {arrow} {target}")

    return "\n".join(lines)


def _to_use_case_flowchart(data: Dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    for element in data.get("elements", []):
        if not isinstance(element, dict):
            continue
        name = _clean_label(element.get("name"))
        node_id = _safe_identifier(name)
        if not name or not node_id:
            continue
        if str(element.get("type", "")).lower() == "actor":
            lines.append(f'  {node_id}["Actor: {name}"]')
        else:
            lines.append(f'  {node_id}(["{name}"])')

    for relationship in data.get("relationships", []):
        if not isinstance(relationship, dict):
            continue
        source = _safe_identifier(relationship.get("source") or relationship.get("from"))
        target = _safe_identifier(relationship.get("target") or relationship.get("to"))
        if not source or not target:
            continue
        relation_type = str(relationship.get("type", "Association")).lower()
        if "include" in relation_type:
            lines.append(f'  {source} -.->|"<<include>>"| {target}')
        elif "extend" in relation_type:
            lines.append(f'  {source} -.->|"<<extend>>"| {target}')
        else:
            lines.append(f"  {source} --- {target}")

    return "\n".join(lines)


def _to_plantuml_class_diagram(data: Dict[str, Any]) -> str:
    lines = ["@startuml", "skinparam classAttributeIconSize 0"]
    aliases = {}
    for element in data.get("elements", []) or []:
        if not isinstance(element, dict):
            continue
        name = _clean_label(element.get("name"))
        alias = _safe_identifier(name)
        if not name or not alias:
            continue
        aliases[name.casefold()] = alias
        lines.append(f'class "{name}" as {alias} {{')
        for attribute in element.get("attributes", []) or []:
            attr = _plantuml_text(attribute)
            if attr:
                lines.append(f"  {attr}")
        lines.append("}")

    for relationship in data.get("relationships", []) or []:
        if not isinstance(relationship, dict):
            continue
        source = _plantuml_lookup_alias(relationship.get("source") or relationship.get("from"), aliases)
        target = _plantuml_lookup_alias(relationship.get("target") or relationship.get("to"), aliases)
        if source and target:
            lines.append(f"{source} {_plantuml_class_arrow(relationship.get('type'))} {target}")

    lines.append("@enduml")
    return "\n".join(lines)


def _to_plantuml_use_case_diagram(data: Dict[str, Any]) -> str:
    lines = ["@startuml", "left to right direction"]
    aliases = {}
    for element in data.get("elements", []) or []:
        if not isinstance(element, dict):
            continue
        name = _clean_label(element.get("name"))
        alias = _safe_identifier(name)
        if not name or not alias:
            continue
        aliases[name.casefold()] = alias
        if str(element.get("type", "")).lower() == "actor":
            lines.append(f'actor "{name}" as {alias}')
        else:
            lines.append(f'usecase "{name}" as {alias}')

    for relationship in data.get("relationships", []) or []:
        if not isinstance(relationship, dict):
            continue
        source = _plantuml_lookup_alias(relationship.get("source") or relationship.get("from"), aliases)
        target = _plantuml_lookup_alias(relationship.get("target") or relationship.get("to"), aliases)
        if not source or not target:
            continue
        relation_type = str(relationship.get("type", "Association")).lower()
        if "include" in relation_type:
            lines.append(f"{source} ..> {target} : <<include>>")
        elif "extend" in relation_type:
            lines.append(f"{source} ..> {target} : <<extend>>")
        else:
            lines.append(f"{source} -- {target}")

    lines.append("@enduml")
    return "\n".join(lines)


def _to_plantuml_sequence_diagram(data: Dict[str, Any]) -> str:
    lines = ["@startuml", "autonumber"]
    aliases = {}
    for participant in data.get("participants", []) or []:
        if not isinstance(participant, dict):
            continue
        name = _clean_label(participant.get("name"))
        alias = _safe_identifier(name)
        if not name or not alias:
            continue
        aliases[name.casefold()] = alias
        keyword = "actor" if participant.get("type") == "actor" else "participant"
        lines.append(f'{keyword} "{name}" as {alias}')

    activations = _activation_index(data.get("activations", []))
    for index, message in enumerate(data.get("messages", []) or [], start=1):
        if not isinstance(message, dict):
            continue
        source = _plantuml_lookup_alias(message.get("from"), aliases)
        target = _plantuml_lookup_alias(message.get("to"), aliases)
        label = _plantuml_text(message.get("message") or "mensaje")
        if not source or not target:
            continue
        arrow = "-->" if message.get("kind") == "return" else "->>" if message.get("kind") == "async" else "->"
        lines.append(f"{source} {arrow} {target}: {label}")
        for participant in activations.get(index, {}).get("activate", []):
            alias = _plantuml_lookup_alias(participant, aliases)
            if alias:
                lines.append(f"activate {alias}")
        for participant in activations.get(index, {}).get("deactivate", []):
            alias = _plantuml_lookup_alias(participant, aliases)
            if alias:
                lines.append(f"deactivate {alias}")

    lines.append("@enduml")
    return "\n".join(lines)


def _to_plantuml_activity_diagram(data: Dict[str, Any]) -> str:
    lines = ["@startuml", "start"]
    nodes_by_id = {
        str(node.get("id") or ""): node
        for node in data.get("nodes", []) or []
        if isinstance(node, dict) and node.get("id")
    }

    ordered_ids = _ordered_activity_node_ids(data.get("flows", []) or [])
    seen = set()
    for node_id in ordered_ids:
        node = nodes_by_id.get(node_id)
        if not node or node_id in seen:
            continue
        seen.add(node_id)
        node_type = node.get("type")
        label = _plantuml_text(node.get("name") or node_id)
        if node_type in ("initial", "final"):
            continue
        if node_type == "decision":
            lines.append(f"if ({label}) then (si)")
            lines.append("endif")
        else:
            lines.append(f":{label};")

    for node in data.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "")
        if node_id in seen or node.get("type") in ("initial", "final"):
            continue
        label = _plantuml_text(node.get("name") or node_id)
        if label:
            lines.append(f":{label};")

    lines.extend(["stop", "@enduml"])
    return "\n".join(lines)


def _to_plantuml_component_diagram(data: Dict[str, Any]) -> str:
    lines = ["@startuml"]
    aliases = {}
    components = data.get("components", []) or []
    layers = data.get("layers", []) or []

    for layer in layers:
        layer_components = [item for item in components if item.get("layer") == layer]
        if not layer_components:
            continue
        lines.append(f'package "{_plantuml_text(layer).title()}" {{')
        for component in layer_components:
            alias = _safe_identifier(component.get("id") or component.get("name"))
            name = _plantuml_text(component.get("name") or alias)
            stereotype = _plantuml_text(component.get("stereotype"))
            if not alias:
                continue
            aliases[str(component.get("id") or name).casefold()] = alias
            suffix = f" <<{stereotype}>>" if stereotype else ""
            lines.append(f'  component "{name}" as {alias}{suffix}')
        lines.append("}")

    for component in components:
        alias = _safe_identifier(component.get("id") or component.get("name"))
        name = _plantuml_text(component.get("name") or alias)
        key = str(component.get("id") or name).casefold()
        if not alias or key in aliases:
            continue
        aliases[key] = alias
        lines.append(f'component "{name}" as {alias}')

    for dependency in data.get("dependencies", []) or []:
        if not isinstance(dependency, dict):
            continue
        source = _plantuml_lookup_alias(dependency.get("from"), aliases)
        target = _plantuml_lookup_alias(dependency.get("to"), aliases)
        label = _plantuml_text(dependency.get("label"))
        if source and target:
            lines.append(f"{source} --> {target}{f' : {label}' if label else ''}")

    lines.append("@enduml")
    return "\n".join(lines)


def _to_plantuml_deployment_diagram(data: Dict[str, Any]) -> str:
    lines = ["@startuml"]
    aliases = {}
    artifacts_by_node = {}
    for artifact in data.get("artifacts", []) or []:
        if isinstance(artifact, dict):
            artifacts_by_node.setdefault(artifact.get("nodeId"), []).append(artifact)

    for node in data.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        alias = _safe_identifier(node.get("id") or node.get("name"))
        name = _plantuml_text(node.get("name") or alias)
        node_type = str(node.get("type") or "").lower()
        if not alias or not name:
            continue
        aliases[str(node.get("id") or name).casefold()] = alias
        keyword = "database" if "database" in node_type else "node"
        lines.append(f'{keyword} "{name}" as {alias} {{')
        for artifact in artifacts_by_node.get(node.get("id"), []):
            artifact_alias = _safe_identifier(artifact.get("id") or artifact.get("name"))
            artifact_name = _plantuml_text(artifact.get("name") or artifact_alias)
            artifact_type = _plantuml_text(artifact.get("type"))
            if not artifact_alias:
                continue
            aliases[str(artifact.get("id") or artifact_name).casefold()] = artifact_alias
            suffix = f" <<{artifact_type}>>" if artifact_type else ""
            lines.append(f'  artifact "{artifact_name}" as {artifact_alias}{suffix}')
        lines.append("}")

    for connection in data.get("connections", []) or []:
        if not isinstance(connection, dict):
            continue
        source = _plantuml_lookup_alias(connection.get("from"), aliases)
        target = _plantuml_lookup_alias(connection.get("to"), aliases)
        label = _plantuml_text(connection.get("label"))
        if not source or not target:
            continue
        if source == target:
            lines.append(f"note right of {source}: {label or 'Conexion interna'}")
            continue
        lines.append(f"{source} --> {target}{f' : {label}' if label else ''}")

    lines.append("@enduml")
    return "\n".join(lines)


def _to_sequence_diagram(data: Dict[str, Any]) -> str:
    lines = ["sequenceDiagram"]
    for participant in data.get("participants", []):
        if not isinstance(participant, dict):
            continue
        name = _clean_label(participant.get("name"))
        alias = _safe_identifier(name)
        if not name or not alias:
            continue
        keyword = "actor" if participant.get("type") == "actor" else "participant"
        lines.append(f"  {keyword} {alias} as {name}")

    activations = _activation_index(data.get("activations", []))
    messages = data.get("messages", []) or []
    for index, message in enumerate(messages, start=1):
        if not isinstance(message, dict):
            continue
        source = _safe_identifier(message.get("from"))
        target = _safe_identifier(message.get("to"))
        label = _clean_label(message.get("message") or "mensaje")
        if not source or not target:
            continue
        arrow = "-->>" if message.get("kind") == "return" else "->>" if message.get("kind") == "async" else "->>"
        lines.append(f"  {source}{arrow}{target}: {label}")
        for participant in activations.get(index, {}).get("activate", []):
            lines.append(f"  activate {_safe_identifier(participant)}")
        for participant in activations.get(index, {}).get("deactivate", []):
            lines.append(f"  deactivate {_safe_identifier(participant)}")

    return "\n".join(lines)


def _to_activity_flowchart(data: Dict[str, Any]) -> str:
    lines = ["flowchart TD"]
    nodes_by_id = {}
    for node in data.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = _safe_identifier(node.get("id") or node.get("name"))
        label = _clean_label(node.get("name") or node_id)
        if not node_id:
            continue
        nodes_by_id[node.get("id") or node_id] = node_id
        node_type = node.get("type")
        if node_type == "initial":
            lines.append(f'  {node_id}(("Inicio"))')
        elif node_type == "final":
            lines.append(f'  {node_id}((("Fin")))')
        elif node_type == "decision":
            lines.append(f'  {node_id}{{"{label}"}}')
        elif node_type in ("fork", "join"):
            lines.append(f'  {node_id}["{label}"]')
        else:
            lines.append(f'  {node_id}["{label}"]')

    _append_edges(lines, data.get("flows", []), nodes_by_id)
    return "\n".join(lines)


def _to_component_flowchart(data: Dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    components = data.get("components", []) or []
    layers = data.get("layers", []) or []
    component_ids = {}

    for layer in layers:
        layer_components = [item for item in components if item.get("layer") == layer]
        if not layer_components:
            continue
        lines.append(f'  subgraph {_safe_identifier(layer)}["{_clean_label(layer).title()}"]')
        for component in layer_components:
            component_id = _safe_identifier(component.get("id") or component.get("name"))
            component_ids[component.get("id") or component_id] = component_id
            lines.append(f'    {component_id}["{_component_label(component)}"]')
        lines.append("  end")

    for component in components:
        component_id = _safe_identifier(component.get("id") or component.get("name"))
        if not component_id or component.get("id") in component_ids:
            continue
        component_ids[component.get("id") or component_id] = component_id
        lines.append(f'  {component_id}["{_component_label(component)}"]')

    _append_edges(lines, data.get("dependencies", []), component_ids)
    return "\n".join(lines)


def _to_deployment_flowchart(data: Dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    entity_ids = {}
    artifacts_by_node = {}
    for artifact in data.get("artifacts", []) or []:
        artifacts_by_node.setdefault(artifact.get("nodeId"), []).append(artifact)

    for node in data.get("nodes", []) or []:
        node_id = _safe_identifier(node.get("id") or node.get("name"))
        if not node_id:
            continue
        entity_ids[node.get("id") or node_id] = node_id
        label = _deployment_node_label(node)
        lines.append(f'  subgraph {node_id}["{label}"]')
        for artifact in artifacts_by_node.get(node.get("id"), []):
            artifact_id = _safe_identifier(artifact.get("id") or artifact.get("name"))
            if artifact_id:
                entity_ids[artifact.get("id") or artifact_id] = artifact_id
                lines.append(f'    {artifact_id}["{_deployment_artifact_label(artifact)}"]')
        lines.append("  end")

    _append_edges(lines, data.get("connections", []), entity_ids)
    return "\n".join(lines)


def _append_edges(lines: list[str], edges: list[Dict[str, Any]], id_map: Dict[str, str]) -> None:
    for edge in edges or []:
        if not isinstance(edge, dict):
            continue
        source_key = edge.get("from") or edge.get("source")
        target_key = edge.get("to") or edge.get("target")
        source = id_map.get(source_key) or _safe_identifier(source_key)
        target = id_map.get(target_key) or _safe_identifier(target_key)
        if not source or not target:
            continue
        label = _clean_label(edge.get("label") or edge.get("name"))
        if label:
            lines.append(f'  {source} -->|"{label}"| {target}')
        else:
            lines.append(f"  {source} --> {target}")


def _activation_index(activations: list[Dict[str, Any]]) -> Dict[int, Dict[str, list[str]]]:
    indexed: Dict[int, Dict[str, list[str]]] = {}
    for activation in activations or []:
        participant = activation.get("participant")
        start = int(activation.get("start_message_index") or 0)
        end = int(activation.get("end_message_index") or start)
        if not participant or start <= 0:
            continue
        indexed.setdefault(start, {"activate": [], "deactivate": []})["activate"].append(participant)
        indexed.setdefault(max(start, end), {"activate": [], "deactivate": []})["deactivate"].append(participant)
    return indexed


def _class_relationship_arrow(relation_type: Any) -> str:
    normalized = str(relation_type or "").lower()
    if "general" in normalized or "herencia" in normalized or "inherit" in normalized:
        return "<|--"
    if "comp" in normalized:
        return "*--"
    if "agreg" in normalized or "aggreg" in normalized:
        return "o--"
    return "-->"


def _plantuml_class_arrow(relation_type: Any) -> str:
    normalized = str(relation_type or "").lower()
    if "general" in normalized or "herencia" in normalized or "inherit" in normalized:
        return "<|--"
    if "comp" in normalized:
        return "*--"
    if "agreg" in normalized or "aggreg" in normalized:
        return "o--"
    return "--"


def _plantuml_lookup_alias(value: Any, aliases: Dict[str, str]) -> str:
    label = _clean_label(value)
    if not label:
        return ""
    return aliases.get(label.casefold()) or _safe_identifier(label)


def _plantuml_text(value: Any) -> str:
    return _clean_label(value).replace("\\", "\\\\").replace(":", "\\:")


def _ordered_activity_node_ids(flows: list[Dict[str, Any]]) -> list[str]:
    ordered = []
    for flow in flows:
        if not isinstance(flow, dict):
            continue
        for key in ("from", "to"):
            node_id = str(flow.get(key) or "")
            if node_id and node_id not in ordered:
                ordered.append(node_id)
    return ordered


def _component_label(component: Dict[str, Any]) -> str:
    name = _clean_label(component.get("name") or component.get("id"))
    stereotype = _clean_label(component.get("stereotype"))
    if stereotype:
        return f"<<{stereotype}>>\\n{name}"
    return name


def _deployment_node_label(node: Dict[str, Any]) -> str:
    name = _clean_label(node.get("name") or node.get("id"))
    environment = _clean_label(node.get("environment"))
    node_type = _clean_label(node.get("type"))
    details = " / ".join(part for part in (node_type, environment) if part)
    return f"{name}\\n{details}" if details else name


def _deployment_artifact_label(artifact: Dict[str, Any]) -> str:
    name = _clean_label(artifact.get("name") or artifact.get("id"))
    artifact_type = _clean_label(artifact.get("type"))
    return f"<<{artifact_type}>>\\n{name}" if artifact_type else name


def _safe_identifier(value: Any) -> str:
    text = _clean_label(value)
    if not text:
        return ""
    identifier = re.sub(r"[^0-9A-Za-z_]", "_", text)
    identifier = re.sub(r"_+", "_", identifier).strip("_")
    if not identifier:
        return ""
    if identifier[0].isdigit():
        identifier = f"n_{identifier}"
    return identifier


def _clean_label(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace('"', "'").replace("\n", " ")
    return re.sub(r"\s+", " ", text)
