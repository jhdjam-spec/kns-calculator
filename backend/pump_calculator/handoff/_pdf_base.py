"""Базовая инфраструктура для PDF-генераторов: шрифт с кириллицей, общие стили.

reportlab по умолчанию использует Helvetica — без кириллицы.
Для русского текста нужен либо встроенный CID-шрифт (HeiseiKakuGo-W5/STSong-Light) —
не русский, либо TTF-шрифт. На Windows есть Arial в C:\\Windows\\Fonts.
В YC Functions (Linux runtime) системных кириллических шрифтов нет — поэтому
fallback'ом подкладываем Vera.ttf из самого пакета reportlab (есть всегда).
"""

from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Cache: регистрируем шрифты только один раз
_FONTS_REGISTERED = False
_REGISTERED_REGULAR = "Helvetica"
_REGISTERED_BOLD = "Helvetica-Bold"


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


def _reportlab_bundled_font(filename: str) -> Path:
    """Путь к шрифту, поставляемому вместе с reportlab (reportlab/fonts/*).

    ВНИМАНИЕ: встроенный Vera.ttf НЕ содержит кириллицу — годится только
    в самом крайнем случае, после bundled DejaVu и системных Liberation.
    """
    import reportlab as _rl
    return Path(_rl.__file__).resolve().parent / "fonts" / filename


def _local_bundled_font(filename: str) -> Path:
    """Путь к шрифту, упакованному рядом с этим модулем (handoff/fonts/*).

    Используем DejaVu Sans — CC0, гарантированно содержит кириллицу.
    Копия лежит в репозитории и попадает в YC Function zip (см. deploy/build.py).
    """
    return Path(__file__).resolve().parent / "fonts" / filename


def register_cyrillic_fonts() -> tuple[str, str]:
    """Регистрирует TTF-шрифты с кириллицей. Возвращает (regular, bold) имена.

    Стратегия:
    1. Системные Linux (DejaVu / Liberation) — на YC Functions Linux runtime
       Liberation Sans есть из коробки.
    2. Системные Windows (Arial / Calibri) — для локального dev.
    3. Bundled fallback: Vera.ttf из пакета reportlab — есть всегда, рендерит
       кириллицу. Это последний рубеж: если ни системного TTF, ни Vera —
       откатимся на Helvetica и кириллица сломается.
    """
    global _FONTS_REGISTERED, _REGISTERED_REGULAR, _REGISTERED_BOLD
    if _FONTS_REGISTERED:
        return _REGISTERED_REGULAR, _REGISTERED_BOLD

    candidates_regular = [
        # Bundled DejaVu — детерминированный кириллический шрифт, едет в YC zip.
        _local_bundled_font("DejaVuSans.ttf"),
        # Linux (YC Functions/Ubuntu/Debian CI) — если bundled пропал
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/liberation/LiberationSans-Regular.ttf"),
        # Windows (локальный dev)
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        # ВНИМАНИЕ: Vera.ttf из reportlab не содержит кириллицу — не годится.
    ]
    candidates_bold = [
        _local_bundled_font("DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/liberation/LiberationSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf"),
    ]

    if _try_register_ttf("CyrillicRegular", candidates_regular):
        _REGISTERED_REGULAR = "CyrillicRegular"
    if _try_register_ttf("CyrillicBold", candidates_bold):
        _REGISTERED_BOLD = "CyrillicBold"

    # Регистрируем PDF font family, чтобы reportlab умел делать <b>...</b> inline.
    if _REGISTERED_REGULAR != "Helvetica":
        try:
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily(
                _REGISTERED_REGULAR,
                normal=_REGISTERED_REGULAR,
                bold=_REGISTERED_BOLD,
                italic=_REGISTERED_REGULAR,
                boldItalic=_REGISTERED_BOLD,
            )
        except Exception:  # noqa: BLE001
            pass

    _FONTS_REGISTERED = True

    # Диагностика в логах YC — поможет понять, какой шрифт подхватился в проде.
    if os.environ.get("KNS_PDF_DEBUG"):
        print(f"[pdf] fonts: regular={_REGISTERED_REGULAR} bold={_REGISTERED_BOLD}")

    return _REGISTERED_REGULAR, _REGISTERED_BOLD


def get_font_names() -> tuple[str, str]:
    """Возвращает текущие зарегистрированные (regular, bold) имена.

    ВАЖНО: использовать вместо импортированных констант DEFAULT_FONT/DEFAULT_BOLD,
    потому что `from _pdf_base import DEFAULT_FONT` копирует значение В МОМЕНТ
    импорта (т.е. до register_cyrillic_fonts() значение Helvetica застывает
    в namespace вызывающего модуля). См. инцидент 2026-05-28: таблицы в PDF
    опросника рендерились квадратами на проде.
    """
    return register_cyrillic_fonts()


def get_font_name() -> str:
    """Alias под singular: возвращает только regular-имя шрифта.

    Используется в reports/calculation_report.py и reports/rpz_gost.py.
    Без этой функции импорт падал в `except Exception → font_name = 'Helvetica'`,
    отчёт выходил без кириллицы (инцидент 2026-05-28).
    """
    return register_cyrillic_fonts()[0]


# --- Backward compat: некоторые модули могут импортировать константы.
# Геттеры через __getattr__ возвращают актуальное значение из cache.
def __getattr__(name: str) -> str:  # noqa: D401
    if name == "DEFAULT_FONT":
        return register_cyrillic_fonts()[0]
    if name == "DEFAULT_BOLD":
        return register_cyrillic_fonts()[1]
    raise AttributeError(name)


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
