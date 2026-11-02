"""审核路由占位：后续实现 /extraction-jobs/{id}/approve 等。"""

from fastapi import APIRouter

router = APIRouter(prefix="/extraction-jobs", tags=["extraction"])
