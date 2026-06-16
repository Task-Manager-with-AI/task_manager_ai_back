import json
import re
import unicodedata
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.core.config import settings

SUPPORTED_DIAGRAM_TYPES = {"activity", "class", "component", "deployment", "sequence", "use_case"}
SEQUENCE_PARTICIPANT_TYPES = {"actor", "boundary", "control", "entity", "lifeline"}
SEQUENCE_MESSAGE_KINDS = {"sync", "async", "return"}
SEQUENCE_FRAGMENT_TYPES = {"alt", "opt", "loop"}
ACTIVITY_NODE_TYPES = {"initial", "action", "decision", "final", "fork", "join", "object"}
COMPONENT_LAYERS = ("client", "gateway", "service", "support", "external", "data")
COMPONENT_STEREOTYPES = {"frontend", "gateway", "service", "external", "database", "component"}
DEPLOYMENT_NODE_TYPES = {"device", "node", "execution_environment", "database_node", "external_node"}
DEPLOYMENT_ARTIFACT_TYPES = {"artifact", "service", "database"}


def _build_minutes_prompt(transcript: str, meeting_title: str, participants: List[str], language: str) -> str:
    participants_str = ", ".join(participants) if participants else "(no se listaron)"
    if language == "es":
        return (
            "Eres un asistente que redacta minutas de reuniones de equipos de software.\n"
            "Analiza la transcripciÃ³n y devuelve un JSON con esta estructura EXACTA:\n"
            "{\n"
            '  "summary": "Resumen ejecutivo de 2 a 4 pÃ¡rrafos.",\n'
            '  "key_points": ["Punto clave 1", "Punto clave 2"],\n'
            '  "agreements": [{"order": 1, "text": "Acuerdo concreto y accionable"}]\n'
            "}\n"
            "Reglas:\n"
            "- Los acuerdos deben ser frases cortas y accionables.\n"
            "- key_points son temas tratados, no acciones.\n"
            "- Si no hay informaciÃ³n suficiente, devuelve listas vacÃ­as.\n"
            f"\nTÃ­tulo de la reuniÃ³n: {meeting_title}\n"
            f"Participantes: {participants_str}\n"
            f"\nTranscripciÃ³n:\n{transcript}\n"
        )
    return (
        "You are an assistant that writes software-team meeting minutes.\n"
        "Analyze the transcript and return a JSON with this EXACT structure:\n"
        "{\n"
        '  "summary": "2-4 paragraph executive summary",\n'
        '  "key_points": ["Key point 1", "Key point 2"],\n'
        '  "agreements": [{"order": 1, "text": "Concrete actionable agreement"}]\n'
        "}\n"
        f"Meeting title: {meeting_title}\n"
        f"Participants: {participants_str}\n"
        f"\nTranscript:\n{transcript}\n"
    )


def _build_suggestions_prompt(
    agreements: List[str], project_members: List[Dict[str, str]], language: str
) -> str:
    members_str = "\n".join(f"- {m['id']} â†’ {m['name']}" for m in project_members)
    agreements_str = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(agreements))
    if language == "es":
        return (
            "Eres un asistente que convierte acuerdos de reuniÃ³n en tareas accionables.\n"
            "Para cada acuerdo, genera una sugerencia de tarea. Devuelve SOLO un JSON con:\n"
            "{\n"
            '  "suggestions": [\n'
            '    {"title": "TÃ­tulo accionable", "description": "Detalle", "priority": "LOW|MEDIUM|HIGH", "suggested_responsible_id": "uuid-o-null"}\n'
            "  ]\n"
            "}\n"
            "Reglas:\n"
            "- El tÃ­tulo debe ser breve e imperativo.\n"
            "- Asigna suggested_responsible_id SOLO si en el acuerdo se menciona un nombre que coincide con un miembro listado abajo.\n"
            "- Si no hay coincidencia clara, usa null.\n"
            "- priority por defecto MEDIUM, HIGH si hay urgencia explÃ­cita, LOW si es opcional.\n"
            f"\nMiembros del proyecto (id â†’ nombre):\n{members_str or '(ninguno)'}\n"
            f"\nAcuerdos:\n{agreements_str}\n"
        )
    return (
        "You convert meeting agreements into actionable tasks. Return JSON:\n"
        '{"suggestions":[{"title":"...","description":"...","priority":"LOW|MEDIUM|HIGH","suggested_responsible_id":"uuid-or-null"}]}\n'
        f"Members:\n{members_str}\n"
        f"\nAgreements:\n{agreements_str}\n"
    )


