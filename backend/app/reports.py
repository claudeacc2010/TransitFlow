"""Генерация PDF-отчёта для аналитика акимата (§7).

Чистый модуль рендеринга: данные на вход — байты PDF на выход. Никаких запросов
к БД здесь нет (их собирает роутер), чтобы не плодить циклические импорты.

Кириллица: reportlab из коробки её не умеет, поэтому регистрируем встроенные
TTF-шрифты DejaVu (лежат в app/assets).
"""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_ASSETS = Path(__file__).parent / "assets"
_FONT = "DejaVu"
_FONT_BOLD = "DejaVu-Bold"
_fonts_ready = False

# Палитра под «диспетчерскую» тему дашборда.
_ACCENT = colors.HexColor("#f5a623")
_DARK = colors.HexColor("#1c222b")
_GRID = colors.HexColor("#c8ced8")
_MUTED = colors.HexColor("#5d6675")


def _ensure_fonts() -> None:
    global _fonts_ready
    if _fonts_ready:
        return
    pdfmetrics.registerFont(TTFont(_FONT, str(_ASSETS / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(_ASSETS / "DejaVuSans-Bold.ttf")))
    _fonts_ready = True


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "tf_title", parent=base["Title"], fontName=_FONT_BOLD,
            fontSize=20, leading=24, textColor=_DARK,
        ),
        "subtitle": ParagraphStyle(
            "tf_subtitle", parent=base["Normal"], fontName=_FONT,
            fontSize=10, leading=14, textColor=_MUTED,
        ),
        "h2": ParagraphStyle(
            "tf_h2", parent=base["Heading2"], fontName=_FONT_BOLD,
            fontSize=13, leading=18, textColor=_DARK, spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "tf_body", parent=base["Normal"], fontName=_FONT,
            fontSize=10, leading=15, textColor=colors.black,
        ),
        "foot": ParagraphStyle(
            "tf_foot", parent=base["Normal"], fontName=_FONT,
            fontSize=8, leading=11, textColor=_MUTED, alignment=TA_CENTER,
        ),
    }


def _table(data: list[list[str]], col_widths: list[float], *, highlight_row: int | None = None) -> Table:
    """Таблица с шапкой-акцентом и зеброй; highlight_row подсвечивает строку данных."""
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), _DARK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f4f8")]),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]
    if highlight_row is not None:
        r = highlight_row + 1  # +1 за шапку
        style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#fff2d6")))
        style.append(("FONTNAME", (0, r), (-1, r), _FONT_BOLD))
    t.setStyle(TableStyle(style))
    return t


def _fmt_date(value) -> str:
    """date/str 'YYYY-MM-DD' → 'дд.мм'."""
    try:
        return value.strftime("%d.%m")
    except AttributeError:
        parts = str(value).split("-")
        return f"{parts[2]}.{parts[1]}" if len(parts) == 3 else str(value)


