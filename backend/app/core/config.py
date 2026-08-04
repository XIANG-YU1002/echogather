from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # str_strip_whitespace：所有字串設定自動去除前後空白。
    # 線上圖片上傳曾整批失敗，原因是 Render 的 SUPABASE_URL 值開頭多了一個
    # tab（貼上時帶進去的），組出 "\thttps://…" 讓 httpx 在解析階段就拋
    # InvalidURL——而它不是 httpx.HTTPError 的子類，逃過攔截變成沒有訊息的
    # 500。環境變數是手動貼上的，前後空白必須在入口就清掉。
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        str_strip_whitespace=True,
    )

    # 應用程式連線：Supabase Transaction pooler（port 6543）。
    # Session pooler（5432）全專案只有 15 個連線，實測 10 台併發就會噴
    # XX_MAXCONN_SESSION；Transaction mode 的連線可在交易之間重用，
    # 才撐得住多人同時操作。
    database_url: str
    # Migration 專用連線：alembic 走 Session pooler（5432）。
    # 建表／改索引這類 DDL 在 transaction mode 下行為較不穩定，而且 migration
    # 是偶爾執行、不需要高併發。留空時退回使用 database_url。
    alembic_database_url: str = ""
    # 測試專用連線（Session pooler 5432）與測試 schema：只有 pytest
    # （tests/_isolation.py）和 scripts/build_test_schema.py 會讀取，
    # 應用程式任何執行路徑都不使用。留空時測試會直接中止，不會退回
    # database_url——這是刻意設計，避免測試打到主要資料庫。
    test_database_url: str = ""
    test_database_schema: str = "wuwa_test"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_allowed_origins: str = "http://localhost:5173"
    max_upload_file_size_bytes: int = 10 * 1024 * 1024
    # 應用程式自己的 log 等級（uvicorn 只設定自己的 logger，不含 app.*）。
    # 線上要查問題時可臨時改成 DEBUG。
    log_level: str = "INFO"

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "media"

    # Email 驗證碼寄送（Gmail SMTP）。
    # smtp_user/smtp_password 未設定時不會真的寄信，改為寫入後端 log 供本機測試。
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "EchoGather"

    # Gmail API（OAuth2）寄信：線上環境用這條路。
    # Render 免費方案封鎖對外 SMTP（實測 587 連線逾時 20 秒，本機同一組憑證卻能登入），
    # 所以線上不能走 smtplib；Gmail API 走 https://gmail.googleapis.com:443，不受影響。
    # 三個值都設定時優先使用 Gmail API，否則退回 SMTP（本機開發照舊）。
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    # 寄件信箱；留空時沿用 smtp_user（必須是授權該 refresh token 的那個 Gmail 帳號）
    gmail_sender: str = ""
    # 信件裡的重設密碼連結要指向前端頁面，部署時需改成正式網址
    frontend_base_url: str = "http://localhost:5173"
    password_reset_ttl_minutes: int = 30
    password_reset_resend_interval_seconds: int = 60
    verification_code_ttl_minutes: int = 10
    verification_code_resend_interval_seconds: int = 60
    verification_code_daily_limit: int = 10
    verification_code_max_attempts: int = 5

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_user and self.smtp_password)

    @property
    def gmail_api_enabled(self) -> bool:
        return bool(
            self.gmail_client_id and self.gmail_client_secret and self.gmail_refresh_token
        )

    @property
    def mail_sender_address(self) -> str:
        """寄件信箱：Gmail API 用 gmail_sender（留空則沿用 smtp_user）。"""
        return self.gmail_sender or self.smtp_user

    @property
    def mail_enabled(self) -> bool:
        return self.gmail_api_enabled or self.smtp_enabled

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
