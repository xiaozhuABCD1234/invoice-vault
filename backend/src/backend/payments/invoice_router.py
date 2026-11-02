"""发票付款路由占位：后续实现 GET /invoices/{id}/payments。"""

from fastapi import APIRouter

router = APIRouter(prefix="/invoices", tags=["payments"])
