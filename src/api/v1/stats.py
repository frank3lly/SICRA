"""Environmental and Legal Compliance Statistics REST API endpoints."""

from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.entities import User
from src.security.dependencies import get_current_user
from src.services.stats_service import StatsService

router = APIRouter()


@router.get(
    "/environmental",
    summary="Get environmental impact metrics and compliance summary",
    status_code=status.HTTP_200_OK,
)
def get_environmental_impact(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve cumulative environmental metrics: oil diverted, water preserved, and CO2 avoided."""
    return StatsService.get_environmental_stats(db)


@router.get(
    "/report-pdf",
    summary="Download publication-grade environmental audit PDF report",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/environmental/report-pdf",
    summary="Download publication-grade environmental audit PDF report",
    status_code=status.HTTP_200_OK,
)
def download_environmental_audit_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Generate and stream publication-ready dark-themed PDF audit report."""
    pdf_bytes = StatsService.generate_audit_report_pdf(db)
    filename = f"Reporte_Trazabilidad_SICRA_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )

