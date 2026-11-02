"""统一错误结构与 FastAPI 异常处理器。"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_STATUS_CODE_MAP: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    410: "gone",
    422: "validation_error",
    423: "account_locked",
    429: "too_many_requests",
    503: "service_unavailable",
}


class AppError(Exception):
    """业务错误。统一转换为 code / message / details / trace_id 结构。"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class BadRequestError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, 400, details)


class UnauthorizedError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, 401, details)


class ForbiddenError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, 403, details)


class NotFoundError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, 404, details)


class ConflictError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, 409, details)


def get_trace_id(request: Request) -> str:
    trace_id = getattr(request.state, "trace_id", None)
    if trace_id:
        return str(trace_id)
    settings = getattr(request.app.state, "settings", None)
    header = getattr(settings, "trace_header", "X-Trace-Id")
    return request.headers.get(header) or uuid.uuid4().hex


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None,
    trace_id: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = {
        "code": code,
        "message": message,
        "details": details,
        "trace_id": trace_id,
    }
    return JSONResponse(content=jsonable_encoder(body), status_code=status_code, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            trace_id=get_trace_id(request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "loc": [str(part) for part in error.get("loc", ())],
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
            for error in exc.errors()
        ]
        return _error_response(
            status_code=422,
            code="validation_error",
            message="请求参数校验失败",
            details={"errors": errors},
            trace_id=get_trace_id(request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        code = _STATUS_CODE_MAP.get(exc.status_code, "http_error")
        details: dict[str, Any] | None = None
        default_messages = {
            401: "未认证或登录已失效",
            403: "没有访问权限",
            404: "请求的资源不存在",
            405: "请求方法不允许",
            409: "资源状态冲突",
            422: "请求参数校验失败",
        }
        if isinstance(detail, dict):
            code = str(detail.get("code", code))
            message = str(
                detail.get("message", default_messages.get(exc.status_code, "请求处理失败"))
            )
            raw_details = detail.get("details")
            details = raw_details if isinstance(raw_details, dict) else None
        else:
            message = (
                str(detail)
                if detail
                else default_messages.get(exc.status_code, "请求处理失败")
            )
            if message in {"Not Found", "Method Not Allowed", "Unauthorized", "Forbidden"}:
                message = default_messages.get(exc.status_code, "请求处理失败")
        headers = dict(exc.headers) if exc.headers else None
        return _error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
            details=details,
            trace_id=get_trace_id(request),
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = get_trace_id(request)
        logger.exception("未处理异常 [trace_id=%s] %s", trace_id, request.url.path)
        return _error_response(
            status_code=500,
            code="internal_error",
            message="服务器内部错误",
            details=None,
            trace_id=trace_id,
        )
