"""Supabase Storage 上傳工具。

圖片改存 Supabase Storage（雲端），避免本機 uploads 資料夾隨環境重建而遺失。
使用 service_role key 呼叫 Storage REST API，DB 內儲存完整公開網址。
"""

import logging

import httpx

from app.core.config import settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

_bucket_ready = False


def _response_detail(resp: httpx.Response) -> str:
    """Supabase 的錯誤原因都在 body 裡，不記下來就只剩一個無用的狀態碼。"""
    return f"status={resp.status_code} body={resp.text[:500]}"


def _headers(extra: dict | None = None) -> dict:
    key = settings.supabase_service_role_key
    base = {"Authorization": f"Bearer {key}", "apikey": key}
    if extra:
        base.update(extra)
    return base


def is_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def ensure_bucket() -> None:
    """確保 public bucket 存在（冪等，第一次呼叫時建立）。"""
    global _bucket_ready
    if _bucket_ready:
        return
    if not is_configured():
        raise AppError(500, "UPLOAD_STORAGE_NOT_CONFIGURED", "圖片儲存服務尚未設定。")

    bucket = settings.supabase_storage_bucket
    url = settings.supabase_url.rstrip("/")
    try:
        resp = httpx.get(f"{url}/storage/v1/bucket/{bucket}", headers=_headers(), timeout=30)
        if resp.status_code == 200:
            _bucket_ready = True
            return
        # 不存在則建立公開 bucket
        create = httpx.post(
            f"{url}/storage/v1/bucket",
            headers=_headers({"Content-Type": "application/json"}),
            json={"id": bucket, "name": bucket, "public": True},
            timeout=30,
        )
        # 409 = 已存在（併發情況），視為成功
        if create.status_code not in (200, 201, 409):
            logger.error("建立 bucket %s 失敗：%s", bucket, _response_detail(create))
            raise AppError(502, "UPLOAD_STORAGE_ERROR", "圖片儲存服務初始化失敗。")
        _bucket_ready = True
    except AppError:
        raise
    except Exception as exc:
        # httpx.InvalidURL 等例外不是 httpx.HTTPError 的子類，只攔 HTTPError
        # 會讓它變成沒有訊息的 500。
        logger.exception("連線圖片儲存服務失敗：bucket=%s", bucket)
        raise AppError(502, "UPLOAD_STORAGE_ERROR", "無法連線圖片儲存服務。") from exc


def upload_bytes(object_path: str, data: bytes, content_type: str = "image/webp") -> str:
    """上傳位元組並回傳完整公開網址。object_path 例如 product/2026/07/xxx.webp。"""
    ensure_bucket()
    bucket = settings.supabase_storage_bucket
    url = settings.supabase_url.rstrip("/")
    object_path = object_path.lstrip("/")
    try:
        resp = httpx.post(
            f"{url}/storage/v1/object/{bucket}/{object_path}",
            headers=_headers({"Content-Type": content_type, "x-upsert": "true"}),
            content=data,
            timeout=60,
        )
    except Exception as exc:
        logger.exception("上傳圖片失敗：path=%s size=%s", object_path, len(data))
        raise AppError(502, "UPLOAD_STORAGE_ERROR", "圖片上傳失敗，請稍後再試。") from exc

    if resp.status_code not in (200, 201):
        logger.error("上傳圖片被拒：path=%s %s", object_path, _response_detail(resp))
        raise AppError(502, "UPLOAD_STORAGE_ERROR", "圖片上傳失敗，請稍後再試。")

    return f"{url}/storage/v1/object/public/{bucket}/{object_path}"
