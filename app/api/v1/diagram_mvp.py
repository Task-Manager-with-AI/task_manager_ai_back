import os
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings
from app.services.diagram_mvp_service import (
    DiagramMvpService,
    public_url_for_file,
)
from app.services.llm_service import SUPPORTED_DIAGRAM_TYPES, parse_architecture_prompt

router = APIRouter(prefix="/diagram-mvp", tags=["Diagram MVP"])

OutputFormat = Literal["png", "svg"]


class DiagramMvpRequest(BaseModel):
    prompt: str
    diagram_type: str = "class"
    output_format: Optional[OutputFormat] = "png"


def _public_root() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    return os.path.join(base_dir, "app", "public", settings.DIAGRAM_MVP_PUBLIC_DIR)


async def _render_provider(req: DiagramMvpRequest, provider: Literal["mermaid", "kroki"], request: Request):
    if req.diagram_type not in SUPPORTED_DIAGRAM_TYPES:
        supported = ", ".join(sorted(SUPPORTED_DIAGRAM_TYPES))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported diagram_type '{req.diagram_type}'. Supported values: {supported}.",
        )

    try:
        architecture_data = await parse_architecture_prompt(req.prompt, req.diagram_type)
        architecture_data["diagram_type"] = req.diagram_type

        public_root = _public_root()
        service = DiagramMvpService(public_root)
        result = service.generate(
            architecture_data,
            req.diagram_type,
            provider,
            req.output_format or "png",
        )
        return {
            "status": "success",
            "provider": result.provider,
            "source_language": result.source_language,
            "diagram_type": result.diagram_type,
            "source": result.source,
            "url": public_url_for_file(
                result.file_path,
                str(request.base_url),
                public_root,
                settings.DIAGRAM_MVP_PUBLIC_DIR,
            ),
            "render_time_ms": result.render_time_ms,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/mermaid/generate")
async def generate_mermaid_diagram(req: DiagramMvpRequest, request: Request):
    return await _render_provider(req, "mermaid", request)


@router.post("/kroki/generate")
async def generate_kroki_diagram(req: DiagramMvpRequest, request: Request):
    return await _render_provider(req, "kroki", request)


@router.post("/compare")
async def compare_diagram_providers(req: DiagramMvpRequest, request: Request):
    mermaid = await _render_provider(req, "mermaid", request)
    kroki = await _render_provider(req, "kroki", request)
    return {
        "status": "success",
        "diagram_type": req.diagram_type,
        "results": [mermaid, kroki],
    }
