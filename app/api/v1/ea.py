import os
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.ea_service import EnterpriseArchitectService
from app.services.llm_service import SUPPORTED_DIAGRAM_TYPES, parse_architecture_prompt

router = APIRouter(prefix="/ea", tags=["Enterprise Architect"])


class DiagramRequest(BaseModel):
    prompt: str
    diagram_type: str = "class"
    output_filename: Optional[str] = "diagram_output.png"


@router.post("/generate")
async def generate_diagram(req: DiagramRequest, request: Request):
    if req.diagram_type not in SUPPORTED_DIAGRAM_TYPES:
        supported = ", ".join(sorted(SUPPORTED_DIAGRAM_TYPES))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported diagram_type '{req.diagram_type}'. Supported values: {supported}.",
        )

    try:
        architecture_data = await parse_architecture_prompt(req.prompt, req.diagram_type)
        architecture_data["diagram_type"] = req.diagram_type

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        model_path = os.path.join(base_dir, "modelo_base.eapx")
        if not os.path.exists(model_path):
            model_path = os.path.join(base_dir, "modelo_base.qea")

        output_dir = os.path.join(base_dir, "app", "public", "diagrams")
        os.makedirs(output_dir, exist_ok=True)

        unique_filename = f"diagram_{int(time.time())}.png"
        if req.output_filename and req.output_filename != "diagram_output.png":
            unique_filename = req.output_filename

        output_image_path = os.path.join(output_dir, unique_filename)
        ea_service = EnterpriseArchitectService(model_path)
        final_image_path = ea_service.generate_diagram(architecture_data, output_image_path)

        base_url = str(request.base_url).rstrip("/")
        public_url = f"{base_url}/public/diagrams/{unique_filename}"

        return {
            "status": "success",
            "message": "Diagram generated successfully via Enterprise Architect COM",
            "image_path": final_image_path,
            "url": public_url,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e
