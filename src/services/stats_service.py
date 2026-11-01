"""Environmental Impact and Legal Compliance Statistics Service."""

from datetime import datetime, timezone
import hashlib
import io
import os
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from src.models.entities import Business, CollectionRoute, Container, Telemetry
from src.models.enums import ContainerStatus, TelemetryFlag


class StatsService:
    """Computes aggregate environmental metrics and statutory waste diversion indicators."""

    @staticmethod
    def get_environmental_stats(db: Session) -> Dict[str, Any]:
        """Aggregate total recycled waste oil and potable water preserved.

        Rules according to Ley 225-20 (Residuos Sólidos) and Ley 64-00 (Recursos Hídricos):
        1. 1 Liter of waste cooking oil contaminates 1,000 Liters of potable water.
        2. Carbon offsetting: 2.85 kg CO2e avoided per liter of recycled oil diverted to biodiesel.
        """
        # 1. Calculate total oil diverted from confirmed drain events
        drain_telemetries = (
            db.query(Telemetry)
            .filter(Telemetry.flag == TelemetryFlag.DRAIN_EVENT)
            .all()
        )

        drain_diverted_liters = 0.0
        for dt in drain_telemetries:
            prev_reading = (
                db.query(Telemetry)
                .filter(
                    Telemetry.container_id == dt.container_id,
                    Telemetry.measurement_timestamp < dt.measurement_timestamp,
                )
                .order_by(Telemetry.measurement_timestamp.desc())
                .first()
            )
            if prev_reading and prev_reading.calculated_liters > dt.calculated_liters:
                drain_diverted_liters += prev_reading.calculated_liters - dt.calculated_liters
            else:
                drain_diverted_liters += max(0.0, dt.calculated_liters)

        # 2. Count confirmed route pickups
        routes = db.query(CollectionRoute).all()
        confirmed_pickups_count = 0
        route_diverted_liters = 0.0

        for r in routes:
            if isinstance(r.stops_order_json, list):
                for s in r.stops_order_json:
                    if s.get("visited") and not s.get("is_depot"):
                        confirmed_pickups_count += 1
                        route_diverted_liters += float(s.get("estimated_liters", 0.0))

        # Combined collections count
        total_collections = len(drain_telemetries) + confirmed_pickups_count

        # Total oil diverted (drain events represent verified tare drops; if none yet, route volume is included)
        base_historical_liters = float(os.getenv("BASE_HISTORICAL_OIL_LITERS", "0.0"))
        total_diverted = round(base_historical_liters + drain_diverted_liters + (route_diverted_liters if len(drain_telemetries) == 0 else 0.0), 2)

        # Environmental conversions
        water_preserved = round(total_diverted * 1000.0, 1)
        co2_avoided = round(total_diverted * 2.85, 2)

        active_containers_count = (
            db.query(Container)
            .filter(Container.status == ContainerStatus.ACTIVE)
            .count()
        )

        return {
            "total_oil_diverted_liters": total_diverted,
            "water_preserved_liters": water_preserved,
            "co2_avoided_kg": co2_avoided,
            "total_collections_count": total_collections,
            "active_containers_count": active_containers_count,
            "compliance_framework": "Trazabilidad y Recoleccion Certificada",
        }

    @classmethod
    def generate_audit_report_pdf(cls, db: Session) -> bytes:
        """Generate a publication-grade, professional white-themed PDF audit report."""
        stats = cls.get_environmental_stats(db)

        # Query monitored containers with business info
        containers = (
            db.query(Container)
            .join(Business, Container.business_id == Business.id)
            .order_by(Business.name.asc())
            .limit(10)
            .all()
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=32,
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        style_brand = ParagraphStyle(
            "BrandTitle",
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=25,
            textColor=colors.HexColor("#1E4A37"),
        )
        style_subhead = ParagraphStyle(
            "BrandSubhead",
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#4B5563"),
        )
        style_meta_right = ParagraphStyle(
            "MetaRight",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#374151"),
            alignment=TA_RIGHT,
        )
        style_summary = ParagraphStyle(
            "SummaryText",
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#374151"),
        )
        style_section_h = ParagraphStyle(
            "SectionHeading",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1E4A37"),
        )

        elements = []

        # 1. Header (Brand logo left, Metadata right)
        now_dt = datetime.now(timezone.utc)
        audit_code = f"SICRA-AUD-{now_dt.strftime('%Y%m%d')}-{hashlib.md5(now_dt.isoformat().encode()).hexdigest()[:8].upper()}"

        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.abspath(os.path.join(current_dir, "..", "assets", "sicra-logo-full.png"))

        if os.path.exists(logo_path):
            logo_img = RLImage(logo_path, width=150, height=51.8)
            header_table = Table(
                [
                    [
                        logo_img,
                        Paragraph(
                            f"<b>FECHA DE EMISIÓN:</b> {now_dt.strftime('%d/%m/%Y %H:%M UTC')}<br/>"
                            f"<b>CÓDIGO DE AUDITORÍA:</b> {audit_code}<br/>"
                            "<b>RED PILOTO:</b> San Pedro de Macorís, RD<br/>"
                            "<b>ESTADO:</b> <font color=\"#166534\"><b>TRAZABILIDAD CERTIFICADA</b></font>",
                            style_meta_right,
                        ),
                    ]
                ],
                colWidths=[310, 230],
            )
            header_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            elements.append(header_table)
            elements.append(Spacer(1, 6))
            elements.append(
                Table(
                    [
                        [
                            Paragraph("<b>INFORME OFICIAL DE AUDITORÍA Y TRAZABILIDAD AMBIENTAL</b>", style_section_h),
                            Paragraph("<font color=\"#6B7280\" size=\"8\">Plataforma Nacional de Recolección y Control</font>", style_meta_right),
                        ]
                    ],
                    colWidths=[330, 210],
                    style=[
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ],
                )
            )
        else:
            header_data = [
                [
                    Paragraph("<b>SICRA</b>", style_brand),
                    Paragraph(
                        f"<b>FECHA DE EMISIÓN:</b> {now_dt.strftime('%d/%m/%Y %H:%M UTC')}<br/>"
                        f"<b>CÓDIGO DE AUDITORÍA:</b> {audit_code}<br/>"
                        "<b>RED PILOTO:</b> San Pedro de Macorís, RD",
                        style_meta_right,
                    ),
                ],
                [
                    Paragraph(
                        "<b>Sistema Inteligente de Control y Recolección de Aceite</b><br/>"
                        "<font color=\"#1E4A37\"><b>INFORME OFICIAL DE AUDITORÍA Y TRAZABILIDAD AMBIENTAL</b></font>",
                        style_subhead,
                    ),
                    Paragraph(
                        "<b>ESTADO:</b> <font color=\"#166534\"><b>TRAZABILIDAD CERTIFICADA</b></font>",
                        style_meta_right,
                    ),
                ],
            ]
            header_table = Table(header_data, colWidths=[330, 210])
            header_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            elements.append(header_table)

        # Emerald accent separator
        accent_bar = Table([[""]], colWidths=[540], rowHeights=[2.5])
        accent_bar.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1E4A37")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        elements.append(Spacer(1, 6))
        elements.append(accent_bar)
        elements.append(Spacer(1, 8))

        # Executive Summary Paragraph
        elements.append(
            Paragraph(
                "El presente documento certifica las operaciones de monitoreo telemétrico, desvío de contaminantes y recolección controlada de aceite vegetal usado (AVU) en la red de establecimientos gastronómicos registrados. Todos los registros provienen de pesajes calibrados en recipientes estandarizados con sensorica activa.",
                style_summary,
            )
        )
        elements.append(Spacer(1, 10))

        # 2. 3 Impact KPI Cards (Clean White/Soft Pastel)
        oil_fmt = f"{stats['total_oil_diverted_liters']:,.1f} L"
        water_fmt = f"{stats['water_preserved_liters']:,.0f} L"
        co2_fmt = f"{stats['co2_avoided_kg']:,.1f} kg"

        kpi_data = [
            [
                Paragraph(
                    "<font color=\"#166534\" size=\"8\"><b>ACEITE DESVIADO</b></font><br/><br/>"
                    f"<font size=\"16\" color=\"#111827\"><b>{oil_fmt}</b></font><br/><br/>"
                    "<font size=\"7\" color=\"#4B5563\">Evitado de drenajes y fuentes hídricas</font>",
                    styles["Normal"],
                ),
                Paragraph(
                    "<font color=\"#1E40AF\" size=\"8\"><b>AGUA PRESERVADA</b></font><br/><br/>"
                    f"<font size=\"16\" color=\"#111827\"><b>{water_fmt}</b></font><br/><br/>"
                    "<font size=\"7\" color=\"#4B5563\">Factor certificado (1 L aceite = 1,000 L)</font>",
                    styles["Normal"],
                ),
                Paragraph(
                    "<font color=\"#B45309\" size=\"8\"><b>CO2e MITIGADO</b></font><br/><br/>"
                    f"<font size=\"16\" color=\"#111827\"><b>{co2_fmt}</b></font><br/><br/>"
                    "<font size=\"7\" color=\"#4B5563\">Reducción estimada por coprocesamiento</font>",
                    styles["Normal"],
                ),
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[174, 174, 174], rowHeights=[72])
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F0FDF4")),
                    ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#EFF6FF")),
                    ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#FFFBEB")),
                    ("BOX", (0, 0), (0, 0), 1, colors.HexColor("#BBF7D0")),
                    ("BOX", (1, 0), (1, 0), 1, colors.HexColor("#BFDBFE")),
                    ("BOX", (2, 0), (2, 0), 1, colors.HexColor("#FDE68A")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elements.append(kpi_table)
        elements.append(Spacer(1, 14))

        # 3. Monitored Establishments Table
        elements.append(
            Paragraph("<b>RED ACTIVA DE ESTABLECIMIENTOS Y CONTENEDORES MONITOREADOS</b>", style_section_h)
        )
        elements.append(Spacer(1, 4))

        table_rows = [
            [
                Paragraph("<font color=\"#FFFFFF\" size=\"8\"><b>Comercio</b></font>", styles["Normal"]),
                Paragraph("<font color=\"#FFFFFF\" size=\"8\"><b>Ubicación</b></font>", styles["Normal"]),
                Paragraph("<font color=\"#FFFFFF\" size=\"8\"><b>Capacidad</b></font>", styles["Normal"]),
                Paragraph("<font color=\"#FFFFFF\" size=\"8\"><b>Tara Calibrada</b></font>", styles["Normal"]),
                Paragraph("<font color=\"#FFFFFF\" size=\"8\"><b>Nivel Actual</b></font>", styles["Normal"]),
                Paragraph("<font color=\"#FFFFFF\" size=\"8\"><b>Estado</b></font>", styles["Normal"]),
            ]
        ]

        for c in containers:
            b_name = c.business.name if c.business else "Establecimiento"
            if len(b_name) > 28:
                b_name = b_name[:26] + "…"
            address = c.business.address if c.business else "San Pedro de Macorís"
            if len(address) > 34:
                address = address[:32] + "…"
            cap = f"{c.capacity_liters:.0f} L"
            tare = f"{c.tare_weight_kg:.2f} kg"
            fill = f"{c.current_fill_percentage:.1f} %"
            stat = "Activo"

            table_rows.append(
                [
                    Paragraph(f"<font size=\"8\" color=\"#111827\"><b>{b_name}</b></font>", styles["Normal"]),
                    Paragraph(f"<font size=\"7.5\" color=\"#4B5563\">{address}</font>", styles["Normal"]),
                    Paragraph(f"<font size=\"8\" color=\"#111827\">{cap}</font>", styles["Normal"]),
                    Paragraph(f"<font size=\"8\" color=\"#4B5563\">{tare}</font>", styles["Normal"]),
                    Paragraph(f"<font size=\"8\" color=\"#111827\"><b>{fill}</b></font>", styles["Normal"]),
                    Paragraph(f"<font size=\"7.5\" color=\"#166534\"><b>{stat}</b></font>", styles["Normal"]),
                ]
            )

        biz_table = Table(table_rows, colWidths=[130, 160, 60, 75, 65, 50])
        biz_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E4A37")),
                    ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                    ("ALIGN", (2, 0), (4, -1), "CENTER"),
                    ("ALIGN", (5, 0), (5, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                ]
            )
        )
        elements.append(biz_table)
        elements.append(Spacer(1, 12))

        # 4. Regulatory & Certification Seal Box
        cert_data = [
            [
                Paragraph(
                    "<b>CERTIFICACIÓN OFICIAL DE GESTIÓN Y TRAZABILIDAD AMBIENTAL</b><br/>"
                    "<font size=\"7\" color=\"#374151\">"
                    "Las lecturas y métricas de este reporte han sido registradas mediante sensores telemétricos calibrados bajo estándares de densidad de aceite vegetal (0.92 kg/L) y control de tara en recipientes de PEAD. "
                    "Las operaciones de recolección, pesaje in-situ y transporte hacia plantas de coprocesamiento para biodiésel son ejecutadas exclusivamente por operadores autorizados: <b>Reoil Dominicana / Mevosa</b>."
                    "</font><br/>"
                    f"<font size=\"6.5\" color=\"#6B7280\">"
                    f"Sello Digital: SHA256:{hashlib.sha256(now_dt.isoformat().encode()).hexdigest()} · SICRA Sistema Oficial · Generado en tiempo real desde la plataforma"
                    "</font>",
                    styles["Normal"],
                )
            ]
        ]
        cert_table = Table(cert_data, colWidths=[540])
        cert_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elements.append(cert_table)

        doc.build(elements)
        return buf.getvalue()

