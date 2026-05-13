"""HTTP Basic auth для admin-эндпоинтов (Phase 33+ closed beta).

Sc.D. audit 2026-05-13 (reference_kns_scd_architecture_prr_2026-05-13.md):
«/admin/uploads/* БЕЗ auth — OWASP A01 + 152-ФЗ ст.19. Closed beta —
HTTP Basic + access log + privacy stub, 1.5 дня».

Дизайн
------
- ``ADMIN_USER`` (default ``admin``) и ``ADMIN_PASS`` (обязателен) — ENV.
- Если ``ADMIN_PASS`` пуст → 503 (fail-closed, лучше чем silent-open).
- ``secrets.compare_digest`` — timing-attack safe.
- Все auth-попытки логируются в logger ``audit.admin`` (для последующего
  сбора в Yandex Cloud Logging / ELK).
"""

from __future__ import annotations

import logging
import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security_basic = HTTPBasic(auto_error=True)
log_audit = logging.getLogger("audit.admin")


def verify_admin(
    creds: HTTPBasicCredentials = Depends(security_basic),  # noqa: B008 — FastAPI DI pattern
) -> str:
    """FastAPI dependency: пускает только если HTTP Basic совпал с ENV.

    Returns
    -------
    str
        Имя пользователя (для аудит-логов).

    Raises
    ------
    HTTPException(503)
        Если ``ADMIN_PASS`` не задана в ENV (fail-closed).
    HTTPException(401)
        Если username/password не совпали. WWW-Authenticate header
        возвращается, чтобы браузер показал диалог.
    """
    expected_user = os.environ.get("ADMIN_USER", "admin")
    expected_pass = os.environ.get("ADMIN_PASS")
    if not expected_pass:
        log_audit.error("ADMIN_PASS not configured — admin endpoints locked")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin auth not configured (set ADMIN_PASS env)",
        )

    is_user_ok = secrets.compare_digest(
        creds.username.encode("utf-8"),
        expected_user.encode("utf-8"),
    )
    is_pass_ok = secrets.compare_digest(
        creds.password.encode("utf-8"),
        expected_pass.encode("utf-8"),
    )
    if not (is_user_ok and is_pass_ok):
        log_audit.warning("Auth fail: user=%s", creds.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    log_audit.info("Auth OK: user=%s", creds.username)
    return creds.username
