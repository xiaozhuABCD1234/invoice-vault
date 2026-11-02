"""FastAPI 应用工厂与 ASGI 入口。"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .api.router import api_router
from .categories.service import seed_default_categories
from .schemas.common import HealthResponse
from .shared.config import Settings, get_settings
from .shared.db import (
    create_engine_for,
    ensure_directories,
    get_session_factory,
    init_db,
    utcnow,
)
from .shared.deps import DbSession
from .shared.errors import AppError, register_exception_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建应用；数据库、上传目录与默认类别在工厂内初始化，便于测试注入。"""

    current_settings = settings or get_settings()
    ensure_directories(current_settings)
    engine = create_engine_for(
        current_settings.database_url, echo=current_settings.sql_echo
    )
    session_factory = get_session_factory(engine)
    init_db(engine, current_settings)
    with session_factory() as db:
        seed_default_categories(db)

    app = FastAPI(
        title=current_settings.app_name,
        version="1.0.0",
        description="发票管理系统 API（FastAPI + SQLite + SQLAlchemy 2）",
    )
    app.state.settings = current_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.initialized_at = utcnow()

    @app.middleware("http")
    async def trace_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        trace_header = current_settings.trace_header
        trace_id = request.headers.get(trace_header) or uuid.uuid4().hex
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers[trace_header] = trace_id
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[current_settings.trace_header],
    )

    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get(
        "/healthz",
        response_model=HealthResponse,
        response_model_exclude_none=True,
        tags=["health"],
        summary="存活检查",
    )
    def healthz() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/readyz", response_model=HealthResponse, tags=["health"], summary="就绪检查")
    def readyz(db: DbSession) -> HealthResponse:
        try:
            db.execute(text("SELECT 1"))
        except Exception as exc:
            raise AppError("not_ready", "数据库未就绪", 503) from exc
        return HealthResponse(status="ready", database="ok")

    return app


app = create_app()
