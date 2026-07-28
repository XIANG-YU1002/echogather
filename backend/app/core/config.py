from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_allowed_origins: str = "http://localhost:5173"
    max_upload_file_size_bytes: int = 10 * 1024 * 1024

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
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
