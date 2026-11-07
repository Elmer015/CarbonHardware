#!/usr/bin/env python
"""Generate the Indonesian CarbonHardware project documentation PDF."""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "CarbonHardware_Project_Documentation_ID.md"
DEFAULT_OUTPUT = ROOT / "docs" / "CarbonHardware_Project_Documentation_ID.pdf"
MONTHS_ID = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)


def current_date_id() -> str:
    today = date.today()
    return f"{today.day} {MONTHS_ID[today.month - 1]} {today.year}"


def register_fonts() -> None:
    windows_fonts = Path(r"C:\Windows\Fonts")
    candidates = [
        (windows_fonts / "arial.ttf", windows_fonts / "arialbd.ttf", windows_fonts / "ariali.ttf"),
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
         Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
         Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf")),
    ]
    for regular, bold, italic in candidates:
        if regular.is_file() and bold.is_file() and italic.is_file():
            pdfmetrics.registerFont(TTFont("DocSans", str(regular)))
            pdfmetrics.registerFont(TTFont("DocSans-Bold", str(bold)))
            pdfmetrics.registerFont(TTFont("DocSans-Italic", str(italic)))
            pdfmetrics.registerFontFamily(
                "DocSans", normal="DocSans", bold="DocSans-Bold", italic="DocSans-Italic",
                boldItalic="DocSans-Bold",
            )
            return
    raise RuntimeError("Tidak menemukan font TrueType Unicode (Arial atau DejaVu Sans).")


def inline_markup(text: str) -> str:
    result = escape(text)
    result = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: f'<link href={quoteattr(match.group(2))} color="#16745B">{match.group(1)}</link>',
        result,
    )
    result = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', result)
    result = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result)
    result = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", result)
    return result


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


class ProjectDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, styles: dict[str, ParagraphStyle]) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            rightMargin=19 * mm,
            leftMargin=19 * mm,
            topMargin=22 * mm,
            bottomMargin=18 * mm,
            title="Dokumentasi Proyek CarbonHardware",
            author="CarbonHardware",
            subject="Dokumentasi teknis, metodologi, dan rekomendasi hardware",
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=self.draw_chrome))
        self.heading_count = 0

    def draw_chrome(self, canvas, document) -> None:
        canvas.saveState()
        page_width, page_height = A4
        canvas.setStrokeColor(colors.HexColor("#D7E3DE"))
        canvas.setLineWidth(0.5)
        canvas.line(19 * mm, page_height - 14 * mm, page_width - 19 * mm, page_height - 14 * mm)
        canvas.setFont("DocSans-Bold", 8)
        canvas.setFillColor(colors.HexColor("#176B52"))
        canvas.drawString(19 * mm, page_height - 11 * mm, "CARBONHARDWARE")
        canvas.setFont("DocSans", 8)
        canvas.setFillColor(colors.HexColor("#5B6862"))
        canvas.drawRightString(
            page_width - 19 * mm, 10 * mm,
            f"Dokumentasi teknis - {current_date_id()}  |  {document.page}",
        )
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, Paragraph) and getattr(flowable, "heading_level", None) is not None:
            self.heading_count += 1
            level = flowable.heading_level
            key = f"section-{self.heading_count}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(), key, level=min(level, 1), closed=False)


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DocTitle", parent=base["Title"], fontName="DocSans-Bold", fontSize=24,
            leading=29, textColor=colors.HexColor("#124D3B"), alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "DocH1", parent=base["Heading1"], fontName="DocSans-Bold", fontSize=16,
            leading=20, textColor=colors.HexColor("#124D3B"), spaceBefore=12,
            spaceAfter=7, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "DocH2", parent=base["Heading2"], fontName="DocSans-Bold", fontSize=12,
            leading=16, textColor=colors.HexColor("#176B52"), spaceBefore=9,
            spaceAfter=5, keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "DocH3", parent=base["Heading3"], fontName="DocSans-Bold", fontSize=10,
            leading=13, textColor=colors.HexColor("#344A40"), spaceBefore=7,
            spaceAfter=4, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "DocBody", parent=base["BodyText"], fontName="DocSans", fontSize=9,
            leading=13, textColor=colors.HexColor("#202923"), alignment=TA_LEFT,
            spaceAfter=6, splitLongWords=True,
        ),
        "bullet": ParagraphStyle(
            "DocBullet", parent=base["BodyText"], fontName="DocSans", fontSize=9,
            leading=13, leftIndent=13, firstLineIndent=-9, textColor=colors.HexColor("#202923"),
            spaceAfter=3,
        ),
        "table": ParagraphStyle(
            "DocTable", parent=base["BodyText"], fontName="DocSans", fontSize=7.1,
            leading=9.4, textColor=colors.HexColor("#202923"), spaceAfter=0,
            splitLongWords=True,
        ),
        "table_header": ParagraphStyle(
            "DocTableHeader", parent=base["BodyText"], fontName="DocSans-Bold", fontSize=7.2,
            leading=9.4, textColor=colors.white, spaceAfter=0,
        ),
        "code": ParagraphStyle(
            "DocCode", parent=base["Code"], fontName="Courier", fontSize=7.6,
            leading=10, leftIndent=7, rightIndent=7, borderColor=colors.HexColor("#D7E3DE"),
            borderWidth=0.5, borderPadding=6, backColor=colors.HexColor("#F4F7F5"),
            spaceBefore=3, spaceAfter=8,
        ),
    }


