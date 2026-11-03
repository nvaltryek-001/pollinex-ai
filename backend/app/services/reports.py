"""CSV and PDF report generation from database records only."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SCAN_COLUMNS = ["scan_id", "created_at", "source", "detection_method", "flower_count", "flower_index", "species",
                "species_confidence", "species_method", "stage", "stage_method", "readiness", "readiness_confidence",
                "detection_score", "low_confidence", "health_status", "x1", "y1", "x2", "y2"]


def scans_csv(scans) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(SCAN_COLUMNS)
    for s in scans:
        if not s.detections:
            w.writerow([s.id, s.created_at.isoformat(), s.source, s.detection_method, s.flower_count] + [""] * 15)
        for d in s.detections:
            w.writerow([s.id, s.created_at.isoformat(), s.source, s.detection_method, s.flower_count, d.index,
                        d.species_id, round(d.species_confidence, 4), d.species_method,
                        d.maturity.stage if d.maturity else "", d.maturity.method if d.maturity else "",
                        d.readiness.category if d.readiness else "", round(d.readiness.confidence, 4) if d.readiness else "",
                        round(d.score, 4), d.low_confidence, (d.health or {}).get("status", ""),
                        round(d.x1, 1), round(d.y1, 1), round(d.x2, 1), round(d.y2, 1)])
    return buf.getvalue().encode()


def summary_pdf(user_email: str, metrics: dict, scans, sims, evaluation: dict | None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="POLLINEX AI report")
    st = getSampleStyleSheet()
    story = [Paragraph("POLLINEX AI — Analysis Report", st["Title"]),
             Paragraph(f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} for {user_email}", st["Normal"]),
             Spacer(1, 6),
             Paragraph("All figures below come from this account's database records. Stage, structure and health "
                       "outputs are heuristics; readiness is a rule-based <i>visual</i> estimate; simulation results are "
                       "computational and are not evidence of fertilisation or yield.", st["Italic"]), Spacer(1, 8)]

    def table(rows, widths=None):
        t = Table(rows, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3d2b")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                               ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b8c4bb")),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6f3")])]))
        return t

    story += [Paragraph("Summary", st["Heading2"]),
              table([["Metric", "Value"]] + [[k.replace("_", " "), str(v)] for k, v in metrics["totals"].items()]), Spacer(1, 8)]
    if metrics.get("species_distribution"):
        story += [Paragraph("Species distribution (detections)", st["Heading3"]),
                  table([["Species", "Count"]] + [[k, str(v)] for k, v in metrics["species_distribution"].items()])]
    if metrics.get("stage_distribution"):
        story += [Paragraph("Stage distribution (heuristic)", st["Heading3"]),
                  table([["Stage", "Count"]] + [[k, str(v)] for k, v in metrics["stage_distribution"].items()])]
    story += [Spacer(1, 8), Paragraph("Recent scans", st["Heading2"])]
    rows = [["Scan", "Date (UTC)", "Source", "Method", "Flowers", "Warnings"]]
    for s in scans[:40]:
        rows.append([str(s.id), s.created_at.strftime("%Y-%m-%d %H:%M"), s.source, s.detection_method, str(s.flower_count),
                     str(len(s.warnings or []))])
    story.append(table(rows))
    if sims:
        story += [Spacer(1, 8), Paragraph("Simulations (computational)", st["Heading2"])]
        rows = [["Sim", "Species", "Mode", "Released", "Captured", "Sim. transfer eff."]]
        for s in sims[:30]:
            r = s.result_summary or {}
            rows.append([str(s.id), s.species_id, s.params.get("mode", ""), str(r.get("released", "")), str(r.get("captured", "")),
                         str(r.get("simulated_transfer_efficiency", ""))])
        story.append(table(rows))
    if evaluation:
        story += [Spacer(1, 8), Paragraph("Model evaluation (held-out test split)", st["Heading2"]),
                  table([["Metric", "Value"]] + [[k, f"{v:.3f}" if isinstance(v, float) else str(v)] for k, v in evaluation.items()])]
    doc.build(story)
    return buf.getvalue()
