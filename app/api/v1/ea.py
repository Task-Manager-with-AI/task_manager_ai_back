from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import os

from app.services.ea_service import EnterpriseArchitectService

router = APIRouter(prefix="/ea", tags=["Enterprise Architect"])

class DiagramRequest(BaseModel):
    prompt: str
    diagram_type: str = "class"
    output_filename: Optional[str] = "diagram_output.png"

import time
from app.services.llm_service import parse_architecture_prompt

@router.post("/generate")
async def generate_diagram(req: DiagramRequest, request: Request):
    try:
        # Call LLM to parse the prompt into a structured architecture
        architecture_data = await parse_architecture_prompt(req.prompt, req.diagram_type)
        architecture_data["diagram_type"] = req.diagram_type
        
        # Resolve the base model path. Assuming it's in the project root.
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        model_path = os.path.join(base_dir, "modelo_base.eapx")
        if not os.path.exists(model_path):
            model_path = os.path.join(base_dir, "modelo_base.qea")
        
        # We need a path to save the output image
        output_dir = os.path.join(base_dir, "app", "public", "diagrams")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate a unique filename using timestamp
        unique_filename = f"diagram_{int(time.time())}.png"
        if req.output_filename and req.output_filename != "diagram_output.png":
             unique_filename = req.output_filename
             
        output_image_path = os.path.join(output_dir, unique_filename)
        
        ea_service = EnterpriseArchitectService(model_path)
        # Pass the architecture_data instead of the raw prompt
        final_image_path = ea_service.generate_diagram(architecture_data, output_image_path)
        
        # Return the public URL dynamically based on the request host
        base_url = str(request.base_url).rstrip("/")
        public_url = f"{base_url}/public/diagrams/{unique_filename}"
        
        return {
            "status": "success",
            "message": "Diagram generated successfully via EA COM",
            "image_path": final_image_path,
            "url": public_url
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