def _traffic_chart(points: list[tuple], width: float = 470, height: float = 175) -> Drawing:
    """Линейный график «машин в сутки» по дате. points: list[(date, trucks)]."""
    d = Drawing(width, height)
    n = len(points)
    if n == 0:
        return d

    lp = LinePlot()
    lp.x = 44
    lp.y = 26
    lp.width = width - 60
    lp.height = height - 46
    lp.data = [[(i, t) for i, (_, t) in enumerate(points)]]
    lp.joinedLines = 1
    lp.lines[0].strokeColor = _ACCENT
    lp.lines[0].strokeWidth = 1.4

    # Ось X: ~7 равномерных подписей дат (иначе 90 меток сольются).
    step = max(1, (n - 1) // 7)
    ticks = list(range(0, n, step))
    if ticks[-1] != n - 1:
        ticks.append(n - 1)
    dates = [p[0] for p in points]
    lp.xValueAxis.valueMin = 0
    lp.xValueAxis.valueMax = n - 1
    lp.xValueAxis.valueSteps = ticks
    lp.xValueAxis.labelTextFormat = lambda v: _fmt_date(dates[max(0, min(n - 1, int(round(v))))])
    lp.xValueAxis.labels.fontName = _FONT
    lp.xValueAxis.labels.fontSize = 7
    lp.xValueAxis.strokeColor = _GRID

    lp.yValueAxis.valueMin = 0
    lp.yValueAxis.labels.fontName = _FONT
    lp.yValueAxis.labels.fontSize = 7
    lp.yValueAxis.strokeColor = _GRID
    lp.yValueAxis.visibleGrid = 1
    lp.yValueAxis.gridStrokeColor = colors.HexColor("#e6e9ef")

    d.add(lp)
    return d


def build_analytics_pdf(
    *,
    generated_at: datetime,
    overview: dict,
    timeseries: list[tuple],
    bottlenecks: list[tuple[str, float]],
    weekday: list[tuple[str, int]],
    cargo: list[tuple[str, int]],
    ai_text: str,
    ai_provider: str,
) -> bytes:
    """Собирает PDF аналитического отчёта и возвращает его байты."""
    _ensure_fonts()
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="TransitFlow — аналитический отчёт",
    )
    story: list = []

    story.append(Paragraph("Аналитический отчёт", st["title"]))
    story.append(Paragraph(
        "TransitFlow · Координация транзита · Мангистауская область", st["subtitle"]))
    story.append(Paragraph(
        f"Сформировано: {generated_at:%d.%m.%Y %H:%M} UTC", st["subtitle"]))
    story.append(Spacer(1, 6))

    # --- Ключевые показатели ---
    story.append(Paragraph("Ключевые показатели", st["h2"]))
    kpi = [
        ["Показатель", "Значение"],
        ["Машин за последние сутки", f"{overview['trucks_today']:,}".replace(",", " ")],
        ["Тонн в сутки (среднее за неделю)", f"{overview['tons_per_day']:,.1f}".replace(",", " ")],
        ["Активные заявки", str(overview["active_requests"])],
        ["Средняя загрузка узлов", f"{overview['avg_load_pct']} %"],
    ]
    story.append(_table(kpi, [95 * mm, 55 * mm]))

    # --- Динамика потока ---
    story.append(Paragraph("Динамика потока, машин в сутки", st["h2"]))
    if timeseries:
        days = len(timeseries)
        story.append(Paragraph(f"Период наблюдения: {days} дн.", st["subtitle"]))
        story.append(Spacer(1, 4))
        story.append(_traffic_chart(timeseries))
    else:
        story.append(Paragraph("Нет данных.", st["body"]))

    # --- Узкие места ---
    story.append(Paragraph("Узкие места: очереди на узлах", st["h2"]))
    if bottlenecks:
        rows = [["#", "Узел", "Ожидание в очереди"]]
        for i, (name, wait) in enumerate(bottlenecks, start=1):
            label = f"≈ {wait:.1f} ч" if wait > 0 else "свободно"
            rows.append([str(i), name, label])
        story.append(_table(rows, [12 * mm, 98 * mm, 40 * mm], highlight_row=0))
    else:
        story.append(Paragraph("Очередей не зафиксировано.", st["body"]))

    # --- Загрузка по дням недели ---
    story.append(Paragraph("Загрузка по дням недели", st["h2"]))
    if weekday:
        peak_idx = max(range(len(weekday)), key=lambda i: weekday[i][1])
        rows = [["День", "Машин за период"]]
        for label, trucks in weekday:
            rows.append([label, f"{trucks:,}".replace(",", " ")])
        story.append(_table(rows, [60 * mm, 90 * mm], highlight_row=peak_idx))
    else:
        story.append(Paragraph("Нет данных.", st["body"]))

    # --- Структура потока по типу груза ---
    story.append(Paragraph("Структура потока по типу груза", st["h2"]))
    if cargo:
        total = sum(t for _, t in cargo) or 1
        rows = [["Тип груза", "Машин", "Доля"]]
        for label, trucks in cargo:
            rows.append([label, f"{trucks:,}".replace(",", " "), f"{trucks / total * 100:.0f} %"])
        story.append(_table(rows, [80 * mm, 35 * mm, 35 * mm]))
    else:
        story.append(Paragraph("Нет данных.", st["body"]))

    # --- AI-резюме ---
    story.append(Paragraph("Аналитическая сводка (AI)", st["h2"]))
    for para in (ai_text or "").split("\n"):
        para = para.strip()
        if para:
            story.append(Paragraph(para, st["body"]))
            story.append(Spacer(1, 2))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Источник сводки: {ai_provider}", st["subtitle"]))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Отчёт сгенерирован платформой TransitFlow автоматически на основе данных мониторинга.",
        st["foot"]))

    doc.build(story)
    return buf.getvalue()
