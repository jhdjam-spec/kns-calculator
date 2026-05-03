# Локальный mirror CI команд. Запускайте перед `git push`.
#
# Использование:
#   make ci      — все проверки (mirror Backend CI)
#   make lint    — только ruff
#   make test    — только pytest
#   make fix     — авто-исправление ruff
#
# На Windows: использовать через Git Bash / WSL, либо запускать команды вручную.

PY ?= ./.venv/Scripts/python.exe

.PHONY: ci lint test fix install

ci: lint test

lint:
	$(PY) -m ruff check pump_calculator tests

test:
	$(PY) -m pytest

fix:
	$(PY) -m ruff check --fix pump_calculator tests

install:
	$(PY) -m pip install -e ".[dev]"
