import io
import uuid
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER


def generate_certificate_pdf(
    student_name: str,
    course_title: str,
    instructor_name: str,
    issued_at: datetime,
    verification_uuid: uuid.UUID,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        fontSize=36,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=20,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        fontSize=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#444444"),
        spaceAfter=10,
        fontName="Helvetica",
    )
    name_style = ParagraphStyle(
        "Name",
        fontSize=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#e94560"),
        spaceAfter=10,
        fontName="Helvetica-Bold",
    )
    course_style = ParagraphStyle(
        "Course",
        fontSize=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=10,
        fontName="Helvetica-Bold",
    )
    small_style = ParagraphStyle(
        "Small",
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#888888"),
        fontName="Helvetica",
    )

    story = [
        Spacer(1, 1*cm),
        Paragraph("CERTIFICATE OF COMPLETION", title_style),
        HRFlowable(width="80%", thickness=2, color=colors.HexColor("#e94560")),
        Spacer(1, 0.5*cm),
        Paragraph("This is to certify that", subtitle_style),
        Spacer(1, 0.3*cm),
        Paragraph(student_name, name_style),
        Spacer(1, 0.3*cm),
        Paragraph("has successfully completed the course", subtitle_style),
        Spacer(1, 0.3*cm),
        Paragraph(course_title, course_style),
        Spacer(1, 0.5*cm),
        HRFlowable(width="60%", thickness=1, color=colors.HexColor("#cccccc")),
        Spacer(1, 0.3*cm),
        Paragraph(f"Instructor: {instructor_name}", subtitle_style),
        Paragraph(f"Issued: {issued_at.strftime('%B %d, %Y')}", subtitle_style),
        Spacer(1, 0.3*cm),
        Paragraph(f"Verification ID: {verification_uuid}", small_style),
    ]

    doc.build(story)
    return buffer.getvalue()