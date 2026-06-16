import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.core.config import settings

SUPPORTED_DIAGRAM_TYPES = {"class", "use_case", "sequence"}
SEQUENCE_PARTICIPANT_TYPES = {"actor", "boundary", "control", "entity", "lifeline"}
SEQUENCE_MESSAGE_KINDS = {"sync", "async", "return"}
SEQUENCE_FRAGMENT_TYPES = {"alt", "opt", "loop"}


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


def _normalize_index(value: Any, max_index: int, default: int) -> int:
    try:
        index = int(value)
    except (TypeError, ValueError):
        index = default
    if max_index < 1:
        return 1
    return max(1, min(index, max_index))


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
        "- Devuelve al menos 2 participants y 1 message.\n"
        "- MantÃ©n los nombres de participants consistentes en messages, fragments y activations.\n"
        f"\nRequerimiento del usuario:\n{prompt_text}\n"
    )


async def parse_architecture_prompt(prompt_text: str, diagram_type: str = "class") -> Dict[str, Any]:
    if diagram_type not in SUPPORTED_DIAGRAM_TYPES:
        raise ValueError(
            f"Unsupported diagram_type '{diagram_type}'. Supported values: class, use_case, sequence."
        )

    if not prompt_text.strip():
        if diagram_type == "sequence":
            return {"participants": [], "messages": [], "fragments": [], "activations": []}
        return {"elements": [], "relationships": []}

    if diagram_type == "use_case":
        prompt = _build_use_case_prompt(prompt_text)
    elif diagram_type == "sequence":
        prompt = _build_sequence_prompt(prompt_text)
    else:
        prompt = _build_architecture_prompt(prompt_text)

    raw = await _call_llm(prompt, json_mode=True)
    try:
        parsed = _safe_parse_json(raw)
    except json.JSONDecodeError:
        if diagram_type == "sequence":
            parsed = {"participants": [], "messages": [], "fragments": [], "activations": []}
        else:
            parsed = {"elements": [], "relationships": []}

    if diagram_type == "sequence":
        return _normalize_sequence_diagram(parsed)

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
