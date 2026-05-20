import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.core.config import settings


def _build_minutes_prompt(transcript: str, meeting_title: str, participants: List[str], language: str) -> str:
    participants_str = ", ".join(participants) if participants else "(no se listaron)"
    if language == "es":
        return (
            "Eres un asistente que redacta minutas de reuniones de equipos de software.\n"
            "Analiza la transcripción y devuelve un JSON con esta estructura EXACTA:\n"
            "{\n"
            '  "summary": "Resumen ejecutivo de 2 a 4 párrafos.",\n'
            '  "key_points": ["Punto clave 1", "Punto clave 2"],\n'
            '  "agreements": [{"order": 1, "text": "Acuerdo concreto y accionable"}]\n'
            "}\n"
            "Reglas:\n"
            "- Los acuerdos deben ser frases cortas y accionables.\n"
            "- key_points son temas tratados, no acciones.\n"
            "- Si no hay información suficiente, devuelve listas vacías.\n"
            f"\nTítulo de la reunión: {meeting_title}\n"
            f"Participantes: {participants_str}\n"
            f"\nTranscripción:\n{transcript}\n"
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
    members_str = "\n".join(f"- {m['id']} → {m['name']}" for m in project_members)
    agreements_str = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(agreements))
    if language == "es":
        return (
            "Eres un asistente que convierte acuerdos de reunión en tareas accionables.\n"
            "Para cada acuerdo, genera una sugerencia de tarea. Devuelve SOLO un JSON con:\n"
            "{\n"
            '  "suggestions": [\n'
            '    {"title": "Título accionable", "description": "Detalle", "priority": "LOW|MEDIUM|HIGH", "suggested_responsible_id": "uuid-o-null"}\n'
            "  ]\n"
            "}\n"
            "Reglas:\n"
            "- El título debe ser breve e imperativo.\n"
            "- Asigna suggested_responsible_id SOLO si en el acuerdo se menciona un nombre que coincide con un miembro listado abajo.\n"
            "- Si no hay coincidencia clara, usa null.\n"
            "- priority por defecto MEDIUM, HIGH si hay urgencia explícita, LOW si es opcional.\n"
            f"\nMiembros del proyecto (id → nombre):\n{members_str or '(ninguno)'}\n"
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
    # Normalize agreements ordering
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


def _build_detect_type_prompt(transcript: str, meeting_title: str, participants: List[str], language: str) -> str:
    participants_str = ", ".join(participants) if participants else "(no listados)"
    if language == "es":
        return (
            "Eres un asistente experto en metodologías ágiles (Scrum/Kanban).\n"
            "Analiza la transcripción y detecta el tipo de reunión. Devuelve SOLO un JSON con:\n"
            '{"meeting_type": "DAILY|SPRINT_PLANNING|REGULAR", "confidence": 0.95, "reason": "explicación breve"}\n'
            "Reglas:\n"
            '- DAILY: si los participantes responden preguntas como "¿qué hice ayer?", "¿qué haré hoy?", "¿tengo impedimentos?". Suele ser breve (<30 min).\n'
            '- SPRINT_PLANNING: si se habla de objetivos del sprint, historias de usuario, estimaciones, asignación de tareas para el próximo sprint.\n'
            '- REGULAR: cualquier otra reunión (retrospectiva, revisión, técnica, general).\n'
            f"\nTítulo: {meeting_title}\nParticipantes: {participants_str}\nTranscripción:\n{transcript}\n"
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
            "1. ¿Qué hice ayer para contribuir al Sprint?\n"
            "2. ¿Qué voy a hacer hoy para contribuir al Sprint?\n"
            "3. ¿Veo algún impedimento que impida lograr el objetivo del Sprint?\n\n"
            "Devuelve SOLO un JSON con esta estructura:\n"
            "{\n"
            '  "entries": [\n'
            '    {"participant_name": "nombre", "yesterday": "resumen", "today": "resumen", "blockers": ["bloqueo 1"]}\n'
            "  ],\n"
            '  "overall_blockers": ["lista de todos los bloqueos del equipo"],\n'
            '  "sprint_health": "GREEN|YELLOW|RED"\n'
            "}\n"
            "Reglas:\n"
            "- sprint_health: GREEN = sin bloqueos, YELLOW = algún bloqueo menor, RED = bloqueos críticos o varios participantes bloqueados.\n"
            "- Si un participante no mencionó algo, usa string vacío.\n"
            "- overall_blockers consolida todos los bloqueos únicos.\n"
            f"\nParticipantes: {participants_str}\nTranscripción:\n{transcript}\n"
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
    members_str = "\n".join(f"- {m['id']} → {m['name']}" for m in project_members) if project_members else "(ninguno)"
    if language == "es":
        return (
            "Eres un asistente experto en planificación de Sprints.\n"
            "Analiza la transcripción de una reunión de Sprint Planning y devuelve un JSON con:\n"
            "{\n"
            '  "sprint_goal": "objetivo del sprint acordado",\n'
            '  "sprint_duration_weeks": 2,\n'
            '  "user_stories": ["Historia de usuario 1", "Historia de usuario 2"],\n'
            '  "tasks": [\n'
            '    {"title": "Título de tarea", "description": "Detalle", "priority": "LOW|MEDIUM|HIGH", '
            '"suggested_responsible_id": "uuid-o-null", "story_points": 3}\n'
            "  ]\n"
            "}\n"
            "Reglas:\n"
            "- sprint_goal: objetivo concreto del sprint.\n"
            "- user_stories: historias mencionadas.\n"
            "- tasks: tareas concretas acordadas, con estimación en story points si se mencionó.\n"
            "- Asigna suggested_responsible_id SOLO si el nombre coincide con un miembro listado.\n"
            f"\nMiembros del proyecto:\n{members_str}\n"
            f"Participantes: {participants_str}\nTítulo: {meeting_title}\nTranscripción:\n{transcript}\n"
        )
    return (
        "You analyze Sprint Planning meetings. Return JSON with sprint_goal, sprint_duration_weeks, user_stories[], tasks[].\n"
        f"Members:\n{members_str}\nTranscript:\n{transcript}\n"
    )


def _build_detect_kanban_prompt(
    transcript: str, existing_tasks: List[Dict[str, str]], language: str
) -> str:
    tasks_str = (
        "\n".join(f"- ID:{t['id']} | Título: {t['title']} | Columna actual: {t['column_title']}" for t in existing_tasks)
        if existing_tasks else "(no hay tareas registradas)"
    )
    if language == "es":
        return (
            "Eres un asistente que detecta actualizaciones de tareas mencionadas durante una reunión.\n"
            "Analiza la transcripción y detecta si alguien mencionó que una tarea:\n"
            "- Fue completada / terminada / finalizada → new_status: DONE\n"
            "- Está en progreso / empezando / trabajando en ello → new_status: IN_PROGRESS\n"
            "- Está bloqueada / tiene impedimento → new_status: BLOCKED\n\n"
            "Devuelve SOLO un JSON:\n"
            "{\n"
            '  "updates": [\n'
            '    {"task_id": "uuid-si-coincide-con-lista-o-null", "task_title": "título mencionado", '
            '"new_status": "DONE|IN_PROGRESS|BLOCKED", "mentioned_by": "nombre del participante", '
            '"confidence": 0.9, "notes": "contexto adicional"}\n'
            "  ]\n"
            "}\n"
            "Reglas:\n"
            "- task_id: intenta hacer match fuzzy con los IDs de la lista de tareas existentes. Si no hay match claro, usa null.\n"
            "- Solo incluye actualizaciones con confidence >= 0.7.\n"
            "- Si no hay actualizaciones, devuelve updates: [].\n"
            f"\nTareas existentes en el proyecto:\n{tasks_str}\n\nTranscripción:\n{transcript}\n"
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


async def _call_llm(prompt: str, json_mode: bool = False) -> str:
    if settings.AI_PROVIDER == "openai":
        return _call_openai(prompt, json_mode)
    return _call_ollama(prompt, json_mode)


def _call_openai(prompt: str, json_mode: bool) -> str:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured. Set AI_PROVIDER=local to use a local model.",
        )
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    completion = client.chat.completions.create(
        model=settings.OPENAI_LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Responde solo con JSON válido cuando se te pida formato JSON.",
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
                "content": "Responde solo con JSON válido cuando se te pida formato JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        format="json" if json_mode else "",
        options={"temperature": 0.2},
    )
    return response["message"]["content"]