def markdown_to_flowables(text: str, styles: dict[str, ParagraphStyle]) -> list:
    lines = text.splitlines()
    flowables = []
    paragraph: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            value = " ".join(line.strip() for line in paragraph)
            flowables.append(Paragraph(inline_markup(value), styles["body"]))
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            index += 1
            continue
        if stripped.startswith("```"):
            flush_paragraph()
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            flowables.append(Preformatted("\n".join(code_lines), styles["code"], maxLineLength=105))
            index += 1
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and re.match(
            r"^\s*\|?\s*:?-{3,}", lines[index + 1]
        ):
            flush_paragraph()
            raw_rows = [split_table_row(stripped)]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                raw_rows.append(split_table_row(lines[index]))
                index += 1
            columns = max(len(row) for row in raw_rows)
            data = []
            for row_number, row in enumerate(raw_rows):
                row += [""] * (columns - len(row))
                style = styles["table_header"] if row_number == 0 else styles["table"]
                data.append([Paragraph(inline_markup(cell), style) for cell in row])
            available_width = A4[0] - 38 * mm
            widths = [available_width / columns] * columns
            table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176B52")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F8F6")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6E1DC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            flowables.extend([table, Spacer(1, 5)])
            continue
        if stripped.startswith("#"):
            flush_paragraph()
            level = len(stripped) - len(stripped.lstrip("#"))
            heading = stripped[level:].strip()
            name = "title" if level == 1 and not flowables else ("h1" if level == 2 else "h2" if level == 3 else "h3")
            item = Paragraph(inline_markup(heading), styles[name])
            item.heading_level = max(0, level - 2)
            flowables.append(item)
            index += 1
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            quote_text = stripped.lstrip("> ").strip()
            quote_style = ParagraphStyle(
                "DocQuote", parent=styles["body"], leftIndent=8, borderColor=colors.HexColor("#63A88D"),
                borderWidth=2, borderPadding=6, backColor=colors.HexColor("#EFF6F2"),
            )
            flowables.append(Paragraph(inline_markup(quote_text), quote_style))
            index += 1
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            flowables.append(Paragraph("• " + inline_markup(stripped[2:]), styles["bullet"]))
            index += 1
            continue
        if re.match(r"^\d+\.\s", stripped):
            flush_paragraph()
            item_text = re.sub(r"^\d+\.\s*", "", stripped)
            flowables.append(Paragraph(inline_markup(stripped.split(".", 1)[0] + ". ") + inline_markup(item_text), styles["bullet"]))
            index += 1
            continue
        if stripped == "---":
            flush_paragraph()
            flowables.append(Spacer(1, 4))
            index += 1
            continue
        paragraph.append(line)
        index += 1
    flush_paragraph()
    return flowables


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.source.is_file():
        parser.error(f"File sumber tidak ditemukan: {args.source}")
    register_fonts()
    styles = make_styles()
    story = markdown_to_flowables(args.source.read_text(encoding="utf-8"), styles)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document = ProjectDocTemplate(str(args.output), styles)
    document.build(story)
    print(f"PDF dihasilkan: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
