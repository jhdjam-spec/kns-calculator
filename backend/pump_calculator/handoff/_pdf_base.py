"""Базовая инфраструктура для PDF-генераторов: шрифт с кириллицей, общие стили.

reportlab по умолчанию использует Helvetica — без кириллицы.
Для русского текста нужен либо встроенный CID-шрифт (HeiseiKakuGo-W5/STSong-Light) —
не русский, либо TTF-шрифт. На Windows есть Arial в C:\\Windows\\Fonts.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Cache: регистрируем шрифты только один раз
_FONTS_REGISTERED = False
DEFAULT_FONT = "Helvetica"
DEFAULT_BOLD = "Helvetica-Bold"


def _try_register_ttf(name: str, paths: list[Path]) -> bool:
    """Пытаемся зарегистрировать TTF-шрифт по списку кандидатов. True если получилось."""
    for path in paths:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont(name, str(path)))
                return True
            except Exception:  # noqa: BLE001
                continue
    return False


def register_cyrillic_fonts() -> tuple[str, str]:
    """Регистрирует TTF-шрифты с кириллицей. Возвращает (regular, bold) имена.

    Стратегия:
    1. Пробуем системные шрифты Windows (Arial, Calibri).
    2. Пробуем системные Linux (DejaVu Sans, Liberation Sans) — для CI.
    3. Fallback: Helvetica (но кириллица сломается).
    """
    global _FONTS_REGISTERED, DEFAULT_FONT, DEFAULT_BOLD
    if _FONTS_REGISTERED:
        return DEFAULT_FONT, DEFAULT_BOLD

    candidates_regular = [
        # Windows
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        # Linux (Ubuntu CI runners)
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        # Common locations
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
    ]
    candidates_bold = [
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
    ]

    if _try_register_ttf("CyrillicRegular", candidates_regular):
        DEFAULT_FONT = "CyrillicRegular"
    if _try_register_ttf("CyrillicBold", candidates_bold):
        DEFAULT_BOLD = "CyrillicBold"

    _FONTS_REGISTERED = True
    return DEFAULT_FONT, DEFAULT_BOLD


def get_styles() -> dict[str, ParagraphStyle]:
    """Стили параграфов с кириллическим шрифтом."""
    font, bold = register_cyrillic_fonts()
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontName=bold, fontSize=16, leading=20,
            textColor=colors.HexColor("#1f2937"),
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName=bold, fontSize=12, leading=15,
            textColor=colors.HexColor("#374151"), spaceBefore=10, spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "H3", parent=base["Heading3"], fontName=bold, fontSize=10, leading=13,
            textColor=colors.HexColor("#4b5563"), spaceBefore=6, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName=font, fontSize=9, leading=12,
            textColor=colors.HexColor("#111827"),
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontName=font, fontSize=8, leading=10,
            textColor=colors.HexColor("#6b7280"),
        ),
        "label": ParagraphStyle(
            "Label", parent=base["BodyText"], fontName=bold, fontSize=9, leading=12,
            textColor=colors.HexColor("#374151"),
        ),
    }
