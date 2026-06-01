from io import BytesIO

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/events/{event_id}/pdf")
def event_report_pdf(event_id: int):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle(f"EcoEvent 360 Reporte Evento {event_id}")
    pdf.drawString(72, 740, "EcoEvent 360")
    pdf.drawString(72, 710, f"Reporte operacional y ambiental del evento #{event_id}")
    pdf.drawString(72, 680, "Resumen generado desde datos registrados en la plataforma.")
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="event-{event_id}-report.pdf"'},
    )

