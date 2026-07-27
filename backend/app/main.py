from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import AppError, app_error_handler, unhandled_error_handler, validation_error_handler

app = FastAPI(title="WuWaGroup API", version="0.1.0", root_path="")

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
