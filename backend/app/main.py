import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core import supabase_storage
from app.core.config import settings
from app.core.errors import (
    AppError,
    UnhandledErrorMiddleware,
    app_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.services import upload_service

# uvicorn 只設定 uvicorn.* 的 logger，app.* 的訊息會落到沒有 handler 的
# root logger，被 lastResort handler 以 WARNING 門檻處理——INFO 直接消失、
# 例外訊息也沒有時間戳。這裡補上 root handler，log 才進得了 Render。
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _log_startup_report() -> None:
    """啟動時把「本機正常、線上壞掉」最常見的環境差異寫進 log。

    圖片上傳曾在線上回 500 而本機正常，當時只能推測 Pillow 缺 WebP 編碼器
    卻無從證實。這份報告讓啟動 log 直接回答，不必再猜。
    """
    logger.info(
        "啟動環境自檢：Pillow=%s WebP編碼器=%s Storage已設定=%s bucket=%s CORS來源=%s",
        upload_service.pillow_version(),
        upload_service.webp_encoder_available(),
        supabase_storage.is_configured(),
        settings.supabase_storage_bucket,
        settings.cors_allowed_origins_list,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log_startup_report()
    yield


app = FastAPI(title="WuWaGroup API", version="0.1.0", root_path="", lifespan=lifespan)

# 中介層順序：add_middleware 後加的在**外層**。
# UnhandledErrorMiddleware 必須在 CORSMiddleware 內層，它回的 500 才會
# 被 CORS 加上標頭，所以先加它、後加 CORS。
app.add_middleware(UnhandledErrorMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(api_router, prefix="/api/v1")

# 圖片一律存 Supabase Storage（見 app/core/supabase_storage.py），
# 不再提供本機 /uploads 靜態目錄——本機檔案會隨環境重建而遺失並造成 404。


@app.get("/api/v1/health")
def health_check() -> dict:
    return {"data": {"status": "ok"}}
