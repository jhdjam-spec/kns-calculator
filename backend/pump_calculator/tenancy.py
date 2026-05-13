"""Multi-tenancy stub для будущих дилеров.

Sc.D. Architecture audit 2026-05-13: «multi-tenancy при дилерах» — нужен
зачаток, чтобы при подключении первого дилера не переписывать /import + /admin
endpoints с нуля.

Approach (MVP)
--------------
- ``tenant_id`` берётся из header ``X-Tenant-ID``.
- Если header не задан или значение не в allow-list — fallback на
  ``DEFAULT_TENANT`` (по умолчанию ``servoyug``).
- Каждый /import/parse upload получит ``tenant_id`` в metadata архива.
- /admin/* потом сможет фильтровать список по ``tenant_id``
  (admin одного дилера не видит ТЗ другого).

Future (Phase 34+)
------------------
- JWT с claim ``tenant_id`` + signing key per-tenant (Auth0 / Yandex IAM).
- Row-level security в БД (PostgreSQL RLS) или database-per-tenant.
- Tenant-specific branding (logo, pricing margins, contact).
- Tenant-specific каталог насосов (дилер видит только свой ассортимент).
- Audit log per-tenant (152-ФЗ ст.19 — оператор обработки ПДн).
"""

from __future__ import annotations

import os

from fastapi import Header

# Главный tenant — Серво-Юг (заказчик), всегда доступен.
DEFAULT_TENANT = os.environ.get("DEFAULT_TENANT", "servoyug")

# Allow-list разрешённых tenants. Расширяется при подключении нового дилера.
# Ключ — машинный ID (slug, snake_case, латиница).
# Значение — человекочитаемое имя для UI/логов.
ALLOWED_TENANTS: dict[str, str] = {
    "servoyug": "Серво-Юг (главный)",
    "demo": "Демо-дилер (показательный)",
}


def get_tenant_id(
    x_tenant_id: str | None = Header(  # noqa: B008 — FastAPI DI pattern
        None,
        alias="X-Tenant-ID",
        description="Tenant ID (slug). Например 'servoyug', 'demo'.",
    ),
) -> str:
    """FastAPI dependency: вернуть валидный tenant_id или ``DEFAULT_TENANT``.

    Проверка allow-list — защита от инъекций tenant-имени в имена файлов
    архива (``/inservo_tz_archive/<tenant>/...``) и SQL-injection в будущем.

    Returns
    -------
    str
        Tenant ID из allow-list. Никогда не возвращает None — всегда
        хоть какой-то tenant (для backwards compatibility со старыми
        клиентами без X-Tenant-ID header).
    """
    if x_tenant_id:
        # Нормализуем case + trim, но всегда сверяем с allow-list.
        normalized = x_tenant_id.strip().lower()
        if normalized in ALLOWED_TENANTS:
            return normalized
    return DEFAULT_TENANT


def get_tenant_label(tenant_id: str) -> str:
    """Человекочитаемое имя tenant'а для UI/PDF/email."""
    return ALLOWED_TENANTS.get(tenant_id, tenant_id)


def is_allowed_tenant(tenant_id: str) -> bool:
    """Проверка: tenant_id в allow-list? Для unit-тестов и валидации."""
    return tenant_id in ALLOWED_TENANTS


def list_allowed_tenants() -> list[dict[str, str]]:
    """Список всех tenants (id + label) — для /admin/tenants endpoint."""
    return [{"id": tid, "label": label} for tid, label in ALLOWED_TENANTS.items()]
