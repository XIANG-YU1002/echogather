"""Email 寄送與信件版型。

寄送管道依序擇一（見 send_email）：
  1. Gmail API（OAuth2，走 HTTPS）——**線上環境用這條**。
     Render 免費方案封鎖對外 SMTP：實測 587 連線逾時 20 秒才失敗，而本機用
     同一組憑證 1.8 秒就能登入，證明不是憑證問題而是網路層被擋。
  2. Gmail SMTP（smtplib）——本機開發用，本機沒有封鎖。
  3. 兩者都沒設定時不會真的寄信，改為把內容寫進後端 log，
     讓本機開發不必先申請帳號就能測試完整流程。

信件一律同時提供 HTML 與純文字版本（multipart/alternative）：
不支援 HTML 的信件軟體會退回純文字，不會看到一堆標籤。
HTML 部分刻意使用 table 佈局與 inline style——多數信件軟體
（尤其 Outlook、Gmail）會剝除 <style> 區塊與現代 CSS 版面屬性。
"""

import base64
import logging
import smtplib
import time
from email.message import EmailMessage

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

# access token 有效約一小時，快取起來，不必每封信都多打一次 OAuth
_access_token: str | None = None
_access_token_expires_at: float = 0.0


def _gmail_access_token() -> str:
    """用 refresh token 換 access token（快取至到期前 60 秒）。"""
    global _access_token, _access_token_expires_at
    now = time.time()
    if _access_token and now < _access_token_expires_at:
        return _access_token

    resp = httpx.post(
        _GMAIL_TOKEN_URL,
        data={
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "refresh_token": settings.gmail_refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        # invalid_grant 最常見的原因是 OAuth 同意畫面仍停在「測試中」，
        # 該狀態下 Google 發的 refresh token 只有 7 天有效期。
        raise RuntimeError(
            f"換取 Gmail access token 失敗：{resp.status_code} {resp.text[:300]}"
        )

    data = resp.json()
    _access_token = data["access_token"]
    _access_token_expires_at = now + int(data.get("expires_in", 3600)) - 60
    return _access_token


def _send_via_gmail_api(message: EmailMessage) -> None:
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    resp = httpx.post(
        _GMAIL_SEND_URL,
        headers={"Authorization": f"Bearer {_gmail_access_token()}"},
        json={"raw": raw},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Gmail API 寄信失敗：{resp.status_code} {resp.text[:300]}")

_BRAND = "EchoGather"
_BRAND_SUBTITLE = "鳴潮周邊團購平台"
_PRIMARY = "#4f46e5"
_TEXT = "#1f1f2e"
_MUTED = "#6b7280"
_BORDER = "#e2e2ec"
_PAGE_BG = "#f3f2fd"


def _wrap_html(heading: str, intro: str, body_html: str, footer_note: str) -> str:
    """信件外框：淡紫底、白色卡片、品牌標頭與頁尾。"""
    return f"""\
<!DOCTYPE html>
<html lang="zh-Hant">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:{_PAGE_BG};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:{_PAGE_BG};padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
               style="max-width:520px;background-color:#ffffff;border-radius:16px;
                      border:1px solid {_BORDER};overflow:hidden;">
          <!-- 品牌標頭 -->
          <tr>
            <td align="center" style="padding:28px 32px 8px 32px;">
              <div style="font-family:'Helvetica Neue',Arial,'Microsoft JhengHei',sans-serif;
                          font-size:22px;font-weight:800;color:{_TEXT};letter-spacing:0.5px;">
                {_BRAND}
              </div>
              <div style="font-family:'Helvetica Neue',Arial,'Microsoft JhengHei',sans-serif;
                          font-size:12px;font-weight:600;color:{_PRIMARY};
                          letter-spacing:3px;margin-top:4px;">
                {_BRAND_SUBTITLE}
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 32px 0 32px;">
              <div style="height:1px;background-color:{_BORDER};"></div>
            </td>
          </tr>
          <!-- 內容 -->
          <tr>
            <td style="padding:24px 32px 8px 32px;font-family:'Helvetica Neue',Arial,'Microsoft JhengHei',sans-serif;">
              <h1 style="margin:0 0 12px 0;font-size:20px;font-weight:800;color:{_TEXT};">
                {heading}
              </h1>
              <p style="margin:0;font-size:14px;line-height:1.75;color:{_MUTED};">
                {intro}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px 8px 32px;">
              {body_html}
            </td>
          </tr>
          <!-- 頁尾 -->
          <tr>
            <td style="padding:8px 32px 28px 32px;font-family:'Helvetica Neue',Arial,'Microsoft JhengHei',sans-serif;">
              <div style="height:1px;background-color:{_BORDER};margin-bottom:16px;"></div>
              <p style="margin:0;font-size:12px;line-height:1.7;color:{_MUTED};">
                {footer_note}
              </p>
              <p style="margin:12px 0 0 0;font-size:12px;color:{_MUTED};">
                — {_BRAND}｜{_BRAND_SUBTITLE}
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_email(to: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    """寄送信件。寄送失敗時拋出例外，由呼叫端決定如何處理。

    管道優先序：Gmail API（線上）> SMTP（本機）> 只寫 log。
    """
    if not settings.mail_enabled:
        logger.warning(
            "未設定寄信管道（Gmail API 與 SMTP 皆無），未實際寄信。收件人=%s 主旨=%s\n%s",
            to,
            subject,
            text_body,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.mail_sender_address}>"
    message["To"] = to
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    if settings.gmail_api_enabled:
        _send_via_gmail_api(message)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


def send_verification_code(to: str, code: str, ttl_minutes: int) -> None:
    """註冊用驗證碼信：驗證碼以大字級、寬字距呈現，方便閱讀與複製。"""
    body_html = f"""
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="background-color:{_PAGE_BG};border-radius:12px;
                                            padding:20px 16px;">
                    <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:12px;
                                color:{_MUTED};margin-bottom:8px;">您的註冊驗證碼</div>
                    <div style="font-family:'Courier New',Consolas,monospace;font-size:34px;
                                font-weight:700;color:{_PRIMARY};letter-spacing:8px;">{code}</div>
                  </td>
                </tr>
              </table>
              <p style="margin:16px 0 0 0;font-family:'Helvetica Neue',Arial,'Microsoft JhengHei',sans-serif;
                        font-size:13px;color:{_MUTED};">
                此驗證碼將於 <strong style="color:{_TEXT};">{ttl_minutes} 分鐘</strong>後失效。
              </p>"""

    text_body = (
        "您好，\n\n"
        f"您的 {_BRAND} 註冊驗證碼為：{code}\n\n"
        f"此驗證碼將於 {ttl_minutes} 分鐘後失效，請盡快完成註冊。\n"
        "若這不是您本人的操作，請忽略這封信。\n\n"
        f"— {_BRAND}｜{_BRAND_SUBTITLE}"
    )

    send_email(
        to,
        f"【{_BRAND}】註冊驗證碼",
        text_body,
        _wrap_html(
            "註冊驗證碼",
            "請在註冊頁面輸入以下驗證碼以完成帳號建立。",
            body_html,
            "若這不是您本人的操作，請忽略這封信，您的帳號不會有任何變更。",
        ),
    )


def send_password_reset(to: str, nickname: str, reset_url: str, ttl_minutes: int) -> None:
    """重設密碼信：主要動作是一顆按鈕，另附純文字連結以防按鈕被信件軟體阻擋。"""
    body_html = f"""
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="padding:4px 0 8px 0;">
                    <a href="{reset_url}"
                       style="display:inline-block;background-color:{_PRIMARY};color:#ffffff;
                              font-family:'Helvetica Neue',Arial,'Microsoft JhengHei',sans-serif;
                              font-size:15px;font-weight:700;text-decoration:none;
                              padding:14px 40px;border-radius:10px;">
                      重設我的密碼
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin:18px 0 6px 0;font-family:'Helvetica Neue',Arial,'Microsoft JhengHei',sans-serif;
                        font-size:12px;color:{_MUTED};">
                按鈕無法點擊時，請複製以下連結到瀏覽器開啟：
              </p>
              <p style="margin:0;font-family:'Courier New',Consolas,monospace;font-size:12px;
                        line-height:1.6;color:{_PRIMARY};word-break:break-all;">
                {reset_url}
              </p>
              <p style="margin:18px 0 0 0;font-family:'Helvetica Neue',Arial,'Microsoft JhengHei',sans-serif;
                        font-size:13px;color:{_MUTED};">
                此連結將於 <strong style="color:{_TEXT};">{ttl_minutes} 分鐘</strong>後失效，且僅能使用一次。
              </p>"""

    text_body = (
        f"{nickname} 您好，\n\n"
        f"我們收到重設 {_BRAND} 密碼的請求。請開啟以下連結設定新密碼：\n\n"
        f"{reset_url}\n\n"
        f"此連結將於 {ttl_minutes} 分鐘後失效，且僅能使用一次。\n"
        "若這不是您本人的操作，請忽略這封信，您的密碼不會有任何變更。\n\n"
        f"— {_BRAND}｜{_BRAND_SUBTITLE}"
    )

    send_email(
        to,
        f"【{_BRAND}】重設密碼",
        text_body,
        _wrap_html(
            "重設密碼",
            f"{nickname} 您好，我們收到重設密碼的請求。請點擊下方按鈕設定新密碼。",
            body_html,
            "若這不是您本人的操作，請忽略這封信，您的密碼不會有任何變更。"
            "為了帳號安全，請不要將這封信轉寄給任何人。",
        ),
    )
