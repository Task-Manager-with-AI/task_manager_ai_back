import asyncio
from fastapi import APIRouter, HTTPException

from app.schemas.docx import DocxJobRequest, DocxJobResponse, DocxJobStatusResponse
from app.services import docx_service

router = APIRouter()


@router.post("/docx/jobs", response_model=DocxJobResponse)
async def create_docx_job(body: DocxJobRequest):
    try:
        state = docx_service.create_job(body)
        asyncio.create_task(docx_service.process_job(body, state))
        return DocxJobResponse(
            data={
                "providerJobId": state.provider_job_id,
                "status": state.status,
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not create DOCX job: {exc}")


@router.get("/docx/jobs/{provider_job_id}", response_model=DocxJobStatusResponse)
async def get_docx_job(provider_job_id: str):
    state = docx_service.get_job(provider_job_id)
    if not state:
        raise HTTPException(status_code=404, detail="DOCX job not found")

    return DocxJobStatusResponse(
        data={
            "providerJobId": state.provider_job_id,
            "status": state.status,
            "errorMessage": state.error_message,
            "createdAt": state.created_at.isoformat().replace("+00:00", "Z"),
            "startedAt": state.started_at.isoformat().replace("+00:00", "Z")
            if state.started_at
            else None,
            "finishedAt": state.finished_at.isoformat().replace("+00:00", "Z")
            if state.finished_at
            else None,
        }
    )
