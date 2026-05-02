from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.database import get_db
from api.dependencies import get_current_user
import os

router = APIRouter()


@router.post("/generate")
async def generate_report(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    from api.services.report_service import generate_pdf_report, generate_excel_report

    report_type = payload.get("report_type", "weekly_summary")
    fmt = payload.get("format", "pdf")
    commodities = payload.get("commodities") or []
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")

    try:
        if fmt == "excel":
            filepath = await generate_excel_report(
                db, report_type, commodities, start_date, end_date
            )
        else:
            filepath = await generate_pdf_report(
                db, report_type, commodities, start_date, end_date
            )

        filename = os.path.basename(filepath)
        return {
            "success": True,
            "filename": filename,
            "download_url": f"/api/reports/download/{filename}",
            "message": f"Report generated successfully!"
        }
    except Exception as e:
        raise HTTPException(500, f"Report generation failed: {str(e)}")


@router.get("/download/{filename}")
async def download_report(
    filename: str,
    current_user=Depends(get_current_user)
):
    from pathlib import Path
    filepath = Path("reports") / filename

    if not filepath.exists():
        raise HTTPException(404, "Report file not found")

    # Determine media type
    if filename.endswith('.pdf'):
        media_type = "application/pdf"
    elif filename.endswith('.xlsx'):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type=media_type
    )