def _safe_parse_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _stable_identifier(value: Any, default_prefix: str = "node") -> str:
    normalized = unicodedata.normalize("NFKD", _normalize_text(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()
    return slug or default_prefix


def _normalize_index(value: Any, max_index: int, default: int) -> int:
    try:
        index = int(value)
    except (TypeError, ValueError):
        index = default
    if max_index < 1:
        return 1
    return max(1, min(index, max_index))


def _merge_sequence_fragments(fragments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not fragments:
        return []

    merged: List[Dict[str, Any]] = []
    for fragment in sorted(
        fragments,
        key=lambda item: (
            item["start_message_index"],
            item["end_message_index"],
            item["type"],
        ),
    ):
        if not merged:
            merged.append(fragment)
            continue

        previous = merged[-1]
        should_merge_alt = (
            fragment["type"] == "alt"
            and previous["type"] == "alt"
            and fragment["start_message_index"] <= previous["end_message_index"] + 1
        )

        if not should_merge_alt:
            merged.append(fragment)
            continue

        previous_branches = previous.setdefault("branches", [])
        if not previous_branches:
            previous_branches.append(
                {
                    "label": previous.get("label", ""),
                    "guard": previous.get("guard", ""),
                    "start_message_index": previous["start_message_index"],
                    "end_message_index": previous["end_message_index"],
                }
            )
        previous_branches.append(
            {
                "label": fragment.get("label", ""),
                "guard": fragment.get("guard", ""),
                "start_message_index": fragment["start_message_index"],
                "end_message_index": fragment["end_message_index"],
            }
        )
        previous["label"] = "Alternativas"
        previous["start_message_index"] = min(
            previous["start_message_index"],
            fragment["start_message_index"],
        )
        previous["end_message_index"] = max(
            previous["end_message_index"],
            fragment["end_message_index"],
        )

    return merged


def _expand_alt_fragments(messages: List[Dict[str, Any]], fragments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not messages or not fragments:
        return fragments

    expanded: List[Dict[str, Any]] = []
    for fragment in fragments:
        if fragment["type"] != "alt":
            expanded.append(fragment)
            continue

        start_index = fragment["start_message_index"]
        end_index = fragment["end_message_index"]
        branches = fragment.get("branches", [])

        if branches:
            start_index = min(
                _normalize_index(branch.get("start_message_index"), len(messages), start_index)
                for branch in branches
            )
            end_index = max(
                _normalize_index(branch.get("end_message_index"), len(messages), end_index)
                for branch in branches
            )

        covered_messages = messages[start_index - 1 : end_index]

        if covered_messages and all(message.get("kind") == "return" for message in covered_messages):
            owner = covered_messages[0].get("from")
            cursor = start_index - 1
            while cursor >= 1:
                candidate = messages[cursor - 1]
                if owner and (candidate.get("from") == owner or candidate.get("to") == owner):
                    start_index = cursor
                    if candidate.get("kind") != "return":
                        break
                cursor -= 1

        start_index = _expand_alt_to_decision_context(messages, start_index)

        expanded.append(
            {
                **fragment,
                "start_message_index": start_index,
                "end_message_index": end_index,
            }
        )

    return expanded


def _expand_alt_to_decision_context(messages: List[Dict[str, Any]], start_index: int) -> int:
    if not messages or start_index <= 1 or start_index > len(messages):
        return start_index

    current_message = messages[start_index - 1]
    owner = _normalize_text(current_message.get("from"))
    if not owner:
        return start_index

    current_target = _normalize_text(current_message.get("to"))
    current_kind = _normalize_text(current_message.get("kind") or "sync").lower()

    if owner != current_target and current_kind in {"sync", "async"}:
        return start_index

    expanded_start = start_index
    cursor = start_index - 1

    while cursor >= 1:
        candidate = messages[cursor - 1]
        source = _normalize_text(candidate.get("from"))
        target = _normalize_text(candidate.get("to"))
        kind = _normalize_text(candidate.get("kind") or "sync").lower()

        involves_owner = source == owner or target == owner
        if not involves_owner:
            break

        if source == owner and target == owner:
            expanded_start = cursor
            cursor -= 1
            continue

        if kind == "return":
            expanded_start = cursor
            cursor -= 1
            continue

        if source == owner and kind in SEQUENCE_MESSAGE_KINDS:
            expanded_start = cursor
            break

        break

    return expanded_start


def _normalize_sequence_diagram(parsed: Dict[str, Any]) -> Dict[str, Any]:
    raw_participants = parsed.get("participants", parsed.get("lifelines", [])) or []
    raw_messages = parsed.get("messages", parsed.get("interactions", [])) or []
    raw_fragments = parsed.get("fragments", []) or []
    raw_activations = parsed.get("activations", []) or []

    participants = []
    participants_by_key: Dict[str, str] = {}
    for raw in raw_participants:
        if not isinstance(raw, dict):
            continue
        name = _normalize_text(raw.get("name") or raw.get("participant") or raw.get("lifeline"))
        if not name:
            continue
        participant_type = _normalize_text(raw.get("type") or "lifeline").lower()
        if participant_type not in SEQUENCE_PARTICIPANT_TYPES:
            participant_type = "lifeline"
        key = name.casefold()
        if key in participants_by_key:
            continue
        participants_by_key[key] = name
        participants.append({"name": name, "type": participant_type})

    def resolve_participant_name(value: Any) -> str:
        candidate = _normalize_text(value)
        return participants_by_key.get(candidate.casefold(), candidate)

    messages = []
    for raw in raw_messages:
        if not isinstance(raw, dict):
            continue
        source = resolve_participant_name(raw.get("from") or raw.get("source"))
        target = resolve_participant_name(raw.get("to") or raw.get("target"))
        if not source or not target:
            continue
        if source.casefold() not in participants_by_key or target.casefold() not in participants_by_key:
            continue
        message = _normalize_text(raw.get("message") or raw.get("name"))
        kind = _normalize_text(raw.get("kind") or raw.get("message_type") or "sync").lower()
        if kind not in SEQUENCE_MESSAGE_KINDS:
            kind = "sync"
        messages.append(
            {
                "from": participants_by_key[source.casefold()],
                "to": participants_by_key[target.casefold()],
                "message": message or "mensaje",
                "kind": kind,
            }
        )

    fragments = []
    for raw in raw_fragments:
        if not isinstance(raw, dict):
            continue
        fragment_type = _normalize_text(raw.get("type") or "alt").lower()
        if fragment_type not in SEQUENCE_FRAGMENT_TYPES:
            continue
        label = _normalize_text(
            raw.get("label") or raw.get("guard") or raw.get("condition") or raw.get("name")
        )
        guard = _normalize_text(raw.get("guard") or raw.get("condition"))
        start_index = _normalize_index(
            raw.get("start_message_index", raw.get("start_message", raw.get("message_start"))),
            len(messages),
            1,
        )
        end_index = _normalize_index(
            raw.get("end_message_index", raw.get("end_message", raw.get("message_end", start_index))),
            len(messages),
            start_index,
        )
        if end_index < start_index:
            end_index = start_index
        fragments.append(
            {
                "type": fragment_type,
                "label": label or f"Fragmento {len(fragments) + 1}",
                "guard": guard,
                "start_message_index": start_index,
                "end_message_index": end_index,
            }
        )

    activations = []
    for raw in raw_activations:
        if not isinstance(raw, dict):
            continue
        participant = resolve_participant_name(raw.get("participant") or raw.get("name"))
        if participant.casefold() not in participants_by_key:
            continue
        start_index = _normalize_index(
            raw.get("start_message_index", raw.get("start_message")),
            len(messages),
            1,
        )
        end_index = _normalize_index(
            raw.get("end_message_index", raw.get("end_message", start_index)),
            len(messages),
            start_index,
        )
        activations.append(
            {
                "participant": participants_by_key[participant.casefold()],
                "start_message_index": start_index,
                "end_message_index": max(start_index, end_index),
            }
        )

    fragments = _merge_sequence_fragments(fragments)
    fragments = _expand_alt_fragments(messages, fragments)

    if len(participants) < 2 or len(messages) < 1:
        raise ValueError(
            "Sequence diagram generation requires at least 2 participants and 1 message."
        )

    return {
        "participants": participants,
        "messages": messages,
        "fragments": fragments,
        "activations": activations,
    }


def _build_activity_prompt(prompt_text: str) -> str:
    return (
        "Eres un Arquitecto de Software Experto en UML. Tu trabajo es analizar requerimientos "
        "en texto libre y extraer un diagrama de actividad UML preciso.\n"
        "Devuelve SOLO un JSON con esta estructura estricta:\n"
        "{\n"
        '  "lanes": ["Cliente", "Sistema", "PasarelaPago"],\n'
        '  "nodes": [\n'
        '    {"id": "inicio", "name": "Inicio", "type": "initial", "lane": "Cliente"},\n'
        '    {"id": "seleccionar_productos", "name": "Seleccionar productos", "type": "action", "lane": "Cliente"},\n'
        '    {"id": "hay_stock", "name": "¿Hay stock disponible?", "type": "decision"},\n'
        '    {"id": "validar_stock", "name": "Validar stock", "type": "action", "lane": "Sistema"},\n'
        '    {"id": "fork_validaciones", "name": "Validaciones en paralelo", "type": "fork", "lane": "Sistema"},\n'
        '    {"id": "obj_solicitud", "name": "Solicitud", "type": "object", "lane": "Sistema"},\n'
        '    {"id": "join_validaciones", "name": "Validaciones completadas", "type": "join", "lane": "Sistema"},\n'
        '    {"id": "fin", "name": "Fin", "type": "final", "lane": "Cliente"}\n'
        "  ],\n"
        '  "flows": [\n'
        '    {"from": "inicio", "to": "seleccionar_productos"},\n'
        '    {"from": "seleccionar_productos", "to": "hay_stock"},\n'
        '    {"from": "seleccionar_productos", "to": "validar_stock"},\n'
        '    {"from": "validar_stock", "to": "hay_stock"},\n'
        '    {"from": "hay_stock", "to": "fork_validaciones", "label": "[Si]"},\n'
        '    {"from": "fork_validaciones", "to": "obj_solicitud"},\n'
        '    {"from": "obj_solicitud", "to": "join_validaciones"},\n'
        '    {"from": "hay_stock", "to": "fin", "label": "[Sí]"}\n'
        "  ]\n"
        "}\n"
        "Reglas:\n"
        "- nodes.type solo puede ser: initial, action, decision o final.\n"
        "- Incluye exactamente un flujo principal de arriba hacia abajo y ramas simples cuando haya decisiones.\n"
        "- Usa labels en flows para guards como [Sí], [No], [Reintentar], [Aprobado], [Error].\n"
        "- Usa ids estables y consistentes entre nodes y flows.\n"
        "- Debe existir al menos 1 nodo initial, 1 nodo final y 1 flow.\n"
        "- Prioriza un caso feliz con ramas de decisión cortas y visualmente claras.\n"
        "- No generes swimlanes, object nodes, fork/join, notas ni coordenadas.\n"
        f"\nRequerimiento del usuario:\n{prompt_text}\n"
    )


def _build_activity_v2_prompt(prompt_text: str) -> str:
    return (
        "Eres un Arquitecto de Software Experto en UML. Tu trabajo es analizar requerimientos "
        "en texto libre y extraer un diagrama de actividad UML preciso.\n"
        "Devuelve SOLO un JSON con esta estructura estricta:\n"
        "{\n"
        '  "lanes": ["Cliente", "Sistema", "PasarelaPago"],\n'
        '  "nodes": [\n'
        '    {"id": "inicio", "name": "Inicio", "type": "initial", "lane": "Cliente"},\n'
        '    {"id": "confirmar_pedido", "name": "Confirmar pedido", "type": "action", "lane": "Cliente"},\n'
        '    {"id": "fork_validaciones", "name": "Validaciones en paralelo", "type": "fork", "lane": "Sistema"},\n'
        '    {"id": "validar_stock", "name": "Validar stock", "type": "action", "lane": "Sistema"},\n'
        '    {"id": "calcular_fraude", "name": "Calcular fraude", "type": "action", "lane": "Sistema"},\n'
        '    {"id": "join_validaciones", "name": "Validaciones completadas", "type": "join", "lane": "Sistema"},\n'
        '    {"id": "decision_validaciones", "name": "Validaciones OK?", "type": "decision", "lane": "Sistema"},\n'
        '    {"id": "enviar_cobro", "name": "Enviar solicitud de cobro", "type": "action", "lane": "Sistema"},\n'
        '    {"id": "solicitud_cobro", "name": "Solicitud de cobro", "type": "object", "lane": "PasarelaPago"},\n'
        '    {"id": "recibir_respuesta", "name": "Recibir respuesta", "type": "action", "lane": "PasarelaPago"},\n'
        '    {"id": "decision_pago", "name": "Pago aprobado?", "type": "decision", "lane": "Sistema"},\n'
        '    {"id": "fin", "name": "Fin", "type": "final", "lane": "Cliente"}\n'
        "  ],\n"
        '  "flows": [\n'
        '    {"from": "inicio", "to": "confirmar_pedido"},\n'
        '    {"from": "confirmar_pedido", "to": "fork_validaciones"},\n'
        '    {"from": "fork_validaciones", "to": "validar_stock"},\n'
        '    {"from": "fork_validaciones", "to": "calcular_fraude"},\n'
        '    {"from": "validar_stock", "to": "join_validaciones"},\n'
        '    {"from": "calcular_fraude", "to": "join_validaciones"},\n'
        '    {"from": "join_validaciones", "to": "decision_validaciones"},\n'
        '    {"from": "decision_validaciones", "to": "fin", "label": "[No]"},\n'
        '    {"from": "decision_validaciones", "to": "enviar_cobro", "label": "[Si]"},\n'
        '    {"from": "enviar_cobro", "to": "solicitud_cobro"},\n'
        '    {"from": "solicitud_cobro", "to": "recibir_respuesta"},\n'
        '    {"from": "recibir_respuesta", "to": "decision_pago"},\n'
        '    {"from": "decision_pago", "to": "fin", "label": "[No]"}\n'
        "  ]\n"
        "}\n"
        "Reglas:\n"
        "- nodes.type solo puede ser: initial, action, decision, final, fork, join u object.\n"
        "- lane es opcional, pero cuando exista debe representar el actor, sistema o area responsable.\n"
        "- Usa fork para abrir actividades paralelas y join para cerrarlas antes de continuar.\n"
        "- Usa object para artefactos o datos que viajan entre actividades, por ejemplo una solicitud de cobro u orden.\n"
        "- Usa labels en flows para guards como [Si], [No], [Reintentar], [Aprobado], [Error].\n"
        "- Usa ids estables y consistentes entre nodes y flows.\n"
        "- Debe existir al menos 1 nodo initial, 1 nodo final y 1 flow.\n"
        "- Si hay paralelismo real, modelalo explicitamente con un fork y un join, no con acciones superpuestas.\n"
        "- Prioriza un diagrama legible: pocas ramas por decision, un join claro y nombres concretos.\n"
        "- No generes notas ni coordenadas.\n"
        f"\nRequerimiento del usuario:\n{prompt_text}\n"
    )


def _build_component_prompt(prompt_text: str) -> str:
    return (
        "Eres un Arquitecto de Software Experto en UML. Tu trabajo es analizar requerimientos "
        "en texto libre y extraer un diagrama de componentes UML preciso.\n"
        "Devuelve SOLO un JSON con esta estructura estricta:\n"
        "{\n"
        '  "layers": ["client", "gateway", "service", "support", "external", "data"],\n'
        '  "components": [\n'
        '    {"id": "cliente_web", "name": "Cliente Web", "stereotype": "frontend", "layer": "client"},\n'
        '    {"id": "api_gateway", "name": "API Gateway", "stereotype": "gateway", "layer": "gateway"},\n'
        '    {"id": "servicio_pedidos", "name": "Servicio de Pedidos", "stereotype": "service", "layer": "service",'
        ' "interfaces": {"provided": ["PedidosAPI"], "required": ["PagosAPI", "InventarioAPI"]}},\n'
        '    {"id": "pasarela_pago", "name": "Pasarela de Pago Externa", "stereotype": "external", "layer": "external"},\n'
        '    {"id": "base_datos", "name": "Base de Datos", "stereotype": "database", "layer": "data"}\n'
        "  ],\n"
        '  "dependencies": [\n'
        '    {"from": "cliente_web", "to": "api_gateway", "label": "HTTPS / REST"},\n'
        '    {"from": "api_gateway", "to": "servicio_pedidos", "label": "crear pedido"},\n'
        '    {"from": "servicio_pedidos", "to": "pasarela_pago", "label": "procesar pago"},\n'
        '    {"from": "servicio_pedidos", "to": "base_datos", "label": "ordenes"}\n'
        "  ]\n"
        "}\n"
        "Reglas:\n"
        "- components.stereotype solo puede ser: frontend, gateway, service, external, database o component.\n"
        "- components.layer solo puede ser: client, gateway, service, support, external o data.\n"
        "- Usa interfaces.provided y interfaces.required solo si el prompt las menciona claramente.\n"
        "- No infieras interfaces de forma agresiva si no son claras.\n"
        "- Las dependencies deben conectar ids exactos de components.\n"
        "- Organiza los componentes por capas lógicas de izquierda a derecha.\n"
        "- Devuelve al menos 2 components y 1 dependency.\n"
        f"\nRequerimiento del usuario:\n{prompt_text}\n"
    )


def _infer_component_stereotype(name: str, current_stereotype: str) -> str:
    if current_stereotype in COMPONENT_STEREOTYPES and current_stereotype != "component":
        return current_stereotype

    normalized = _normalize_text(name).casefold()
    if any(token in normalized for token in ("cliente", "frontend", "web", "ui", "mobile", "movil", "app")):
        return "frontend"
    if "gateway" in normalized or "api" in normalized:
        return "gateway"
    if any(token in normalized for token in ("base de datos", "database", "db", "repositorio")):
        return "database"
    if any(token in normalized for token in ("extern", "third party", "tercero", "pasarela", "proveedor")):
        return "external"
    if any(token in normalized for token in ("worker", "cola", "queue", "notificacion", "notificación", "cache")):
        return "support"
    if "servicio" in normalized or "service" in normalized:
        return "service"
    return "component"


def _infer_component_layer(stereotype: str) -> str:
    return {
        "frontend": "client",
        "gateway": "gateway",
        "service": "service",
        "external": "external",
        "database": "data",
        "component": "service",
        "support": "support",
    }.get(stereotype, "service")


def _normalize_component_diagram(parsed: Dict[str, Any]) -> Dict[str, Any]:
    raw_layers = parsed.get("layers", []) or []
    raw_components = parsed.get("components", parsed.get("elements", [])) or []
    raw_dependencies = parsed.get("dependencies", parsed.get("relationships", [])) or []

    layers: List[str] = []
    layer_keys = set()

    for raw_layer in raw_layers:
        layer_name = _normalize_text(raw_layer).lower()
        if layer_name in COMPONENT_LAYERS and layer_name not in layer_keys:
            layer_keys.add(layer_name)
            layers.append(layer_name)

    components: List[Dict[str, Any]] = []
    components_by_id: Dict[str, Dict[str, Any]] = {}
    aliases: Dict[str, str] = {}

    def register_alias(value: Any, component_id: str) -> None:
        alias = _normalize_text(value)
        if alias:
            aliases[alias.casefold()] = component_id

    for index, raw in enumerate(raw_components, start=1):
        if not isinstance(raw, dict):
            continue

        raw_name = _normalize_text(raw.get("name") or raw.get("label") or raw.get("title"))
        candidate_id = raw.get("id") or raw_name or f"component_{index}"
        component_id = _stable_identifier(candidate_id, f"component_{index}")

        if component_id in components_by_id:
            register_alias(raw.get("id"), component_id)
            register_alias(raw_name, component_id)
            continue

        stereotype = _infer_component_stereotype(
            raw_name or component_id,
            _normalize_text(raw.get("stereotype") or raw.get("type") or "component").lower(),
        )
        layer = _normalize_text(raw.get("layer") or raw.get("group") or raw.get("package")).lower()
        if layer not in COMPONENT_LAYERS:
            layer = _infer_component_layer(stereotype)
        if layer not in layer_keys:
            layer_keys.add(layer)
            layers.append(layer)

        interfaces_payload = raw.get("interfaces") if isinstance(raw.get("interfaces"), dict) else {}
        provided = [
            _normalize_text(item)
            for item in (interfaces_payload.get("provided") or [])
            if _normalize_text(item)
        ]
        required = [
            _normalize_text(item)
            for item in (interfaces_payload.get("required") or [])
            if _normalize_text(item)
        ]

        component = {
            "id": component_id,
            "name": raw_name or component_id.replace("_", " ").title(),
            "stereotype": stereotype,
            "layer": layer,
            "interfaces": {
                "provided": provided,
                "required": required,
            },
        }
        components.append(component)
        components_by_id[component_id] = component
        register_alias(component_id, component_id)
        register_alias(raw.get("id"), component_id)
        register_alias(component["name"], component_id)

    def resolve_component_id(value: Any) -> str:
        candidate = _normalize_text(value)
        if not candidate:
            return ""
        return aliases.get(candidate.casefold(), _stable_identifier(candidate))

    dependencies: List[Dict[str, str]] = []
    for raw in raw_dependencies:
        if not isinstance(raw, dict):
            continue
        source = resolve_component_id(raw.get("from") or raw.get("source"))
        target = resolve_component_id(raw.get("to") or raw.get("target"))
        if not source or not target:
            continue
        if source not in components_by_id or target not in components_by_id:
            raise ValueError("Component diagram contains dependencies referencing unknown components.")
        dependencies.append(
            {
                "from": source,
                "to": target,
                "label": _normalize_text(raw.get("label") or raw.get("name") or raw.get("protocol")),
            }
        )

    if not components and not dependencies:
        return {"layers": list(COMPONENT_LAYERS), "components": [], "dependencies": []}

    if len(components) < 2 or len(dependencies) < 1:
        raise ValueError("Component diagram generation requires at least 2 components and 1 dependency.")

    ordered_layers = [layer for layer in COMPONENT_LAYERS if layer in layer_keys]
    remaining_layers = [layer for layer in layers if layer not in ordered_layers]

    return {
        "layers": ordered_layers + remaining_layers,
        "components": components,
        "dependencies": dependencies,
    }


def _build_deployment_prompt(prompt_text: str) -> str:
    return (
        "Eres un Arquitecto de Software Experto en UML. Tu trabajo es analizar requerimientos "
        "en texto libre y extraer un diagrama de despliegue UML preciso.\n"
        "Devuelve SOLO un JSON con esta estructura estricta:\n"
        "{\n"
        '  "nodes": [\n'
        '    {"id": "cliente_web", "name": "Cliente Web", "type": "external_node"},\n'
        '    {"id": "api_gateway", "name": "API Gateway", "type": "node", "environment": "DMZ"},\n'
        '    {"id": "app_server", "name": "App Server", "type": "node", "environment": "Produccion"},\n'
        '    {"id": "runtime_java", "name": "JVM", "type": "execution_environment", "parentId": "app_server"},\n'
        '    {"id": "base_datos", "name": "Base de Datos", "type": "database_node", "environment": "Produccion"}\n'
        "  ],\n"
        '  "artifacts": [\n'
        '    {"id": "frontend", "name": "Frontend Web", "type": "artifact", "nodeId": "cliente_web"},\n'
        '    {"id": "backend_api", "name": "Backend API", "type": "service", "nodeId": "runtime_java"},\n'
        '    {"id": "worker", "name": "Worker de Emails", "type": "service", "nodeId": "app_server"},\n'
        '    {"id": "db_schema", "name": "PostgreSQL", "type": "database", "nodeId": "base_datos"}\n'
        "  ],\n"
        '  "connections": [\n'
        '    {"from": "cliente_web", "to": "api_gateway", "label": "HTTPS"},\n'
        '    {"from": "api_gateway", "to": "backend_api", "label": "REST"},\n'
        '    {"from": "backend_api", "to": "db_schema", "label": "SQL"},\n'
        '    {"from": "backend_api", "to": "worker", "label": "queue interna"}\n'
        "  ]\n"
        "}\n"
        "Reglas:\n"
        "- nodes.type solo puede ser: device, node, execution_environment, database_node o external_node.\n"
        "- artifacts.type solo puede ser: artifact, service o database.\n"
        "- Usa parentId solo si hay un entorno de ejecucion o nodo contenido dentro de otro nodo.\n"
        "- artifacts.nodeId debe apuntar a un node existente.\n"
        "- connections puede conectar nodes o artifacts por sus ids exactos.\n"
        "- Prioriza infraestructura basica: cliente, gateway, servidor, runtime, base de datos y servicios desplegados.\n"
        "- Devuelve al menos 2 nodes, 1 artifact o service y 1 connection.\n"
        "- No generes puertos, multiplicidades, coordenadas ni notas.\n"
        f"\nRequerimiento del usuario:\n{prompt_text}\n"
    )


def _infer_deployment_node_type(name: str, current_type: str) -> str:
    if current_type in DEPLOYMENT_NODE_TYPES:
        return current_type

    normalized = _normalize_text(name).casefold()
    if any(token in normalized for token in ("browser", "cliente", "usuario", "extern", "third party", "proveedor")):
        return "external_node"
    if any(token in normalized for token in ("database", "base de datos", "postgres", "mysql", "sql", "redis")):
        return "database_node"
    if any(token in normalized for token in ("runtime", "jvm", "container", "docker", "k8s", "kubernetes", "tomcat")):
        return "execution_environment"
    if any(token in normalized for token in ("server", "vm", "host", "gateway", "balanceador", "lb", "api")):
        return "node"
    if any(token in normalized for token in ("device", "dispositivo", "mobile", "movil")):
        return "device"
    return "node"


def _infer_deployment_artifact_type(name: str, current_type: str) -> str:
    if current_type in DEPLOYMENT_ARTIFACT_TYPES:
        return current_type

    normalized = _normalize_text(name).casefold()
    if any(token in normalized for token in ("database", "base de datos", "schema", "postgres", "mysql")):
        return "database"
    if any(token in normalized for token in ("service", "api", "worker", "backend", "frontend")):
        return "service"
    return "artifact"


def _normalize_deployment_diagram(parsed: Dict[str, Any]) -> Dict[str, Any]:
    raw_nodes = parsed.get("nodes", parsed.get("devices", [])) or []
    raw_artifacts = parsed.get("artifacts", parsed.get("services", [])) or []
    raw_connections = parsed.get("connections", parsed.get("relationships", [])) or []

    nodes: List[Dict[str, str]] = []
    nodes_by_id: Dict[str, Dict[str, str]] = {}
    artifacts: List[Dict[str, str]] = []
    artifacts_by_id: Dict[str, Dict[str, str]] = {}
    aliases: Dict[str, str] = {}

    def register_alias(value: Any, entity_id: str) -> None:
        alias = _normalize_text(value)
        if alias:
            aliases[alias.casefold()] = entity_id

    for index, raw in enumerate(raw_nodes, start=1):
        if not isinstance(raw, dict):
            continue

        raw_name = _normalize_text(raw.get("name") or raw.get("label") or raw.get("title"))
        candidate_id = raw.get("id") or raw_name or f"node_{index}"
        node_id = _stable_identifier(candidate_id, f"node_{index}")
        if node_id in nodes_by_id:
            register_alias(raw.get("id"), node_id)
            register_alias(raw_name, node_id)
            continue

        node_type = _infer_deployment_node_type(
            raw_name or node_id,
            _normalize_text(raw.get("type") or raw.get("node_type") or "node").lower(),
        )
        node = {
            "id": node_id,
            "name": raw_name or node_id.replace("_", " ").title(),
            "type": node_type,
            "environment": _normalize_text(raw.get("environment") or raw.get("zone") or raw.get("network")),
            "parentId": "",
        }
        nodes.append(node)
        nodes_by_id[node_id] = node
        register_alias(node_id, node_id)
        register_alias(raw.get("id"), node_id)
        register_alias(node["name"], node_id)

    def resolve_entity_id(value: Any) -> str:
        candidate = _normalize_text(value)
        if not candidate:
            return ""
        return aliases.get(candidate.casefold(), _stable_identifier(candidate))

    for raw in raw_nodes:
        if not isinstance(raw, dict):
            continue
        current_id = resolve_entity_id(raw.get("id") or raw.get("name") or raw.get("label"))
        parent_id = resolve_entity_id(raw.get("parentId") or raw.get("parent_id") or raw.get("parent"))
        if current_id in nodes_by_id and parent_id and parent_id in nodes_by_id and parent_id != current_id:
            nodes_by_id[current_id]["parentId"] = parent_id

    for index, raw in enumerate(raw_artifacts, start=1):
        if not isinstance(raw, dict):
            continue

        raw_name = _normalize_text(raw.get("name") or raw.get("label") or raw.get("title"))
        candidate_id = raw.get("id") or raw_name or f"artifact_{index}"
        artifact_id = _stable_identifier(candidate_id, f"artifact_{index}")
        if artifact_id in artifacts_by_id:
            register_alias(raw.get("id"), artifact_id)
            register_alias(raw_name, artifact_id)
            continue

        node_id = resolve_entity_id(raw.get("nodeId") or raw.get("node_id") or raw.get("node") or raw.get("deployed_on"))
        if node_id not in nodes_by_id:
            raise ValueError("Deployment diagram contains artifacts referencing unknown nodes.")

        artifact_type = _infer_deployment_artifact_type(
            raw_name or artifact_id,
            _normalize_text(raw.get("type") or raw.get("artifact_type") or "artifact").lower(),
        )
        artifact = {
            "id": artifact_id,
            "name": raw_name or artifact_id.replace("_", " ").title(),
            "type": artifact_type,
            "nodeId": node_id,
        }
        artifacts.append(artifact)
        artifacts_by_id[artifact_id] = artifact
        register_alias(artifact_id, artifact_id)
        register_alias(raw.get("id"), artifact_id)
        register_alias(artifact["name"], artifact_id)

    connections: List[Dict[str, str]] = []
    valid_entity_ids = set(nodes_by_id) | set(artifacts_by_id)
    for raw in raw_connections:
        if not isinstance(raw, dict):
            continue
        source = resolve_entity_id(raw.get("from") or raw.get("source"))
        target = resolve_entity_id(raw.get("to") or raw.get("target"))
        if not source or not target:
            continue
        if source not in valid_entity_ids or target not in valid_entity_ids:
            raise ValueError("Deployment diagram contains connections referencing unknown nodes or artifacts.")
        connections.append(
            {
                "from": source,
                "to": target,
                "label": _normalize_text(raw.get("label") or raw.get("name") or raw.get("protocol")),
            }
        )

    if not nodes and not artifacts and not connections:
        return {"nodes": [], "artifacts": [], "connections": []}

    if len(nodes) < 2 or len(artifacts) < 1 or len(connections) < 1:
        raise ValueError("Deployment diagram generation requires at least 2 nodes, 1 artifact or service, and 1 connection.")

    return {"nodes": nodes, "artifacts": artifacts, "connections": connections}


def _normalize_activity_diagram(parsed: Dict[str, Any]) -> Dict[str, Any]:
    raw_nodes = parsed.get("nodes", parsed.get("elements", [])) or []
    raw_flows = parsed.get("flows", parsed.get("relationships", [])) or []
    raw_lanes = parsed.get("lanes", parsed.get("swimlanes", [])) or []

    nodes: List[Dict[str, str]] = []
    nodes_by_id: Dict[str, Dict[str, str]] = {}
    aliases: Dict[str, str] = {}
    lanes: List[str] = []
    lane_keys = set()

    def register_lane(value: Any) -> str:
        lane_name = _normalize_text(value.get("name") if isinstance(value, dict) else value)
        if not lane_name:
            return ""
        key = lane_name.casefold()
        if key not in lane_keys:
            lane_keys.add(key)
            lanes.append(lane_name)
        return lane_name

    for raw_lane in raw_lanes:
        register_lane(raw_lane)

    for index, raw in enumerate(raw_nodes, start=1):
        if not isinstance(raw, dict):
            continue

        node_type = _normalize_text(raw.get("type") or raw.get("node_type") or "action").lower()
        if node_type not in ACTIVITY_NODE_TYPES:
            continue

        raw_name = _normalize_text(raw.get("name") or raw.get("label") or raw.get("title"))
        candidate_id = raw.get("id") or raw_name or f"{node_type}_{index}"
        normalized_id = _stable_identifier(candidate_id, f"{node_type}_{index}")

        if normalized_id in nodes_by_id:
            aliases[_normalize_text(raw.get("id")).casefold()] = normalized_id
            aliases[raw_name.casefold()] = normalized_id
            continue

        if raw_name:
            name = raw_name
        elif node_type == "initial":
            name = "Inicio"
        elif node_type == "final":
            name = "Fin"
        elif node_type == "fork":
            name = "Fork"
        elif node_type == "join":
            name = "Join"
        else:
            name = normalized_id.replace("_", " ").title()

        lane_name = register_lane(raw.get("lane") or raw.get("swimlane") or raw.get("partition"))
        node = {"id": normalized_id, "name": name, "type": node_type, "lane": lane_name}
        nodes.append(node)
        nodes_by_id[normalized_id] = node
        aliases[normalized_id.casefold()] = normalized_id
        aliases[_normalize_text(raw.get("id")).casefold()] = normalized_id
        aliases[name.casefold()] = normalized_id

    def resolve_node_id(value: Any) -> str:
        candidate = _normalize_text(value)
        if not candidate:
            return ""
        return aliases.get(candidate.casefold(), _stable_identifier(candidate))

    flows: List[Dict[str, str]] = []
    for raw in raw_flows:
        if not isinstance(raw, dict):
            continue

        source = resolve_node_id(raw.get("from") or raw.get("source"))
        target = resolve_node_id(raw.get("to") or raw.get("target"))
        if not source or not target:
            continue
        if source not in nodes_by_id or target not in nodes_by_id:
            raise ValueError(
                "Activity diagram contains flows referencing unknown nodes."
            )

        label = _normalize_text(raw.get("label") or raw.get("guard") or raw.get("name"))
        flows.append({"from": source, "to": target, "label": label})

    if not nodes and not flows:
        return {"lanes": lanes, "nodes": [], "flows": []}

    has_initial = any(node["type"] == "initial" for node in nodes)
    has_final = any(node["type"] == "final" for node in nodes)

    if not has_initial or not has_final or not flows:
        raise ValueError(
            "Activity diagram generation requires at least 1 initial node, 1 final node and 1 flow."
        )

    return {"lanes": lanes, "nodes": nodes, "flows": flows}


async def generate_minutes(
    transcript: str, meeting_title: str, participants: List[str], language: str
) -> Dict[str, Any]:
    prompt = _build_minutes_prompt(transcript, meeting_title, participants, language)
    raw = await _call_llm(prompt, json_mode=True)
    try:
        parsed = _safe_parse_json(raw)
    except json.JSONDecodeError:
        parsed = {"summary": raw, "key_points": [], "agreements": []}
    parsed.setdefault("summary", "")
    parsed.setdefault("key_points", [])
    parsed.setdefault("agreements", [])
    normalized = []
    for i, item in enumerate(parsed.get("agreements", []) or []):
        if isinstance(item, dict):
            normalized.append(
                {"order": int(item.get("order") or i + 1), "text": str(item.get("text", ""))}
            )
        else:
            normalized.append({"order": i + 1, "text": str(item)})
    parsed["agreements"] = normalized
    return parsed


async def extract_suggestions(
    agreements: List[str], project_members: List[Dict[str, str]], language: str
) -> Dict[str, Any]:
    if not agreements:
        return {"suggestions": []}
    prompt = _build_suggestions_prompt(agreements, project_members, language)
    raw = await _call_llm(prompt, json_mode=True)
    try:
        parsed = _safe_parse_json(raw)
    except json.JSONDecodeError:
        parsed = {"suggestions": []}
    parsed.setdefault("suggestions", [])
    return parsed


def _build_chat_summary_prompt(transcript: str, language: str) -> str:
    if language == "es":
        return (
            "Eres un asistente que resume conversaciones de chat de un equipo de trabajo.\n"
            "Resume los mensajes recientes en 3 a 5 viñetas claras y concisas que respondan "
            '"¿qué me perdí?". Enfócate en decisiones, pedidos, bloqueos y próximos pasos.\n'
            'Devuelve SOLO un JSON con esta estructura: {"summary": ["viñeta 1", "viñeta 2"]}\n'
            "Si no hay nada relevante, devuelve una lista vacía.\n"
            f"\nConversación:\n{transcript}\n"
        )
    return (
        "You summarize a team chat conversation. Summarize the recent messages in 3-5 "
        'concise bullets answering "what did I miss?". Focus on decisions, requests, '
        'blockers and next steps. Return ONLY JSON: {"summary": ["bullet 1", "bullet 2"]}\n'
        f"\nConversation:\n{transcript}\n"
    )


async def summarize_chat(transcript: str, language: str = "es") -> Dict[str, Any]:
    if not transcript.strip():
        return {"summary": []}
    prompt = _build_chat_summary_prompt(transcript, language)
    raw = await _call_llm(prompt, json_mode=True)
    try:
        parsed = _safe_parse_json(raw)
    except json.JSONDecodeError:
        parsed = {"summary": [line.strip("-• ") for line in raw.splitlines() if line.strip()]}
    summary = parsed.get("summary", []) or []
    # Normalize to a list of non-empty strings.
    normalized = [str(item).strip() for item in summary if str(item).strip()]
    return {"summary": normalized}


def _build_detect_type_prompt(transcript: str, meeting_title: str, participants: List[str], language: str) -> str:
    participants_str = ", ".join(participants) if participants else "(no listados)"
    if language == "es":
        return (
            "Eres un asistente experto en metodologÃ­as Ã¡giles (Scrum/Kanban).\n"
            "Analiza la transcripciÃ³n y detecta el tipo de reuniÃ³n. Devuelve SOLO un JSON con:\n"
            '{"meeting_type": "DAILY|SPRINT_PLANNING|REGULAR", "confidence": 0.95, "reason": "explicaciÃ³n breve"}\n'
            "Reglas:\n"
            '- DAILY: si los participantes responden preguntas como "Â¿quÃ© hice ayer?", "Â¿quÃ© harÃ© hoy?", "Â¿tengo impedimentos?". Suele ser breve (<30 min).\n'
            '- SPRINT_PLANNING: si se habla de objetivos del sprint, historias de usuario, estimaciones, asignaciÃ³n de tareas para el prÃ³ximo sprint.\n'
            '- REGULAR: cualquier otra reuniÃ³n (retrospectiva, revisiÃ³n, tÃ©cnica, general).\n'
            f"\nTÃ­tulo: {meeting_title}\nParticipantes: {participants_str}\nTranscripciÃ³n:\n{transcript}\n"
        )
    return (
        "You are an expert in agile methodologies. Classify this meeting. Return JSON:\n"
        '{"meeting_type": "DAILY|SPRINT_PLANNING|REGULAR", "confidence": 0.95, "reason": "brief reason"}\n'
        f"Title: {meeting_title}\nParticipants: {participants_str}\nTranscript:\n{transcript}\n"
    )


def _build_analyze_daily_prompt(transcript: str, participants: List[str], language: str) -> str:
    participants_str = ", ".join(participants) if participants else "(no listados)"
    if language == "es":
        return (
            "Eres un asistente que analiza reuniones de Daily Scrum.\n"
            "Para cada participante extrae sus respuestas a las 3 preguntas del Daily:\n"
            "1. Â¿QuÃ© hice ayer para contribuir al Sprint?\n"
            "2. Â¿QuÃ© voy a hacer hoy para contribuir al Sprint?\n"
            "3. Â¿Veo algÃºn impedimento que impida lograr el objetivo del Sprint?\n\n"
            "Devuelve SOLO un JSON con esta estructura:\n"
            "{\n"
            '  "entries": [\n'
            '    {"participant_name": "nombre", "yesterday": "resumen", "today": "resumen", "blockers": ["bloqueo 1"]}\n'
            "  ],\n"
            '  "overall_blockers": ["lista de todos los bloqueos del equipo"],\n'
            '  "sprint_health": "GREEN|YELLOW|RED"\n'
            "}\n"
            "Reglas:\n"
            "- sprint_health: GREEN = sin bloqueos, YELLOW = algÃºn bloqueo menor, RED = bloqueos crÃ­ticos o varios participantes bloqueados.\n"
            "- Si un participante no mencionÃ³ algo, usa string vacÃ­o.\n"
            "- overall_blockers consolida todos los bloqueos Ãºnicos.\n"
            f"\nParticipantes: {participants_str}\nTranscripciÃ³n:\n{transcript}\n"
        )
    return (
        "You analyze Daily Scrum meetings. For each participant extract answers to the 3 daily questions.\n"
        "Return JSON: {entries:[{participant_name, yesterday, today, blockers:[]}], overall_blockers:[], sprint_health:'GREEN|YELLOW|RED'}\n"
        f"Participants: {participants_str}\nTranscript:\n{transcript}\n"
    )


def _build_analyze_sprint_prompt(
    transcript: str, meeting_title: str, participants: List[str],
    project_members: List[Dict[str, str]], language: str
) -> str:
    participants_str = ", ".join(participants) if participants else "(no listados)"
    members_str = "\n".join(f"- {m['id']} â†’ {m['name']}" for m in project_members) if project_members else "(ninguno)"
    if language == "es":
        return (
            "Eres un asistente experto en planificaciÃ³n de Sprints.\n"
            "Analiza la transcripciÃ³n de una reuniÃ³n de Sprint Planning y devuelve un JSON con:\n"
            "{\n"
            '  "sprint_goal": "objetivo del sprint acordado",\n'
            '  "sprint_duration_weeks": 2,\n'
            '  "user_stories": ["Historia de usuario 1", "Historia de usuario 2"],\n'
            '  "tasks": [\n'
            '    {"title": "TÃ­tulo de tarea", "description": "Detalle", "priority": "LOW|MEDIUM|HIGH", '
            '"suggested_responsible_id": "uuid-o-null", "story_points": 3}\n'
            "  ]\n"
            "}\n"
            "Reglas:\n"
            "- sprint_goal: objetivo concreto del sprint.\n"
            "- user_stories: historias mencionadas.\n"
            "- tasks: tareas concretas acordadas, con estimaciÃ³n en story points si se mencionÃ³.\n"
            "- Asigna suggested_responsible_id SOLO si el nombre coincide con un miembro listado.\n"
            f"\nMiembros del proyecto:\n{members_str}\n"
            f"Participantes: {participants_str}\nTÃ­tulo: {meeting_title}\nTranscripciÃ³n:\n{transcript}\n"
        )
    return (
        "You analyze Sprint Planning meetings. Return JSON with sprint_goal, sprint_duration_weeks, user_stories[], tasks[].\n"
        f"Members:\n{members_str}\nTranscript:\n{transcript}\n"
    )


def _build_detect_kanban_prompt(
    transcript: str, existing_tasks: List[Dict[str, str]], language: str
) -> str:
    tasks_str = (
        "\n".join(f"- ID:{t['id']} | TÃ­tulo: {t['title']} | Columna actual: {t['column_title']}" for t in existing_tasks)
        if existing_tasks else "(no hay tareas registradas)"
    )
    if language == "es":
        return (
            "Eres un asistente que detecta actualizaciones de tareas mencionadas durante una reuniÃ³n.\n"
            "Analiza la transcripciÃ³n y detecta si alguien mencionÃ³ que una tarea:\n"
            "- Fue completada / terminada / finalizada â†’ new_status: DONE\n"
            "- EstÃ¡ en progreso / empezando / trabajando en ello â†’ new_status: IN_PROGRESS\n"
            "- EstÃ¡ bloqueada / tiene impedimento â†’ new_status: BLOCKED\n\n"
            "Devuelve SOLO un JSON:\n"
            "{\n"
            '  "updates": [\n'
            '    {"task_id": "uuid-si-coincide-con-lista-o-null", "task_title": "tÃ­tulo mencionado", '
            '"new_status": "DONE|IN_PROGRESS|BLOCKED", "mentioned_by": "nombre del participante", '
            '"confidence": 0.9, "notes": "contexto adicional"}\n'
            "  ]\n"
            "}\n"
            "Reglas:\n"
            "- task_id: intenta hacer match fuzzy con los IDs de la lista de tareas existentes. Si no hay match claro, usa null.\n"
            "- Solo incluye actualizaciones con confidence >= 0.7.\n"
            "- Si no hay actualizaciones, devuelve updates: [].\n"
            f"\nTareas existentes en el proyecto:\n{tasks_str}\n\nTranscripciÃ³n:\n{transcript}\n"
        )
    return (
        "Detect task status updates mentioned during the meeting. Return JSON: "
        "{updates:[{task_id,task_title,new_status:'DONE|IN_PROGRESS|BLOCKED',mentioned_by,confidence,notes}]}\n"
        f"Existing tasks:\n{tasks_str}\nTranscript:\n{transcript}\n"
    )


async def detect_meeting_type(
    transcript: str, meeting_title: str, participants: List[str], language: str
) -> Dict[str, Any]:
    prompt = _build_detect_type_prompt(transcript, meeting_title, participants, language)
    raw = await _call_llm(prompt, json_mode=True)
    try:
        parsed = _safe_parse_json(raw)
    except json.JSONDecodeError:
        parsed = {}
    valid_types = {"DAILY", "SPRINT_PLANNING", "REGULAR"}
    if parsed.get("meeting_type") not in valid_types:
        parsed["meeting_type"] = "REGULAR"
    parsed.setdefault("confidence", 0.5)
    parsed.setdefault("reason", "")
    return parsed


async def analyze_daily(
    transcript: str, participants: List[str], language: str
) -> Dict[str, Any]:
    prompt = _build_analyze_daily_prompt(transcript, participants, language)
    raw = await _call_llm(prompt, json_mode=True)
    try:
        parsed = _safe_parse_json(raw)
    except json.JSONDecodeError:
        parsed = {}
    parsed.setdefault("entries", [])
    parsed.setdefault("overall_blockers", [])
    valid_health = {"GREEN", "YELLOW", "RED"}
    if parsed.get("sprint_health") not in valid_health:
        parsed["sprint_health"] = "GREEN"
    normalized_entries = []
    for entry in parsed.get("entries", []) or []:
        if isinstance(entry, dict):
            normalized_entries.append({
                "participant_name": str(entry.get("participant_name", "")),
                "yesterday": str(entry.get("yesterday", "")),
                "today": str(entry.get("today", "")),
                "blockers": [str(b) for b in (entry.get("blockers") or [])],
            })
    parsed["entries"] = normalized_entries
    return parsed


async def analyze_sprint_planning(
    transcript: str, meeting_title: str, participants: List[str],
    project_members: List[Dict[str, str]], language: str
) -> Dict[str, Any]:
    prompt = _build_analyze_sprint_prompt(transcript, meeting_title, participants, project_members, language)
    raw = await _call_llm(prompt, json_mode=True)
    try:
        parsed = _safe_parse_json(raw)
    except json.JSONDecodeError:
        parsed = {}
    parsed.setdefault("sprint_goal", "")
    parsed.setdefault("sprint_duration_weeks", None)
    parsed.setdefault("user_stories", [])
    parsed.setdefault("tasks", [])
    return parsed


async def detect_kanban_updates(
    transcript: str, existing_tasks: List[Dict[str, str]], language: str
) -> Dict[str, Any]:
    if not transcript.strip():
        return {"updates": []}
    prompt = _build_detect_kanban_prompt(transcript, existing_tasks, language)
    raw = await _call_llm(prompt, json_mode=True)
    try:
        parsed = _safe_parse_json(raw)
    except json.JSONDecodeError:
        parsed = {"updates": []}
    parsed.setdefault("updates", [])
    filtered = [
        u for u in (parsed.get("updates") or [])
        if isinstance(u, dict) and float(u.get("confidence", 0)) >= 0.7
    ]
    parsed["updates"] = filtered
    return parsed


def _build_architecture_prompt(prompt_text: str) -> str:
    return (
        "Eres un Arquitecto de Software Experto. Tu trabajo es analizar requerimientos "
        "en texto libre y extraer un modelo de clases UML preciso.\n"
        "Devuelve SOLO un JSON con la siguiente estructura estricta:\n"
        "{\n"
        '  "elements": [\n'
        '    {"name": "NombreClase", "type": "Class", "attributes": ["atributo1: tipo", "atributo2: tipo"]}\n'
        "  ],\n"
        '  "relationships": [\n'
        '    {"source": "ClaseOrigen", "target": "ClaseDestino", "type": "AsociaciÃ³n|AgregaciÃ³n|ComposiciÃ³n|GeneralizaciÃ³n"}\n'
        "  ]\n"
        "}\n"
        "Reglas:\n"
        "- Extrae las entidades principales como elementos tipo 'Class'.\n"
        "- Deduce atributos lÃ³gicos si no se especifican (ej. id, nombre).\n"
        "- Las relaciones deben conectar nombres exactos de las clases extraÃ­das.\n"
        "- Si el prompt es muy simple, deduce al menos 3 o 4 clases lÃ³gicas.\n"
        f"\nRequerimiento del usuario:\n{prompt_text}\n"
    )


def _build_use_case_prompt(prompt_text: str) -> str:
    return (
        "Eres un Analista de Requerimientos Experto. Tu trabajo es analizar requerimientos "
        "en texto libre y extraer un modelo de Casos de Uso UML preciso.\n"
        "Devuelve SOLO un JSON con la siguiente estructura estricta:\n"
        "{\n"
        '  "elements": [\n'
        '    {"name": "UsuarioWeb", "type": "Actor"},\n'
        '    {"name": "Comprar Producto", "type": "UseCase"}\n'
        "  ],\n"
        '  "relationships": [\n'
        '    {"source": "UsuarioWeb", "target": "Comprar Producto", "type": "Association"}\n'
        "  ]\n"
        "}\n"
        "Reglas:\n"
        "- Extrae los roles principales como elementos tipo 'Actor'.\n"
        "- Extrae las acciones principales como elementos tipo 'UseCase'.\n"
        "- Las relaciones pueden ser 'Association' (Actor a Caso de Uso), 'Include' o 'Extend' (Caso de Uso a Caso de Uso).\n"
        f"\nRequerimiento del usuario:\n{prompt_text}\n"
    )


def _build_sequence_prompt(prompt_text: str) -> str:
    return (
        "Eres un Arquitecto de Software Experto en UML. Tu trabajo es analizar requerimientos "
        "en texto libre y extraer un diagrama de secuencia UML preciso.\n"
        "Devuelve SOLO un JSON con esta estructura estricta:\n"
        "{\n"
        '  "participants": [\n'
        '    {"name": "Usuario", "type": "actor"},\n'
        '    {"name": "ServicioAutenticacion", "type": "control"},\n'
        '    {"name": "BaseDeDatos", "type": "entity"}\n'
        "  ],\n"
        '  "messages": [\n'
        '    {"from": "Usuario", "to": "ServicioAutenticacion", "message": "iniciarSesion(usuario, clave)", "kind": "sync"},\n'
        '    {"from": "ServicioAutenticacion", "to": "BaseDeDatos", "message": "buscarUsuario(usuario)", "kind": "sync"},\n'
        '    {"from": "ServicioAutenticacion", "to": "ServicioAutenticacion", "message": "validarFormato()", "kind": "sync"},\n'
        '    {"from": "BaseDeDatos", "to": "ServicioAutenticacion", "message": "usuarioEncontrado", "kind": "return"}\n'
        "  ],\n"
        '  "fragments": [\n'
        '    {"type": "alt", "label": "Credenciales validas", "guard": "[usuario existe]", "start_message_index": 1, "end_message_index": 4},\n'
        '    {"type": "loop", "label": "Reintentos", "start_message_index": 1, "end_message_index": 2}\n'
        "  ],\n"
        '  "activations": [\n'
        '    {"participant": "ServicioAutenticacion", "start_message_index": 1, "end_message_index": 3}\n'
        "  ]\n"
        "}\n"
        "Reglas:\n"
        "- participants.type solo puede ser: actor, boundary, control, entity o lifeline.\n"
        "- messages.kind solo puede ser: sync, async o return.\n"
        "- fragments.type solo puede ser: alt, opt o loop.\n"
        "- Usa start_message_index y end_message_index con base 1 y refiriÃ©ndote a la lista messages.\n"
        "- Puedes usar self-messages cuando un participante se envÃ­a un mensaje a sÃ­ mismo.\n"
        "- Si el fragmento tiene una condiciÃ³n de guarda, inclÃºyela en guard o label.\n"
        "- Cuando existan ramas de Ã©xito y error, usa un solo fragmento alt que abarque ambas ramas; no generes varios alt independientes para el mismo punto de decisiÃ³n.\n"
        "- Devuelve al menos 2 participants y 1 message.\n"
        "- MantÃ©n los nombres de participants consistentes en messages, fragments y activations.\n"
        f"\nRequerimiento del usuario:\n{prompt_text}\n"
    )


async def parse_architecture_prompt(prompt_text: str, diagram_type: str = "class") -> Dict[str, Any]:
    if diagram_type not in SUPPORTED_DIAGRAM_TYPES:
        raise ValueError(
            f"Unsupported diagram_type '{diagram_type}'. Supported values: activity, class, component, deployment, sequence, use_case."
        )

    if not prompt_text.strip():
        if diagram_type == "sequence":
            return {"participants": [], "messages": [], "fragments": [], "activations": []}
        if diagram_type == "activity":
            return {"lanes": [], "nodes": [], "flows": []}
        if diagram_type == "component":
            return {"layers": list(COMPONENT_LAYERS), "components": [], "dependencies": []}
        if diagram_type == "deployment":
            return {"nodes": [], "artifacts": [], "connections": []}
        return {"elements": [], "relationships": []}

    if diagram_type == "use_case":
        prompt = _build_use_case_prompt(prompt_text)
    elif diagram_type == "sequence":
        prompt = _build_sequence_prompt(prompt_text)
    elif diagram_type == "activity":
        prompt = _build_activity_v2_prompt(prompt_text)
    elif diagram_type == "component":
        prompt = _build_component_prompt(prompt_text)
    elif diagram_type == "deployment":
        prompt = _build_deployment_prompt(prompt_text)
    else:
        prompt = _build_architecture_prompt(prompt_text)

    raw = await _call_llm(prompt, json_mode=True)
    try:
        parsed = _safe_parse_json(raw)
    except json.JSONDecodeError:
        if diagram_type == "sequence":
            parsed = {"participants": [], "messages": [], "fragments": [], "activations": []}
        elif diagram_type == "activity":
            parsed = {"lanes": [], "nodes": [], "flows": []}
        elif diagram_type == "component":
            parsed = {"layers": list(COMPONENT_LAYERS), "components": [], "dependencies": []}
        elif diagram_type == "deployment":
            parsed = {"nodes": [], "artifacts": [], "connections": []}
        else:
            parsed = {"elements": [], "relationships": []}

    if diagram_type == "sequence":
        return _normalize_sequence_diagram(parsed)
    if diagram_type == "activity":
        return _normalize_activity_diagram(parsed)
    if diagram_type == "component":
        return _normalize_component_diagram(parsed)
    if diagram_type == "deployment":
        return _normalize_deployment_diagram(parsed)

    if "classes" in parsed and "elements" not in parsed:
        parsed["elements"] = [
            {"name": c["name"], "type": "Class", "attributes": c.get("attributes", [])}
            for c in parsed["classes"]
        ]

    parsed.setdefault("elements", [])
    parsed.setdefault("relationships", [])
    return parsed


async def _call_llm(prompt: str, json_mode: bool = False) -> str:
    if settings.AI_PROVIDER == "deepseek":
        return _call_deepseek(prompt, json_mode)
    return _call_ollama(prompt, json_mode)


def _call_deepseek(prompt: str, json_mode: bool) -> str:
    if not settings.DEEPSEEK_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="DEEPSEEK_API_KEY is not configured. Set AI_PROVIDER=local to use Ollama.",
        )
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )
    completion = client.chat.completions.create(
        model=settings.DEEPSEEK_LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Responde solo con JSON vÃ¡lido cuando se te pida formato JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"} if json_mode else None,
        temperature=0.2,
    )
    return completion.choices[0].message.content or ""


def _call_ollama(prompt: str, json_mode: bool) -> str:
    try:
        import ollama
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="ollama package not installed. Run: pip install ollama",
        ) from exc

    client = ollama.Client(host=settings.OLLAMA_HOST)
    response = client.chat(
        model=settings.OLLAMA_LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Responde solo con JSON vÃ¡lido cuando se te pida formato JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        format="json" if json_mode else "",
        options={"temperature": 0.2},
    )
    return response["message"]["content"]
