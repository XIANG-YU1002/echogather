"""Email 寄送（Gmail SMTP）與信件版型。

未設定 SMTP 帳號密碼時不會真的寄信，改為把內容寫進後端 log，
讓本機開發不必先申請帳號就能測試完整流程。

信件一律同時提供 HTML 與純文字版本（multipart/alternative）：
不支援 HTML 的信件軟體會退回純文字，不會看到一堆標籤。
HTML 部分刻意使用 table 佈局與 inline style——多數信件軟體
（尤其 Outlook、Gmail）會剝除 <style> 區塊與現代 CSS 版面屬性。
"""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

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
    """寄送信件。寄送失敗時拋出例外，由呼叫端決定如何處理。"""
    if not settings.smtp_enabled:
        logger.warning(
            "SMTP 未設定，未實際寄信。收件人=%s 主旨=%s\n%s",
            to,
            subject,
            text_body,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_user}>"
    message["To"] = to
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

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
