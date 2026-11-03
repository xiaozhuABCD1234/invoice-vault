"""挂载全部领域路由。

占位 router 为空；后续智能体替换对应文件即可，无需修改本文件。
review_router 与 invoice_router 的 prefix 在各自文件内定义。
"""

from __future__ import annotations

from fastapi import APIRouter

from ..app_settings.router import router as app_settings_router
from ..audit.router import router as audit_router
from ..auth.router import router as auth_router
from ..categories.router import router as categories_router
from ..dashboard.router import router as dashboard_router
from ..documents.router import router as documents_router
from ..extraction.router import router as extraction_router
from ..invoices.review_router import router as review_router
from ..invoices.router import router as invoices_router
from ..payments.invoice_router import router as invoice_payments_router
from ..payments.router import router as payments_router
from ..reconciliation.router import router as reconciliation_router
from ..reports.router import router as reports_router
from ..users.router import router as users_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(categories_router)
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(extraction_router, tags=["extraction"])
api_router.include_router(review_router)
api_router.include_router(invoices_router, tags=["invoices"])
api_router.include_router(payments_router, tags=["payments"])
api_router.include_router(invoice_payments_router)
api_router.include_router(reconciliation_router, tags=["reconciliation"])
api_router.include_router(reports_router, tags=["reports"])
api_router.include_router(dashboard_router, tags=["dashboard"])
api_router.include_router(audit_router)
api_router.include_router(app_settings_router)
