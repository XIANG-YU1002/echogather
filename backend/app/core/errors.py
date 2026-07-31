import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AppError(Exception):
    """統一的業務錯誤，依 05_API_Design_v2.1 §6 Error Format 輸出。"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )


# pydantic 會把自訂 validator 拋出的訊息包成 "Value error, 實際訊息"，
# 這些字串會直接顯示給使用者，前綴要剝掉。
_PYDANTIC_MESSAGE_PREFIXES = ("Value error, ", "Assertion failed, ")


def _clean_message(message: str) -> str:
    for prefix in _PYDANTIC_MESSAGE_PREFIXES:
        if message.startswith(prefix):
            return message[len(prefix):]
    return message


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    fields: dict[str, list[str]] = {}
    for error in exc.errors():
        loc = [str(part) for part in error["loc"] if part not in ("body", "query", "path")]
        # 沒有對應欄位的錯誤（model_validator 的跨欄位檢查）歸到 "_"，
        # 前端需把這一組顯示為整體錯誤，否則使用者會看不到任何提示。
        field_name = ".".join(loc) if loc else "_"
        # 一個 validator 只能拋一次錯，需要同時回報多項時以換行分隔，這裡拆回多筆
        message = _clean_message(error["msg"])
        fields.setdefault(field_name, []).extend(
            part for part in message.split("\n") if part.strip()
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(
            "VALIDATION_ERROR",
            "輸入資料格式不正確。",
            {"fields": fields},
        ),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # 一定要記 traceback：註冊了 Exception handler 之後，Starlette 的
    # ServerErrorMiddleware 就不會再把例外往上拋，uvicorn 預設的例外記錄
    # 也不會觸發——不在這裡記，線上就完全查不到 500 的原因。
    logger.exception(
        "未處理的例外：%s %s", request.method, request.url.path, exc_info=exc
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("INTERNAL_SERVER_ERROR", "伺服器發生未預期錯誤。"),
    )


class UnhandledErrorMiddleware(BaseHTTPMiddleware):
    """把未處理例外攔在 CORSMiddleware 的內層。

    app.add_exception_handler(Exception, ...) 是交給中介層堆疊**最外層**的
    ServerErrorMiddleware 處理，它產生的回應不會再經過 CORSMiddleware，
    因此 500 回應不帶 CORS 標頭，瀏覽器會把伺服器錯誤誤報成 CORS 錯誤
    （查錯方向會被帶偏，見 docs/目前進度.txt 第 13 批）。

    改在這裡攔下來，回應就會往外經過 CORS。註冊順序見 app/main.py。
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except AppError as exc:
            # 正常情況下 AppError 已由內層的 app_error_handler 處理掉，
            # 這裡只是保險，避免它落進下面的 500 分支。
            return await app_error_handler(request, exc)
        except Exception as exc:
            return await unhandled_error_handler(request, exc)
