"""Тесты CLI команд parse / review / merge (Phase 6.4).

Тесты прогоняют CLI как subprocess, проверяют exit codes и stdout/stderr.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "pedrollo_vx_50hz.pdf"


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Запустить `python -m pump_calculator.etl.cli ...` и вернуть результат."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "pump_calculator.etl.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        env=env,
    )


def test_cli_help_lists_all_commands() -> None:
    """`cli --help` показывает import / parse / review / merge."""
    result = _run_cli("--help")
    assert result.returncode == 0
    out = result.stdout + result.stderr
    for cmd in ("import", "parse", "review", "merge"):
        assert cmd in out, f"command '{cmd}' missing from --help output"


@pytest.fixture(scope="module")
def parsed_run_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Один прогон `cli parse` для модуля — выдаёт путь к run_dir."""
    runs_root = tmp_path_factory.mktemp("cli_runs")
    result = _run_cli(
        "parse",
        str(FIXTURE_PDF),
        "--brand", "Pedrollo",
        "--runs-root", str(runs_root),
    )
    assert result.returncode == 0, (
        f"cli parse failed: stdout={result.stdout}, stderr={result.stderr}"
    )
    # stdout содержит путь к run_dir (последняя строка)
    run_dir = Path(result.stdout.strip().splitlines()[-1])
    assert run_dir.exists(), f"run_dir не существует: {run_dir}"
    return run_dir


def test_cli_parse_creates_validated_json(parsed_run_dir: Path) -> None:
    """parse создаёт 05_validated.json с записями."""
    validated_path = parsed_run_dir / "05_validated.json"
    assert validated_path.exists()
    records = json.loads(validated_path.read_text(encoding="utf-8"))
    assert isinstance(records, list)
    assert len(records) >= 8


def test_cli_review_outputs_diff_md(parsed_run_dir: Path) -> None:
    """review печатает 07_diff.md в stdout."""
    result = _run_cli("review", str(parsed_run_dir))
    assert result.returncode == 0
    assert "# ETL diff-отчёт" in result.stdout
    assert "Pedrollo" in result.stdout


def test_cli_review_missing_dir_returns_error() -> None:
    """review на несуществующий run_dir → exit 1."""
    result = _run_cli("review", "C:/no/such/run_dir_xxx")
    assert result.returncode == 1


def test_cli_merge_into_isolated_pumps_json(
    parsed_run_dir: Path, tmp_path: Path
) -> None:
    """merge в копию pumps.json — записи добавляются (или пропускаются если уже есть)."""
    # Подготовка: копируем существующий pumps.json во временный target
    real_pumps = (
        Path(__file__).resolve().parents[2]
        / "02_dataset" / "pumps" / "pumps.json"
    )
    target = tmp_path / "pumps.json"
    shutil.copy2(real_pumps, target)
    before = json.loads(target.read_text(encoding="utf-8"))
    before_count = len(before["pumps"])

    result = _run_cli(
        "merge", str(parsed_run_dir),
        "--target", str(target),
    )
    assert result.returncode == 0, (
        f"cli merge failed: stdout={result.stdout}, stderr={result.stderr}"
    )

    after = json.loads(target.read_text(encoding="utf-8"))
    assert len(after["pumps"]) >= before_count, (
        "merge не должен уменьшать число насосов"
    )
    # В stderr должно быть сообщение Merged into ...: added=N, skipped=M
    assert "Merged" in result.stderr
